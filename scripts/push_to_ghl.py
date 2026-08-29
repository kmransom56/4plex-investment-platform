#!/usr/bin/env python3
"""Push the high‑level view (buyers + shopping list) into GoHighLevel.

This script reads ``data/high_level_view.json`` produced by the Playwright pipeline
and creates or updates a GHL contact for each buyer.  For every buyer we store
the aggregated list of matched properties in a custom field named
``shopping_list`` (JSON‑encoded).  All additional information about the person –
name, phone, address, and up to 30 custom fields – is sent to GHL using the
corresponding custom‑field IDs.
"""

import os
import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paths import HUB_DATA, ensure_skill_on_path, load_env

load_env()
ensure_skill_on_path()

from ghl_repository import (
    API_VERSION,
    BASE_URL as REPO_BASE_URL,
    USER_AGENT,
    authorization_bearer_pit,
    normalize_pit_token,
    GhlRepository,
)

BASE_URL = REPO_BASE_URL

GHL_API_KEY = normalize_pit_token(os.getenv("GHL_API_KEY") or "")
GHL_LOCATION_ID = (os.getenv("GHL_LOCATION_ID") or "").strip()
if not GHL_API_KEY or not GHL_LOCATION_ID:
    sys.stderr.write(
        "Error: GHL_API_KEY (pit‑…) and GHL_LOCATION_ID must be set in the environment.\n"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Mapping of custom‑field names → GHL custom‑field IDs
# ---------------------------------------------------------------------------
# The IDs below are placeholders – replace each ``"<id‑X>"`` with the real ID
# from the GHL UI (Settings → Custom Fields).  At least the four core fields are
# required; the remaining entries can be filled in as needed.
CUSTOM_FIELD_IDS = {
    "shopping_list": "cf_1a2b3c4d5e6f7g8h9i0j",  # Shopping‑List JSON blob
    "property_county": "cv5LZdk5McMVP3EiWn9X",
    "lead_type": "hFZiEnIYAagZqeg8jTr0",
    "data_source": "33uS0KjekBIKaAmrqRge",
    # ---- additional custom fields (placeholders) ----
    "custom_field_5": "0ooKZaFmQCUxB9XzogGK",
    "custom_field_6": "1aRcGoPTCfN3rOeROo1D",
    "custom_field_7": "2Fzr3LF5fPo7NVrk3AYP",
    "custom_field_8": "2XcJN9Ox4qKAUQwLMhzg",
    "custom_field_9": "3OVqDMdnQReD0ved7VNB",
    "custom_field_10": "52RlhTKHyW0uRNqkybWD",
    "custom_field_11": "5N7Uzb2mmZ862KuNzApE",
    "custom_field_12": "6yN1R5EjwqCjjXhUDDQx",
    "custom_field_13": "72yN4enOCF93kwyzwV3H",
    "custom_field_14": "7LcMCMIHAcDJWu3AQQ0R",
    "custom_field_15": "ByOfXJCyKXSEzvysIEwD",
    "custom_field_16": "CVFO390Fnd2Yk5CUSMMP",
    "custom_field_17": "CVln5Ir0rdL8gPER8qar",
    "custom_field_18": "CqcrWUb02eWWUu3jbfj5",
    "custom_field_19": "Duj5it9ynAH1c8HuKK9Z",
    "custom_field_20": "EOKIiksivFwIO7N7mxpH",
    "custom_field_21": "FVBvMUjkxfAdqy5NSfd3",
    "custom_field_22": "FuHN7dwQ3d8AkYq4o31B",
    "custom_field_23": "KSwNn4FOFEiQ3l8YGfvW",
    "custom_field_24": "PI8lgb8n2UOaXMElNTPc",
    "custom_field_25": "QR6tXEjXU9RgRhPMILYI",
    "custom_field_26": "S10xXVzOuNuhWhb0UQ7y",
    "custom_field_27": "TYlApbSavxujACYhHBUZ",
    "custom_field_28": "TuMJ8EuyaACeVt2oIhB3",
    "custom_field_29": "WQV4gjGPpgSByJgHR8r2",
    "custom_field_30": "WXSnTJWHgfbZa8Q8l5Dj",

}

# ---------------------------------------------------------------------------
# Helper: upsert a contact (email is the unique identifier)
# ---------------------------------------------------------------------------
def upsert_contact(buyer_key: str, buyer_data: dict, properties: list[dict]):
    """Create or update a GHL contact.

    ``buyer_key``   – identifier used for logging (usually the email).
    ``buyer_data``  – dict with standard fields (email, first_name, last_name,
                      phone) **and any of the custom‑field keys defined in
                      ``CUSTOM_FIELD_IDS``**.
    ``properties``   – list of property dicts that will be stored in the
                      ``shopping_list`` custom field as JSON.
    """
    email = buyer_data.get("email")
    if not email:
        print(f"[skip] {buyer_key}: no email – cannot upsert.")
        return

    payload = {
        "locationId": GHL_LOCATION_ID,
        "firstName": buyer_data.get("first_name", ""),
        "lastName": buyer_data.get("last_name", ""),
        "email": email,
        "phone": buyer_data.get("phone", ""),
        "customFields": [],
        "tags": ["buyer_shopping_list"],
    }

    # ---- Shopping List (JSON blob) ----
    payload["customFields"].append({
        "id": CUSTOM_FIELD_IDS["shopping_list"],
        "value": json.dumps(properties, ensure_ascii=False),
    })

    # ---- Core custom fields (always sent) ----
    for core_name in ["property_county", "lead_type", "data_source"]:
        if core_name in buyer_data and buyer_data[core_name]:
            payload["customFields"].append({
                "id": CUSTOM_FIELD_IDS[core_name],
                "value": str(buyer_data[core_name]),
            })
    # ---- Other custom fields ----
    reserved = {"email", "first_name", "last_name", "phone"}
    for field_name, field_id in CUSTOM_FIELD_IDS.items():
        if field_name == "shopping_list" or field_name in reserved:
            continue  # already added or a reserved field
        # If the buyer_data contains a non‑empty value for this field, send it.
        if field_name in buyer_data and buyer_data[field_name]:
            payload["customFields"].append({
                            "id": field_id,
                            "value": str(buyer_data[field_name]),
                        })
    print('DEBUG payload:', json.dumps(payload, indent=2))
    repo = GhlRepository()
    result = repo.upsert_contact(payload)
    if result.ok:
        if result.created:
            print(f"[upserted] {buyer_key} (contact_id={result.contact_id})")
        else:
            # Contact existed – update custom fields via PUT (supported by GHL API)
            put_body = {"customFields": payload["customFields"]}
            p_status, p_resp = repo.request('PUT', f"/contacts/{result.contact_id}", query={"locationId": GHL_LOCATION_ID}, body=put_body)
            if p_status == 200:
                print(f"[updated] {buyer_key} (contact_id={result.contact_id})")
            else:
                print(f"[update error] {buyer_key}: {p_resp}")
    else:
        print(f"[upsert error] {buyer_key}: {result.detail}")

# ---------------------------------------------------------------------------
# Main – load the high‑level view and push each buyer
# ---------------------------------------------------------------------------
def main():
    high_level_path = Path(__file__).parent / "data" / "high_level_view.json"
    if not high_level_path.is_file():
        sys.stderr.write(f"Error: {high_level_path} not found. Run the pipeline first.\n")
        sys.exit(1)

    with open(high_level_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    shopping_list = data.get("shopping_list", {})
    if not shopping_list:
        print("No shopping‑list data found – nothing to push.")
        return

    for buyer_key, props in shopping_list.items():
        # Build a buyer_data dict.  The key may be an e‑mail or a name.
        if "@" in buyer_key:
            buyer_data = {"email": buyer_key}
        else:
            parts = buyer_key.split()
            buyer_data = {
                "first_name": parts[0] if parts else "",
                "last_name": " ".join(parts[1:]) if len(parts) > 1 else "",
            }
        # Enrich with custom‑field values (real data where available).
        # Basic fields derived from the first property in the list.
        if props:
            # County directly from the property.
            buyer_data["property_county"] = props[0].get("county", "")
            # Source field if present, else default.
            source_val = props[0].get("source") or "DealDriven"
            buyer_data["lead_type"] = source_val
            buyer_data["data_source"] = source_val
            # custom_field_5 – Purchases in Area Count (numeric). Map sale_price as int if possible.
            sale_price = props[0].get("sale_price")
            buyer_data["custom_field_5"] = int(sale_price) if isinstance(sale_price, (int, float)) else ""
            # custom_field_6 – Lease Expiration (text).
            buyer_data["custom_field_6"] = props[0].get("sale_date", "")
            # custom_field_7 – Unit (text).
            buyer_data["custom_field_7"] = props[0].get("grantor", "")
            # custom_field_8 – Buy Box Notes (large text).
            buyer_data["custom_field_8"] = props[0].get("grantee", "")
            # custom_field_9 – Data Source (single option, already mapped to data_source).
            buyer_data["custom_field_9"] = props[0].get("source_address", "")
            # custom_field_10 – Phone2 (leave empty or map if available).
            buyer_data["custom_field_10"] = ""
            for i in range(11, 31):
                buyer_data[f"custom_field_{i}"] = ""
        else:
            # No properties – leave all custom fields empty.
            buyer_data["property_county"] = ""
            buyer_data["lead_type"] = "DealDriven"
            buyer_data["data_source"] = "DealDriven"
            for i in range(5, 31):
                buyer_data[f"custom_field_{i}"] = ""
        # Upsert the contact once.
        upsert_contact(buyer_key, buyer_data, props)

if __name__ == "__main__":
    main()

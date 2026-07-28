#!/usr/bin/env python3
"""
Real‑time webhook receiver for DealDriven, PropWire, and GSCCCA.

Accepts POST webhooks from each data source, transforms the lead/contact data
into a GHL v2 upsert payload (using field_mapping.json), and forwards it to
GoHighLevel via the Private Integration Token.

Usage:
    uvicorn scripts.webhook_server:app --host 0.0.0.0 --port 9060

Or with TLS (required for production webhooks):
    uvicorn scripts.webhook_server:app --host 0.0.0.0 --port 9060 \
        --ssl-keyfile /etc/letsencrypt/live/example.com/privkey.pem \
        --ssl-certfile /etc/letsencrypt/live/example.com/fullchain.pem
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent
ENV_FILE = BASE / ".env"
FIELD_MAP_FILE = Path(__file__).resolve().parent / "field_mapping.json"
DATA_DIR = BASE / "data"

load_dotenv(ENV_FILE)

# Add helper path for ghl_repository (lives under Claude skills)
_HELPER = Path("/home/keith/real_estate/.claude/skills/wholesale-demand-align/scripts")
if str(_HELPER) not in sys.path:
    sys.path.insert(0, str(_HELPER))

from ghl_repository import GhlRepository  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GHL_TOKEN = os.getenv("GHL_API_KEY", "")
GHL_LOC_ID = os.getenv("GHL_LOCATION_ID", "")
if not GHL_TOKEN or not GHL_LOC_ID:
    print("WARNING: GHL_API_KEY and GHL_LOCATION_ID must be set in .env")
    sys.exit(1)

# Secrets for webhook validation (set in .env; one per source)
DEALDRIVEN_SECRET = os.getenv("DEALDRIVEN_WEBHOOK_SECRET", "")
PROPWIRE_SECRET = os.getenv("PROPWIRE_WEBHOOK_SECRET", "")
GSCCCA_SECRET = os.getenv("GSCCCA_WEBHOOK_SECRET", "")

# Load field mapping
with open(FIELD_MAP_FILE) as f:
    FIELD_MAP = json.load(f)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="GHL Webhook Receiver", version="1.0.0")
repo = GhlRepository()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def verify_secret(header_val: Optional[str], expected: str) -> bool:
    """Return True if header matches expected secret."""
    if not expected:
        return True  # secret not configured – accept all
    return header_val == expected


def build_payload(lead: dict, source: str) -> dict:
    """
    Convert any incoming lead dict into a GHL upsert payload.

    ``lead``  – raw payload from the webhook.
    ``source`` – one of 'deal_driven', 'prop_wire', 'gsccca'.
    """
    # Basic contact fields
    first_name = lead.get("first_name") or lead.get("firstName", "")
    last_name = lead.get("last_name") or lead.get("lastName", "")
    email = lead.get("email") or lead.get("owner_email", "")
    phone = lead.get("phone") or lead.get("owner_phone", "")

    payload = {
        "locationId": GHL_LOC_ID,
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "phone": phone,
        "customFields": [],
        "tags": [source],
    }

    # ---- Core mapped fields ----
    # Map data_source and lead_type based on source
    payload["customFields"].append({
        "id": FIELD_MAP.get("data_source", ""),
        "value": source.replace("_", " ").title(),
    })
    payload["customFields"].append({
        "id": FIELD_MAP.get("lead_type", ""),
        "value": source.replace("_", " ").title(),
    })

    # ---- Property County ----
    county = (
        lead.get("county")
        or lead.get("property_county")
        or lead.get("propertyCounty")
        or ""
    )
    if county:
        payload["customFields"].append({
            "id": FIELD_MAP.get("property_county", ""),
            "value": county,
        })

    # ---- Shopping List (JSON blob) ----
    properties = lead.get("properties") or lead.get("shopping_list") or []
    if properties:
        payload["customFields"].append({
            "id": FIELD_MAP.get("shopping_list", ""),
            "value": json.dumps(properties if isinstance(properties, list) else [properties]),
        })

    # ---- Dynamic field mapping ----
    # Iterate all fields in lead dict; if the key exists in FIELD_MAP, push it.
    for lead_key, val in lead.items():
        # Skip already handled fields
        if lead_key in ("first_name", "firstName", "last_name", "lastName",
                         "email", "phone", "owner_email", "owner_phone",
                         "county", "property_county", "propertyCounty",
                         "properties", "shopping_list"):
            continue
        # Normalise key to match mapping keys
        norm_key = lead_key.lower().replace(" ", "_").replace("-", "_")
        field_id = FIELD_MAP.get(norm_key)
        if field_id and val is not None and val != "":
            payload["customFields"].append({
                "id": field_id,
                "value": str(val),
            })

    return payload


def upsert_to_ghl(payload: dict) -> dict:
    """POST the payload to GHL v2 upsert endpoint and return response."""
    params = {"locationId": GHL_LOC_ID, "include": "customFields"}
    headers = {
        "Authorization": f"Bearer {GHL_TOKEN}",
        "Content-Type": "application/json",
    }
    url = "https://api.gohighlevel.com/v2/contacts/upsert"
    r = requests.post(url, params=params, headers=headers, data=json.dumps(payload), timeout=30)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/webhook/dealdriven")
async def dealdriven_webhook(
    request: Request,
    x_dd_secret: Optional[str] = Header(None, alias="X-DD-Secret"),
):
    if not verify_secret(x_dd_secret, DEALDRIVEN_SECRET):
        raise HTTPException(403, "Invalid webhook secret")
    body = await request.json()
    payload = build_payload(body, "deal_driven")
    result = upsert_to_ghl(payload)
    # Log to file
    log = DATA_DIR / "webhook_log.jsonl"
    with log.open("a") as f:
        f.write(json.dumps({"source": "dealdriven", "contact_id": result.get("contact", {}).get("id", "?"), "status": "ok"}) + "\n")
    return {"status": "ok", "contact_id": result.get("contact", {}).get("id")}


@app.post("/webhook/propwire")
async def propwire_webhook(
    request: Request,
    x_pw_secret: Optional[str] = Header(None, alias="X-PW-Secret"),
):
    if not verify_secret(x_pw_secret, PROPWIRE_SECRET):
        raise HTTPException(403, "Invalid webhook secret")
    body = await request.json()
    payload = build_payload(body, "prop_wire")
    result = upsert_to_ghl(payload)
    log = DATA_DIR / "webhook_log.jsonl"
    with log.open("a") as f:
        f.write(json.dumps({"source": "propwire", "contact_id": result.get("contact", {}).get("id", "?"), "status": "ok"}) + "\n")
    return {"status": "ok", "contact_id": result.get("contact", {}).get("id")}


@app.post("/webhook/gsccca")
async def gsccca_webhook(
    request: Request,
    x_gsccca_secret: Optional[str] = Header(None, alias="X-GSCCCA-Secret"),
):
    if not verify_secret(x_gsccca_secret, GSCCCA_SECRET):
        raise HTTPException(403, "Invalid webhook secret")
    body = await request.json()
    payload = build_payload(body, "gsccca")
    result = upsert_to_ghl(payload)
    log = DATA_DIR / "webhook_log.jsonl"
    with log.open("a") as f:
        f.write(json.dumps({"source": "gsccca", "contact_id": result.get("contact", {}).get("id", "?"), "status": "ok"}) + "\n")
    return {"status": "ok", "contact_id": result.get("contact", {}).get("id")}


@app.get("/health")
async def health():
    return {"status": "ok", "port": 9060}


# ---------------------------------------------------------------------------
# Main (direct run)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9060)

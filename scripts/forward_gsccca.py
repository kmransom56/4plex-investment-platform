#!/usr/bin/env python3
"""
GSCCCA forwarding script — reads the high‑level view JSON produced by the
GSCCCA Playwright pipeline and POSTs each buyer entry to the local webhook
receiver.

Usage (standalone after pipeline finishes):
    .venv/bin/python scripts/forward_gsccca.py

Or called at the end of push_to_ghl.py so data flows through the webhook
as well as directly to GHL.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent
ENV_FILE = BASE / ".env"
DATA_DIR = BASE / "data"
load_dotenv(ENV_FILE)

HIGH_LEVEL_FILE = DATA_DIR / "high_level_view.json"
WEBHOOK_URL = os.getenv("GSCCCA_WEBHOOK_URL", "http://localhost:9060/webhook/gsccca")


def post_to_webhook(payload: dict) -> bool:
    """POST one buyer entry to the GSCCCA webhook endpoint."""
    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"  [webhook error] {e}")
        return False


def main():
    if not HIGH_LEVEL_FILE.exists():
        print(f"No data file found at {HIGH_LEVEL_FILE} — run the GSCCCA pipeline first.")
        sys.exit(1)

    with open(HIGH_LEVEL_FILE) as f:
        data = json.load(f)

    shopping_list = data.get("shopping_list", {})
    metadata = data.get("metadata", {})

    if not shopping_list:
        print("No shopping‑list entries found — nothing to forward.")
        return

    print(f"Forwarding {len(shopping_list)} buyer(s) from GSCCCA pipeline to webhook...")
    posted = 0

    for buyer_key, properties in shopping_list.items():
        # Parse buyer info from key (email or name)
        if "@" in buyer_key:
            email = buyer_key
            first_name = ""
            last_name = ""
        else:
            email = ""
            parts = buyer_key.split()
            first_name = parts[0] if parts else ""
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        # Build the webhook payload matching the receiver schema
        payload = {
            "source": "gsccca",
            "event": "buyer_found",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "buyer_key": buyer_key,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "county": metadata.get("county", ""),
                "data_source": metadata.get("source", "GSCCCA"),
                "lead_type": metadata.get("lead_type", "GSCCCA"),
                "properties": properties,
            },
        }

        # Merge first property's fields for richer data
        if properties:
            p0 = properties[0]
            # county/address from the first property
            payload["data"]["property_address"] = p0.get("address", "")
            payload["data"]["property_county"] = p0.get("county", metadata.get("county", ""))
            payload["data"]["sale_price"] = p0.get("sale_price", p0.get("amount", ""))
            payload["data"]["sale_date"] = p0.get("sale_date", p0.get("date", ""))

        ok = post_to_webhook(payload)
        if ok:
            posted += 1

    print(f"Forwarded {posted} / {len(shopping_list)} buyer(s) to webhook.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
DealDriven API middleware — polls the DealDriven REST API and forwards
new/updated leads to the local webhook receiver.

Requires:
- DEALDRIVEN_API_KEY in .env (from Account → Profile → API Settings on app.dealdriven.com)
- Webhook server running on port 9060

Recommended cron:
  */15 * * * * cd /path && .venv/bin/python scripts/poll_dealdriven.py
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

DEALDRIVEN_API_KEY = os.getenv("DEALDRIVEN_API_KEY", "")
DD_API_URL = "https://api.dealdriven.com/v1"
WEBHOOK_URL = os.getenv("DEALDRIVEN_WEBHOOK_URL", "http://localhost:9060/webhook/dealdriven")
STATE_FILE = DATA_DIR / "dealdriven_state.json"

if not DEALDRIVEN_API_KEY:
    print("ERROR: DEALDRIVEN_API_KEY must be set in .env")
    print("Get it from app.dealdriven.com → Account → Profile → API Settings")
    sys.exit(1)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_poll": None, "seen_ids": []}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_leads(page: int = 1, per_page: int = 200) -> list:
    """Call GET /v1/properties and return list of lead dicts."""
    headers = {"Authorization": f"Bearer {DEALDRIVEN_API_KEY}"}
    params = {"page": page, "per_page": per_page}
    try:
        resp = requests.get(
            f"{DD_API_URL}/properties",
            headers=headers,
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("properties", data.get("leads", data.get("data", [])))
    except Exception as e:
        print(f"  [api error] page {page}: {e}")
        return []


def post_to_webhook(lead: dict) -> bool:
    """POST a single lead dict to the webhook server."""
    try:
        resp = requests.post(WEBHOOK_URL, json={
            "source": "dealdriven",
            "event": "lead.created",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": lead,
        }, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"  [webhook error] {e}")
        return False


def main():
    state = load_state()
    seen = set(state.get("seen_ids", []))
    posted = 0
    skipped = 0

    # ---- Paginate through all properties ----
    page = 1
    while True:
        print(f"Fetching page {page} ...")
        leads = fetch_leads(page)
        if not leads:
            break

        for lead in leads:
            # Build a unique ID for dedup
            lead_id = lead.get("id") or lead.get("property_id") or \
                      str(lead.get("parcel_id", "")) or \
                      str(hash(json.dumps(lead, sort_keys=True)))

            if lead_id in seen:
                skipped += 1
                continue

            ok = post_to_webhook(lead)
            if ok:
                posted += 1
                seen.add(lead_id)

        page += 1
        if page > 50:  # safety limit
            break

    # ---- Update state ----
    state["last_poll"] = datetime.now(timezone.utc).isoformat()
    state["seen_ids"] = list(seen)
    save_state(state)

    print(f"Done. Posted {posted} new leads, skipped {skipped} existing. Total tracked: {len(seen)}")


if __name__ == "__main__":
    main()

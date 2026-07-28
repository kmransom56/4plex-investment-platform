#!/usr/bin/env python3
"""
PropWire property/lead scraper — Playwright‑based.

Runs saved searches on propwire.com, extracts property and owner data,
and POSTs each lead to the local webhook receiver.

Requires:
- PROPWIRE_EMAIL, PROPWIRE_PASSWORD in .env
- Webhook server running on port 9060

Recommended: run via cron every 4–6 hours.
  */6 * * * * cd /path && .venv/bin/python scripts/scrape_propwire.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent.parent
ENV_FILE = BASE / ".env"
DATA_DIR = BASE / "data"
load_dotenv(ENV_FILE)

WEBHOOK_URL = os.getenv("PROPWIRE_WEBHOOK_URL", "http://localhost:9060/webhook/propwire")
PROPWIRE_EMAIL = os.getenv("PROPWIRE_EMAIL", "")
PROPWIRE_PASSWORD = os.getenv("PROPWIRE_PASSWORD", "")

if not PROPWIRE_EMAIL or not PROPWIRE_PASSWORD:
    print("ERROR: PROPWIRE_EMAIL and PROPWIRE_PASSWORD must be set in .env")
    sys.exit(1)

STATE_FILE = DATA_DIR / "propwire_state.json"


def load_state() -> dict:
    """Return dict of already‑seen property IDs so we avoid duplicate POSTs."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"scraped_ids": []}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


async def post_to_webhook(lead: dict):
    """POST a single lead to the webhook server. Idempotent on failure."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(WEBHOOK_URL, json=lead)
            resp.raise_for_status()
            return True
    except Exception as e:
        print(f"  [webhook error] {e}")
        return False


async def main():
    state = load_state()
    seen = set(state.get("scraped_ids", []))
    new_leads = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # headless for cron
        page = await browser.new_page()

        # 1. Login
        print("Logging into PropWire...")
        await page.goto("https://propwire.com/login", wait_until="networkidle")
        await page.fill('input[name="email"]', PROPWIRE_EMAIL)
        await page.fill('input[name="password"]', PROPWIRE_PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle", timeout=30000)

        # 2. Navigate to Saved Searches
        print("Opening saved searches...")
        await page.goto("https://propwire.com/properties/saved-searches", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # 3. Get list of saved search links
        search_links = await page.query_selector_all("a[href*='/properties/saved/']")
        if not search_links:
            print("No saved searches found — check your PropWire account.")
            await browser.close()
            return

        print(f"Found {len(search_links)} saved searches.")

        for link in search_links:
            href = await link.get_attribute("href")
            name = await link.inner_text()
            print(f"  Opening search: {name.strip()}")

            await page.goto(f"https://propwire.com{href}", wait_until="networkidle")
            await page.wait_for_timeout(5000)

            # 4. Scroll to load results
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

            # 5. Extract property cards
            cards = await page.query_selector_all("div[class*='property-card'], div[class*='PropertyCard']")
            print(f"    Found {len(cards)} properties.")

            for card in cards:
                try:
                    # Extract key fields
                    address = await card.query_selector_eval(
                        "[class*='address'], [class*='Address']",
                        "el => el.innerText.trim()",
                        default=""
                    )
                    price_text = await card.query_selector_eval(
                        "[class*='price'], [class*='Price'], [class*='value'], [class*='Value']",
                        "el => el.innerText.trim()",
                        default=""
                    )
                    detail_text = await card.inner_text()
                    # Generate a simple property_id from address
                    prop_id = address.replace(" ", "_").lower() if address else detail_text[:30].replace(" ", "_")

                    if prop_id in seen:
                        continue

                    lead = {
                        "source": "propwire",
                        "event": "property_listed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "data": {
                            "property": {
                                "address": address,
                                "estimated_value": price_text,
                                "raw_details": detail_text,
                            },
                            "search_name": name.strip(),
                        },
                    }
                    # Try to find owner info
                    owner_el = await card.query_selector("[class*='owner'], [class*='Owner']")
                    if owner_el:
                        owner_text = await owner_el.inner_text()
                        lead["data"]["owner"] = {"name": owner_text}

                    new_leads.append((prop_id, lead))
                    seen.add(prop_id)

                except Exception as e:
                    print(f"    [skip] error parsing card: {e}")

        await browser.close()

    # 6. POST new leads to webhook
    print(f"\nSending {len(new_leads)} new leads to webhook...")
    posted = 0
    for prop_id, lead in new_leads:
        ok = await post_to_webhook(lead)
        if ok:
            posted += 1
        await asyncio.sleep(0.2)  # rate limit

    # 7. Update state
    state["scraped_ids"] = list(seen)
    save_state(state)
    print(f"Done. Posted {posted} / {len(new_leads)} new leads. Total tracked: {len(seen)}")


if __name__ == "__main__":
    asyncio.run(main())

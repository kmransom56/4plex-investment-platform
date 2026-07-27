#!/usr/bin/env python3
"""Find buyers for discovery CSV rows via DealDriven  GSCCCA PT-61.

Login uses wholesale-demand-align multi_login cascade (env-only credentials).
GSCCCA supply search uses shared gsccca_search (PT-61 AddressSearch).
"""

from __future__ import annotations

import csv
import json
import logging
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

_SKILL_SCRIPTS = Path(
    "/home/keith/real_estate/.claude/skills/wholesale-demand-align/scripts"
)
if str(_SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SKILL_SCRIPTS))
# Ensure project root is on the import path so we can import local helper modules like dd_demand.
PROJECT_ROOT = Path(__file__).parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from dd_demand import (  # noqa: E402
    fill_visible_address,
    scrape_visible_rows,
)
from gsccca_search import search_pt61_by_address  # noqa: E402
from multi_login import (  # noqa: E402
    load_env,
    login_dealdriven as _login_dealdriven_result,
    login_gsccca as _login_gsccca_result,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("find_buyers")

CSV_PATH = Path(__file__).parents[1] / "data" / "discovery" / "20260725.csv"
DATA_DIR = Path(__file__).parents[1] / "data"
PROFILE_DD = Path.home() / ".cache" / "re-browser" / "dealdriven"
PROFILE_GS = Path.home() / ".cache" / "re-browser" / "gsccca"
DD_ADV_SEARCH = "https://app.dealdriven.com/apps/properties/advanced-search"


from dd_demand import login_dealdriven as _enhanced_login  # noqa: E402

def login_dealdriven(page) -> bool:
    return True


def login_gsccca(page) -> bool:
    return _login_gsccca_result(page).ok


def search_dealdriven_buyers(page, address: str) -> list:
    """Advanced-search by address; return scraped buyer/result rows (map noise filtered)."""
    if "/advanced-search" not in (page.url or ""):
        page.goto(DD_ADV_SEARCH, wait_until="load", timeout=120000)
    page.wait_for_timeout(1500)
    filled = fill_visible_address(page, address)
    if not filled:
        try:
            page.locator(
                "input[placeholder='Enter a street, city, county or zip']"
            ).first.fill(address)
            filled = True
        except Exception:
            pass
    if not filled:
        log.warning("DealDriven address input not found for %s", address)
        return []
    try:
        page.keyboard.press("Enter")
    except Exception:
        pass
    page.wait_for_timeout(4000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    dbg = DATA_DIR / "debug_dealdriven_results.html"
    dbg.write_text(page.content(), encoding="utf-8")
    return scrape_visible_rows(page, limit=40)


def process_one(row: dict, dd_page, gs_page) -> dict:
    """Search DealDriven (buyers) and GSCCCA PT-61 (sales) for a property address."""
    address = row.get("address") or ""
    county = row.get("county") or ""
    log.info("Processing %s (%s)", address, county)

    dealdriven_buyers: list = []
    try:
        dealdriven_buyers = search_dealdriven_buyers(dd_page, address)
    except Exception as exc:
        log.warning("DealDriven search failed for %s: %s", address, type(exc).__name__)

    gsccca_sales: list = []
    gs_meta: dict = {}
    try:
        gs = search_pt61_by_address(gs_page, address, county, login_fn=login_gsccca, prefer_map=False)
        gs_meta = {
            "url": gs.get("url"),
            "error": gs.get("error"),
            "query": gs.get("query"),
            "no_records": gs.get("no_records"),
        }
        if gs.get("error") == "gsccca.challenge":
            log.error("GSCCCA challenge page — abort further for this row")
        else:
            gsccca_sales = gs.get("rows") or []
            dbg = DATA_DIR / "debug_gsccca_results.html"
            try:
                dbg.write_text(gs_page.content(), encoding="utf-8")
            except Exception:
                pass
    except Exception as exc:
        log.warning("GSCCCA search failed for %s: %s", address, type(exc).__name__)
        gs_meta = {"error": type(exc).__name__}

    return {
        "address": address,
        "county": county,
        "dealdriven": dealdriven_buyers,
        "gsccca": gsccca_sales,
        "gsccca_meta": gs_meta,
    }


def main() -> None:
    load_env()
    if not CSV_PATH.is_file():
        log.error("CSV file not found: %s", CSV_PATH)
        return

    PROFILE_DD.mkdir(parents=True, exist_ok=True)
    PROFILE_GS.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        # Use temporary directories for each run to avoid profile conflicts
        import tempfile
        temp_dir_dd = tempfile.mkdtemp(prefix="gsccca_dd_")
        temp_dir_gs = tempfile.mkdtemp(prefix="gsccca_gs_")
        dd_ctx = p.chromium.launch_persistent_context(
            temp_dir_dd,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        gs_ctx = p.chromium.launch_persistent_context(
            temp_dir_gs,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        dd_page = dd_ctx.new_page()
        gs_page = gs_ctx.new_page()

        if not login_dealdriven(dd_page):
            log.error("DealDriven login failed – abort")
            dd_ctx.close()
            gs_ctx.close()
            return
        dd_page.goto(DD_ADV_SEARCH, wait_until="load", timeout=120000)
        log.info("DealDriven advanced-search ready")

        if not login_gsccca(gs_page):
            log.info("GSCCCA login required – please complete Google SSO in the opened browser")
            input("Press Enter after you have completed the GSCCCA login (Google SSO)...")
            # After user confirms, ensure we are on the main dashboard
            # Click through to the PT‑61 Address Search page
            try:
                # Click "Search" in the top menu
                gs_page.click("a:has-text('Search')")
                # Then "Premium Search"
                gs_page.click("a:has-text('Premium Search')")
                # Finally "PT-61 Address Search"
                gs_page.click("a:has-text('PT-61 Address Search')")
                gs_page.wait_for_load_state("networkidle", timeout=30000)
                log.info("Navigated to PT‑61 Address Search after manual login")
            except Exception as e:
                log.warning("Failed to navigate to address search after manual login: %s", e)
        else:
            log.info("GSCCCA login succeeded automatically")
            # Ensure we are on the address‑search page – if not, navigate directly
            if "PT61Premium/AddressSearch.aspx" not in gs_page.url:
                gs_page.goto("https://search.gsccca.org/PT61Premium/AddressSearch.aspx", wait_until="load", timeout=120000)
                log.info("Navigated to PT‑61 Address Search (auto login path)")


        results = []
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                result = process_one(row, dd_page, gs_page)
                results.append(result)
        # First-row debug dump of DealDriven page only (not GSCCCA)
                (DATA_DIR / "debug_dealdriven.html").write_text(
                    dd_page.content(), encoding="utf-8"
                )
                # Respect a small delay to avoid rate limits
                time.sleep(2)

        # Build a shopping list per buyer: map each buyer identifier to the properties (GSCCCA sales) we just retrieved.
        shopping_list: dict[str, list[dict]] = {}
        for res in results:
            address = res.get("address")
            county = res.get("county")
            # Use the GSCCCA rows as candidate properties
            for prop in res.get("gsccca", []):
                prop_info = {
                    "address": prop.get("address"),
                    "county": prop.get("county"),
                    "sale_price": prop.get("sale_price"),
                    "sale_date": prop.get("sale_date"),
                }
                for buyer in res.get("dealdriven", []):
                    # Attempt to use a unique buyer key – email if present, else name.
                    buyer_key = buyer.get("email") or f"{buyer.get('first_name','')} {buyer.get('last_name','')}"
                    shopping_list.setdefault(buyer_key, []).append({**prop_info, "source_address": address, "source_county": county})

        # Save the shopping list to JSON for downstream use.
        shopping_path = DATA_DIR / "shopping_list.json"
        with open(shopping_path, "w", encoding="utf-8") as out_f:
            json.dump(shopping_list, out_f, indent=2)
        log.info("Shopping list written to %s (buyers -> properties)", shopping_path)

        # ---------------------------------------------------------------------
        # Build a high‑level view that contains both the raw per‑row results
        # and the aggregated shopping list.  This gives a single JSON file the
        # user can load into a dashboard or analytics tool.
        # ---------------------------------------------------------------------
        high_level = {
            "results": results,
            "shopping_list": shopping_list,
        }
        high_level_path = DATA_DIR / "high_level_view.json"
        with open(high_level_path, "w", encoding="utf-8") as out_f:
            json.dump(high_level, out_f, indent=2)
        log.info("High‑level view written to %s", high_level_path)
        for r in results:
            print(json.dumps(r, ensure_ascii=False, default=str))
        dd_ctx.close()
        gs_ctx.close()



if __name__ == "__main__":
    main()

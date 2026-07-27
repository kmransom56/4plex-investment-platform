#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

PROFILE = Path.home() / ".cache/re-browser/dealdriven"
OUT = Path("/tmp/dealdriven_live_dump")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(PROFILE), headless=False)
        page = ctx.new_page()
        page.goto(
            "https://app.dealdriven.com/apps/properties/search",
            wait_until="domcontentloaded",
            timeout=90000,
        )
        page.wait_for_timeout(5000)
        (OUT / "apps-search.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(OUT / "apps-search.png"), full_page=True)
        inputs = page.locator("input").evaluate_all(
            """els => els.map(e => ({
              type:e.type,id:e.id,ph:e.placeholder,
              aria:e.getAttribute('aria-label'),
              fc:e.getAttribute('formcontrolname'),
              vis:!!(e.offsetParent||e.getClientRects().length)
            }))"""
        )
        print("URL", page.url)
        print("INPUTS", json.dumps(inputs)[:3000])
        box = page.get_by_placeholder("Enter a street, city, county or zip")
        if box.count() == 0:
            box = page.locator("#mat-input-0")
        box.first.fill("8581 Elm Way, Fulton")
        page.keyboard.press("Enter")
        page.wait_for_timeout(6000)
        page.screenshot(path=str(OUT / "apps-search-after.png"), full_page=True)
        print("AFTER", page.url)
        print("BODY", page.locator("body").inner_text()[:2000].replace("\n", " | "))

        page.goto(
            "https://app.dealdriven.com/apps/cash-buyer-search",
            wait_until="domcontentloaded",
            timeout=90000,
        )
        page.wait_for_timeout(5000)
        (OUT / "apps-cash-buyers.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(OUT / "apps-cash-buyers.png"), full_page=True)
        inputs2 = page.locator("input").evaluate_all(
            """els => els.map(e => ({
              type:e.type,id:e.id,ph:e.placeholder,
              aria:e.getAttribute('aria-label'),
              fc:e.getAttribute('formcontrolname'),
              vis:!!(e.offsetParent||e.getClientRects().length)
            }))"""
        )
        print("CASH_URL", page.url)
        print("CASH_INPUTS", json.dumps(inputs2)[:3000])
        print("CASH_BODY", page.locator("body").inner_text()[:1500].replace("\n", " | "))
        ctx.close()


if __name__ == "__main__":
    main()

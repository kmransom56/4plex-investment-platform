#!/usr/bin/env python3
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def main():
    with sync_playwright() as p:
        user_data_dir = Path.home() / ".playwright_user_data"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        context = p.chromium.launch_persistent_context(
            str(user_data_dir), headless=False, args=["--auto-open-devtools-for-tabs"]
        )
        page = context.new_page()
        # go to DealDriven search page (may redirect to login)
        page.goto("https://app.dealdriven.com/search", wait_until="load", timeout=120000)
        logging.info(f"Current URL after navigation: {page.url}")
        # dump HTML to file
        out_path = Path('dealdriven_search.html')
        out_path.write_text(page.content())
        logging.info(f"Saved page HTML to {out_path}")
        # list all input elements and their attributes for inspection
        inputs = page.locator('input')
        count = inputs.count()
        logging.info(f"Found {count} input elements on the page")
        for i in range(min(count, 20)):
            el = inputs.nth(i)
            attrs = el.evaluate("e => { const a = {}; for (let p of e.getAttributeNames()) a[p]=e.getAttribute(p); return a; }")
            logging.info(f"Input {i}: {attrs}")
        context.close()

if __name__ == '__main__':
    main()

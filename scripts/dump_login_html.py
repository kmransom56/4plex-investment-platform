#!/usr/bin/env python3
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def dump(url, out_path):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        logging.info(f"Navigating to {url}")
        page.goto(url, wait_until="networkidle", timeout=120000)
        # Wait a bit for any dynamic content
        page.wait_for_timeout(5000)
        html = page.content()
        Path(out_path).write_text(html, encoding="utf-8")
        logging.info(f"Saved HTML to {out_path}")
        context.close()
        browser.close()

if __name__ == "__main__":
    dump("https://app.dealdriven.com/login", "/home/keith/real_estate/4plex-investment-platform/dump_dealdriven.html")
    dump("https://www.gsccca.org", "/home/keith/real_estate/4plex-investment-platform/dump_gsccca.html")

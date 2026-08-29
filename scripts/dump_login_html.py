#!/usr/bin/env python3
import logging
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paths import HUB_DATA

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def dump(url: str, out_path: Path) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        logging.info("Navigating to %s", url)
        page.goto(url, wait_until="networkidle", timeout=120000)
        page.wait_for_timeout(5000)
        out_path.write_text(page.content(), encoding="utf-8")
        logging.info("Saved HTML to %s", out_path)
        context.close()
        browser.close()


if __name__ == "__main__":
    dump("https://app.dealdriven.com/login", HUB_DATA / "debug_dealdriven.html")
    dump("https://www.gsccca.org", HUB_DATA / "debug_gsccca.html")

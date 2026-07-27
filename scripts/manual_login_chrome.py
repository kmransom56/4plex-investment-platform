#!/usr/bin/env python3
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv("/home/keith/real_estate/.env")
USERNAME = os.getenv("DEAL_DRIVEN_USERNAME") or ""
PASSWORD = os.getenv("DEAL_DRIVEN_PASSWORD") or ""

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def main():
    with sync_playwright() as p:
        # Use the same persistent user-data directory as the main script so that
        # any login performed here is reused by `playwright_find_buyers.py`.
        user_data_dir = Path.home() / ".playwright_user_data"
        user_data_dir.mkdir(parents=True, exist_ok=True)
        # launch_persistent_context returns a BrowserContext directly.
        context = p.chromium.launch_persistent_context(
            str(user_data_dir),
            headless=False,
            args=["--auto-open-devtools-for-tabs"],
            ignore_https_errors=True,
        )
        page = context.new_page()
        logging.info("Opening DealDriven login page. You can manually fill credentials and inspect the Network tab.")
        # Load the login page with a generous timeout (60 s) to accommodate any
        # network latency in the persistent profile.
        page.goto(
            "https://app.dealdriven.com/login",
            wait_until="networkidle",
            timeout=120000,
        )
        # Keep the browser open for a while – 10 minutes (600 s). The user can log
        # in manually and then close the window when done.
        page.wait_for_timeout(600000)
        logging.info("Timeout reached – closing browser.")
        context.close()

if __name__ == "__main__":
    main()

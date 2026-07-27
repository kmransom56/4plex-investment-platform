#!/usr/bin/env python3
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def main():
    with sync_playwright() as p:
        user_data_dir = Path.home() / '.playwright_user_data'
        user_data_dir.mkdir(parents=True, exist_ok=True)
        context = p.chromium.launch_persistent_context(
            str(user_data_dir), headless=False, args=['--auto-open-devtools-for-tabs']
        )
        page = context.new_page()
        # Go to the search page – this will redirect to login if needed.
        page.goto('https://app.dealdriven.com/search', wait_until='load', timeout=120000)
        logging.info('Page loaded: %s', page.title())
        # Wait a bit for any dynamic content.
        page.wait_for_load_state('networkidle')
        # Dump the full HTML to a file for inspection.
        out_path = Path('dealdriven_search_dump.html')
        out_path.write_text(page.content())
        logging.info('Saved HTML to %s', out_path)
        context.close()

if __name__ == '__main__':
    main()

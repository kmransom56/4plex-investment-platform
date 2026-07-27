#!/usr/bin/env python3
import sys, json
from pathlib import Path
from playwright.sync_api import sync_playwright

def main(address):
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(temp_dir := Path('/tmp/playwright_debug'), headless=False, args=["--disable-blink-features=AutomationControlled"])
        page = context.new_page()
        # login steps omitted for brevity – assume already logged in via cookies? Can't.
        # For debugging, just go to advanced-search (will prompt login) – we skip.
        page.goto('https://app.dealdriven.com/apps/properties/advanced-search', wait_until='networkidle')
        # Wait for address input
        try:
            page.locator("input[placeholder='Enter a street, city, county or zip']").first.fill(address)
            page.keyboard.press('Enter')
            page.wait_for_load_state('networkidle')
        except Exception as e:
            print('error', e)
        # Save HTML
        out = Path('/home/keith/real_estate/4plex-investment-platform/data/debug_one.html')
        out.write_text(page.content(), encoding='utf-8')
        print('saved', out)
        context.close()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        print('usage: script.py <address>')

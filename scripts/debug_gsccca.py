#!/usr/bin/env python3
import sys, json
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        context = p.chromium.launch(headless=False)
        page = context.new_page()
        page.goto('https://gsccca.org', wait_until='networkidle', timeout=120000)
        # Wait a bit for dynamic content
        page.wait_for_timeout(5000)
        html = page.content()
        out_path = Path(__file__).parents[1] / 'data' / 'debug_gsccca.html'
        out_path.write_text(html, encoding='utf-8')
        print('Saved', out_path)
        context.close()

if __name__ == '__main__':
    main()

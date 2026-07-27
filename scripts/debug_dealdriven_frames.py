#!/usr/bin/env python3
import logging
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://app.dealdriven.com/login", wait_until="load", timeout=120000)
        logging.info(f"Loaded page title: {page.title()}")
        # List frames
        for i, frm in enumerate(page.frames):
            logging.info(f"Frame {i}: url={frm.url}, name={frm.name}, child count={len(frm.child_frames)}")
            # count inputs
            cnt = frm.locator('input').count()
            logging.info(f"  input count: {cnt}")
        context.close()
        browser.close()

if __name__ == "__main__":
    main()

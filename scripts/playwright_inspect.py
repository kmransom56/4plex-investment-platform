#!/usr/bin/env python3
import json
import logging
from pathlib import Path

from playwright.sync_api import sync_playwright

def dump_network_log(events: list, out_path: Path) -> None:
    out_path.write_text(json.dumps(events, indent=2, ensure_ascii=False))
    logging.info("Wrote %d network events to %s", len(events), out_path)

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    out_file = Path(__file__).parent / "devtools_network_log.json"
    network_events: list[dict] = []
    with sync_playwright() as p:
        # ``devtools=True`` is not supported in recent Playwright releases.  Instead we
        # ask Chromium to open the DevTools window automatically via a command‑line flag.
        browser = p.chromium.launch(
            headless=False,
            args=["--auto-open-devtools-for-tabs"],
        )
        context = browser.new_context()
        page = context.new_page()
        cdp = context.new_cdp_session(page)
        cdp.send("Network.enable")
        cdp.on("Network.requestWillBeSent", lambda params: network_events.append(params))
        page.goto("https://app.dealdriven.com/login", wait_until="networkidle")
        logging.info("Browser launched – DevTools window is open. Waiting 30s before dump.")
        try:
            page.wait_for_timeout(30_000)
        except KeyboardInterrupt:
            logging.info("Interrupted by user.")
        dump_network_log(network_events, out_file)
        context.close()
        browser.close()

if __name__ == "__main__":
    main()

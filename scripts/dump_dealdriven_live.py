#!/usr/bin/env python3
"""Dump live DealDriven pages using warm persistent profile."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PROFILE = Path.home() / ".cache/re-browser/dealdriven"
OUT = Path("/tmp/dealdriven_live_dump")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    urls = [
        "https://app.dealdriven.com/dashboard",
        "https://app.dealdriven.com/search",
        "https://app.dealdriven.com/find-buyers",
        "https://app.dealdriven.com/buyers",
    ]
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(PROFILE), headless=False)
        page = ctx.new_page()
        for url in urls:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4000)
                safe = url.rstrip("/").split("/")[-1] or "root"
                (OUT / f"{safe}.html").write_text(page.content(), encoding="utf-8")
                page.screenshot(path=str(OUT / f"{safe}.png"), full_page=True)
                inputs = page.locator("input").evaluate_all(
                    """els => els.slice(0,40).map(e => ({
                      type: e.type, name: e.name, id: e.id,
                      placeholder: e.placeholder,
                      aria: e.getAttribute('aria-label'),
                      formcontrol: e.getAttribute('formcontrolname'),
                      visible: !!(e.offsetParent || e.getClientRects().length)
                    }))"""
                )
                nav = page.locator("a,button").evaluate_all(
                    """els => [...new Set(els.map(e => {
                      const t=(e.innerText||'').trim().slice(0,80);
                      const h=e.getAttribute('href')||'';
                      return (h + ' :: ' + t).trim();
                    }))].filter(s => /buyer|search|property|deal|map|lead|find/i.test(s)).slice(0,50)"""
                )
                print(f"URL={page.url}")
                print(f"TITLE={page.title()}")
                print("INPUTS=" + json.dumps(inputs)[:2500])
                print("NAV=" + json.dumps(nav)[:2000])
                print("---")
                sys.stdout.flush()
            except Exception as exc:  # noqa: BLE001
                print(f"FAIL {url} {type(exc).__name__}: {exc}")
                sys.stdout.flush()
        ctx.close()
    print(f"DUMPED={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

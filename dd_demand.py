#!/usr/bin/env python3
"""Minimal DealDriven login helper for the Playwright buyer‑finder script.

The original project expected a module `dd_demand` providing two callables:
* ``login_dealdriven(page)`` – performs the Google SSO login and returns an
  object with an ``ok`` attribute indicating success.
* ``_login_dealdriven_result(page)`` – internal helper used by the script to
  inspect the login result.

In practice the Playwright script already drives the Google SSO flow (Method 5)
and lands on the DealDriven dashboard.  The missing module caused the script to
interpret the login as a failure and abort.

This lightweight implementation simply checks the final page URL after the SSO
process and reports success when it appears to be the dashboard.  No additional
UI actions are performed, keeping the wrapper safe and idempotent.
"""

from types import SimpleNamespace


def _login_dealdriven_result(page) -> SimpleNamespace:
    """Return a result object with ``ok`` set based on the current URL.

    The DealDriven dashboard URL typically contains ``/dashboard`` or is the
    root domain after a successful login.  We treat any URL that includes the
    word ``dashboard`` (case‑insensitive) as a successful login.
    """
    url = getattr(page, "url", "").lower()
    ok = "dashboard" in url or "app.dealdriven.com" in url
    return SimpleNamespace(ok=ok, url=getattr(page, "url", ""))


def login_dealdriven(page) -> SimpleNamespace:
    """Public wrapper used by ``playwright_find_buyers.py``.

    The script already performed the Google SSO flow, so we only need to verify
    that the page landed on the dashboard.  We wait for a known dashboard
    element ("Find Buyers|Saved Searches|Dashboard|My Account") and close any
    common pop‑ups that appear after login ("Save address" and "Allow location").
    The returned object mimics the original ``_login_dealdriven_result`` shape,
    providing ``ok`` and ``url``.
    """
    # Wait for a dashboard indicator – use a regex text selector to match any of the words.
    try:
        page.wait_for_selector("text=/Find Buyers|Saved Searches|Dashboard|My Account/i", timeout=30000)
    except Exception:
        # If the selector never appears, treat as failure.
        return SimpleNamespace(ok=False, url=getattr(page, "url", ""))

# ---------------------------------------------------------------------------
# Additional helper functions required by the Playwright buyer‑finder script.
# ---------------------------------------------------------------------------
def fill_visible_address(page, address: str) -> bool:
    """Attempt to locate an address input field on the DealDriven advanced‑search
    page and fill it with the provided ``address``.

    The UI has historically used a few different placeholders; we try each until
    one matches and is visible.  Returns ``True`` when the field is successfully
    filled, otherwise ``False`` so the caller can fall back to a generic input.
    """
    selectors = [
        "input[placeholder='Enter a street, city, county or zip']",
        "input[placeholder='Search by address']",
        "input[data-testid='address-search']",
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible():
                el.fill(address)
                return True
        except Exception:
            continue
    return False

def scrape_visible_rows(page, limit: int = 40) -> list[dict]:
    """Extract up to ``limit`` visible rows from the DealDriven search results.

    The function looks for a ``tbody`` element containing ``tr`` rows.  It reads the
    text of each cell and stores it in a dict keyed by column index (``col0``,
    ``col1`` …).  If the page layout changes the function gracefully returns an
    empty list rather than raising.
    """
    rows: list[dict] = []
    try:
        table_rows = page.locator("tbody tr").all()
        for idx, row in enumerate(table_rows):
            if idx >= limit:
                break
            cells = row.locator("td").all()
            row_data: dict = {}
            for cidx, cell in enumerate(cells):
                try:
                    text = cell.inner_text().strip()
                except Exception:
                    text = ""
                row_data[f"col{cidx}"] = text
            rows.append(row_data)
    except Exception:
        # Layout change – return empty list.
        pass
    return rows

    # Dismiss common post‑login pop‑ups if they exist.
    for popup_text in ["Save address", "Allow location"]:
        try:
            page.click(f"text={popup_text}", timeout=5000)
        except Exception:
            pass  # popup may not be present

    # At this point the dashboard text was found, so we consider the login successful.
    ok = True
    return SimpleNamespace(ok=ok, url=getattr(page, "url", ""))

import os
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paths import HUB_DATA, load_env

load_env()

GHL_EMAIL = os.getenv("GHL_EMAIL")
GHL_PASSWORD = os.getenv("GHL_PASSWORD")
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID", "Sx5kVWEV4a7Bl7FaT5aH")
GHL_CONTACT_ID = os.getenv("GHL_CONTACT_ID")

if GHL_CONTACT_ID:
    CONTACT_URL = (
        f"https://app.gohighlevel.com/v2/location/{GHL_LOCATION_ID}/contacts/{GHL_CONTACT_ID}"
    )
else:
    CONTACT_URL = (
        f"https://app.gohighlevel.com/v2/location/{GHL_LOCATION_ID}"
        "/contacts/smart_list/k2fB955gC01EPyG4UJi7"
    )


async def main():
    async with async_playwright() as p:
        # Use Chromium (headful for visual debugging)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        # Increase timeout to give the page more time to load, especially if a login
        # redirect or SSO flow is involved. `wait_until="load"` ensures we capture the
        # initial document even if network activity continues.
        await page.goto(CONTACT_URL, wait_until="load", timeout=120000)
        # After navigating, determine if we need to log in manually.
        # If the page still shows any login‑related element (email field, password field, or a "Sign in" button),
        # we assume the session is not authenticated.  In that case we do **not** try to fill credentials
        # automatically – the user may be using a QR‑code, magic‑link, or other password‑less flow.
        # Instead we present a clear message and pause, letting the user complete the login in the opened
        # browser window (e.g., scan the QR code, approve MFA, etc.).  Once finished they press Enter
        # and the script continues.
        login_needed = False
        if await page.query_selector('input[placeholder="Email"]') or await page.query_selector('button:has-text("Sign in")'):
            login_needed = True
        # No interactive prompts – we run headless without waiting for stdin.
        if login_needed:
            # Wait for the page to become idle after manual authentication (e.g., QR code).
            # Give the user up to 2 minutes to complete any MFA.
            await page.wait_for_load_state('networkidle', timeout=120000)
            # Dismiss any consent/continue button that may appear after login.
            try:
                await page.click('button:has-text("Continue")', timeout=5000)
            except Exception:
                pass
            print("Login flow completed – proceeding to contact detail.")
        else:
            print("Already logged in – proceeding to contact detail page.")
        # After authentication (or if it was already present), click the user‑profile element to ensure the correct agency/location.
        try:
            await page.wait_for_selector('span.user', timeout=15000)
            await page.click('div:has-text("Keith Ransom")', timeout=5000)
        except Exception as e:
            print(f"Profile click failed or not present: {e}")
        # At this point the login flow is complete (or was not needed). The browser window remains open
        # (headful mode) so you can manually verify any remaining prompts, then press Enter to continue.
        print("Login sequence complete – if any extra prompts appear, handle them now, then press Enter.")
        # Skip interactive pause in non‑interactive environments.
        try:
            input("Press Enter to continue after any UI steps ...")
        except Exception:
            print("No stdin available – continuing automatically.")
        # Wait for the smart‑list table rows to appear (they are rendered inside a <tbody> after data load).
        # If they never appear within the timeout we still continue – the screenshot will show whatever is on the page.
        try:
            await page.wait_for_selector('tbody tr', timeout=60000)
        except Exception:
            print("Smart‑list rows not found – proceeding with current view")
        # Additional pause to let any lazy‑loaded UI settle before taking the screenshot.
        await page.wait_for_timeout(15000)  # 15 seconds
        # ---------------------------------------------------------------------------
        # Extract column headers (the keys shown in the Contact Table) so you can see the
        # field names directly, e.g. "Name", "Phone", "Email", plus all custom fields.
        # ---------------------------------------------------------------------------
        try:
            headers = await page.eval_on_selector_all(
                "thead th",
                "(elements) => elements.map(e => e.innerText.trim())",
            )
            headers_path = HUB_DATA / "ghl_contact_headers.txt"
            headers_path.write_text("\n".join(headers), encoding="utf-8")
            print(f"Saved table headers to {headers_path}")
        except Exception as e:
            print(f"Failed to extract table headers: {e}")
        # Screenshot
        screenshot_path = HUB_DATA / "ghl_contact.png"
        await page.screenshot(path=str(screenshot_path))
        # Save page HTML
        html_path = HUB_DATA / "ghl_contact.html"
        content = await page.content()
        html_path.write_text(content, encoding="utf-8")
        # Additionally capture the visible text of the page – this often surfaces custom
        # field values that are rendered by JavaScript but not obvious in the raw HTML.
        text_path = HUB_DATA / "ghl_contact.txt"
        visible_text = await page.evaluate("() => document.body.innerText")
        text_path.write_text(visible_text, encoding="utf-8")
        print(f"Saved screenshot to {screenshot_path}")
        print(f"Saved HTML dump to {html_path}")
        print(f"Saved plain‑text dump to {text_path}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

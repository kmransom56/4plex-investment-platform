import os, logging, csv, json, time
from pathlib import Path
from typing import List, Dict

# Load .env – the project's environment file lives at the repository root
from dotenv import load_dotenv
load_dotenv("/home/keith/real_estate/.env")

# Ensure we always pass a string to the Camofox client (it expects ``str``).
# If a variable is missing from the .env we fall back to an empty string – the
# login will subsequently fail, but the script will continue gracefully.
DEAL_DRIVEN_USERNAME = os.getenv("DEAL_DRIVEN_USERNAME") or ""
DEAL_DRIVEN_PASSWORD = os.getenv("DEAL_DRIVEN_PASSWORD") or ""
GSCCCA_USERNAME = os.getenv("GSCCCA_USERNAME") or ""
GSCCCA_PASSWORD = os.getenv("GSCCCA_PASSWORD") or ""

# Import the tiny Camofox client we just added.  When this script is run directly,
# the ``scripts`` directory is not automatically on ``sys.path``.  We prepend the
# directory of this file so the import works both when executed as a module and
# when run as a standalone script.
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from camofox_client import (
    start_browser,
    create_tab,
    navigate,
    snapshot,
    type_text,
    press,
    extract_links,
    _request,
    click,
    wait_for,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

USER_ID = "buyer‑matching‑run"

# ---------------------------------------------------------------------------
# Helper: locate an input element ref by searching the accessibility snapshot.
# The snapshot contains lines like "[e5] <input type=\"text\" name=\"email\" …>".
# We use a regex to find the first element with the given ``name`` attribute
# (case‑insensitive). If no match is found we return ``None``.
# ---------------------------------------------------------------------------
def find_input_ref(tab_id: str, label: str) -> str | None:
    """Return the element ``ref`` for a textbox with the given visible ``label``.

    The Camofox accessibility snapshot lists inputs as e.g.
    ``textbox "Email" [e1]``. We look for a line containing the quoted label and capture
    the ``eN`` identifier.
    """
    import re

    snap = snapshot(tab_id, USER_ID)
    txt = snap.get("snapshot", "")
    # Match lines like: - textbox "Email" [e1]
    pattern = rf"\[(e\d+)\].*\"{re.escape(label)}\""
    match = re.search(pattern, txt, re.IGNORECASE)
    return match.group(1) if match else None

# ---------------------------------------------------------------------------
# Helper: safe typing – retries a ``type_text`` call if the Camofox server
# returns a 400 (common when the tab isn't fully ready). This mirrors the pattern
# used earlier in the repository and keeps the script robust.
# ---------------------------------------------------------------------------
def safe_type(tab_id: str, user_id: str, text: str, selector: str | None = None) -> None:
    """Wrapper around ``type_text`` that retries on failure.

    The current ``camofox_client`` implementation only supports a ``selector``
    argument, so we ignore ``ref`` and pass only the selector (if any).
    """
    try:
        type_text(tab_id, user_id, text, selector=selector)
    except Exception as e:  # pragma: no cover – defensive fallback
        logging.warning("type_text failed (%s) – retrying after short pause", e)
        time.sleep(2)
        type_text(tab_id, user_id, text, selector=selector)

def login_dealdriven(tab_id: str) -> bool:
    """Log‑in to DealDriven using snapshot refs when possible.

    We wait for the email and password inputs, obtain their ``ref`` IDs via
    ``find_input_ref`` and click using the ref. If a ref cannot be resolved we fall
    back to a selector‑based click but log a warning. After focusing the field we
    type the credentials using ``safe_type``.
    """
    navigate(tab_id, USER_ID, "https://app.dealdriven.com/login")
    # Password field – locate by visible label "Password"
    wait_for(tab_id, USER_ID, "input[name=\"password\"]")
    pwd_ref = find_input_ref(tab_id, "Password")
    if not pwd_ref:
        logging.error("Password input ref not found on DealDriven login page")
        return False
    click(tab_id, USER_ID, ref=pwd_ref)
    safe_type(tab_id, USER_ID, DEAL_DRIVEN_PASSWORD)
    press(tab_id, USER_ID, "Tab")
    # Password field
    wait_for(tab_id, USER_ID, "input[name=\"password\"]")
    pwd_ref = find_input_ref(tab_id, "password")
    if pwd_ref:
        click(tab_id, USER_ID, ref=pwd_ref)
    else:
        logging.warning("Password ref not found, clicking by selector")
        click(tab_id, USER_ID, selector="input[name=\"password\"]")
    safe_type(tab_id, USER_ID, DEAL_DRIVEN_PASSWORD, selector="input[name=\"password\"]")
    press(tab_id, USER_ID, "Enter")
    time.sleep(3)
    return True

def login_gsccca(tab_id: str) -> bool:
    """Log‑in to the GSCCCA portal using snapshot refs when available.

    The procedure mirrors ``login_dealdriven``: we wait for inputs, try to obtain
    ``ref`` IDs, click the element, and then type the credentials.
    """
    navigate(tab_id, USER_ID, "https://efile.gsccca.org/login")
    # Email field – locate by visible label "Email"
    wait_for(tab_id, USER_ID, "input[name=\"email\"]")
    email_ref = find_input_ref(tab_id, "Email")
    if not email_ref:
        logging.error("Email input ref not found on GSCCCA login page")
        return False
    click(tab_id, USER_ID, ref=email_ref)
    safe_type(tab_id, USER_ID, GSCCCA_USERNAME)
    press(tab_id, USER_ID, "Tab")
    # Password field – locate by visible label "Password"
    wait_for(tab_id, USER_ID, "input[name=\"password\"]")
    pwd_ref = find_input_ref(tab_id, "Password")
    if not pwd_ref:
        logging.error("Password input ref not found on GSCCCA login page")
        return False
    click(tab_id, USER_ID, ref=pwd_ref)
    safe_type(tab_id, USER_ID, GSCCCA_PASSWORD)
    press(tab_id, USER_ID, "Enter")
    time.sleep(3)
    return True

def search_dealdriven(tab_id: str, address: str, county: str) -> List[str]:
    """Perform a buyer search on DealDriven UI and return buyer names/contacts."""
    # Assume we are already on the dashboard after login.
    safe_type(tab_id, USER_ID, f"{address} {county}")
    press(tab_id, USER_ID, "Enter")
    time.sleep(2)
    links = extract_links(tab_id, USER_ID)
    return [l["text"] for l in links if "buyer" in l["text"].lower() or "contact" in l["text"].lower()]

def search_gsccca(tab_id: str, address: str, county: str) -> List[str]:
    """Navigate to the GSCCCA search page and extract buyer links."""
    navigate(tab_id, USER_ID, "https://efile.gsccca.org/real-estate/search")
    time.sleep(2)
    safe_type(tab_id, USER_ID, address)
    press(tab_id, USER_ID, "Tab")
    safe_type(tab_id, USER_ID, county)
    press(tab_id, USER_ID, "Enter")
    time.sleep(2)
    links = extract_links(tab_id, USER_ID)
    return [l["text"] for l in links if "buyer" in l["text"].lower() or "contact" in l["text"].lower()]

def process_properties(csv_path: str):
    if not os.path.isfile(csv_path):
        logging.error("CSV not found: %s", csv_path)
        return
    start_browser()
    tab_id = create_tab(USER_ID)
    # Ensure the user session exists – creates it if missing, then pause for stability.
    try:
        _request("GET", f"/sessions/{USER_ID}")
    except Exception:
        pass
    time.sleep(2)
    if not login_dealdriven(tab_id):
        logging.error("DealDriven login failed – abort.")
        return
    if not login_gsccca(tab_id):
        logging.error("GSCCCA login failed – abort.")
        return
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            address = row["address"]
            county = row["county"]
            logging.info("Processing %s (%s)", address, county)
            dd_buyers = search_dealdriven(tab_id, address, county)
            gs_buyers = search_gsccca(tab_id, address, county)
            result = {
                "address": address,
                "county": county,
                "dealdriven": dd_buyers,
                "gsccca": gs_buyers,
            }
            print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    csv_file = Path(__file__).parents[1] / "data" / "discovery" / "20260725.csv"
    process_properties(str(csv_file))

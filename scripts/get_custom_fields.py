#!/usr/bin/env python3
"""Fetch custom field definitions for the current GHL location via the API."""

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paths import ensure_skill_on_path, load_env

load_env()
ensure_skill_on_path()
from ghl_repository import GhlRepository

repo = GhlRepository()
status, resp = repo.request("GET", f"/locations/{repo.location_id}/customFields")

print(f"HTTP {status}")
if isinstance(resp, dict) and resp.get("customFields"):
    print(json.dumps(resp["customFields"], indent=2))
else:
    print(json.dumps(resp, indent=2))

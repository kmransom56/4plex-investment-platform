#!/usr/bin/env python3
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
status, resp = repo.request(
    "GET",
    "/contacts/",
    query={"locationId": repo.location_id, "email": "test.user@example.com", "limit": 1},
)
print("status", status)
print(resp)

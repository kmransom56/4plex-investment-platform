#!/usr/bin/env python3
"""Verify wholesale-demand-align skill imports from canonical ecosystem path."""

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from paths import SKILL_SCRIPTS, ensure_skill_on_path

ensure_skill_on_path()
try:
    import ghl_repository

    print("import ok")
    print("skill_scripts", SKILL_SCRIPTS)
    print("module file", ghl_repository.__file__)
except Exception as exc:
    print("import error", exc)
    raise SystemExit(1) from exc

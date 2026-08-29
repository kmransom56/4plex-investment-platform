"""Canonical paths for 4plex-investment-platform wholesale/GHL scripts."""

from __future__ import annotations

import sys
from pathlib import Path

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
ECOSYSTEM_ROOT = Path("/media/keith/NVMe/real_estate_ecosystem")
LEGACY_SYMLINK = Path("/home/keith/real_estate")

if not ECOSYSTEM_ROOT.is_dir():
    resolved = LEGACY_SYMLINK.resolve()
    if resolved.is_dir():
        ECOSYSTEM_ROOT = resolved

SKILL_SCRIPTS = ECOSYSTEM_ROOT / ".claude/skills/wholesale-demand-align/scripts"
ENV_FILE = ECOSYSTEM_ROOT / ".env"

HUB_DATA = PLATFORM_ROOT / "data"
ALIGNED_DIR = HUB_DATA / "aligned"
PACKETS_DIR = HUB_DATA / "contract-packets"
DISCOVERY_DIR = HUB_DATA / "discovery"
LOG_DIR = HUB_DATA / "logs"
HIGH_LEVEL_VIEW = HUB_DATA / "high_level_view.json"


def ensure_skill_on_path() -> Path:
    """Insert wholesale-demand-align skill scripts on sys.path."""
    path = str(SKILL_SCRIPTS)
    if path not in sys.path:
        sys.path.insert(0, path)
    return SKILL_SCRIPTS


def load_env() -> None:
    """Load GHL and DealDriven credentials from ecosystem .env."""
    from dotenv import load_dotenv

    if ENV_FILE.is_file():
        load_dotenv(ENV_FILE)

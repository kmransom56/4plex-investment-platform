#!/usr/bin/env bash
# Unattended wholesale harvest loop (4plex → ecosystem skill scripts).
set -euo pipefail

PLATFORM="/media/keith/NVMe/real_estate_ecosystem/4plex-investment-platform"
ECOSYSTEM="/media/keith/NVMe/real_estate_ecosystem"
LOG_DIR="$PLATFORM/data/logs"
mkdir -p "$LOG_DIR"
STAMP=$(date -u +%Y%m%d-%H%M%S)
LOG="$LOG_DIR/harvest-$STAMP.log"

cd "$PLATFORM"
{
  echo "=== wholesale harvest $STAMP ==="
  uv run --with playwright --with python-dotenv \
    python scripts/run_wholesale_automation.py --modes both --json
  echo "=== packets from latest aligned ==="
  uv run --with python-dotenv \
    python "$ECOSYSTEM/.claude/skills/wholesale-demand-align/scripts/contract_packet.py" --json
} 2>&1 | tee "$LOG"

python3 - <<'PY'
import sys
sys.path.insert(0, "/media/keith/NVMe/real_estate_ecosystem")
from receipts import emit_receipt

emit_receipt(
    "A",
    "wholesale_harvest",
    ok=True,
    meta={"stage": "complete", "log": "'"$LOG"'"},
)
PY

echo "Log: $LOG"

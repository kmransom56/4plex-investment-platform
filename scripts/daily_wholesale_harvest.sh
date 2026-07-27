#!/usr/bin/env bash
# Unattended 30-day wholesale harvest loop (prep only; never --submit contracts).
set -euo pipefail
ROOT=/home/keith/real_estate
LOG_DIR="$ROOT/4plex-investment-platform/data/logs"
mkdir -p "$LOG_DIR"
STAMP=$(date -u +%Y%m%d-%H%M%S)
LOG="$LOG_DIR/harvest-$STAMP.log"

cd "$ROOT"
{
  echo "=== wholesale harvest $STAMP ==="
  uv run --with playwright --with python-dotenv \
    python 4plex-investment-platform/scripts/run_wholesale_automation.py \
    --modes both --json
  echo "=== packets from latest aligned ==="
  uv run --with python-dotenv \
    python .claude/skills/wholesale-demand-align/scripts/contract_packet.py --json
} 2>&1 | tee "$LOG"

echo "Log: $LOG"

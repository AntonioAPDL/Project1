#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -ne 1 ]; then
  echo "usage: $0 <config-path>" >&2
  exit 2
fi
CONFIG="$1"
RUN_ID=$(awk '/^[[:space:]]*run_id:/ {gsub(/\047|"/, "", $2); print $2; exit}' "$CONFIG")
if [ -z "${RUN_ID:-}" ]; then
  echo "Unable to resolve run_id from $CONFIG" >&2
  exit 3
fi
LOG_DIR="repro/hardening_logs"
mkdir -p "$LOG_DIR"
LOG_PATH="$LOG_DIR/${RUN_ID}.repair.log"
echo "[repair_run] start run_id=$RUN_ID config=$CONFIG log=$LOG_PATH" | tee "$LOG_PATH"
CLEANUP_RDATA_AFTER_POST=0 Rscript --vanilla scripts/unified_run.R --config "$CONFIG" 2>&1 | tee -a "$LOG_PATH"

#!/usr/bin/env bash
set -euo pipefail

# Monitor full NWM v1.2 yearly shard extraction progress.
#
# Usage:
#   ./scripts/monitor_nwm_v12_full_point_extraction.sh [RUN_ID]
#
# Default:
#   RUN_ID=nwm_retrospective_campaign_20260218T024352Z

RUN_ID="${1:-nwm_retrospective_campaign_20260218T024352Z}"
ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd"
cd "$ROOT"

RUN_ROOT="repro/nwm_retrospective_runs/${RUN_ID}"
YEARLY_DIR="${RUN_ROOT}/point_series/v12_yearly"
LOG_DIR="${RUN_ROOT}/logs/v12_yearly"

echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) =="
echo "RUN_ID=$RUN_ID"
echo "RUN_ROOT=$RUN_ROOT"
echo

echo "[TMUX] active v12 workers:"
tmux ls 2>/dev/null | grep 'nwm_v12_w' || echo "  (none)"
echo

echo "[YEARLY CSV] completion:"
DONE=$(find "$YEARLY_DIR" -name 'v12_*_daily.csv' -type f 2>/dev/null | wc -l | awk '{print $1}')
echo "done_years=$DONE / 25"
echo

echo "[MISSING HOURS] summary:"
LOG_DIR="$LOG_DIR" python3 - <<'PY'
import glob
import os
import pandas as pd

log_dir = os.environ["LOG_DIR"]
files = sorted(glob.glob(os.path.join(log_dir, "v12_*_missing_hours.csv")))
rows = []
for p in files:
    base = os.path.basename(p)
    year = base.split("_")[1]
    try:
        df = pd.read_csv(p)
        n = len(df)
    except Exception:
        n = -1
    rows.append((year, n))

if not rows:
    print("no missing-hours files yet")
else:
    bad = [r for r in rows if r[1] > 0]
    print(f"years_with_missing_file={len(rows)} years_with_nonzero_missing={len(bad)}")
    if bad:
        print("nonzero_missing_examples=", bad[:10])
PY
echo

echo "[LOG TAIL] worker logs:"
for f in "$LOG_DIR"/worker_*.log; do
  [[ -f "$f" ]] || continue
  echo "--- $f"
  tail -n 5 "$f"
done

#!/usr/bin/env bash
set -euo pipefail

# Launch full NWM v1.2 point-only extraction in background tmux workers.
#
# Usage:
#   ./scripts/run_nwm_v12_full_point_extraction.sh [RUN_ID] [WORKERS] [AGG_SCALE] [RUN_BASE_ROOT]
#
# Defaults:
#   RUN_ID=nwm_retrospective_campaign_20260218T024352Z
#   WORKERS=4
#   AGG_SCALE=log_log1p_cms
#   RUN_BASE_ROOT=repro/nwm_retrospective_runs
#
# Environment overrides:
#   NWM_V12_RUN_BASE_ROOT
#   PROJECT_ROOT

RUN_ID="${1:-nwm_retrospective_campaign_20260218T024352Z}"
WORKERS="${2:-4}"
AGG_SCALE="${3:-log_log1p_cms}"
RUN_BASE_ROOT="${4:-${NWM_V12_RUN_BASE_ROOT:-repro/nwm_retrospective_runs}}"

ROOT="${PROJECT_ROOT:-/data/muscat_data/jaguir26/project1_ucsc_phd}"
cd "$ROOT"

if ! [[ "$WORKERS" =~ ^[0-9]+$ ]] || [[ "$WORKERS" -lt 1 ]]; then
  echo "[FATAL] WORKERS must be a positive integer (got: $WORKERS)" >&2
  exit 2
fi

RUN_ROOT="${RUN_BASE_ROOT}/${RUN_ID}"
YEARLY_DIR="${RUN_ROOT}/point_series/v12_yearly"
LOG_DIR="${RUN_ROOT}/logs/v12_yearly"
mkdir -p "$YEARLY_DIR" "$LOG_DIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
SESSION_FILE="${LOG_DIR}/sessions_${TS}.txt"
touch "$SESSION_FILE"

echo "[INFO] RUN_ID=$RUN_ID"
echo "[INFO] WORKERS=$WORKERS"
echo "[INFO] RUN_ROOT=$RUN_ROOT"
echo "[INFO] AGG_SCALE=$AGG_SCALE"
echo "[INFO] RUN_BASE_ROOT=$RUN_BASE_ROOT"

RUN_ROOT="$RUN_ROOT" WORKERS="$WORKERS" LOG_DIR="$LOG_DIR" YEARLY_DIR="$YEARLY_DIR" python3 - <<'PY'
from pathlib import Path
import os

run_root = Path(os.environ["RUN_ROOT"])
workers = int(os.environ["WORKERS"])
log_dir = Path(os.environ["LOG_DIR"])
yearly_dir = Path(os.environ["YEARLY_DIR"])

years = list(range(1993, 2018))
pending = []
for y in years:
    out_csv = yearly_dir / f"v12_{y}_daily.csv"
    if out_csv.exists() and out_csv.stat().st_size > 0:
        continue
    pending.append(y)

for i in range(workers):
    f = log_dir / f"years_worker_{i:02d}.txt"
    with f.open("w") as w:
        for y in pending:
            if (y - 1993) % workers == i:
                w.write(f"{y}\n")

print(f"[OK] total_years=25 pending_years={len(pending)}")
PY

echo "[STEP] launching tmux workers..."
for i in $(seq 0 $((WORKERS - 1))); do
  YEAR_FILE="${LOG_DIR}/years_worker_$(printf '%02d' "$i").txt"
  SESS="nwm_v12_w$(printf '%02d' "$i")_${TS}"
  WLOG="${LOG_DIR}/worker_$(printf '%02d' "$i").log"
  WSCRIPT="${LOG_DIR}/worker_$(printf '%02d' "$i").sh"
  cat > "$WSCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
while read -r Y; do
  [[ -z "\$Y" ]] && continue
  OUT_CSV="${YEARLY_DIR}/v12_\${Y}_daily.csv"
  OUT_META="${LOG_DIR}/v12_\${Y}_meta.json"
  OUT_MISS="${LOG_DIR}/v12_\${Y}_missing_hours.csv"
  if [[ -s "\$OUT_CSV" ]]; then
    echo "[SKIP] year=\$Y already exists"
    continue
  fi
  echo "[RUN ] year=\$Y"
  python3 scripts/nwm_retrospective_extract_point_v12_comp.py \\
    --bucket nwm-archive \\
    --version 1.2 \\
    --lat 37.0443931 \\
    --lon -122.072464 \\
    --feature-id 17682474 \\
    --start-date "\${Y}-01-01" \\
    --end-date "\${Y}-12-31" \\
    --aggregate daily \\
    --aggregation-scale "$AGG_SCALE" \\
    --aws-retries 5 \\
    --retry-sleep-sec 2.0 \\
    --out-csv "\$OUT_CSV" \\
    --out-meta "\$OUT_META" \\
    --missing-hours-csv "\$OUT_MISS"
done < "$YEAR_FILE"
echo "[DONE] worker=$(printf '%02d' "$i")"
EOF
  chmod +x "$WSCRIPT"
  tmux new-session -d -s "$SESS" "bash \"$WSCRIPT\" |& tee \"$WLOG\""
  echo "$SESS" >> "$SESSION_FILE"
  echo "  - $SESS"
done

echo "[OK] launched workers"
echo "[OK] session list: $SESSION_FILE"
echo "[TIP] monitor: ./scripts/monitor_nwm_v12_full_point_extraction.sh \"$RUN_ID\""

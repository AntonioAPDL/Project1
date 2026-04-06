#!/usr/bin/env bash
set -euo pipefail

# Launch year-sharded NWM retrospective Zarr point extraction in background tmux workers.
#
# Usage:
#   ./scripts/run_nwm_zarr_yearly_point_extraction.sh \
#     <VERSION> <ZARR_URL> <START_DATE> <END_DATE> \
#     [RUN_ID] [WORKERS] [AGG_SCALE] [RUN_BASE_ROOT] [FEATURE_ID]
#
# Example:
#   ./scripts/run_nwm_zarr_yearly_point_extraction.sh \
#     2.0 s3://noaa-nwm-retro-v2-zarr-pds 1993-01-01 2018-12-31 \
#     nwm_v20_campaign_20260406T000000Z 4 log_log1p_cms \
#     /path/to/runtime/family=nwm_retrospective/full_runs/source_native_tranche1 \
#     17682474

VERSION="${1:?VERSION is required}"
ZARR_URL="${2:?ZARR_URL is required}"
START_DATE="${3:?START_DATE is required}"
END_DATE="${4:?END_DATE is required}"
RUN_ID="${5:-nwm_zarr_$(echo "$VERSION" | tr -d '.')_$(date -u +%Y%m%dT%H%M%SZ)}"
WORKERS="${6:-4}"
AGG_SCALE="${7:-log_log1p_cms}"
RUN_BASE_ROOT="${8:-${NWM_ZARR_RUN_BASE_ROOT:-repro/nwm_retrospective_runs}}"
FEATURE_ID="${9:-17682474}"

ROOT="${PROJECT_ROOT:-/data/muscat_data/jaguir26/project1_ucsc_phd}"
cd "$ROOT"

if ! [[ "$WORKERS" =~ ^[0-9]+$ ]] || [[ "$WORKERS" -lt 1 ]]; then
  echo "[FATAL] WORKERS must be a positive integer (got: $WORKERS)" >&2
  exit 2
fi

VERSION_TAG="v$(echo "$VERSION" | tr -d '.')"
RUN_ROOT="${RUN_BASE_ROOT}/${RUN_ID}"
YEARLY_DIR="${RUN_ROOT}/point_series/${VERSION_TAG}_yearly"
LOG_DIR="${RUN_ROOT}/logs/${VERSION_TAG}_yearly"
mkdir -p "$YEARLY_DIR" "$LOG_DIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
SESSION_FILE="${LOG_DIR}/sessions_${TS}.txt"
touch "$SESSION_FILE"

echo "[INFO] VERSION=$VERSION"
echo "[INFO] VERSION_TAG=$VERSION_TAG"
echo "[INFO] RUN_ID=$RUN_ID"
echo "[INFO] WORKERS=$WORKERS"
echo "[INFO] RUN_ROOT=$RUN_ROOT"
echo "[INFO] AGG_SCALE=$AGG_SCALE"
echo "[INFO] START_DATE=$START_DATE"
echo "[INFO] END_DATE=$END_DATE"
echo "[INFO] FEATURE_ID=$FEATURE_ID"
echo "[INFO] RUN_BASE_ROOT=$RUN_BASE_ROOT"

RUN_ROOT="$RUN_ROOT" \
WORKERS="$WORKERS" \
LOG_DIR="$LOG_DIR" \
YEARLY_DIR="$YEARLY_DIR" \
START_DATE="$START_DATE" \
END_DATE="$END_DATE" \
python3 - <<'PY'
from pathlib import Path
import os
import pandas as pd

run_root = Path(os.environ["RUN_ROOT"])
workers = int(os.environ["WORKERS"])
log_dir = Path(os.environ["LOG_DIR"])
yearly_dir = Path(os.environ["YEARLY_DIR"])
start_date = pd.Timestamp(os.environ["START_DATE"])
end_date = pd.Timestamp(os.environ["END_DATE"])

years = list(range(start_date.year, end_date.year + 1))
pending = []
for y in years:
    out_csv = yearly_dir / f"{y}_daily.csv"
    if out_csv.exists() and out_csv.stat().st_size > 0:
        continue
    pending.append(y)

for i in range(workers):
    f = log_dir / f"years_worker_{i:02d}.txt"
    with f.open("w", encoding="utf-8") as w:
        for y in pending:
            if (y - years[0]) % workers == i:
                w.write(f"{y}\n")

print(f"[OK] total_years={len(years)} pending_years={len(pending)}")
PY

echo "[STEP] launching tmux workers..."
for i in $(seq 0 $((WORKERS - 1))); do
  YEAR_FILE="${LOG_DIR}/years_worker_$(printf '%02d' "$i").txt"
  SESS="${VERSION_TAG}_w$(printf '%02d' "$i")_${TS}"
  WLOG="${LOG_DIR}/worker_$(printf '%02d' "$i").log"
  WSCRIPT="${LOG_DIR}/worker_$(printf '%02d' "$i").sh"
  cat > "$WSCRIPT" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
while read -r Y; do
  [[ -z "\$Y" ]] && continue
  YEAR_START="\${Y}-01-01"
  YEAR_END="\${Y}-12-31"
  if [[ "\$Y" == "${START_DATE%%-*}" ]]; then
    YEAR_START="$START_DATE"
  fi
  if [[ "\$Y" == "${END_DATE%%-*}" ]]; then
    YEAR_END="$END_DATE"
  fi
  OUT_CSV="${YEARLY_DIR}/\${Y}_daily.csv"
  OUT_META="${LOG_DIR}/\${Y}_meta.json"
  if [[ -s "\$OUT_CSV" ]]; then
    echo "[SKIP] year=\$Y already exists"
    continue
  fi
  echo "[RUN ] version=$VERSION year=\$Y start=\$YEAR_START end=\$YEAR_END"
  python3 scripts/nwm_retrospective_extract_point_zarr.py \\
    --zarr-url "$ZARR_URL" \\
    --version "$VERSION" \\
    --lat 37.0443931 \\
    --lon -122.072464 \\
    --feature-id "$FEATURE_ID" \\
    --start-date "\$YEAR_START" \\
    --end-date "\$YEAR_END" \\
    --aggregate daily \\
    --aggregation-scale "$AGG_SCALE" \\
    --out-csv "\$OUT_CSV" \\
    --out-meta "\$OUT_META"
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
echo "[TIP] when workers finish, combine shards with:"
echo "python3 scripts/nwm_retrospective_concat_yearly_shards.py --input-dir \"$YEARLY_DIR\" --out-csv \"$RUN_ROOT/point_series/${VERSION_TAG}_full_daily.csv\" --out-meta \"$RUN_ROOT/logs/${VERSION_TAG}_full_daily.meta.json\" --version \"$VERSION\" --expected-start \"$START_DATE\" --expected-end \"$END_DATE\""

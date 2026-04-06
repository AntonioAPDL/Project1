#!/usr/bin/env bash
set -euo pipefail

# Launch the first full source-native redownload tranche under an existing
# external recovery campaign root. This tranche targets the lanes whose repo-
# local outputs were definitely lost and should be rebuilt from source first.
#
# Tranche contents:
# - NWM retrospective v1.2
# - NWM retrospective v2.0
# - GLOFAS historical version_2_1 / version_3_1 / version_4_0
# - GEFS full extraction (GEFS source only)
# - USGS full historical daily flow
#
# Usage:
#   ./scripts/recovery_launch_source_native_tranche1.sh <RECOVERY_RUN_ROOT> [LAUNCH_ID]
#
# Environment overrides:
#   DRY_RUN=1        stage everything but do not execute/launch
#   PROJECT_ROOT=...

RECOVERY_RUN_ROOT="${1:?RECOVERY_RUN_ROOT is required}"
LAUNCH_ID="${2:-source_native_tranche1_$(date -u +%Y%m%dT%H%M%SZ)}"
DRY_RUN="${DRY_RUN:-0}"

ROOT="${PROJECT_ROOT:-/data/muscat_data/jaguir26/project1_ucsc_phd}"
cd "$ROOT"

RUN_ROOT="$(python3 - <<'PY' "$RECOVERY_RUN_ROOT"
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve())
PY
)"

GROUP_ROOT="${RUN_ROOT}/backfill_groups/${LAUNCH_ID}"
GROUP_CMD_DIR="${GROUP_ROOT}/commands"
GROUP_LOG_DIR="${GROUP_ROOT}/logs"
GROUP_STATUS_DIR="${GROUP_ROOT}/status"
GROUP_MANIFEST_DIR="${GROUP_ROOT}/manifests"
mkdir -p "$GROUP_CMD_DIR" "$GROUP_LOG_DIR" "$GROUP_STATUS_DIR" "$GROUP_MANIFEST_DIR"

NWM_FAMILY_ROOT="${RUN_ROOT}/family=nwm_retrospective/full_runs/${LAUNCH_ID}"
GLOFAS_FAMILY_ROOT="${RUN_ROOT}/family=glofas_historical/full_runs/${LAUNCH_ID}"
GEFS_FAMILY_ROOT="${RUN_ROOT}/family=gefs_forecasts/full_runs/${LAUNCH_ID}"
USGS_FAMILY_ROOT="${RUN_ROOT}/family=usgs_daily_flow/full_runs/${LAUNCH_ID}"
mkdir -p "$NWM_FAMILY_ROOT" "$GLOFAS_FAMILY_ROOT" "$GEFS_FAMILY_ROOT" "$USGS_FAMILY_ROOT"

ENV_FILE="${GROUP_CMD_DIR}/env.sh"
cat > "$ENV_FILE" <<EOF
export RECOVERY_RUN_ROOT="$RUN_ROOT"
export BACKFILL_LAUNCH_ID="$LAUNCH_ID"
export BACKFILL_GROUP_ROOT="$GROUP_ROOT"
export NWM_FAMILY_ROOT="$NWM_FAMILY_ROOT"
export GLOFAS_FAMILY_ROOT="$GLOFAS_FAMILY_ROOT"
export GEFS_FAMILY_ROOT="$GEFS_FAMILY_ROOT"
export USGS_FAMILY_ROOT="$USGS_FAMILY_ROOT"
EOF

USGS_LOG="${GROUP_LOG_DIR}/usgs_full_fetch.log"
USGS_CMD="${GROUP_CMD_DIR}/launch_usgs_full.sh"
cat > "$USGS_CMD" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
python3 scripts/fetch_usgs_daily_flow.py \\
  --site-id 11160500 \\
  --start-date 1979-01-01 \\
  --end-date 2026-04-06 \\
  --out-csv "$USGS_FAMILY_ROOT/outputs/usgs_daily_flow_11160500.csv" \\
  --out-meta "$USGS_FAMILY_ROOT/logs/usgs_daily_flow_11160500.meta.json"
EOF
chmod +x "$USGS_CMD"

NWM_V12_RUN_ID="nwm_v12_campaign_${LAUNCH_ID}"
NWM_V12_CMD="${GROUP_CMD_DIR}/launch_nwm_v12.sh"
cat > "$NWM_V12_CMD" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
PROJECT_ROOT="$ROOT" \\
NWM_V12_RUN_BASE_ROOT="$NWM_FAMILY_ROOT" \\
bash scripts/run_nwm_v12_full_point_extraction.sh \\
  "$NWM_V12_RUN_ID" \\
  4 \\
  log_log1p_cms \\
  "$NWM_FAMILY_ROOT"
EOF
chmod +x "$NWM_V12_CMD"

NWM_V20_RUN_ID="nwm_v20_campaign_${LAUNCH_ID}"
NWM_V20_CMD="${GROUP_CMD_DIR}/launch_nwm_v20.sh"
cat > "$NWM_V20_CMD" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
PROJECT_ROOT="$ROOT" \\
NWM_ZARR_RUN_BASE_ROOT="$NWM_FAMILY_ROOT" \\
bash scripts/run_nwm_zarr_yearly_point_extraction.sh \\
  2.0 \\
  s3://noaa-nwm-retro-v2-zarr-pds \\
  1993-01-01 \\
  2018-12-31 \\
  "$NWM_V20_RUN_ID" \\
  4 \\
  log_log1p_cms \\
  "$NWM_FAMILY_ROOT" \\
  17682474
EOF
chmod +x "$NWM_V20_CMD"

GLOFAS_CMD="${GROUP_CMD_DIR}/launch_glofas_historical.sh"
cat > "$GLOFAS_CMD" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
OUT_ROOT="$GLOFAS_FAMILY_ROOT/outputs/historical_zips"
PLAN_ROOT="$GLOFAS_FAMILY_ROOT/plans"
POINT_ROOT="$GLOFAS_FAMILY_ROOT/outputs/point_series"
LOG_ROOT="$GLOFAS_FAMILY_ROOT/logs"
mkdir -p "\$OUT_ROOT" "\$PLAN_ROOT" "\$POINT_ROOT" "\$LOG_ROOT"

for PID in hist_v21_htessel_cons hist_v31_lisflood_cons hist_v40_lisflood_cons; do
  echo "[STEP] download campaign product=\$PID"
  python3 scripts/forecats_download_glofas_historical_consolidated.py \\
    --out-root "\$OUT_ROOT" \\
    --plan-root "\$PLAN_ROOT" \\
    --product-id "\$PID" \\
    --focus-start 1987-05-29 \\
    --focus-end 2023-05-01 \\
    --run

  echo "[STEP] point extract product=\$PID"
  python3 scripts/forecats_extract_glofas_historical_point.py \\
    --campaign-root "\$OUT_ROOT/\$PID" \\
    --out-csv "\$POINT_ROOT/\${PID}_point.csv" \\
    --out-meta "\$LOG_ROOT/\${PID}_point.meta.json" \\
    --lat 37.0443931 \\
    --lon -122.072464 \\
    --cell-policy nearest_valid
done
EOF
chmod +x "$GLOFAS_CMD"

GEFS_MANIFEST_RUN_ID="gefs_nwm_forecast_manifest_${LAUNCH_ID}"
GEFS_MANIFEST_CMD="${GROUP_CMD_DIR}/build_gefs_manifest.sh"
cat > "$GEFS_MANIFEST_CMD" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
python3 scripts/build_gefs_nwm_forecast_manifest.py \\
  --run-root "$GEFS_FAMILY_ROOT" \\
  --run-id "$GEFS_MANIFEST_RUN_ID" \\
  --site-config config/forecats_pipeline.template.yaml \\
  --dates "2021-01-23,2021-11-12,2021-12-21,2022-05-11,2022-12-25" \\
  --gefs-cycle 00 \\
  --nwm-cycle 00
EOF
chmod +x "$GEFS_MANIFEST_CMD"

GEFS_FULL_CMD="${GROUP_CMD_DIR}/launch_gefs_full.sh"
cat > "$GEFS_FULL_CMD" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$ROOT"
MANIFEST_RUN_DIR="$GEFS_FAMILY_ROOT/$GEFS_MANIFEST_RUN_ID"
python3 scripts/gefs_nwm_point_smoke_extract.py \\
  --manifest-run-dir "\$MANIFEST_RUN_DIR" \\
  --site-config config/forecats_pipeline.template.yaml \\
  --gefs-init-date 2021-01-23 \\
  --nwm-init-date 2021-11-12 \\
  --gefs-cycle 0 \\
  --nwm-cycle 0
python3 scripts/check_gefs_nwm_forecast_extract_health.py \\
  --manifest-run-dir "\$MANIFEST_RUN_DIR" \\
  --mode smoke \\
  --out-json "\$MANIFEST_RUN_DIR/health_checks/forecast_extract_health_smoke.json"
python3 scripts/extract_gefs_nwm_forecast_points.py \\
  --manifest-run-dir "\$MANIFEST_RUN_DIR" \\
  --out-subdir extract_gefs_full \\
  --sources gefs \\
  --gefs-workers 16 \\
  --batch-size 512 \\
  --gefs-file-retries 3
python3 scripts/check_gefs_nwm_forecast_extract_health.py \\
  --manifest-run-dir "\$MANIFEST_RUN_DIR" \\
  --mode full \\
  --sources gefs \\
  --gefs-out-subdir extract_gefs_full \\
  --out-json "\$MANIFEST_RUN_DIR/health_checks/forecast_extract_health_full.json"
EOF
chmod +x "$GEFS_FULL_CMD"

SESSION_FILE="${GROUP_STATUS_DIR}/tmux_sessions.txt"
: > "$SESSION_FILE"

python3 - <<'PY' "$GROUP_MANIFEST_DIR/launch_manifest.json" "$LAUNCH_ID" "$RUN_ROOT" "$GROUP_ROOT" "$NWM_FAMILY_ROOT" "$GLOFAS_FAMILY_ROOT" "$GEFS_FAMILY_ROOT" "$USGS_FAMILY_ROOT" "$GEFS_MANIFEST_RUN_ID"
import json
import sys

out_path = sys.argv[1]
payload = {
    "launch_id": sys.argv[2],
    "recovery_run_root": sys.argv[3],
    "group_root": sys.argv[4],
    "family_roots": {
        "nwm_retrospective": sys.argv[5],
        "glofas_historical": sys.argv[6],
        "gefs_forecasts": sys.argv[7],
        "usgs_daily_flow": sys.argv[8],
    },
    "gefs_manifest_run_id": sys.argv[9],
    "lanes": [
        "nwm_v12_full",
        "nwm_v20_full",
        "glofas_historical_full",
        "gefs_full",
        "usgs_full",
    ],
}
with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(payload, fh, indent=2)
PY

echo "[OK] staged launch bundle: $GROUP_ROOT"
echo "[OK] launch manifest: $GROUP_MANIFEST_DIR/launch_manifest.json"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "[DRY-RUN] would execute:"
  echo "  1. $USGS_CMD"
  echo "  2. $GEFS_MANIFEST_CMD"
  echo "  3. tmux launch $NWM_V12_CMD"
  echo "  4. tmux launch $NWM_V20_CMD"
  echo "  5. tmux launch $GLOFAS_CMD"
  echo "  6. tmux launch $GEFS_FULL_CMD"
  exit 0
fi

echo "[STEP] materializing USGS full fetch..."
bash "$USGS_CMD" |& tee "$USGS_LOG"

echo "[STEP] building dedicated GEFS manifest..."
bash "$GEFS_MANIFEST_CMD" |& tee "${GROUP_LOG_DIR}/gefs_manifest_build.log"

launch_tmux() {
  local session_name="$1"
  local command_path="$2"
  local log_path="$3"
  tmux new-session -d -s "$session_name" "bash \"$command_path\" |& tee \"$log_path\""
  echo "$session_name" >> "$SESSION_FILE"
  echo "[OK] launched $session_name"
}

launch_tmux "nwm_v12_${LAUNCH_ID}" "$NWM_V12_CMD" "${GROUP_LOG_DIR}/nwm_v12_full.log"
launch_tmux "nwm_v20_${LAUNCH_ID}" "$NWM_V20_CMD" "${GROUP_LOG_DIR}/nwm_v20_full.log"
launch_tmux "glofas_hist_${LAUNCH_ID}" "$GLOFAS_CMD" "${GROUP_LOG_DIR}/glofas_historical_full.log"
launch_tmux "gefs_full_${LAUNCH_ID}" "$GEFS_FULL_CMD" "${GROUP_LOG_DIR}/gefs_full.log"

echo "[OK] launched tranche 1 sessions"
echo "[OK] session list: $SESSION_FILE"

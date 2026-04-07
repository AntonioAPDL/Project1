#!/usr/bin/env bash
set -euo pipefail

PRODUCT_ID="${1:?PRODUCT_ID is required}"
CAMPAIGN_ROOT="${2:?CAMPAIGN_ROOT is required}"
FOCUS_START="${3:-1987-05-29}"
FOCUS_END="${4:-2023-05-01}"
ROOT="${PROJECT_ROOT:-/data/muscat_data/jaguir26/project1_ucsc_phd}"

cd "$ROOT"
OUT_ROOT="$CAMPAIGN_ROOT/outputs/historical_zips"
PLAN_ROOT="$CAMPAIGN_ROOT/plans"
POINT_ROOT="$CAMPAIGN_ROOT/outputs/point_series"
LOG_ROOT="$CAMPAIGN_ROOT/logs"
mkdir -p "$OUT_ROOT" "$PLAN_ROOT" "$POINT_ROOT" "$LOG_ROOT"

python3 scripts/forecats_download_glofas_historical_consolidated.py   --out-root "$OUT_ROOT"   --plan-root "$PLAN_ROOT"   --product-id "$PRODUCT_ID"   --focus-start "$FOCUS_START"   --focus-end "$FOCUS_END"   --run

python3 scripts/forecats_extract_glofas_historical_point.py   --campaign-root "$OUT_ROOT/$PRODUCT_ID"   --out-csv "$POINT_ROOT/${PRODUCT_ID}_point.csv"   --out-meta "$LOG_ROOT/${PRODUCT_ID}_point.meta.json"   --lat 37.0443931   --lon -122.072464   --cell-policy nearest_valid

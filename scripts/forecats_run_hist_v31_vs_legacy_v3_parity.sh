#!/usr/bin/env bash
set -euo pipefail

ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd"
cd "$ROOT"

RUN_ID="hist_v31_vs_legacy_v3_$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="repro/glofas_probe_runs/$RUN_ID"
mkdir -p "$OUT_DIR"

HIST_ROOT="data/glofas_historical_consolidated_point/hist_v31_lisflood_cons"
LEGACY_NC="data/glofas_legacy_global/dis_1980_2018_v3_legacy.nc"

if [[ ! -d "$HIST_ROOT" ]]; then
  echo "[ERROR] Missing historical root: $HIST_ROOT" >&2
  exit 1
fi
if [[ ! -f "$LEGACY_NC" ]]; then
  echo "[ERROR] Missing legacy file: $LEGACY_NC" >&2
  exit 1
fi

# 1) Extract C historical v3.1 point series
python3 scripts/forecats_extract_glofas_historical_point.py \
  --campaign-root "$HIST_ROOT" \
  --out-csv "$OUT_DIR/historical_v31_point.csv" \
  --out-meta "$OUT_DIR/historical_v31_point.meta.json" \
  --lat 37.0443931 --lon -122.072464 \
  --var dis24 --cell-policy nearest_valid

# 2) Extract legacy v3 point series
python3 scripts/forecats_extract_legacy_glofas_point.py \
  --input-nc "$LEGACY_NC" \
  --out-csv "$OUT_DIR/legacy_v3_point.csv" \
  --out-meta "$OUT_DIR/legacy_v3_point.meta.json" \
  --lat 37.0443931 --lon -122.072464 \
  --start-date 1987-05-29 --end-date 2018-12-31

# 3) Compare overlap metrics
python3 scripts/forecats_compare_point_series_overlap.py \
  --left-csv "$OUT_DIR/historical_v31_point.csv" \
  --right-csv "$OUT_DIR/legacy_v3_point.csv" \
  --left-label historical_v31 \
  --right-label legacy_v3 \
  --out-csv "$OUT_DIR/overlap_diff.csv" \
  --out-json "$OUT_DIR/overlap_summary.json"

# 4) Optional transition diagnostics on historical series around key dates
python3 scripts/forecats_transition_diagnostics.py \
  --csv "$OUT_DIR/historical_v31_point.csv" \
  --transition-date 2019-11-05 \
  --transition-date 2021-05-26 \
  --window-days 30 \
  --out-csv "$OUT_DIR/historical_v31_transitions.csv" \
  --out-json "$OUT_DIR/historical_v31_transitions.json"

echo "[DONE] parity bundle: $OUT_DIR"

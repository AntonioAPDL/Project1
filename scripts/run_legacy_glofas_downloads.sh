#!/usr/bin/env bash
set -euo pipefail

# Template commands for legacy GloFAS global downloads.
# This script is safe to run incrementally: curl uses resume (-C -).
#
# Usage:
#   ./scripts/run_legacy_glofas_downloads.sh [OUT_DIR] [LOG_DIR]
#
# Environment overrides:
#   GLOFAS_LEGACY_OUT_DIR
#   GLOFAS_LEGACY_LOG_DIR

ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd"
OUT_DIR="${1:-${GLOFAS_LEGACY_OUT_DIR:-$ROOT/data/glofas_legacy_global}}"
LOG_DIR="${2:-${GLOFAS_LEGACY_LOG_DIR:-$OUT_DIR/logs}}"
mkdir -p "$OUT_DIR" "$LOG_DIR"

echo "[INFO] OUT_DIR=$OUT_DIR"
echo "[INFO] LOG_DIR=$LOG_DIR"

# Stable confirmed URL (v3.0 legacy reanalysis):
V3_URL="https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS-RA/streamflow_analysis/LATEST/dis_1980_2018.nc"
V3_OUT="$OUT_DIR/dis_1980_2018_v3_legacy.nc"

# v4.0 legacy direct file URL is currently unresolved from JRC catalogue metadata.
# Keep empty until resolved, or use EWDS API campaign fallback.
V4_URL=""
V4_OUT="$OUT_DIR/dis_1980_2022_v4_legacy.nc"

# Preflight checks
{
  date -u
  echo "== df -h =="
  df -h /data
  echo "== free target =="
  du -sh "$OUT_DIR" || true
} | tee "$LOG_DIR/preflight_$(date -u +%Y%m%dT%H%M%SZ).log"

# 1) Start/continue v3 download in background
nohup curl -fL --retry 20 --retry-delay 15 -C - "$V3_URL" -o "$V3_OUT" > "$LOG_DIR/v3_download.log" 2>&1 &
echo "Started v3 download PID=$!"

# 2) Optional v4 direct download (only if URL resolved)
if [[ -n "$V4_URL" ]]; then
  nohup curl -fL --retry 20 --retry-delay 15 -C - "$V4_URL" -o "$V4_OUT" > "$LOG_DIR/v4_download.log" 2>&1 &
  echo "Started v4 download PID=$!"
else
  echo "V4_URL is empty: direct v4 global file URL unresolved; use EWDS API fallback workflow."
fi

# 3) Quick monitor commands (manual):
# tail -f "$LOG_DIR/v3_download.log"
# ls -lh "$V3_OUT"
# pgrep -af "curl.*dis_1980_2018"

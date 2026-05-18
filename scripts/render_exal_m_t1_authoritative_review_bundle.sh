#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  render_exal_m_t1_authoritative_review_bundle.sh \
    --run-root <run_root> \
    --report-tag <tag> \
    [--quant-source-run-root <run_root>]

This renders the authoritative forecast-window and mean-location review bundles
from a corrected representative exAL-M-T1 run root.
EOF
}

RUN_ROOT=""
QUANT_SOURCE_RUN_ROOT=""
REPORT_TAG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --run-root)
      RUN_ROOT="${2:-}"
      shift 2
      ;;
    --quant-source-run-root)
      QUANT_SOURCE_RUN_ROOT="${2:-}"
      shift 2
      ;;
    --report-tag)
      REPORT_TAG="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$RUN_ROOT" || -z "$REPORT_TAG" ]]; then
  usage >&2
  exit 1
fi

if [[ -z "$QUANT_SOURCE_RUN_ROOT" ]]; then
  QUANT_SOURCE_RUN_ROOT="$RUN_ROOT"
fi

PROJECT_ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd"
FORECAST_REPORT_DIR="$PROJECT_ROOT/reports/he2_exal_m_t1_forecast_window_review_20221225_${REPORT_TAG}"
LOCATION_REPORT_DIR="$PROJECT_ROOT/reports/he2_exal_m_t1_usgs_location_dynamics_review_20221225_${REPORT_TAG}"

mkdir -p "$FORECAST_REPORT_DIR" "$LOCATION_REPORT_DIR"

Rscript "$PROJECT_ROOT/scripts/render_exal_m_t1_forecast_window_review.R" \
  --run-root "$RUN_ROOT" \
  --report-dir "$FORECAST_REPORT_DIR"

Rscript "$PROJECT_ROOT/scripts/render_exal_m_t1_usgs_location_dynamics_review.R" \
  --run-root "$RUN_ROOT" \
  --quant-source-run-root "$QUANT_SOURCE_RUN_ROOT" \
  --report-dir "$LOCATION_REPORT_DIR" \
  --mean-only

echo "FORECAST_REPORT_DIR=$FORECAST_REPORT_DIR"
echo "LOCATION_REPORT_DIR=$LOCATION_REPORT_DIR"

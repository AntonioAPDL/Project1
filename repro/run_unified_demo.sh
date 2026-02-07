#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

P0="${P0:-0.5}"
SEED="${SEED:-777}"

# Required fit input placeholders for unified runner example.
# Replace these defaults (or export env vars) before running real mode.
PARAMETERS_PATH="${PARAMETERS_PATH:-/REPLACE_ME/parameters.txt}"
RETROS_PATH="${RETROS_PATH:-/REPLACE_ME/retros.csv}"
NWS_FORECAST_PATH="${NWS_FORECAST_PATH:-/REPLACE_ME/nws_forecast.csv}"
GLOFAS_FORECAST_PATH="${GLOFAS_FORECAST_PATH:-/REPLACE_ME/weighted_time_series.csv}"

mkdir -p repro/tmp
DEMO_CONFIG="repro/tmp/unified_demo_config.yaml"

cat > "$DEMO_CONFIG" <<YAML
config_version: 1
run:
  run_id: null
  run_root: "repro/runs"
  repro_mode: "strict"
  seed: ${SEED}
  overwrite: false
  dry_run: false
  git_require_clean: false
  threads:
    omp: 1
    openblas: 1
    mkl: 1
    veclib: 1
    numexpr: 1
    mc_cores: 1
stages:
  forecats: false
  fit: true
  post: false
  validate: true
  report: true
site:
  usgs_site: "11160500"
  lat: 37.0443931
  lon: -122.072464
dates:
  cutoff_date: "2022-12-25"
  plot_start: "2022-12-07"
  plot_end: "2023-01-22"
inputs:
  fit:
    parameters_path: "${PARAMETERS_PATH}"
    retros_path: "${RETROS_PATH}"
    retros_storage_scale: "log1p_cms"
    nws_forecast_path: "${NWS_FORECAST_PATH}"
    nws_storage_scale: "log1p_cms"
    glofas_forecast_path: "${GLOFAS_FORECAST_PATH}"
    glofas_storage_scale: "log1p_cms"
    usgs_mode: "live"
    usgs_cache_path: null
  post:
    use_fit_outputs_from_run: true
  forecats:
    mode: "use_existing"
    pipeline_config_path: "config/forecats_pipeline.template.yaml"
    existing_bundle_path: null
fit:
  quantiles: [0.5]
  warm_start:
    enabled: false
    source_run_id: null
    mode: "resume"
post:
  figures: true
  profile: false
  profile_detail: false
validation:
  canonical_run_id: null
  compare:
    mode: "both"
    numeric_abs_tol: 0.0
    numeric_rel_tol: 0.0
    pixel_max_abs_tol: 0.0
scale_contract:
  canonical_storage_scale: "raw_cms"
  legacy_fit_input_scale: "log1p_cms"
  legacy_post_input_scale: "log1p_cms"
  analysis_scale_fit_internal: "log_log1p_cms"
  analysis_scale_post_internal: "log_log1p_cms"
write_audit:
  enabled: true
  enforce_from_stage: 4
  allowlist_outside_run_root: []
YAML

echo "[1/4] Running legacy Stage 0 baseline script"
bash repro/run_stage0_baseline.sh "$P0" "$SEED"

latest_stage0="$(ls -1dt repro/baseline_runs/*_p0_${P0}_seed_${SEED} 2>/dev/null | head -n 1)"
if [[ -z "$latest_stage0" ]]; then
  echo "ERROR: no Stage 0 run directory found after baseline run" >&2
  exit 1
fi

echo "[2/4] Capturing Stage 0 baseline metadata"
Rscript --vanilla repro/stage0_capture_baseline_metadata.R "$latest_stage0"

if [[ ! -x scripts/unified_run.R ]]; then
  echo "ERROR: scripts/unified_run.R not found/executable yet. Implement unified runner first." >&2
  exit 1
fi

echo "[3/4] Unified runner dry-run"
Rscript --vanilla scripts/unified_run.R --config "$DEMO_CONFIG" --dry-run

if [[ "$PARAMETERS_PATH" == /REPLACE_ME/* || "$RETROS_PATH" == /REPLACE_ME/* || "$NWS_FORECAST_PATH" == /REPLACE_ME/* || "$GLOFAS_FORECAST_PATH" == /REPLACE_ME/* ]]; then
  echo "[4/4] Skipping real unified run: replace placeholder input paths in $DEMO_CONFIG first."
  exit 0
fi

echo "[4/4] Unified runner real mode (strict)"
Rscript --vanilla scripts/unified_run.R --config "$DEMO_CONFIG"

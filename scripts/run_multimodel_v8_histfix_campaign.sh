#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ARTIFACT_ROOT="${MULTIMODEL_V8_HISTFIX_ARTIFACT_ROOT:-/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_histfix_20260407}"
CONFIG_DIR="${MULTIMODEL_V8_HISTFIX_CONFIG_DIR:-$ROOT/config/unified_runs_histfix_20260407}"
BUNDLE_RUN_ID="${MULTIMODEL_V8_HISTFIX_BUNDLE_RUN_ID:-20260407_long_history_r01}"
DATA_START="${MULTIMODEL_V8_HISTFIX_DATA_START:-1987-05-29}"
GLOFAS_READY_END="${MULTIMODEL_V8_HISTFIX_GLOFAS_READY_END:-2022-05-11}"
CUTS=( ${MULTIMODEL_V8_HISTFIX_CUTOFFS:-20211221 20220511} )
GLOFAS_RECOVERY_FAMILY_ROOT="${MULTIMODEL_V8_HISTFIX_GLOFAS_RECOVERY_FAMILY_ROOT:-/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=glofas_historical/full_runs/source_native_tranche1_20260406T194500Z}"
GLOFAS_REFILL_WORKERS="${MULTIMODEL_V8_HISTFIX_GLOFAS_REFILL_WORKERS:-4}"
GLOFAS_REFILL_PASSES="${MULTIMODEL_V8_HISTFIX_GLOFAS_REFILL_PASSES:-4}"

START_AT_PHASE="${MULTIMODEL_V8_HISTFIX_START_AT_PHASE:-sources}"
STOP_AFTER_PHASE="${MULTIMODEL_V8_HISTFIX_STOP_AFTER_PHASE:-cf1}"

TT_DIR="${ARTIFACT_ROOT}/control/histfix_tt_20260407"
C100_DIR="${ARTIFACT_ROOT}/control/histfix_c100_20260407"
CF1_DIR="${ARTIFACT_ROOT}/control/histfix_cf1_20260407"

TT_ORDINARY_MAX_CONCURRENT="${MULTIMODEL_V8_HISTFIX_TT_ORDINARY_MAX_CONCURRENT:-1}"
MV_ORDINARY_MAX_CONCURRENT="${MULTIMODEL_V8_HISTFIX_MV_ORDINARY_MAX_CONCURRENT:-2}"
PAUSE_FREE_GB="${MULTIMODEL_V8_HISTFIX_PAUSE_FREE_GB:-180}"
LAUNCH_FREE_GB="${MULTIMODEL_V8_HISTFIX_LAUNCH_FREE_GB:-220}"
HEAVY_FREE_GB="${MULTIMODEL_V8_HISTFIX_HEAVY_FREE_GB:-240}"
POLL_SECONDS="${MULTIMODEL_V8_HISTFIX_POLL_SECONDS:-60}"

mkdir -p "${ARTIFACT_ROOT}/control"

phase_rank() {
  case "$1" in
    sources) echo 1 ;;
    bundles) echo 2 ;;
    tt) echo 3 ;;
    c100) echo 4 ;;
    cf1) echo 5 ;;
    *) echo 99 ;;
  esac
}

should_run_phase() {
  local phase="$1"
  local start_rank stop_rank current_rank
  start_rank="$(phase_rank "$START_AT_PHASE")"
  stop_rank="$(phase_rank "$STOP_AFTER_PHASE")"
  current_rank="$(phase_rank "$phase")"
  [[ "$current_rank" -ge "$start_rank" && "$current_rank" -le "$stop_rank" ]]
}

cutoff_args=()
for c in "${CUTS[@]}"; do
  cutoff_args+=("$c")
done

build_bundles() {
  python3 scripts/build_multimodel_v8_histfix_bundles.py \
    --artifact-root "${ARTIFACT_ROOT}" \
    --bundle-run-id "${BUNDLE_RUN_ID}" \
    --data-start "${DATA_START}" \
    --glofas-ready-end "${GLOFAS_READY_END}" \
    --cutoffs "${cutoff_args[@]}"
}

ensure_sources() {
  python3 scripts/ensure_glofas_hist_v31_histfix_ready.py \
    --recovery-family-root "${GLOFAS_RECOVERY_FAMILY_ROOT}" \
    --focus-start "${DATA_START}" \
    --focus-end "${GLOFAS_READY_END}" \
    --workers "${GLOFAS_REFILL_WORKERS}" \
    --passes "${GLOFAS_REFILL_PASSES}"
}

build_phase() {
  local phase="$1"
  local matrix_dir="$2"
  python3 scripts/build_multimodel_v8_histfix_matrix.py \
    --phase "$phase" \
    --artifact-root "${ARTIFACT_ROOT}" \
    --config-dir "${CONFIG_DIR}" \
    --matrix-dir "${matrix_dir}" \
    --bundle-run-id "${BUNDLE_RUN_ID}" \
    --data-start "${DATA_START}" \
    --cutoffs "${cutoff_args[@]}"
}

run_phase_queue() {
  local matrix_dir="$1"
  local ordinary_max="$2"
  bash scripts/run_multimodel_v8_queue.sh \
    --matrix-dir "${matrix_dir}" \
    --artifact-root "${ARTIFACT_ROOT}" \
    --ordinary-max-concurrent "${ordinary_max}" \
    --pause-free-gb "${PAUSE_FREE_GB}" \
    --launch-free-gb "${LAUNCH_FREE_GB}" \
    --heavy-free-gb "${HEAVY_FREE_GB}" \
    --poll-seconds "${POLL_SECONDS}"
}

cat <<EOF
multimodel v8 hist-fix campaign settings:
  artifact_root=${ARTIFACT_ROOT}
  config_dir=${CONFIG_DIR}
  bundle_run_id=${BUNDLE_RUN_ID}
  data_start=${DATA_START}
  glofas_ready_end=${GLOFAS_READY_END}
  glofas_recovery_family_root=${GLOFAS_RECOVERY_FAMILY_ROOT}
  glofas_refill_workers=${GLOFAS_REFILL_WORKERS}
  glofas_refill_passes=${GLOFAS_REFILL_PASSES}
  cutoffs=${CUTS[*]}
  start_at_phase=${START_AT_PHASE}
  stop_after_phase=${STOP_AFTER_PHASE}
  tt_matrix_dir=${TT_DIR}
  c100_matrix_dir=${C100_DIR}
  cf1_matrix_dir=${CF1_DIR}
  tt_ordinary_max_concurrent=${TT_ORDINARY_MAX_CONCURRENT}
  mv_ordinary_max_concurrent=${MV_ORDINARY_MAX_CONCURRENT}
  pause_free_gb=${PAUSE_FREE_GB}
  launch_free_gb=${LAUNCH_FREE_GB}
  heavy_free_gb=${HEAVY_FREE_GB}
  poll_seconds=${POLL_SECONDS}
EOF

if should_run_phase sources; then
  ensure_sources
fi
if should_run_phase bundles; then
  build_bundles
fi
if should_run_phase tt; then
  build_phase tt "${TT_DIR}"
  run_phase_queue "${TT_DIR}" "${TT_ORDINARY_MAX_CONCURRENT}"
fi
if should_run_phase c100; then
  build_phase c100 "${C100_DIR}"
  run_phase_queue "${C100_DIR}" "${MV_ORDINARY_MAX_CONCURRENT}"
fi
if should_run_phase cf1; then
  build_phase cf1 "${CF1_DIR}"
  run_phase_queue "${CF1_DIR}" "${MV_ORDINARY_MAX_CONCURRENT}"
fi

echo "hist-fix campaign complete"

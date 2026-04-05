#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ARTIFACT_ROOT="${MULTIMODEL_V8_ARTIFACT_ROOT:-/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402}"
INPUT_SOURCE_ROOT="${MULTIMODEL_V8_INPUT_SOURCE_ROOT:-/data/muscat_data/jaguir26/project1_ucsc_phd}"

PHASE_A_DIR="${ARTIFACT_ROOT}/control/cfactor1_main_20260405"
PHASE_B_DIR="${ARTIFACT_ROOT}/control/cfactor1_20221225_loweps_20260405"

FIT_PARALLEL_MODE="${MULTIMODEL_V8_CF1_FIT_PARALLEL_MODE:-global_models}"
FIT_PARALLEL_WORKERS="${MULTIMODEL_V8_CF1_FIT_PARALLEL_WORKERS:-14}"
MULTIVAR_C_FACTOR="${MULTIMODEL_V8_CF1_MULTIVAR_C_FACTOR:-1}"

ORDINARY_MAX_CONCURRENT="${MULTIMODEL_V8_CF1_ORDINARY_MAX_CONCURRENT:-2}"
PAUSE_FREE_GB="${MULTIMODEL_V8_CF1_PAUSE_FREE_GB:-180}"
LAUNCH_FREE_GB="${MULTIMODEL_V8_CF1_LAUNCH_FREE_GB:-220}"
HEAVY_FREE_GB="${MULTIMODEL_V8_CF1_HEAVY_FREE_GB:-240}"
POLL_SECONDS="${MULTIMODEL_V8_CF1_POLL_SECONDS:-60}"

export MULTIMODEL_V8_ARTIFACT_ROOT="${ARTIFACT_ROOT}"
export MULTIMODEL_V8_INPUT_SOURCE_ROOT="${INPUT_SOURCE_ROOT}"

build_phase_a() {
  python3 scripts/build_multimodel_v8_matrix_configs.py \
    --matrix-dir "${PHASE_A_DIR}" \
    --artifact-root "${ARTIFACT_ROOT}" \
    --cutoffs 20211112 20210123 20211221 20220511 20221225 \
    --epsilon-spec epsTTcf1=tt \
    --epsilon-spec eps30cf1=30 \
    --epsilon-spec eps90cf1=90 \
    --epsilon-spec eps180cf1=180 \
    --epsilon-spec eps360cf1=360 \
    --multivar-c-factor "${MULTIVAR_C_FACTOR}" \
    --fit-parallel-mode "${FIT_PARALLEL_MODE}" \
    --fit-parallel-workers "${FIT_PARALLEL_WORKERS}"
}

build_phase_b() {
  python3 scripts/build_multimodel_v8_matrix_configs.py \
    --matrix-dir "${PHASE_B_DIR}" \
    --artifact-root "${ARTIFACT_ROOT}" \
    --cutoffs 20221225 \
    --epsilon-spec eps25cf1=25 \
    --epsilon-spec eps20cf1=20 \
    --epsilon-spec eps15cf1=15 \
    --epsilon-spec eps10cf1=10 \
    --epsilon-spec eps5cf1=5 \
    --epsilon-spec eps1cf1=1 \
    --multivar-c-factor "${MULTIVAR_C_FACTOR}" \
    --fit-parallel-mode "${FIT_PARALLEL_MODE}" \
    --fit-parallel-workers "${FIT_PARALLEL_WORKERS}"
}

run_phase_queue() {
  local matrix_dir="$1"
  bash scripts/run_multimodel_v8_queue.sh \
    --matrix-dir "${matrix_dir}" \
    --artifact-root "${ARTIFACT_ROOT}" \
    --ordinary-max-concurrent "${ORDINARY_MAX_CONCURRENT}" \
    --pause-free-gb "${PAUSE_FREE_GB}" \
    --launch-free-gb "${LAUNCH_FREE_GB}" \
    --heavy-free-gb "${HEAVY_FREE_GB}" \
    --poll-seconds "${POLL_SECONDS}"
}

echo "cf1 campaign settings:"
echo "  artifact_root=${ARTIFACT_ROOT}"
echo "  input_source_root=${INPUT_SOURCE_ROOT}"
echo "  multivar_c_factor=${MULTIVAR_C_FACTOR}"
echo "  fit_parallel_mode=${FIT_PARALLEL_MODE}"
echo "  fit_parallel_workers=${FIT_PARALLEL_WORKERS}"
echo "  ordinary_max_concurrent=${ORDINARY_MAX_CONCURRENT}"
echo "  phase_a_dir=${PHASE_A_DIR}"
echo "  phase_b_dir=${PHASE_B_DIR}"

build_phase_a
run_phase_queue "${PHASE_A_DIR}"

build_phase_b
run_phase_queue "${PHASE_B_DIR}"

echo "cf1 campaign complete"

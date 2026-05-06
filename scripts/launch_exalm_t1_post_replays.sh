#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

MANIFEST_REL="${1:-repro/manifests/exalm_t1_authoritative_runs_20260505.csv}"
CONFIG_DIR_REL="${2:-config/unified_runs_exalm_t1_postreplay_20260505}"
SUFFIX="${3:-20260505}"
LOG_DIR_REL="${4:-repro/logs/exalm_t1_postreplay_${SUFFIX}}"
SNAPSHOT_ROOT_REL="${5:-repro/frozen_shared_inputs/exalm_t1_authoritative_20260505}"

mkdir -p "${REPO_ROOT}/${LOG_DIR_REL}"

python3 "${REPO_ROOT}/scripts/prepare_exalm_t1_replay_snapshots.py" \
  --manifest "${MANIFEST_REL}" \
  --out-root "${SNAPSHOT_ROOT_REL}" >/dev/null

python3 "${REPO_ROOT}/scripts/build_exalm_t1_post_replay_configs.py" \
  --manifest "${MANIFEST_REL}" \
  --out-dir "${CONFIG_DIR_REL}" \
  --snapshot-root "${SNAPSHOT_ROOT_REL}" \
  --suffix "${SUFFIX}" >/dev/null

export CLEANUP_RDATA_AFTER_POST=0

for cfg in "${REPO_ROOT}/${CONFIG_DIR_REL}"/paper_exalm_t1_postreplay_*_"${SUFFIX}".yaml; do
  run_id="$(basename "${cfg}" .yaml)"
  log_path="${REPO_ROOT}/${LOG_DIR_REL}/${run_id}.log"
  echo "[launch] ${run_id}"
  (
    cd "${REPO_ROOT}"
    Rscript --vanilla scripts/unified_run.R --config "${cfg}"
  ) 2>&1 | tee "${log_path}"
done

python3 "${REPO_ROOT}/scripts/verify_exalm_t1_post_replays.py" \
  --manifest "${MANIFEST_REL}" \
  --suffix "${SUFFIX}"

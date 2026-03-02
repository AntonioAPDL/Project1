#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${1:-${ROOT_DIR}/config/nws_operational_latest.yaml}"
LOG_DIR="${ROOT_DIR}/logs/nws_operational_latest"
RUN_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_LOG="${LOG_DIR}/run_${RUN_STAMP}.log"
RUN_LOCK="${LOG_DIR}/run.lock"

mkdir -p "${LOG_DIR}"
CONFIG_PATH="$(realpath -m "${CONFIG_PATH}")"

exec 9>"${RUN_LOCK}"
if ! flock -n 9; then
  echo "[INFO] $(date -u +%Y-%m-%dT%H:%M:%SZ) another NWS latest updater run is in progress; skipping."
  exit 0
fi

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "[ERROR] missing config: ${CONFIG_PATH}" | tee -a "${RUN_LOG}"
  exit 2
fi

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"

echo "[INFO] ===== NWS latest updater run started ${RUN_STAMP} =====" | tee -a "${RUN_LOG}"
echo "[INFO] repo_root=${ROOT_DIR}" | tee -a "${RUN_LOG}"
echo "[INFO] config=${CONFIG_PATH}" | tee -a "${RUN_LOG}"

set +e
python3 "${ROOT_DIR}/scripts/nws_operational_latest_update.py" \
  --repo-root "${ROOT_DIR}" \
  --config "${CONFIG_PATH}" 2>&1 | tee -a "${RUN_LOG}"
rc=${PIPESTATUS[0]}
set -e

ln -sfn "$(basename "${RUN_LOG}")" "${LOG_DIR}/latest.log"
echo "[INFO] ===== NWS latest updater run finished rc=${rc} =====" | tee -a "${RUN_LOG}"
exit "${rc}"

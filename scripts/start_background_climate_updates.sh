#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_END_DATE="${1:-2026-02-24}"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${ROOT_DIR}/logs/climate_updates"

mkdir -p "${LOG_DIR}"

PPT_LOG="${LOG_DIR}/ppt_update_${STAMP}.log"
SOIL_LOG="${LOG_DIR}/soil_update_${STAMP}.log"
PPT_SESSION="climate_ppt_${STAMP}"
SOIL_SESSION="climate_soil_${STAMP}"

tmux new-session -d -s "${PPT_SESSION}" \
  "bash ${ROOT_DIR}/scripts/update_ppt_incremental.sh ${TARGET_END_DATE} 2>&1 | tee ${PPT_LOG}"
tmux new-session -d -s "${SOIL_SESSION}" \
  "bash ${ROOT_DIR}/scripts/update_soil_incremental.sh ${TARGET_END_DATE} 2>&1 | tee ${SOIL_LOG}"

echo "PPT session: ${PPT_SESSION}"
echo "PPT log: ${PPT_LOG}"
echo "SOIL session: ${SOIL_SESSION}"
echo "SOIL log: ${SOIL_LOG}"
echo "Attach: tmux attach -t ${PPT_SESSION}"
echo "Attach: tmux attach -t ${SOIL_SESSION}"

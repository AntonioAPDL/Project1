#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_END_DATE="${1:-$(date -u +%Y-%m-%d)}"
LOG_DIR="${ROOT_DIR}/logs/climate_updates"
RUN_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_LOG="${LOG_DIR}/run_${RUN_STAMP}.log"
RUN_LOCK="${LOG_DIR}/run.lock"
STATUS_CSV="${ROOT_DIR}/climate_series_status.csv"
COMBINED_CSV="${ROOT_DIR}/climate_daily_ppt_soil.csv"

mkdir -p "${LOG_DIR}"

exec 9>"${RUN_LOCK}"
if ! flock -n 9; then
  echo "[INFO] $(date -u +%Y-%m-%dT%H:%M:%SZ) another climate update is in progress; skipping."
  exit 0
fi

echo "[INFO] ===== Climate update run started ${RUN_STAMP} =====" | tee -a "${RUN_LOG}"
echo "[INFO] target_end_date=${TARGET_END_DATE}" | tee -a "${RUN_LOG}"

overall_rc=0

echo "[INFO] Running PPT incremental update..." | tee -a "${RUN_LOG}"
if ! bash "${ROOT_DIR}/scripts/update_ppt_incremental.sh" "${TARGET_END_DATE}" >>"${RUN_LOG}" 2>&1; then
  echo "[ERROR] PPT incremental update failed." | tee -a "${RUN_LOG}"
  overall_rc=1
else
  echo "[OK] PPT incremental update finished." | tee -a "${RUN_LOG}"
fi

echo "[INFO] Running soil incremental update..." | tee -a "${RUN_LOG}"
if ! bash "${ROOT_DIR}/scripts/update_soil_incremental.sh" "${TARGET_END_DATE}" >>"${RUN_LOG}" 2>&1; then
  echo "[ERROR] Soil incremental update failed." | tee -a "${RUN_LOG}"
  overall_rc=1
else
  echo "[OK] Soil incremental update finished." | tee -a "${RUN_LOG}"
fi

echo "[INFO] Refreshing NWM retrospective soil series..." | tee -a "${RUN_LOG}"
if ! bash "${ROOT_DIR}/scripts/update_nwm_soil_retro_full.sh" "${TARGET_END_DATE}" >>"${RUN_LOG}" 2>&1; then
  echo "[ERROR] NWM retrospective soil refresh failed." | tee -a "${RUN_LOG}"
  overall_rc=1
else
  echo "[OK] NWM retrospective soil refresh finished." | tee -a "${RUN_LOG}"
fi

echo "[INFO] Refreshing climate status CSV..." | tee -a "${RUN_LOG}"
if ! python3 "${ROOT_DIR}/scripts/write_climate_series_status.py" \
  --root-dir "${ROOT_DIR}" \
  --target-date "${TARGET_END_DATE}" \
  --output-csv "${STATUS_CSV}" >>"${RUN_LOG}" 2>&1; then
  echo "[ERROR] Climate status CSV refresh failed." | tee -a "${RUN_LOG}"
  overall_rc=1
else
  echo "[OK] Climate status CSV refreshed: ${STATUS_CSV}" | tee -a "${RUN_LOG}"
fi

echo "[INFO] Refreshing combined climate CSV..." | tee -a "${RUN_LOG}"
if ! python3 "${ROOT_DIR}/scripts/build_climate_daily_combined_csv.py" \
  --ppt-csv "${ROOT_DIR}/prism_precipitation_santa_cruz_1987_2023.csv" \
  --soil-csv "${ROOT_DIR}/soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv" \
  --nwm-soil-csv "${ROOT_DIR}/soil_moisture_data/nwm_soil_moisture_big_trees_daily_1987_present.csv" \
  --output-csv "${COMBINED_CSV}" >>"${RUN_LOG}" 2>&1; then
  echo "[ERROR] Combined climate CSV refresh failed." | tee -a "${RUN_LOG}"
  overall_rc=1
else
  echo "[OK] Combined climate CSV refreshed: ${COMBINED_CSV}" | tee -a "${RUN_LOG}"
fi

ln -sfn "$(basename "${RUN_LOG}")" "${LOG_DIR}/latest.log"
echo "[INFO] ===== Climate update run finished rc=${overall_rc} =====" | tee -a "${RUN_LOG}"
exit "${overall_rc}"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs/nws_operational_latest"
RUNNER="${ROOT_DIR}/scripts/run_nws_operational_latest_update.sh"
CRON_SCHEDULE="${1:-11 */6 * * *}"
BEGIN_MARKER="# >>> project1 nws operational latest >>>"
END_MARKER="# <<< project1 nws operational latest <<<"

mkdir -p "${LOG_DIR}"

if [[ ! -x "${RUNNER}" ]]; then
  echo "[ERROR] Runner not executable: ${RUNNER}"
  exit 1
fi

tmp_existing="$(mktemp)"
tmp_new="$(mktemp)"
trap 'rm -f "${tmp_existing}" "${tmp_new}"' EXIT

crontab -l >"${tmp_existing}" 2>/dev/null || true

awk -v begin="${BEGIN_MARKER}" -v end="${END_MARKER}" '
  $0 == begin {skip=1; next}
  $0 == end   {skip=0; next}
  !skip {print}
' "${tmp_existing}" > "${tmp_new}"

{
  echo "${BEGIN_MARKER}"
  echo "${CRON_SCHEDULE} ${RUNNER} >> ${LOG_DIR}/cron_driver.log 2>&1"
  echo "${END_MARKER}"
} >> "${tmp_new}"

crontab "${tmp_new}"

echo "[OK] Installed NWS operational latest cron block."
echo "[OK] Schedule: ${CRON_SCHEDULE}"
echo "[OK] Runner: ${RUNNER}"
echo "[OK] Driver log: ${LOG_DIR}/cron_driver.log"

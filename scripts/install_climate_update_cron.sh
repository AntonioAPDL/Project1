#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs/climate_updates"
RUNNER="${ROOT_DIR}/scripts/run_climate_updates_cron.sh"
CRON_SCHEDULE="${1:-17 */6 * * *}"
BEGIN_MARKER="# >>> project1 climate updates >>>"
END_MARKER="# <<< project1 climate updates <<<"

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

echo "[OK] Installed climate update cron block."
echo "[OK] Schedule: ${CRON_SCHEDULE}"
echo "[OK] Runner: ${RUNNER}"
echo "[OK] Driver log: ${LOG_DIR}/cron_driver.log"


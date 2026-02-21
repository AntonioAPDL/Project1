#!/usr/bin/env bash
set -euo pipefail

RUN_ID="prod_canonical_full_e2e_parallel_onecore_refresh_20260221"
RUN_ROOT="repro/runs/${RUN_ID}"
SCHEDULE_ROOT="${RUN_ROOT}/healthchecks/scheduled_checkin_6h"
DELAY_SECONDS=21600
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUN_ROOT_ABS="${REPO_ROOT}/${RUN_ROOT}"

mkdir -p "${SCHEDULE_ROOT}"

SCHEDULED_AT_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
TRIGGER_AT_UTC="$(date -u -d "+${DELAY_SECONDS} seconds" +"%Y-%m-%dT%H:%M:%SZ")"
CHECK_DIR="${SCHEDULE_ROOT}/checkin_${TRIGGER_AT_UTC//[:]/}"
LOG_PATH="${CHECK_DIR}/scheduled_checkin.log"
CHECK_DIR_ABS="${REPO_ROOT}/${CHECK_DIR}"
LOG_PATH_ABS="${REPO_ROOT}/${LOG_PATH}"
mkdir -p "${CHECK_DIR}"
AT_WHEN="$(date -u -d "+${DELAY_SECONDS} seconds" +"%H:%M %m/%d/%Y")"

cat > "${CHECK_DIR}/schedule_meta.env" <<EOF
RUN_ID=${RUN_ID}
RUN_ROOT=${RUN_ROOT}
SCHEDULED_AT_UTC=${SCHEDULED_AT_UTC}
TRIGGER_AT_UTC=${TRIGGER_AT_UTC}
CHECK_DIR=${CHECK_DIR}
LOG_PATH=${LOG_PATH}
DELAY_SECONDS=${DELAY_SECONDS}
EOF

CMD="cd ${REPO_ROOT} && python3 repro/tools/unified_run_healthcheck.py --run-id ${RUN_ID} --run-root ${RUN_ROOT_ABS} --output-dir ${CHECK_DIR_ABS} --emit-s3-on-pass > ${LOG_PATH_ABS} 2>&1"
printf '%s\n' "${CMD}" > "${CHECK_DIR}/at_command.sh"
chmod +x "${CHECK_DIR}/at_command.sh"
AT_OUTPUT="$(at -M -f "${CHECK_DIR}/at_command.sh" "${AT_WHEN}" 2>&1)"
AT_JOB_ID="$(printf '%s\n' "${AT_OUTPUT}" | awk '/^job[[:space:]]+[0-9]+/{print $2; exit}')"

cat > "${CHECK_DIR}/scheduled_job.txt" <<EOF
at_job_id=${AT_JOB_ID}
at_when_utc=${AT_WHEN}
scheduled_at_utc=${SCHEDULED_AT_UTC}
trigger_at_utc=${TRIGGER_AT_UTC}
check_dir=${CHECK_DIR}
log_path=${LOG_PATH}
command=${CMD}
at_output=${AT_OUTPUT}
EOF

echo "scheduled_at_utc=${SCHEDULED_AT_UTC}"
echo "trigger_at_utc=${TRIGGER_AT_UTC}"
echo "at_job_id=${AT_JOB_ID}"
echo "check_dir=${CHECK_DIR}"
echo "log_path=${LOG_PATH}"

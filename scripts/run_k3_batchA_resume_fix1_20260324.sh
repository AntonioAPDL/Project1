#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
BATCH_LOG="${BATCH_LOG_OVERRIDE:-${REPO_ROOT}/repro/hardening_logs/J4_batch_monitor_resume_fix1_${ts}.log}"

CONFIGS=(
  "config/unified_runs/prod_phaseK3_batchA_20210123_l1_fix1_20260324.yaml"
  "config/unified_runs/prod_phaseK3_batchA_20210123_l2_20260324.yaml"
  "config/unified_runs/prod_phaseK3_batchA_20211112_l1_20260324.yaml"
  "config/unified_runs/prod_phaseK3_batchA_20211112_l2_20260324.yaml"
)

mkdir -p "$(dirname "${BATCH_LOG}")"

if [[ -n "${BATCH_LOG_OVERRIDE:-}" && -f "${BATCH_LOG}" ]]; then
  {
    echo "=== RESUME SEGMENT START ==="
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "batch=batchA"
    echo "cutoffs=20210123 20211112"
    echo "configs=${CONFIGS[*]}"
    echo "runner=$(realpath "$0")"
  } >> "${BATCH_LOG}"
else
  {
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "batch=batchA"
    echo "cutoffs=20210123 20211112"
    echo "configs=${CONFIGS[*]}"
    echo "runner=$(realpath "$0")"
  } > "${BATCH_LOG}"
fi

append_gate_block() {
  local cfg="$1"
  local launcher_log="$2"
  Rscript --vanilla \
    "${REPO_ROOT}/scripts/gate_batch_run.R" \
    "${REPO_ROOT}" \
    "${cfg}" \
    "${launcher_log}" \
    "${BATCH_LOG}"
}

for cfg in "${CONFIGS[@]}"; do
  run_id="$(Rscript --vanilla -e "suppressPackageStartupMessages(library(yaml)); cat(read_yaml('${cfg}')\$run\$run_id)")"
  cutoff="$(Rscript --vanilla -e "suppressPackageStartupMessages(library(yaml)); x<-read_yaml('${cfg}'); cat(gsub('-', '', x\$dates\$cutoff_date))")"
  lane="$(basename "${cfg}" .yaml | awk -F'_' '{print $(NF-1)}')"
  expected_ndlm_mode="$(Rscript --vanilla -e "suppressPackageStartupMessages(library(yaml)); cat(read_yaml('${cfg}')\$models\$ndlm_main\$forecast_transfer_mode)")"
  launcher_log="${REPO_ROOT}/repro/hardening_logs/${run_id}.launcher.log"

  {
    echo "=== START run_id ${run_id} ==="
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "config=${cfg}"
    echo "cutoff=${cutoff}"
    echo "lane=${lane}"
  } >> "${BATCH_LOG}"

  if ! "${REPO_ROOT}/scripts/run_unified_with_cleanup.sh" --config "${cfg}" > "${launcher_log}" 2>&1; then
    {
      echo "RUN_EXIT=fail"
      echo "launcher_log=${launcher_log}"
    } >> "${BATCH_LOG}"
    exit 1
  fi

  echo "RUN_EXIT=pass" >> "${BATCH_LOG}"
  append_gate_block "${cfg}" "${launcher_log}"
done

{
  echo "=== BATCH COMPLETE ==="
  echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "${BATCH_LOG}"

echo "${BATCH_LOG}"

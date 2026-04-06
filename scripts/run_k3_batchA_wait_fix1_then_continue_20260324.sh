#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
BATCH_LOG="${BATCH_LOG_OVERRIDE:-${REPO_ROOT}/repro/hardening_logs/J4_batch_monitor_wait_fix1_then_continue_${ts}.log}"
CFG="config/unified_runs/prod_phaseK3_batchA_20210123_l1_fix1_20260324.yaml"
RUN_ID="$(Rscript --vanilla -e "suppressPackageStartupMessages(library(yaml)); cat(read_yaml('${CFG}')\$run\$run_id)")"
RUN_ROOT="${REPO_ROOT}/repro/runs/${RUN_ID}"
MANIFEST="${RUN_ROOT}/run_manifest.yaml"
LAUNCHER_LOG="${REPO_ROOT}/repro/hardening_logs/${RUN_ID}.launcher.log"

mkdir -p "$(dirname "${BATCH_LOG}")"

{
  echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "mode=wait_fix1_then_continue"
  echo "target_config=${CFG}"
  echo "target_run_id=${RUN_ID}"
  echo "runner=$(realpath "$0")"
} > "${BATCH_LOG}"

while true; do
  if [[ ! -f "${MANIFEST}" ]]; then
    {
      echo "wait_status=manifest_missing"
      echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    } >> "${BATCH_LOG}"
    sleep 60
    continue
  fi

  status_triplet="$(Rscript --vanilla -e "suppressPackageStartupMessages(library(yaml)); x<-read_yaml('${MANIFEST}'); cat(paste(vapply(c('fit','post','report'), function(s) { y<-x\$stages[[s]]\$status; if (is.null(y)) 'missing' else y }, character(1)), collapse=' '))")"
  {
    echo "wait_status=${status_triplet}"
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >> "${BATCH_LOG}"

  if [[ "${status_triplet}" == "pass pass pass" ]]; then
    break
  fi

  if [[ "${status_triplet}" =~ fail|error ]]; then
    echo "wait_result=target_run_failed" >> "${BATCH_LOG}"
    exit 1
  fi

  sleep 60
done

Rscript --vanilla \
  "${REPO_ROOT}/scripts/gate_batch_run.R" \
  "${REPO_ROOT}" \
  "${CFG}" \
  "${LAUNCHER_LOG}" \
  "${BATCH_LOG}"

{
  echo "wait_result=target_run_gate_pass"
  echo "handoff_runner=${REPO_ROOT}/scripts/run_k3_batchA_continue_after_fix1_20260324.sh"
  echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "${BATCH_LOG}"

BATCH_LOG_OVERRIDE="${BATCH_LOG}" \
  "${REPO_ROOT}/scripts/run_k3_batchA_continue_after_fix1_20260324.sh"

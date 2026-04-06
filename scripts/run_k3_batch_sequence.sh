#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_k3_batch_sequence.sh \
    --batch-name <name> \
    --cutoffs "<cutoff1 cutoff2 ...>" \
    --log-prefix <prefix> \
    [--next-runner <script>] \
    --config <yaml> [--config <yaml> ...]
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

BATCH_NAME=""
CUTOFFS=""
LOG_PREFIX=""
NEXT_RUNNER=""
CONFIGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --batch-name)
      BATCH_NAME="$2"
      shift 2
      ;;
    --cutoffs)
      CUTOFFS="$2"
      shift 2
      ;;
    --log-prefix)
      LOG_PREFIX="$2"
      shift 2
      ;;
    --next-runner)
      NEXT_RUNNER="$2"
      shift 2
      ;;
    --config)
      CONFIGS+=("$2")
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown arg: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${BATCH_NAME}" || -z "${CUTOFFS}" || -z "${LOG_PREFIX}" || "${#CONFIGS[@]}" -eq 0 ]]; then
  usage >&2
  exit 2
fi

ts="$(date -u +%Y%m%dT%H%M%SZ)"
BATCH_LOG="${BATCH_LOG_OVERRIDE:-${REPO_ROOT}/repro/hardening_logs/${LOG_PREFIX}_${ts}.log}"

mkdir -p "$(dirname "${BATCH_LOG}")"

if [[ -n "${BATCH_LOG_OVERRIDE:-}" && -f "${BATCH_LOG}" ]]; then
  {
    echo "=== BATCH SEGMENT START ==="
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "batch=${BATCH_NAME}"
    echo "cutoffs=${CUTOFFS}"
    echo "configs=${CONFIGS[*]}"
    echo "runner=$(realpath "$0")"
  } >> "${BATCH_LOG}"
else
  {
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "batch=${BATCH_NAME}"
    echo "cutoffs=${CUTOFFS}"
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

if [[ -n "${NEXT_RUNNER}" ]]; then
  {
    echo "next_runner=${NEXT_RUNNER}"
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >> "${BATCH_LOG}"
  BATCH_LOG_OVERRIDE="${BATCH_LOG}" "${NEXT_RUNNER}"
fi

echo "${BATCH_LOG}"

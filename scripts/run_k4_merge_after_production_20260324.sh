#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
BATCH_LOG="${BATCH_LOG_OVERRIDE:-${REPO_ROOT}/repro/hardening_logs/J4_k4_merge_${ts}.log}"

mkdir -p "$(dirname "${BATCH_LOG}")"

if [[ -n "${BATCH_LOG_OVERRIDE:-}" && -f "${BATCH_LOG}" ]]; then
  {
    echo "=== K4 MERGE START ==="
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "runner=$(realpath "$0")"
  } >> "${BATCH_LOG}"
else
  {
    echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "runner=$(realpath "$0")"
  } > "${BATCH_LOG}"
fi

mapfile -t merge_outputs < <(Rscript --vanilla "${REPO_ROOT}/scripts/merge_k4_benchmark_crps.R" "${REPO_ROOT}")

{
  echo "merge_status=pass"
  for path in "${merge_outputs[@]}"; do
    echo "merge_output=${path}"
  done
  echo "=== K4 MERGE COMPLETE ==="
  echo "timestamp_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "${BATCH_LOG}"

printf '%s\n' "${merge_outputs[@]}"

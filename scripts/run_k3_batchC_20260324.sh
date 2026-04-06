#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

"${REPO_ROOT}/scripts/run_k3_batch_sequence.sh" \
  --batch-name batchC \
  --cutoffs "20221225" \
  --log-prefix "J4_batch_monitor_batchC" \
  --next-runner "${REPO_ROOT}/scripts/run_k4_merge_after_production_20260324.sh" \
  --config "config/unified_runs/prod_phaseK3_batchC_20221225_l1_20260324.yaml" \
  --config "config/unified_runs/prod_phaseK3_batchC_20221225_l2_20260324.yaml"

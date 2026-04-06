#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

"${REPO_ROOT}/scripts/run_k3_batch_sequence.sh" \
  --batch-name batchB \
  --cutoffs "20211221 20220511" \
  --log-prefix "J4_batch_monitor_batchB_then_C" \
  --next-runner "${REPO_ROOT}/scripts/run_k3_batchC_20260324.sh" \
  --config "config/unified_runs/prod_phaseK3_batchB_20211221_l1_20260324.yaml" \
  --config "config/unified_runs/prod_phaseK3_batchB_20211221_l2_20260324.yaml" \
  --config "config/unified_runs/prod_phaseK3_batchB_20220511_l1_20260324.yaml" \
  --config "config/unified_runs/prod_phaseK3_batchB_20220511_l2_20260324.yaml"

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPLAY_RUN_ID="prod_phaseK3_batchB_20220511_l1_post_replay_fix1_20260324"
REPLAY_MANIFEST="${REPO_ROOT}/repro/runs/${REPLAY_RUN_ID}/run_manifest.yaml"
BATCH_LOG="${REPO_ROOT}/repro/hardening_logs/J4_batch_monitor_batchB_then_C_20260324T202506Z.log"

status_of() {
  local stage_name="$1"
  Rscript --vanilla -e "suppressPackageStartupMessages(library(yaml)); x <- read_yaml('${REPLAY_MANIFEST}'); cat(x\$stages[['${stage_name}']]\$status)"
}

while true; do
  if [[ ! -f "${REPLAY_MANIFEST}" ]]; then
    echo "waiting_for_replay_manifest=${REPLAY_MANIFEST}"
    sleep 30
    continue
  fi

  post_status="$(status_of post)"
  case "${post_status}" in
    pass)
      break
      ;;
    fail)
      echo "replay_post_status=fail"
      exit 1
      ;;
    pending|skip)
      echo "replay_post_status=${post_status}"
      sleep 30
      ;;
    *)
      echo "replay_post_status=${post_status}"
      sleep 30
      ;;
  esac
done

BATCH_LOG_OVERRIDE="${BATCH_LOG}" "${REPO_ROOT}/scripts/run_k3_batch_sequence.sh" \
  --batch-name batchB_resume \
  --cutoffs "20220511" \
  --log-prefix "J4_batch_monitor_batchB_then_C" \
  --next-runner "${REPO_ROOT}/scripts/run_k3_batchC_20260324.sh" \
  --config "config/unified_runs/prod_phaseK3_batchB_20220511_l1_fix1_20260325.yaml" \
  --config "config/unified_runs/prod_phaseK3_batchB_20220511_l2_20260324.yaml"

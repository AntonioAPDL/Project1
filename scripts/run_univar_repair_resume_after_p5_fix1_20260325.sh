#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

STAMP="${1:-20260325}"
LOG_DIR="repro/hardening_logs"
mkdir -p "$LOG_DIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="$LOG_DIR/univar_repair_resume_after_p5_fix3_${TS}.log"

P5_BASE="config/unified_runs/repair_p5_univar_exal_triage_20210123_${STAMP}.yaml"
P5_SOURCE_RUN="repair_p5_univar_exal_triage_20210123_${STAMP}"
P5_REPLAY_RUN="repair_p5_univar_exal_triage_20210123_${STAMP}_post_replay_fix3"
P5_REPLAY_CFG="config/unified_runs/${P5_REPLAY_RUN}.yaml"

Rscript --vanilla scripts/build_post_replay_config.R \
  --base-config "$P5_BASE" \
  --source-run-id "$P5_SOURCE_RUN" \
  --run-id "$P5_REPLAY_RUN" \
  --out-config "$P5_REPLAY_CFG"

run_and_gate() {
  local cfg="$1"
  local run_id="$2"
  local model_id="$3"
  echo "RUN_START run_id=${run_id} config=${cfg} model_id=${model_id}" | tee -a "$LOG_FILE"
  CLEANUP_RDATA_AFTER_POST=0 Rscript --vanilla scripts/unified_run.R --config "$cfg" 2>&1 | tee -a "$LOG_FILE"
  echo "RUN_GATE_START run_id=${run_id}" | tee -a "$LOG_FILE"
  Rscript --vanilla scripts/gate_univar_repair_run.R --run-id "$run_id" --expected-model-id "$model_id" 2>&1 | tee -a "$LOG_FILE"
  echo "RUN_GATE_END run_id=${run_id}" | tee -a "$LOG_FILE"
}

echo "UNIVAR_REPAIR_RESUME_START ${TS}" | tee -a "$LOG_FILE"

run_and_gate "$P5_REPLAY_CFG" "$P5_REPLAY_RUN" "exdqlm_univar_synth"
run_and_gate "config/unified_runs/repair_p6_univar_exal_full7_20210123_${STAMP}.yaml" "repair_p6_univar_exal_full7_20210123_${STAMP}" "exdqlm_univar_synth"
run_and_gate "config/unified_runs/repair_p7_univar_al_triage_20210123_${STAMP}.yaml" "repair_p7_univar_al_triage_20210123_${STAMP}" "dqlm_univar_al_synth"
run_and_gate "config/unified_runs/repair_p7_univar_al_full7_20210123_${STAMP}.yaml" "repair_p7_univar_al_full7_20210123_${STAMP}" "dqlm_univar_al_synth"

echo "UNIVAR_REPAIR_RESUME_END $(date -u +%Y%m%dT%H%M%SZ)" | tee -a "$LOG_FILE"

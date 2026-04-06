#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

STAMP="${1:-20260325}"
CONFIG_DIR="config/unified_runs"
LOG_DIR="repro/hardening_logs"
mkdir -p "$LOG_DIR"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_FILE="$LOG_DIR/univar_repair_p5_p7_${TS}.log"

Rscript --vanilla scripts/build_univar_repair_configs.R --stamp "$STAMP" > "$LOG_DIR/univar_repair_config_paths_${TS}.txt"

mapfile -t CONFIGS < "$LOG_DIR/univar_repair_config_paths_${TS}.txt"

expected_model_id_for_cfg() {
  case "$1" in
    *repair_p5_univar_exal_triage*|*repair_p6_univar_exal_full7*)
      printf '%s\n' "exdqlm_univar_synth"
      ;;
    *repair_p7_univar_al_triage*|*repair_p7_univar_al_full7*)
      printf '%s\n' "dqlm_univar_al_synth"
      ;;
    *)
      return 1
      ;;
  esac
}

echo "UNIVAR_REPAIR_SEQUENCE_START ${TS}" | tee -a "$LOG_FILE"

for cfg in "${CONFIGS[@]}"; do
  run_id="$(basename "$cfg" .yaml)"
  model_id="$(expected_model_id_for_cfg "$cfg")"
  echo "RUN_START run_id=${run_id} config=${cfg} model_id=${model_id}" | tee -a "$LOG_FILE"
  CLEANUP_RDATA_AFTER_POST=0 Rscript --vanilla scripts/unified_run.R --config "$cfg" 2>&1 | tee -a "$LOG_FILE"
  echo "RUN_GATE_START run_id=${run_id}" | tee -a "$LOG_FILE"
  Rscript --vanilla scripts/gate_univar_repair_run.R --run-id "$run_id" --expected-model-id "$model_id" 2>&1 | tee -a "$LOG_FILE"
  echo "RUN_GATE_END run_id=${run_id}" | tee -a "$LOG_FILE"
done

echo "UNIVAR_REPAIR_SEQUENCE_END $(date -u +%Y%m%dT%H%M%SZ)" | tee -a "$LOG_FILE"

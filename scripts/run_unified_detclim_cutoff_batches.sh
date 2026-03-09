#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

timestamp_utc() {
  date -u +"%Y%m%dT%H%M%SZ"
}

RUN_TS="${RUN_TS:-$(timestamp_utc)}"
LOG_ROOT="${LOG_ROOT:-$ROOT/repro/tmp/unified_detclim_batches_${RUN_TS}}"
STATUS_TSV="${LOG_ROOT}/status.tsv"
RUNNER_LOG="${LOG_ROOT}/runner.log"
SNAPSHOT_CFG_DIR="${LOG_ROOT}/resolved_configs"

mkdir -p "$LOG_ROOT"
mkdir -p "$SNAPSHOT_CFG_DIR"

log() {
  local msg="$1"
  printf '[%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$msg" | tee -a "$RUNNER_LOG"
}

write_status_header() {
  if [[ ! -f "$STATUS_TSV" ]]; then
    printf 'batch\trun_id\tstatus\tlog_path\n' > "$STATUS_TSV"
  fi
}

record_status() {
  local batch="$1"
  local run_id="$2"
  local status="$3"
  local log_path="$4"
  printf '%s\t%s\t%s\t%s\n' "$batch" "$run_id" "$status" "$log_path" >> "$STATUS_TSV"
}

run_one() {
  local batch="$1"
  local run_id="$2"
  local cfg_path="$3"
  local run_dir="$ROOT/repro/runs/${run_id}"
  local run_log="${LOG_ROOT}/${run_id}.log"
  local snapshot_cfg="${SNAPSHOT_CFG_DIR}/${run_id}.yaml"

  log "Starting ${run_id} from ${cfg_path}"
  if [[ ! -f "$cfg_path" ]]; then
    log "Missing config ${cfg_path}"
    record_status "$batch" "$run_id" "fail_missing_config" "$run_log"
    return 1
  fi
  cp "$cfg_path" "$snapshot_cfg"
  if [[ -d "$run_dir" ]]; then
    log "Removing existing run directory ${run_dir}"
    rm -rf "$run_dir"
  fi
  mkdir -p "$(dirname "$run_dir")"

  if nice -n 10 Rscript --vanilla scripts/unified_run.R --config "$snapshot_cfg" >"$run_log" 2>&1; then
    record_status "$batch" "$run_id" "pass" "$run_log"
    log "Completed ${run_id}"
  else
    record_status "$batch" "$run_id" "fail" "$run_log"
    log "FAILED ${run_id}; see ${run_log}"
    return 1
  fi
}

run_batch() {
  local batch_label="$1"
  shift
  log "Batch ${batch_label} begin"
  while (( "$#" >= 2 )); do
    run_one "$batch_label" "$1" "$2"
    shift 2
  done
  log "Batch ${batch_label} complete"
}

write_status_header
cat > "${LOG_ROOT}/batch_plan.txt" <<'EOF'
batch1 multimodel_20210123 repro/runs/multimodel_20210123/resolved_config.yaml
batch1 multimodel_20211112 repro/runs/multimodel_20211112/resolved_config.yaml
batch2 multimodel_20211221 repro/runs/multimodel_20211221/resolved_config.yaml
batch2 multimodel_20220511 repro/runs/multimodel_20220511/resolved_config.yaml
batch3 multimodel_20221225 repro/runs/multimodel_20221225/resolved_config.yaml
EOF

log "Log root ${LOG_ROOT}"
run_batch batch1 \
  multimodel_20210123 repro/runs/multimodel_20210123/resolved_config.yaml \
  multimodel_20211112 repro/runs/multimodel_20211112/resolved_config.yaml
run_batch batch2 \
  multimodel_20211221 repro/runs/multimodel_20211221/resolved_config.yaml \
  multimodel_20220511 repro/runs/multimodel_20220511/resolved_config.yaml
run_batch batch3 \
  multimodel_20221225 repro/runs/multimodel_20221225/resolved_config.yaml
log "All batches complete"

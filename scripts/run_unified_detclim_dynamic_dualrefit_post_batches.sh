#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

timestamp_utc() {
  date -u +"%Y%m%dT%H%M%SZ"
}

RUN_TS="${RUN_TS:-$(timestamp_utc)}"
LOG_ROOT="${LOG_ROOT:-$ROOT/repro/tmp/unified_detclim_dynamic_dualrefit_post_${RUN_TS}}"
STATUS_TSV="${LOG_ROOT}/status.tsv"
RUNNER_LOG="${LOG_ROOT}/runner.log"
CFG_DIR="${LOG_ROOT}/configs"

mkdir -p "$LOG_ROOT" "$CFG_DIR"

log() {
  local msg="$1"
  printf '[%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$msg" | tee -a "$RUNNER_LOG"
}

write_status_header() {
  if [[ ! -f "$STATUS_TSV" ]]; then
    printf 'batch\trun_id\tfit_status\tpost_status\tfit_log\tpost_log\n' > "$STATUS_TSV"
  fi
}

record_status() {
  local batch="$1"
  local run_id="$2"
  local fit_status="$3"
  local post_status="$4"
  local fit_log="$5"
  local post_log="$6"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$batch" "$run_id" "$fit_status" "$post_status" "$fit_log" "$post_log" >> "$STATUS_TSV"
}

build_cfg() {
  local base_cfg="$1"
  local out_cfg="$2"
  local phase="$3"
  Rscript --vanilla scripts/build_detclim_selective_rerun_config.R \
    --base-config "$base_cfg" \
    --out-config "$out_cfg" \
    --phase "$phase" >/dev/null
}

clean_dual_refit_outputs() {
  local run_dir="$1"
  rm -rf \
    "${run_dir}"/fit/q=* \
    "${run_dir}/fit/exdqlm_multivar/keep" \
    "${run_dir}/fit/exdqlm_univar" \
    "${run_dir}/post"
}

run_one() {
  local batch="$1"
  local run_id="$2"
  local base_cfg="$3"
  local run_dir="$ROOT/repro/runs/${run_id}"
  local fit_cfg="${CFG_DIR}/${run_id}_fit.yaml"
  local post_cfg="${CFG_DIR}/${run_id}_post.yaml"
  local fit_log="${LOG_ROOT}/${run_id}_fit.log"
  local post_log="${LOG_ROOT}/${run_id}_post.log"

  log "Preparing ${run_id}"
  build_cfg "$base_cfg" "$fit_cfg" "fit_multivar_dual_univar"
  build_cfg "$base_cfg" "$post_cfg" "post_all"

  log "Cleaning dual-refit outputs for ${run_id}"
  clean_dual_refit_outputs "$run_dir"

  log "Starting dual multivar + univar fit rerun for ${run_id}"
  if nice -n 10 Rscript --vanilla scripts/unified_run.R --config "$fit_cfg" >"$fit_log" 2>&1; then
    log "Fit rerun complete for ${run_id}"
  else
    record_status "$batch" "$run_id" "fail" "not_started" "$fit_log" "$post_log"
    log "FAILED fit rerun for ${run_id}; see ${fit_log}"
    return 1
  fi

  log "Starting post rerun for ${run_id}"
  if nice -n 10 Rscript --vanilla scripts/unified_run.R --config "$post_cfg" >"$post_log" 2>&1; then
    record_status "$batch" "$run_id" "pass" "pass" "$fit_log" "$post_log"
    log "Completed ${run_id}"
  else
    record_status "$batch" "$run_id" "pass" "fail" "$fit_log" "$post_log"
    log "FAILED post rerun for ${run_id}; see ${post_log}"
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
batch1 multimodel_20211221 repro/runs/multimodel_20211221/resolved_config.yaml
batch2 multimodel_20220511 repro/runs/multimodel_20220511/resolved_config.yaml
batch2 multimodel_20221225 repro/runs/multimodel_20221225/resolved_config.yaml
EOF

log "Log root ${LOG_ROOT}"
run_batch batch1 \
  multimodel_20210123 repro/runs/multimodel_20210123/resolved_config.yaml \
  multimodel_20211112 repro/runs/multimodel_20211112/resolved_config.yaml \
  multimodel_20211221 repro/runs/multimodel_20211221/resolved_config.yaml
run_batch batch2 \
  multimodel_20220511 repro/runs/multimodel_20220511/resolved_config.yaml \
  multimodel_20221225 repro/runs/multimodel_20221225/resolved_config.yaml
log "All batches complete"

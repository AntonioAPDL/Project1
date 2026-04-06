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
STATUS_LOCK="${LOG_ROOT}/status.lock"
MAX_PARALLEL="${MAX_PARALLEL:-2}"
RUN_SUFFIX="${RUN_SUFFIX:-}"
MIN_FREE_GB="${MIN_FREE_GB:-120}"
CLEANUP_RDATA_ON_PASS="${CLEANUP_RDATA_ON_PASS:-0}"
CLEANUP_RDATA_AFTER_POST="${CLEANUP_RDATA_AFTER_POST:-0}"

mkdir -p "$LOG_ROOT"
mkdir -p "$SNAPSHOT_CFG_DIR"
touch "$STATUS_LOCK"

log() {
  local msg="$1"
  printf '[%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$msg" | tee -a "$RUNNER_LOG"
}

resolve_cfg_path() {
  local run_id="$1"
  local preferred_cfg="$2"
  local run_cfg="$ROOT/repro/runs/${run_id}/resolved_config.yaml"
  local rerun_full_cfg="$ROOT/repro/tmp/${run_id}_rerun_full.yaml"
  local fullhist_22_cfg="$ROOT/repro/tmp/${run_id}_fullhist_allmodels_22cores.yaml"

  local candidate=""
  for candidate in "$preferred_cfg" "$run_cfg" "$rerun_full_cfg" "$fullhist_22_cfg"; do
    if [[ -f "$candidate" ]]; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  return 1
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
  if command -v flock >/dev/null 2>&1; then
    (
      flock -x 9
      printf '%s\t%s\t%s\t%s\n' "$batch" "$run_id" "$status" "$log_path" >> "$STATUS_TSV"
    ) 9>>"$STATUS_LOCK"
  else
    printf '%s\t%s\t%s\t%s\n' "$batch" "$run_id" "$status" "$log_path" >> "$STATUS_TSV"
  fi
}

cleanup_rdata_for_run() {
  local run_dir="$1"
  if [[ ! -d "$run_dir" ]]; then
    return 0
  fi
  local before_count=0
  before_count=$(find "$run_dir" -type f \( -name '*.RData' -o -name '*.rdata' \) | wc -l | tr -d ' ')
  if [[ "$before_count" -gt 0 ]]; then
    find "$run_dir" -type f \( -name '*.RData' -o -name '*.rdata' \) -delete
    local after_count=0
    after_count=$(find "$run_dir" -type f \( -name '*.RData' -o -name '*.rdata' \) | wc -l | tr -d ' ')
    log "Failure cleanup for ${run_dir}: removed .RData files ${before_count} -> ${after_count}"
  fi
}

check_min_free_gb() {
  local min_free_gb="$1"
  local mount_path="$2"
  local free_gb=""
  local used_pct=""
  free_gb="$(df -Pk "$mount_path" | awk 'NR==2{printf "%.2f", $4/1024/1024}')"
  used_pct="$(df -Pk "$mount_path" | awk 'NR==2{printf "%.2f", 100-$4/$2*100}')"
  local below_min=0
  below_min="$(awk -v free="$free_gb" -v min="$min_free_gb" 'BEGIN{if (free < min) print 1; else print 0}')"
  if [[ "$below_min" == "1" ]]; then
    log "Insufficient free space on ${mount_path}: free_gb=${free_gb} used_pct=${used_pct} required_min_free_gb=${min_free_gb}"
    return 1
  fi
  log "Free space check ok on ${mount_path}: free_gb=${free_gb} used_pct=${used_pct} required_min_free_gb=${min_free_gb}"
  return 0
}

run_one() {
  local batch="$1"
  local run_id="$2"
  local cfg_path="$3"
  local run_dir="$ROOT/repro/runs/${run_id}"
  local run_log="${LOG_ROOT}/${run_id}.log"
  local snapshot_cfg="${SNAPSHOT_CFG_DIR}/${run_id}.yaml"
  local resolved_cfg=""

  resolved_cfg="$(resolve_cfg_path "$run_id" "$cfg_path" || true)"
  if [[ -z "$resolved_cfg" ]]; then
    log "Missing config for ${run_id}; checked ${cfg_path}, ${run_dir}/resolved_config.yaml, ${ROOT}/repro/tmp/${run_id}_rerun_full.yaml, ${ROOT}/repro/tmp/${run_id}_fullhist_allmodels_22cores.yaml"
    record_status "$batch" "$run_id" "fail_missing_config" "$run_log"
    return 1
  fi

  log "Starting ${run_id} from ${resolved_cfg}"
  cp "$resolved_cfg" "$snapshot_cfg"
  if ! check_min_free_gb "$MIN_FREE_GB" "$ROOT"; then
    record_status "$batch" "$run_id" "fail_low_disk" "$run_log"
    return 1
  fi
  if [[ -d "$run_dir" ]]; then
    log "Removing existing run directory ${run_dir}"
    rm -rf "$run_dir"
  fi
  mkdir -p "$(dirname "$run_dir")"

  if nice -n 10 env CLEANUP_RDATA_AFTER_POST="$CLEANUP_RDATA_AFTER_POST" Rscript --vanilla scripts/unified_run.R --config "$snapshot_cfg" >"$run_log" 2>&1; then
    if [[ "$CLEANUP_RDATA_ON_PASS" =~ ^(1|true|TRUE|yes|YES)$ ]]; then
      cleanup_rdata_for_run "$run_dir"
      log "Pass cleanup for ${run_dir}: .RData removal enabled"
    fi
    record_status "$batch" "$run_id" "pass" "$run_log"
    log "Completed ${run_id}"
  else
    cleanup_rdata_for_run "$run_dir"
    record_status "$batch" "$run_id" "fail" "$run_log"
    log "FAILED ${run_id}; see ${run_log}"
    return 1
  fi
}

run_batch() {
  local batch_label="$1"
  shift
  local max_parallel=2
  if [[ "$MAX_PARALLEL" =~ ^[0-9]+$ ]] && [[ "$MAX_PARALLEL" -ge 1 ]]; then
    max_parallel="$MAX_PARALLEL"
  fi

  log "Batch ${batch_label} begin (max_parallel=${max_parallel})"
  local -a pids=()
  local -a run_ids=()

  while (( "$#" >= 2 )); do
    local run_id="$1"
    local cfg_path="$2"
    shift 2

    run_one "$batch_label" "$run_id" "$cfg_path" &
    local pid=$!
    pids+=("$pid")
    run_ids+=("$run_id")
    log "Launched ${run_id} (pid=${pid})"

    while (( ${#pids[@]} >= max_parallel )); do
      local wait_pid="${pids[0]}"
      local wait_run="${run_ids[0]}"
      if wait "$wait_pid"; then
        log "Finished ${wait_run} (pid=${wait_pid})"
      else
        log "FAILED ${wait_run} (pid=${wait_pid})"
        local i=0
        for (( i = 1; i < ${#pids[@]}; i++ )); do
          wait "${pids[$i]}" || true
        done
        return 1
      fi
      pids=("${pids[@]:1}")
      run_ids=("${run_ids[@]:1}")
    done
  done

  local i=0
  for (( i = 0; i < ${#pids[@]}; i++ )); do
    local wait_pid="${pids[$i]}"
    local wait_run="${run_ids[$i]}"
    if wait "$wait_pid"; then
      log "Finished ${wait_run} (pid=${wait_pid})"
    else
      log "FAILED ${wait_run} (pid=${wait_pid})"
      local j=0
      for (( j = i + 1; j < ${#pids[@]}; j++ )); do
        wait "${pids[$j]}" || true
      done
      return 1
    fi
  done

  log "Batch ${batch_label} complete"
}

write_status_header
RUN_ID_20210123="multimodel_20210123${RUN_SUFFIX}"
RUN_ID_20211112="multimodel_20211112${RUN_SUFFIX}"
RUN_ID_20211221="multimodel_20211221${RUN_SUFFIX}"
RUN_ID_20220511="multimodel_20220511${RUN_SUFFIX}"
RUN_ID_20221225="multimodel_20221225${RUN_SUFFIX}"

CFG_20210123="repro/tmp/${RUN_ID_20210123}_rerun_full.yaml"
CFG_20211112="repro/tmp/${RUN_ID_20211112}_rerun_full.yaml"
CFG_20211221="repro/tmp/${RUN_ID_20211221}_rerun_full.yaml"
CFG_20220511="repro/tmp/${RUN_ID_20220511}_rerun_full.yaml"
CFG_20221225="repro/tmp/${RUN_ID_20221225}_rerun_full.yaml"

cat > "${LOG_ROOT}/batch_plan.txt" <<EOF
batch1 ${RUN_ID_20210123} ${CFG_20210123}
batch1 ${RUN_ID_20211112} ${CFG_20211112}
batch2 ${RUN_ID_20211221} ${CFG_20211221}
batch2 ${RUN_ID_20220511} ${CFG_20220511}
batch3 ${RUN_ID_20221225} ${CFG_20221225}
EOF

log "Log root ${LOG_ROOT}"
log "Runner settings: run_suffix='${RUN_SUFFIX}' max_parallel=${MAX_PARALLEL} min_free_gb=${MIN_FREE_GB} cleanup_rdata_on_pass=${CLEANUP_RDATA_ON_PASS} cleanup_rdata_after_post=${CLEANUP_RDATA_AFTER_POST}"
run_batch batch1 \
  "${RUN_ID_20210123}" "${CFG_20210123}" \
  "${RUN_ID_20211112}" "${CFG_20211112}"
run_batch batch2 \
  "${RUN_ID_20211221}" "${CFG_20211221}" \
  "${RUN_ID_20220511}" "${CFG_20220511}"
run_batch batch3 \
  "${RUN_ID_20221225}" "${CFG_20221225}"
log "All batches complete"

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

timestamp_utc() {
  date -u +"%Y%m%dT%H%M%SZ"
}

RUN_TS="${RUN_TS:-$(timestamp_utc)}"
DATA_START="${DATA_START:-1987-05-29}"
LOG_ROOT="${LOG_ROOT:-$ROOT/repro/tmp/unified_fullhist_19870529_${RUN_TS}}"
CFG_DIR="${LOG_ROOT}/configs"
STATUS_TSV="${LOG_ROOT}/status.tsv"
RUNNER_LOG="${LOG_ROOT}/runner.log"

mkdir -p "$LOG_ROOT" "$CFG_DIR"

log() {
  local msg="$1"
  printf '[%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$msg" | tee -a "$RUNNER_LOG"
}

write_status_header() {
  if [[ ! -f "$STATUS_TSV" ]]; then
    printf 'run_id\tstatus\tconfig\tlog\n' > "$STATUS_TSV"
  fi
}

record_status() {
  local run_id="$1"
  local status="$2"
  local cfg="$3"
  local log_path="$4"
  printf '%s\t%s\t%s\t%s\n' "$run_id" "$status" "$cfg" "$log_path" >> "$STATUS_TSV"
}

build_cfgs() {
  local base_cfg="$1"
  local out_cfg="$2"
  local out_fore_cfg="$3"
  Rscript --vanilla scripts/build_unified_fullhist_rerun_config.R \
    --base-config "$base_cfg" \
    --out-config "$out_cfg" \
    --out-forecats-config "$out_fore_cfg" \
    --data-start "$DATA_START" >/dev/null
}

clean_run_root() {
  local run_dir="$1"
  log "Cleaning stale outputs under ${run_dir}"
  find "$run_dir" -type f -name '*.RData' -delete
  rm -rf \
    "$run_dir/forecats" \
    "$run_dir/fit" \
    "$run_dir/post" \
    "$run_dir/validate" \
    "$run_dir/report" \
    "$run_dir/diagnostics" \
    "$run_dir/preflight" \
    "$run_dir/inputs/shared" \
    "$run_dir/run_manifest.yaml"
}

run_one() {
  local run_id="$1"
  local base_cfg="$2"
  local run_dir="$ROOT/repro/runs/${run_id}"
  local cfg_path="${CFG_DIR}/${run_id}_fullhist.yaml"
  local fore_cfg_path="${CFG_DIR}/${run_id}_forecats_fullhist.yaml"
  local log_path="${LOG_ROOT}/${run_id}.log"

  log "Preparing ${run_id}"
  build_cfgs "$base_cfg" "$cfg_path" "$fore_cfg_path"
  clean_run_root "$run_dir"

  log "Starting full rerun for ${run_id}"
  if nice -n 10 Rscript --vanilla scripts/unified_run.R --config "$cfg_path" >"$log_path" 2>&1; then
    record_status "$run_id" "pass" "$cfg_path" "$log_path"
    log "Completed ${run_id}"
  else
    record_status "$run_id" "fail" "$cfg_path" "$log_path"
    log "FAILED ${run_id}; see ${log_path}"
    return 1
  fi
}

write_status_header

cat > "${LOG_ROOT}/run_plan.txt" <<'EOF'
multimodel_20210123 repro/runs/multimodel_20210123/resolved_config.yaml
multimodel_20211112 repro/runs/multimodel_20211112/resolved_config.yaml
multimodel_20211221 repro/runs/multimodel_20211221/resolved_config.yaml
multimodel_20220511 repro/runs/multimodel_20220511/resolved_config.yaml
multimodel_20221225 repro/runs/multimodel_20221225/resolved_config.yaml
EOF

log "Log root ${LOG_ROOT}"
log "Using data_start=${DATA_START}"

while read -r run_id cfg_path; do
  [[ -n "${run_id}" ]] || continue
  run_one "$run_id" "$cfg_path"
done < "${LOG_ROOT}/run_plan.txt"

log "All full-history reruns complete"

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

timestamp_utc() {
  date -u +"%Y%m%dT%H%M%SZ"
}

RUN_TS="${RUN_TS:-$(timestamp_utc)}"
MATRIX_ROOT="${MATRIX_ROOT:-$ROOT/repro/tmp/unified_detclim_matrix_${RUN_TS}}"
MATRIX_LOG="$MATRIX_ROOT/matrix.log"
MATRIX_STATUS="$MATRIX_ROOT/matrix_status.tsv"
MATRIX_BATCHES="$MATRIX_ROOT/batches.tsv"

MAX_PARALLEL="${MAX_PARALLEL:-2}"
MIN_FREE_GB="${MIN_FREE_GB:-120}"
CLEANUP_RDATA_ON_PASS="${CLEANUP_RDATA_ON_PASS:-1}"
CLEANUP_RDATA_AFTER_POST="${CLEANUP_RDATA_AFTER_POST:-1}"
STOP_ACTIVE="${STOP_ACTIVE:-1}"
GENERATE_CONFIGS="${GENERATE_CONFIGS:-1}"
VALIDATE_CONFIGS="${VALIDATE_CONFIGS:-1}"
MATRIX_SUFFIXES="${MATRIX_SUFFIXES:-,_v2,_v3}"
MATRIX_SUFFIX_EPSILON_MAP="${MATRIX_SUFFIX_EPSILON_MAP:-}"

mkdir -p "$MATRIX_ROOT"

log() {
  local msg="$1"
  printf '[%s] %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$msg" | tee -a "$MATRIX_LOG"
}

build_suffix_epsilon_args() {
  local map="$1"
  if [[ -z "$map" ]]; then
    return 0
  fi
  local IFS=','
  local entries=()
  read -r -a entries <<< "$map"
  local entry=""
  for entry in "${entries[@]}"; do
    entry="$(echo "$entry" | xargs)"
    [[ -z "$entry" ]] && continue
    SUFFIX_EPSILON_ARGS+=(--suffix-epsilon "$entry")
  done
}

record_status() {
  local suffix="$1"
  local batch_root="$2"
  local status="$3"
  printf '%s\t%s\t%s\n' "$suffix" "$batch_root" "$status" >> "$MATRIX_STATUS"
}

stop_active_workers() {
  local pids
  pids=$(pgrep -f "scripts/unified_run\.R --config .*multimodel_" || true)
  local batch_pids
  batch_pids=$(pgrep -f "scripts/run_unified_detclim_cutoff_batches\.sh" || true)

  local all=""
  if [[ -n "$pids" ]]; then
    all="$pids"
  fi
  if [[ -n "$batch_pids" ]]; then
    if [[ -n "$all" ]]; then
      all+=$'\n'
    fi
    all+="$batch_pids"
  fi

  if [[ -z "$all" ]]; then
    log "No active unified/batch workers detected."
    return 0
  fi

  local unique
  unique=$(printf '%s\n' "$all" | awk 'NF>0 {print $1}' | sort -u)
  if [[ -z "$unique" ]]; then
    log "No active unified/batch workers detected after dedupe."
    return 0
  fi

  log "Stopping active workers: $(echo "$unique" | tr '\n' ' ')"
  while read -r pid; do
    [[ -z "$pid" ]] && continue
    if [[ "$pid" == "$$" ]]; then
      continue
    fi
    kill -TERM "$pid" 2>/dev/null || true
  done <<< "$unique"

  sleep 5

  local remain
  remain=$(printf '%s\n' "$unique" | while read -r pid; do
    [[ -z "$pid" ]] && continue
    if kill -0 "$pid" 2>/dev/null; then
      echo "$pid"
    fi
  done)

  if [[ -n "$remain" ]]; then
    log "Force-killing remaining workers: $(echo "$remain" | tr '\n' ' ')"
    while read -r pid; do
      [[ -z "$pid" ]] && continue
      kill -KILL "$pid" 2>/dev/null || true
    done <<< "$remain"
  fi
}

printf 'suffix\tbatch_root\tstatus\n' > "$MATRIX_STATUS"
printf 'suffix\tbatch_root\n' > "$MATRIX_BATCHES"

log "Matrix root: $MATRIX_ROOT"
log "Settings: max_parallel=$MAX_PARALLEL min_free_gb=$MIN_FREE_GB cleanup_on_pass=$CLEANUP_RDATA_ON_PASS cleanup_after_post=$CLEANUP_RDATA_AFTER_POST stop_active=$STOP_ACTIVE"
log "Matrix suffixes: ${MATRIX_SUFFIXES}"
if [[ -n "$MATRIX_SUFFIX_EPSILON_MAP" ]]; then
  log "Matrix suffix->epsilon map: ${MATRIX_SUFFIX_EPSILON_MAP}"
fi

declare -a SUFFIX_EPSILON_ARGS=()
build_suffix_epsilon_args "$MATRIX_SUFFIX_EPSILON_MAP"

if [[ "$STOP_ACTIVE" =~ ^(1|true|TRUE|yes|YES)$ ]]; then
  stop_active_workers
fi

if [[ "$GENERATE_CONFIGS" =~ ^(1|true|TRUE|yes|YES)$ ]]; then
  log "Generating strict rerun matrix configs"
  python3 scripts/build_unified_relaunch_matrix_configs.py --out-dir "$ROOT/repro/tmp" "${SUFFIX_EPSILON_ARGS[@]}"
fi

if [[ "$VALIDATE_CONFIGS" =~ ^(1|true|TRUE|yes|YES)$ ]]; then
  log "Validating strict rerun matrix configs"
  python3 scripts/validate_unified_relaunch_matrix_configs.py --config-dir "$ROOT/repro/tmp" "${SUFFIX_EPSILON_ARGS[@]}"
fi

launch_suffix_batch() {
  local suffix="$1"
  local tag="base"
  if [[ -n "$suffix" ]]; then
    tag="${suffix#_}"
  fi
  local batch_root="$MATRIX_ROOT/batch_${tag}"
  mkdir -p "$batch_root"
  printf '%s\t%s\n' "$suffix" "$batch_root" >> "$MATRIX_BATCHES"

  log "Launching suffix='${suffix:-<base>}' with LOG_ROOT=$batch_root"
  if RUN_SUFFIX="$suffix" \
      LOG_ROOT="$batch_root" \
      RUN_TS="$RUN_TS" \
      MAX_PARALLEL="$MAX_PARALLEL" \
      MIN_FREE_GB="$MIN_FREE_GB" \
      CLEANUP_RDATA_ON_PASS="$CLEANUP_RDATA_ON_PASS" \
      CLEANUP_RDATA_AFTER_POST="$CLEANUP_RDATA_AFTER_POST" \
      bash scripts/run_unified_detclim_cutoff_batches.sh; then
    record_status "$suffix" "$batch_root" "pass"
    log "Completed suffix='${suffix:-<base>}'"
  else
    record_status "$suffix" "$batch_root" "fail"
    log "FAILED suffix='${suffix:-<base>}'"
    return 1
  fi
}

IFS=',' read -r -a requested_suffixes <<< "$MATRIX_SUFFIXES"
for suffix in "${requested_suffixes[@]}"; do
  suffix="$(echo "$suffix" | xargs)"
  launch_suffix_batch "$suffix"
done

log "All matrix batches complete"

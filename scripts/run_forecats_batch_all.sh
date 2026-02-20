#!/usr/bin/env bash
set -euo pipefail

# Orchestrate the full batch run (audit -> build caches -> render) with sharding.
#
# Default config (San Lorenzo Big Trees / 11160500):
#   config/forecats_batch.site=11160500.default.yaml
#
# Usage:
#   bash scripts/run_forecats_batch_all.sh [CONFIG_PATH] [SHARDS]
#
# Notes:
# - NWS build is run single-process (loads `results.pkl` once).
# - GloFAS build + render are sharded/parallelized.
# - Outputs land under `data/forecats_inputs/` (ignored) and caches under `data/forecats_cache/` (ignored).

CONFIG_PATH="${1:-config/forecats_batch.site=11160500.default.yaml}"
SHARDS="${2:-4}"

cd /data/muscat_data/jaguir26/project1_ucsc_phd

CONFIG_PATH="$(realpath -m "$CONFIG_PATH")"

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"

if ! [[ "$SHARDS" =~ ^[0-9]+$ ]] || [[ "$SHARDS" -lt 1 ]]; then
  echo "[FATAL] SHARDS must be a positive integer (got: $SHARDS)" >&2
  exit 2
fi

# Compute batch_root the same way as scripts/forecats_batch.R.
BATCH_ROOT="$(
  CFG="$CONFIG_PATH" Rscript --vanilla - <<'RS'
suppressPackageStartupMessages(library(yaml))
cfg <- yaml::read_yaml(Sys.getenv("CFG"))
cache_root <- cfg$run$cache_root
site_id <- as.character(cfg$site$usgs_site)
run_id <- as.character(cfg$run$run_id)
cat(normalizePath(file.path(getwd(), cache_root, paste0("site=", site_id), paste0("run_id=", run_id)), mustWork = FALSE))
RS
)"

mkdir -p "$BATCH_ROOT/logs"

RUN_LOG="$BATCH_ROOT/logs/run_all.log"
touch "$RUN_LOG"

log() {
  # Print to stdout and append to run log (timestamped).
  echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] $*" | tee -a "$RUN_LOG"
}

log "START"
log "CONFIG=$CONFIG_PATH"
log "SHARDS=$SHARDS"
log "BATCH_ROOT=$BATCH_ROOT"

log "PHASE audit"
Rscript --vanilla scripts/forecats_batch.R \
  --config "$CONFIG_PATH" \
  --mode audit \
  2>&1 | tee "$BATCH_ROOT/logs/audit.log"

log "PHASE build-forecasts (NWS single-process, GloFAS sharded)"

PIDS=()

# NWS: single to avoid multiple results.pkl loads.
(
  nice -n 10 Rscript --vanilla scripts/forecats_batch.R \
    --config "$CONFIG_PATH" \
    --mode build-forecasts \
    --providers nws \
    --shard-count 1 \
    --shard-index 0 \
    2>&1 | tee "$BATCH_ROOT/logs/build_nws.log"
) &
PIDS+=("$!")

# GloFAS: sharded.
for i in $(seq 0 $((SHARDS - 1))); do
  (
    nice -n 10 Rscript --vanilla scripts/forecats_batch.R \
      --config "$CONFIG_PATH" \
      --mode build-forecasts \
      --providers glofas \
      --shard-count "$SHARDS" \
      --shard-index "$i" \
      2>&1 | tee "$BATCH_ROOT/logs/build_glofas_shard${i}.log"
  ) &
  PIDS+=("$!")
done

FAIL=0
for pid in "${PIDS[@]}"; do
  if ! wait "$pid"; then
    FAIL=1
  fi
done
if [[ "$FAIL" -ne 0 ]]; then
  log "PHASE build-forecasts FAILED (see logs in $BATCH_ROOT/logs)"
  exit 1
fi
log "PHASE build-forecasts DONE"

log "PHASE prepare shared cache skipped (handled by scripts/forecats_batch.R render mode)"

log "PHASE render (sharded)"

PIDS=()
for i in $(seq 0 $((SHARDS - 1))); do
  (
    nice -n 10 Rscript --vanilla scripts/forecats_batch.R \
      --config "$CONFIG_PATH" \
      --mode render \
      --shard-count "$SHARDS" \
      --shard-index "$i" \
      2>&1 | tee "$BATCH_ROOT/logs/render_shard${i}.log"
  ) &
  PIDS+=("$!")
done

FAIL=0
for pid in "${PIDS[@]}"; do
  if ! wait "$pid"; then
    FAIL=1
  fi
done
if [[ "$FAIL" -ne 0 ]]; then
  log "PHASE render FAILED (see logs in $BATCH_ROOT/logs)"
  exit 1
fi
log "PHASE render DONE"

log "PHASE summary"
BATCH_ROOT="$BATCH_ROOT" python3 - <<'PY' 2>&1 | tee "$BATCH_ROOT/logs/summary.log"
import csv
import glob
import os
from collections import Counter

batch_root = os.environ.get("BATCH_ROOT", "")
if not batch_root:
    # Best-effort locate from working dir (should match this script's layout)
    batch_root = glob.glob("data/forecats_cache/site=*/run_id=*")[0]

manifests = sorted(glob.glob(os.path.join(batch_root, "batch_manifest*.csv")))
print("batch_root:", batch_root)
print("manifests:", len(manifests))

ctr = Counter()
errors = []
rows_total = 0
for path in manifests:
    with open(path, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows_total += 1
            st = row.get("status", "")
            ctr[st] += 1
            if st not in ("success", "skipped_exists") and st:
                msg = (row.get("note", "") or "")[:200]
                errors.append((row.get("cutoff_date", ""), st, msg))

print("rows_total:", rows_total)
print("status_counts:", dict(ctr))
if errors:
    print("non_success_examples (first 20):")
    for d, st, msg in errors[:20]:
        print(f"  {d} {st} {msg}")
PY

log "DONE"

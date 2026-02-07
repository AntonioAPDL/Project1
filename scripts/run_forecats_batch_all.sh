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

log "PHASE prepare shared cache (USGS + retros)"
CFG="$CONFIG_PATH" BATCH="$BATCH_ROOT" Rscript --vanilla - <<'RS' 2>&1 | tee "$BATCH_ROOT/logs/prepare_shared_cache.log"
suppressPackageStartupMessages({
  library(yaml)
  library(readr)
  library(dplyr)
  library(dataRetrieval)
})

`%||%` <- function(x, y) if (is.null(x)) y else x

cfg <- yaml::read_yaml(Sys.getenv("CFG"))
batch_root <- Sys.getenv("BATCH")

pre_days <- as.integer(cfg$dates$plot_pre_days %||% 18)
post_days <- as.integer(cfg$dates$plot_post_days %||% 28)

seq_dates_inclusive <- function(start_date, end_date) seq.Date(as.Date(start_date), as.Date(end_date), by = "day")
cutoff_dates <- c()
for (iv in cfg$dates$intervals) cutoff_dates <- c(cutoff_dates, seq_dates_inclusive(iv$start, iv$end))
cutoff_dates <- sort(unique(as.Date(cutoff_dates)))

max_plot_end <- max(cutoff_dates + post_days)

cache_dir <- file.path(batch_root, "cache")
dir.create(cache_dir, showWarnings = FALSE, recursive = TRUE)

usgs_cache_path <- file.path(cache_dir, "usgs_daily.csv")
retros_cache_path <- file.path(cache_dir, "retros_daily_cms.csv")

CFSToCMS <- 0.028316846592

if (!file.exists(usgs_cache_path) || isTRUE(cfg$run$overwrite)) {
  message("[USGS] fetching daily values ...")
  usgs_site <- as.character(cfg$site$usgs_site)
  start_date <- as.character(cfg$site$usgs$start_date %||% "1979-01-01")
  parameterCd <- as.character(cfg$site$usgs$parameterCd %||% "00060")
  statCd <- as.character(cfg$site$usgs$statCd %||% "00003")

  dv <- dataRetrieval::readNWISdv(
    siteNumbers = usgs_site,
    parameterCd = parameterCd,
    statCd = statCd,
    startDate = start_date,
    endDate = as.character(max_plot_end)
  )
  if (!("Date" %in% names(dv))) stop("USGS dv missing Date column")
  if (!("X_00060_00003" %in% names(dv))) stop("USGS dv missing X_00060_00003 column (check statCd?)")

  out <- tibble::tibble(
    date = as.Date(dv$Date),
    discharge_cms = as.numeric(dv$X_00060_00003) * CFSToCMS
  )
  readr::write_csv(out, usgs_cache_path)
  message(sprintf("[USGS] wrote %s (%d rows)", usgs_cache_path, nrow(out)))
} else {
  message(sprintf("[USGS] cache exists, skipping: %s", usgs_cache_path))
}

if (!file.exists(retros_cache_path) || isTRUE(cfg$run$overwrite)) {
  message("[RETROS] building cache ...")
  in_path <- cfg$inputs$retros$path
  in_scale <- cfg$inputs$retros$scale %||% "log1p_cms"
  retro <- readr::read_csv(in_path, show_col_types = FALSE)
  if (!("Date" %in% names(retro))) stop("Retros CSV must contain Date column")

  nws_col <- NULL
  if ("NWS3.0" %in% names(retro)) nws_col <- "NWS3.0"
  if ("NWS" %in% names(retro)) nws_col <- "NWS"
  if (is.null(nws_col)) stop("Retros CSV missing NWS column (expected NWS3.0 or NWS)")

  convert_scale_to_cms <- function(x, scale) {
    if (scale == "raw_cms") return(x)
    if (scale == "log1p_cms") return(exp(x) - 1)
    stop(paste("Unknown scale:", scale))
  }

  out <- tibble::tibble(
    date = as.Date(retro$Date),
    usgs_cms = convert_scale_to_cms(retro$USGS, in_scale),
    glofas_cms = convert_scale_to_cms(retro$GloFAS, in_scale),
    nws_cms = convert_scale_to_cms(retro[[nws_col]], in_scale)
  ) %>% filter(date <= max_plot_end)

  readr::write_csv(out, retros_cache_path)
  message(sprintf("[RETROS] wrote %s (%d rows)", retros_cache_path, nrow(out)))
} else {
  message(sprintf("[RETROS] cache exists, skipping: %s", retros_cache_path))
}

message("[OK] shared cache ready")
RS

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

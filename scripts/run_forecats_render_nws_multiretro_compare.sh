#!/usr/bin/env bash
set -euo pipefail

# Launch background sharded rendering for the NWS multi-retro comparison run.
# This preserves existing outputs by using a separate run_id in config.
#
# Usage:
#   ./scripts/run_forecats_render_nws_multiretro_compare.sh [CONFIG] [SHARDS] [SOURCE_RUN_ID]
#
# Defaults:
#   CONFIG=config/forecats_batch.site=11160500.nws_multiretro_compare.yaml
#   SHARDS=8
#   SOURCE_RUN_ID=20260206_paper_default_latest

CONFIG_PATH="${1:-config/forecats_batch.site=11160500.nws_multiretro_compare.yaml}"
SHARDS="${2:-8}"
SOURCE_RUN_ID="${3:-20260206_paper_default_latest}"

ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd"
cd "$ROOT"

CONFIG_PATH="$(realpath -m "$CONFIG_PATH")"

if ! [[ "$SHARDS" =~ ^[0-9]+$ ]] || [[ "$SHARDS" -lt 1 ]]; then
  echo "[FATAL] SHARDS must be a positive integer (got: $SHARDS)" >&2
  exit 2
fi

readarray -t META < <(CFG="$CONFIG_PATH" Rscript --vanilla - <<'RS'
suppressPackageStartupMessages(library(yaml))
cfg <- yaml::read_yaml(Sys.getenv("CFG"))
cache_root <- cfg$run$cache_root
site_id <- as.character(cfg$site$usgs_site)
run_id <- as.character(cfg$run$run_id)
batch_root <- normalizePath(file.path(getwd(), cache_root, paste0("site=", site_id), paste0("run_id=", run_id)), mustWork = FALSE)
cat(site_id, "\n", sep = "")
cat(run_id, "\n", sep = "")
cat(batch_root, "\n", sep = "")
RS
)

SITE_ID="${META[0]}"
RUN_ID="${META[1]}"
BATCH_ROOT="${META[2]}"
LOG_DIR="$BATCH_ROOT/logs"
mkdir -p "$LOG_DIR"

echo "[INFO] CONFIG=$CONFIG_PATH"
echo "[INFO] SITE_ID=$SITE_ID"
echo "[INFO] RUN_ID=$RUN_ID"
echo "[INFO] SHARDS=$SHARDS"
echo "[INFO] BATCH_ROOT=$BATCH_ROOT"

# Copy forecast cache from the already-built run to avoid rebuild time.
SRC_BATCH_ROOT="$(realpath -m "data/forecats_cache/site=${SITE_ID}/run_id=${SOURCE_RUN_ID}")"
SRC_FC="$SRC_BATCH_ROOT/forecast_cache"
DST_FC="$BATCH_ROOT/forecast_cache"
if [[ -d "$SRC_FC" ]]; then
  mkdir -p "$DST_FC"
  echo "[STEP] Syncing forecast cache from source run: $SOURCE_RUN_ID"
  rsync -a "$SRC_FC/" "$DST_FC/"
else
  echo "[WARN] Source forecast cache not found: $SRC_FC"
  echo "[WARN] Render shards may produce waiting_forecast_cache status."
fi

# Pre-build shared caches once (USGS + retros) to avoid cross-shard race.
echo "[STEP] Preparing shared caches (USGS + retros)..."
CFG="$CONFIG_PATH" Rscript --vanilla - <<'RS' |& tee "$LOG_DIR/prepare_shared_cache.log"
suppressPackageStartupMessages({
  library(yaml)
  library(readr)
  library(dplyr)
  library(dataRetrieval)
})

source("scripts/forecats_batch.R", local = TRUE)

cfg <- yaml::read_yaml(Sys.getenv("CFG"))
cutoff_all <- compute_cutoff_dates(cfg)
post_days <- as.integer(cfg$dates$plot_post_days %||% 28)
max_plot_end <- max(as.Date(cutoff_all) + post_days)

batch_root <- file.path(
  as_abs_path(cfg$run$cache_root),
  paste0("site=", as.character(cfg$site$usgs_site)),
  paste0("run_id=", as.character(cfg$run$run_id))
)
ensure_dir(batch_root)
cache_dir <- file.path(batch_root, "cache")
ensure_dir(cache_dir)

usgs_cache <- file.path(cache_dir, "usgs_daily.csv")
retros_cache <- file.path(cache_dir, "retros_daily_cms.csv")

usgs <- fetch_usgs_cache(cfg, usgs_cache, max_plot_end)
retros <- build_retros_cache(cfg, retros_cache, max_plot_end)

cat(sprintf("[OK] usgs cache rows=%d path=%s\n", nrow(usgs), usgs_cache))
cat(sprintf("[OK] retros cache rows=%d path=%s\n", nrow(retros), retros_cache))
RS

TS="$(date -u +%Y%m%dT%H%M%SZ)"
META_FILE="$LOG_DIR/render_compare_sessions_${TS}.txt"
touch "$META_FILE"

echo "[STEP] Launching tmux render shards..."
for i in $(seq 0 $((SHARDS - 1))); do
  SESS="forecats_cmp_${i}_${TS}"
  LOG="$LOG_DIR/render_compare_shard${i}.log"
  CMD="cd $ROOT && nice -n 10 Rscript --vanilla scripts/forecats_batch.R --config \"$CONFIG_PATH\" --mode render --shard-count $SHARDS --shard-index $i |& tee \"$LOG\""
  tmux new-session -d -s "$SESS" "$CMD"
  echo "$SESS" >> "$META_FILE"
  echo "  - $SESS"
done

echo "[OK] launched $SHARDS tmux sessions"
echo "[OK] session list file: $META_FILE"
echo "[TIP] monitor: ./scripts/monitor_forecats_render_nws_multiretro_compare.sh \"$CONFIG_PATH\""

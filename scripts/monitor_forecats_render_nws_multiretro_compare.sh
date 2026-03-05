#!/usr/bin/env bash
set -euo pipefail

# Monitor status for NWS multi-retro comparison render shards.
#
# Usage:
#   ./scripts/monitor_forecats_render_nws_multiretro_compare.sh [CONFIG]
#
# Default:
#   CONFIG=config/forecats_batch.site=11160500.nws_multiretro_compare.yaml

CONFIG_PATH="${1:-config/forecats_batch.site=11160500.nws_multiretro_compare.yaml}"
ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd"
cd "$ROOT"
CONFIG_PATH="$(realpath -m "$CONFIG_PATH")"

readarray -t META < <(CFG="$CONFIG_PATH" Rscript --vanilla - <<'RS'
suppressPackageStartupMessages(library(yaml))
cfg <- yaml::read_yaml(Sys.getenv("CFG"))
cache_root <- cfg$run$cache_root
out_root <- cfg$run$out_root
site_id <- as.character(cfg$site$usgs_site)
run_id <- as.character(cfg$run$run_id)
batch_root <- normalizePath(file.path(getwd(), cache_root, paste0("site=", site_id), paste0("run_id=", run_id)), mustWork = FALSE)
out_site_root <- normalizePath(file.path(getwd(), out_root, paste0("site=", site_id)), mustWork = FALSE)
cat(site_id, "\n", sep = "")
cat(run_id, "\n", sep = "")
cat(batch_root, "\n", sep = "")
cat(out_site_root, "\n", sep = "")
RS
)

SITE_ID="${META[0]}"
RUN_ID="${META[1]}"
BATCH_ROOT="${META[2]}"
OUT_SITE_ROOT="${META[3]}"

echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) =="
echo "CONFIG=$CONFIG_PATH"
echo "SITE_ID=$SITE_ID RUN_ID=$RUN_ID"
echo "BATCH_ROOT=$BATCH_ROOT"
echo

echo "[TMUX] active render sessions:"
tmux ls 2>/dev/null | grep "forecats_cmp_" || echo "  (none)"
echo

echo "[MANIFEST] aggregate status:"
BATCH_ROOT="$BATCH_ROOT" python3 - <<'PY'
import csv
import glob
import os
from collections import Counter

batch_root = os.environ["BATCH_ROOT"]
manifests = sorted(glob.glob(os.path.join(batch_root, "batch_manifest*.csv")))
ctr = Counter()
total = 0
for p in manifests:
    with open(p, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            st = (row.get("status") or "").strip()
            if not st:
                continue
            ctr[st] += 1
            total += 1
print(f"manifests={len(manifests)} rows={total}")
print("status_counts=", dict(ctr))
PY
echo

echo "[FIGURES] current output count:"
find "$OUT_SITE_ROOT" -path "*run_id=$RUN_ID/figures/forecats.png" -type f 2>/dev/null | wc -l | awk '{print "forecats_png_count=" $1}'
echo

echo "[LOG TAIL] latest 5 from each shard log:"
for f in "$BATCH_ROOT"/logs/render_compare_shard*.log; do
  [[ -f "$f" ]] || continue
  echo "--- $f"
  tail -n 5 "$f"
done

#!/usr/bin/env bash
set -euo pipefail
ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd"
cd "$ROOT"

echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) =="

# Workstream C sessions
echo "[C] active tmux sessions (hist_v21/v31/v40):"
tmux ls 2>/dev/null | rg "hist_v(21|31|40)_.._20260217T" || echo "  none"

# Workstream C manifest aggregate
echo "[C] manifest aggregate:"
python3 scripts/forecats_summarize_hist_campaign_status.py \
  --plan-dir repro/glofas_probe_runs/hist_campaign_20260217T013445Z \
  --run-glob 'repro/glofas_probe_runs/hist_campaign_20260217T0*' \
  --out-csv repro/glofas_probe_runs/hist_campaign_20260217T013445Z/status_aggregate_latest.csv

# Workstream D process + file growth
echo "[D] v3 download process:"
pgrep -af "curl.*dis_1980_2018" || echo "  no active curl for v3"

V3_FILE="data/glofas_legacy_global/dis_1980_2018_v3_legacy.nc"
if [[ -f "$V3_FILE" ]]; then
  echo "[D] v3 file size:"
  ls -lh "$V3_FILE"
else
  echo "[D] v3 file not created yet"
fi

echo "[D] last log lines:"
if [[ -f data/glofas_legacy_global/logs/v3_download.log ]]; then
  tail -n 20 data/glofas_legacy_global/logs/v3_download.log
else
  echo "  log not found yet"
fi

# Script Runner Status

Date: 2026-01-29 13:31:46

Reference notebook (logic truth):
- repro/recovery/Environmetrics_Figures__OLDEST.ipynb

Canonical output folder (compute gold):
- Environmetrics_reproduce/  (PNG count: 147)

Runner (headless, no comparisons):
- scripts/run_environmetrics_figures.R

Background helper:
- scripts/run_environmetrics_figures_bg.sh

Linearized script (expected path):
- repro/recovery/Environmetrics_Figures__OLDEST_linearized.R

Extraction helper (do not run automatically):
- scripts/extract_ipynb_to_R.sh

Notes:
- No automatic comparisons are performed; user will inspect outputs manually.
- Runner writes outputs to: Environmetrics_reproduce_script_runs/YYYYMMDD_HHMMSS/
- Logs are written to: repro/logs/script_runs/YYYYMMDD_HHMMSS/

Commands:
1) Generate linearized script (only if missing):
   scripts/extract_ipynb_to_R.sh

2) Launch background run:
   scripts/run_environmetrics_figures_bg.sh

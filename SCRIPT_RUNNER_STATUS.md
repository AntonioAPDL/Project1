# Script Runner Status

Date: 2026-01-30 00:47:00

Reference notebook (logic truth):
- repro/recovery/Environmetrics_Figures__OLDEST.ipynb

Canonical output folder (compute gold; do not modify):
- Environmetrics_reproduce/ (PNG count: 147)

Linearized script (expected):
- Environmetrics_Figures__OLDEST_linearized.R

Modularized script pieces (sourced in order):
- R/environmetrics/00_paths.R
- R/environmetrics/00_setup.R
- R/environmetrics/00_constants.R
- R/environmetrics/01_config.R
- R/environmetrics/02_helpers_core.R
- R/environmetrics/utils_data.R
- R/environmetrics/utils_plot.R
- R/environmetrics/10_data_inputs.R
- R/environmetrics/20_model_setup.R
- R/environmetrics/30_univariate_and_misc.R
- R/environmetrics/40_figures.R

Runner (headless, no comparisons, univariate always runs):
- scripts/run_environmetrics_figures.R

Module responsibilities (brief):
- 00_setup.R: library setup and package imports
- 00_paths.R: centralized input/output paths
- 00_constants.R: global constants (p0, deltas, harmonics)
- 01_config.R: reserved placeholder (future config)
- 02_helpers_core.R: math + model helper functions
- utils_data.R: standardization helpers
- utils_plot.R: plot device helpers (optional)
- 10_data_inputs.R: load/prepare covariates + responses
- 20_model_setup.R: model matrices and priors
- 30_univariate_and_misc.R: univariate diagnostics (always run)
- 40_figures.R: figure generation (redirected by runner)

Background launcher (tmux):
- scripts/run_environmetrics_figures_bg.sh

Outputs:
- Environmetrics_reproduce_script_runs/YYYYMMDD_HHMMSS/

Logs:
- repro/logs/script_runs/YYYYMMDD_HHMMSS/

Commands:
1) Extract linearized script (only if missing):
   scripts/extract_ipynb_to_R.sh

1b) Optional fast input check:
   Rscript scripts/check_inputs.R

2) Launch background run:
   scripts/run_environmetrics_figures_bg.sh

3) Monitor logs:
   tail -f repro/logs/script_runs/<RUN_ID>/run_log.txt

4) Attach to tmux:
   tmux attach -t envm_figs_<RUN_ID>

5) Stop tmux session:
   tmux kill-session -t envm_figs_<RUN_ID>

Note:
- No automatic comparisons are performed; user will inspect outputs manually.

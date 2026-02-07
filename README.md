# project1_ucsc_phd

Code + manuscript repo. Data, outputs, and environments are local-only.

How to run the headless figure script
1) Optional input preflight:
   Rscript scripts/check_inputs.R
2) Run in background via tmux:
   scripts/run_environmetrics_figures_bg.sh
3) Monitor logs:
   tail -f repro/logs/script_runs/<RUN_ID>/run_log.txt
4) Outputs are written to:
   Environmetrics_reproduce_script_runs/<RUN_ID>/

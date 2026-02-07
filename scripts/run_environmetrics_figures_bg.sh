#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd"
RUN_ID=$(date +"%Y%m%d_%H%M%S")
OUT_DIR="$PROJECT_ROOT/Environmetrics_reproduce_script_runs/$RUN_ID"
LOG_DIR="$PROJECT_ROOT/repro/logs/script_runs/$RUN_ID"
SESSION="envm_figs_${RUN_ID}"

mkdir -p "$LOG_DIR"

CMD="cd $PROJECT_ROOT && RUN_ID=$RUN_ID Rscript scripts/run_environmetrics_figures.R > $LOG_DIR/console.txt 2>&1"

tmux new-session -d -s "$SESSION" "$CMD"

echo "tmux session: $SESSION"
echo "RUN_ID: $RUN_ID"
echo "OUT_DIR: $OUT_DIR"
echo "LOG_DIR: $LOG_DIR"
echo "console: $LOG_DIR/console.txt"
echo "monitor logs: tail -f $LOG_DIR/run_log.txt"
echo "attach: tmux attach -t $SESSION"
echo "stop: tmux kill-session -t $SESSION"

#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$REPO_ROOT/imcmc_env/bin/python}"
KERNEL_NAME="${KERNEL_NAME:-imcmc_env}"
FAST_MODE="${FAST_MODE:-1}"
export PATH="$REPO_ROOT/imcmc_env/bin:$PATH"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python not found at $PYTHON_BIN" >&2
  exit 1
fi

NB_EXECUTED_DIR="$REPO_ROOT/outputs/notebooks/executed"
LOG_DIR="$REPO_ROOT/logs/notebooks"

mkdir -p "$NB_EXECUTED_DIR" "$LOG_DIR"

notebooks=(
  "$REPO_ROOT/forecast_nws_eda.ipynb"
  "$REPO_ROOT/glofas_forecasts.ipynb"
  "$REPO_ROOT/Retro-Analysis.ipynb"
)

for nb in "${notebooks[@]}"; do
  nb_name="$(basename "$nb")"
  log_file="$LOG_DIR/${nb_name%.ipynb}.log"
  out_nb="$NB_EXECUTED_DIR/${nb_name%.ipynb}.executed.ipynb"

  echo "Running $nb_name (FAST_MODE=$FAST_MODE)..."
  set +e
  env FAST_MODE="$FAST_MODE" "$PYTHON_BIN" -m jupyter nbconvert \
    --to notebook \
    --execute \
    --ExecutePreprocessor.timeout=600 \
    --ExecutePreprocessor.kernel_name="$KERNEL_NAME" \
    --output "$out_nb" \
    "$nb" >"$log_file" 2>&1
  status=$?
  set -e

  if [[ $status -ne 0 ]]; then
    echo "ERROR: $nb_name failed (exit $status). See $log_file" >&2
    if command -v rg >/dev/null 2>&1; then
      rg -n "Traceback|Error|Exception" "$log_file" | head -n 5 >&2 || true
    else
      grep -nE "Traceback|Error|Exception" "$log_file" | head -n 5 >&2 || true
    fi
    exit $status
  fi

  echo "Completed $nb_name"
done

echo "All notebooks executed successfully." 

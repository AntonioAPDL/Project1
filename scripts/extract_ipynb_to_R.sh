#!/usr/bin/env bash
set -euo pipefail

IN_NB=${1:-"repro/recovery/Environmetrics_Figures__OLDEST.ipynb"}
OUT_R=${2:-"Environmetrics_Figures__OLDEST_linearized.R"}
FORCE=${3:-""}

if [[ -f "$OUT_R" && "$FORCE" != "--force" ]]; then
  echo "Refusing to overwrite $OUT_R (use --force as 3rd arg)" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT_R")"

if command -v jupyter >/dev/null 2>&1; then
  jupyter nbconvert --to script "$IN_NB" --output "$(basename "$OUT_R")" --output-dir "$(dirname "$OUT_R")"
  # nbconvert may output .r or .R; normalize name if needed
  if [[ ! -f "$OUT_R" ]]; then
    ALT_R="${OUT_R%.R}.r"
    if [[ -f "$ALT_R" ]]; then
      mv "$ALT_R" "$OUT_R"
    fi
  fi
  echo "$OUT_R"
  exit 0
fi

if [[ -f "tools/export_ipynb_to_R.py" ]]; then
  python3 tools/export_ipynb_to_R.py "$IN_NB" "$OUT_R"
  echo "$OUT_R"
  exit 0
fi

echo "No export method found (jupyter or tools/export_ipynb_to_R.py)." >&2
exit 1

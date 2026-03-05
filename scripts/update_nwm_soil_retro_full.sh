#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_END_DATE="${1:-$(date -u +%Y-%m-%d)}"
OUT_DIR="${ROOT_DIR}/soil_moisture_data"
OUT_CSV="${OUT_DIR}/nwm_soil_moisture_big_trees_daily_1987_present.csv"
OUT_META="${OUT_DIR}/nwm_soil_moisture_big_trees_daily_1987_present.meta.json"

mkdir -p "${OUT_DIR}"

if [[ -f "${OUT_CSV}" && -f "${OUT_META}" ]]; then
  COMPLETED_END="$(
  python3 - <<'PY' "${OUT_CSV}" "${OUT_META}" "${TARGET_END_DATE}"
import json
import sys
from pathlib import Path
import pandas as pd

csv_path = Path(sys.argv[1])
meta_path = Path(sys.argv[2])
target_end = pd.Timestamp(sys.argv[3]).date()

try:
    df = pd.read_csv(csv_path)
    dmax = pd.to_datetime(df.get("Date"), errors="coerce").max()
except Exception:
    dmax = pd.NaT

try:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    m_end_raw = meta.get("effective_end_date", "")
    m_end = pd.Timestamp(m_end_raw).date() if m_end_raw else None
except Exception:
    m_end = None

if pd.notna(dmax) and m_end is not None:
    done_through = min(target_end, m_end)
    if dmax.date() >= done_through:
        print(done_through.isoformat())
PY
  )"
  if [[ -n "${COMPLETED_END}" ]]; then
    echo "[INFO] NWM retrospective soil already complete through ${COMPLETED_END}; skipping."
    exit 0
  fi
fi

python3 "${ROOT_DIR}/scripts/build_nwm_retro_soil_point_series.py" \
  --lat 37.0443931 \
  --lon -122.072464 \
  --start-date 1987-01-01 \
  --end-date "${TARGET_END_DATE}" \
  --soil-layer-index 0 \
  --out-csv "${OUT_CSV}" \
  --out-meta "${OUT_META}"

echo "[OK] NWM retrospective soil build complete."
echo "[OK] CSV: ${OUT_CSV}"
echo "[OK] META: ${OUT_META}"

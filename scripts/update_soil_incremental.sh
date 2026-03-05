#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_END_DATE="${1:-2026-02-24}"
CSV_PATH="${ROOT_DIR}/soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv"
TMP_DIR="${ROOT_DIR}/soil_moisture_data/.tmp_era5_incremental_$$"
TMP_DAILY="${ROOT_DIR}/soil_moisture_data/.soil_daily_incremental_${TARGET_END_DATE}_$$.csv"

mkdir -p "${ROOT_DIR}/soil_moisture_data"

START_DATE="$(
python3 - <<'PY' "${CSV_PATH}"
import sys
from datetime import timedelta
from pathlib import Path
import pandas as pd

csv_path = Path(sys.argv[1])
if not csv_path.exists():
    print("1987-01-01")
    raise SystemExit(0)

df = pd.read_csv(csv_path)
if "Date" not in df.columns:
    print("1987-01-01")
    raise SystemExit(0)

dt = pd.to_datetime(df["Date"], errors="coerce")
if dt.notna().any():
    print((dt.max().date() + timedelta(days=1)).isoformat())
else:
    print("1987-01-01")
PY
)"

echo "[INFO] Soil incremental start=${START_DATE} end=${TARGET_END_DATE}"
if [[ "${START_DATE}" > "${TARGET_END_DATE}" ]]; then
  echo "[INFO] Soil already up to date; nothing to do."
  exit 0
fi

python3 -u "${ROOT_DIR}/scripts/build_era5_soil_moisture_point_series.py" \
  --start-date "${START_DATE}" \
  --end-date "${TARGET_END_DATE}" \
  --cds-url "https://cds.climate.copernicus.eu/api" \
  --tmp-dir "${TMP_DIR}" \
  --daily-csv "${TMP_DAILY}" \
  --overwrite

python3 - <<'PY' "${CSV_PATH}" "${TMP_DAILY}" "${START_DATE}" "${TARGET_END_DATE}"
import sys
from pathlib import Path
import pandas as pd

base_csv = Path(sys.argv[1])
inc_csv = Path(sys.argv[2])
start_date = pd.Timestamp(sys.argv[3])
end_date = pd.Timestamp(sys.argv[4])

parts = []
if base_csv.exists():
    base_df = pd.read_csv(base_csv)
    if "Date" in base_df.columns:
        parts.append(base_df)

if inc_csv.exists():
    inc_df = pd.read_csv(inc_csv)
    if "Date" in inc_df.columns:
        inc_df["Date"] = pd.to_datetime(inc_df["Date"], errors="coerce")
        inc_df = inc_df.dropna(subset=["Date"])
        inc_df = inc_df[(inc_df["Date"] >= start_date) & (inc_df["Date"] <= end_date)]
        if not inc_df.empty:
            inc_df["Date"] = inc_df["Date"].dt.strftime("%Y-%m-%d")
            parts.append(inc_df)

if not parts:
    print("[WARN] No soil dataframes available to merge.")
    raise SystemExit(0)

out = pd.concat(parts, ignore_index=True)
out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
out = out.dropna(subset=["Date"])
if "Daily_Avg_Soil_Moisture" in out.columns:
    out["Daily_Avg_Soil_Moisture"] = pd.to_numeric(out["Daily_Avg_Soil_Moisture"], errors="coerce")
out = out[out["Date"] <= end_date]
out = out.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")
out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
out.to_csv(base_csv, index=False)
print(f"[OK] merged soil rows={len(out)} output={base_csv}")
PY

rm -f "${TMP_DAILY}"
rm -rf "${TMP_DIR}"
echo "[OK] Soil incremental update complete."

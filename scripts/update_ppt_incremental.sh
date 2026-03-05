#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_END_DATE="${1:-2026-02-24}"
CSV_PATH="${ROOT_DIR}/prism_precipitation_santa_cruz_1987_2023.csv"
DOWNLOAD_DIR="${ROOT_DIR}/prism_data_work"
TMP_OUT="${ROOT_DIR}/prism_data_work/.ppt_incremental_${TARGET_END_DATE}_$$.csv"

mkdir -p "${DOWNLOAD_DIR}"

Rscript --vanilla -e "if (!requireNamespace('prism', quietly=TRUE)) install.packages('prism', repos='https://cloud.r-project.org')"

START_DATE="$(
python3 - <<'PY' "${CSV_PATH}"
import sys
from datetime import date, timedelta
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

echo "[INFO] PPT incremental start=${START_DATE} end=${TARGET_END_DATE}"
if [[ "${START_DATE}" > "${TARGET_END_DATE}" ]]; then
  echo "[INFO] PPT already up to date; nothing to do."
  exit 0
fi

Rscript --vanilla "${ROOT_DIR}/scripts/build_prism_ppt_point_series.R" \
  --start-date "${START_DATE}" \
  --end-date "${TARGET_END_DATE}" \
  --resolution "4km" \
  --download-dir "${DOWNLOAD_DIR}" \
  --output-csv "${TMP_OUT}"

python3 - <<'PY' "${CSV_PATH}" "${TMP_OUT}" "${TARGET_END_DATE}"
import sys
from pathlib import Path
import pandas as pd

base_csv = Path(sys.argv[1])
inc_csv = Path(sys.argv[2])
end_date = pd.Timestamp(sys.argv[3])

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
        inc_df = inc_df[inc_df["Date"] <= end_date]
        if not inc_df.empty:
            inc_df["Date"] = inc_df["Date"].dt.strftime("%Y-%m-%d")
            parts.append(inc_df)

if not parts:
    print("[WARN] No dataframes available to merge.")
    raise SystemExit(0)

out = pd.concat(parts, ignore_index=True)
out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
out = out.dropna(subset=["Date"])
if "PRCP_mm" in out.columns:
    out["PRCP_mm"] = pd.to_numeric(out["PRCP_mm"], errors="coerce")
out = out[out["Date"] <= end_date]
out = out.sort_values("Date").drop_duplicates(subset=["Date"], keep="last")
out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
out.to_csv(base_csv, index=False)
print(f"[OK] merged ppt rows={len(out)} output={base_csv}")
PY

rm -f "${TMP_OUT}"
echo "[OK] PPT incremental update complete."

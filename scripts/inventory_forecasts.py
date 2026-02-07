#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

# Allow local imports
REPO_ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(REPO_ROOT / "src"))

from utils.config import ensure_dirs, load_paths


DATE_PATTERNS = [
    re.compile(r"(\d{4}-\d{2}-\d{2})"),
    re.compile(r"(\d{8})"),
]

LEAD_PATTERN = re.compile(r"f(\d{2,3})")
SITE_PATTERN = re.compile(r"\b(\d{7,8})\b")

KEYWORDS = [
    "glofas",
    "nwm",
    "nws",
    "noaa",
    "forecast",
    "retrospective",
    "retro",
    "reanalysis",
    "medium",
    "seasonal",
    "ensemble",
    "ens",
]

EXTENSIONS = {
    ".csv",
    ".nc",
    ".nc4",
    ".grib",
    ".grb",
    ".grib2",
    ".zarr",
    ".parquet",
    ".feather",
    ".pkl",
    ".pickle",
}

SKIP_DIRS = {
    ".git",
    ".venv",
    ".ipynb_checkpoints",
    "imcmc_env",
    "build",
    "boost_1_81_0",
    "boost_1_82_0",
    "R-4.3.1",
    "julia-1.9.3",
    "google-cloud-sdk",
    "cmake-3.22.1",
    "fftw-3.3.10",
    "eccodes-2.26.0-Source",
    "nlopt-2.7.0",
    "lapack",
    "ngrok",
}


def parse_dates_from_string(text: str) -> List[pd.Timestamp]:
    dates: List[pd.Timestamp] = []
    for pattern in DATE_PATTERNS:
        for match in pattern.findall(text):
            try:
                if len(match) == 8:
                    dates.append(pd.to_datetime(match, format="%Y%m%d"))
                else:
                    dates.append(pd.to_datetime(match, format="%Y-%m-%d"))
            except Exception:
                continue
    return dates


def classify_provider(path_str: str) -> str:
    name = path_str.lower()
    if "glofas" in name:
        return "GloFAS"
    if "nwm" in name:
        return "NWM"
    if "nws" in name or "noaa" in name:
        return "NWS/NOAA"
    return "Unknown"


def classify_product(path_str: str) -> str:
    name = path_str.lower()
    if "retrospective" in name or "retro" in name:
        if "2-1" in name or "v2" in name or "retro_old" in name:
            return "NWM retrospective v2.1"
        if "3-0" in name or "v3" in name or "retro" in name:
            return "NWM retrospective v3.0"
        return "retrospective"
    if "seasonal" in name:
        return "seasonal forecast"
    if "medium" in name:
        return "medium-range forecast"
    if "forecast" in name:
        return "forecast"
    if "reanalysis" in name:
        return "reanalysis"
    return "unspecified"


def infer_variable(columns: List[str], path_str: str) -> Optional[str]:
    lower_cols = [c.lower() for c in columns]
    if any("streamflow" in c for c in lower_cols):
        return "streamflow"
    if any("discharge" in c for c in lower_cols):
        return "discharge"
    name = path_str.lower()
    if "streamflow" in name:
        return "streamflow"
    if "discharge" in name:
        return "discharge"
    return None


def inspect_csv(path: Path) -> Dict[str, Any]:
    info: Dict[str, Any] = {}
    try:
        header_df = pd.read_csv(path, nrows=5)
        columns = list(header_df.columns)
        info["columns"] = columns
        info["variable"] = infer_variable(columns, str(path))

        ensemble_cols = [c for c in columns if c.lower().startswith("ensemble_member")]
        if ensemble_cols:
            info["ensemble_members"] = len(ensemble_cols)

        if "Date" in columns or "date" in [c.lower() for c in columns]:
            date_col = "Date" if "Date" in columns else [c for c in columns if c.lower() == "date"][0]
            # For larger files, read only the date column
            date_series = pd.read_csv(path, usecols=[date_col])[date_col]
            date_series = pd.to_datetime(date_series, errors="coerce")
            info["date_min"] = date_series.min()
            info["date_max"] = date_series.max()
    except Exception as exc:
        info["notes"] = f"csv_inspect_failed: {exc}"
    return info


def collect_files(roots: List[Path]) -> List[Path]:
    files: List[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for filename in filenames:
                path = Path(dirpath) / filename
                if path.suffix.lower() not in EXTENSIONS:
                    continue
                lower_path = str(path).lower()
                if not any(k in lower_path for k in KEYWORDS):
                    continue
                files.append(path)
    return files


def build_inventory(files: List[Path]) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []
    for path in files:
        path_str = str(path)
        stat = path.stat()
        provider = classify_provider(path_str)
        product = classify_product(path_str)

        dates = parse_dates_from_string(path_str)
        date_min = min(dates) if dates else None
        date_max = max(dates) if dates else None

        lead_match = LEAD_PATTERN.search(path_str)
        lead_time = int(lead_match.group(1)) if lead_match else None

        site_match = SITE_PATTERN.search(path_str)
        spatial_id = site_match.group(1) if site_match else None

        record: Dict[str, Any] = {
            "path": path_str,
            "provider": provider,
            "product": product,
            "file_type": path.suffix.lower().lstrip("."),
            "size_bytes": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime),
            "date_min": date_min,
            "date_max": date_max,
            "lead_time_hours": lead_time,
            "spatial_id": spatial_id,
            "variable": None,
            "ensemble_members": None,
            "notes": None,
        }

        if path.suffix.lower() == ".csv" and stat.st_size < 200 * 1024 * 1024:
            csv_info = inspect_csv(path)
            record.update({k: v for k, v in csv_info.items() if v is not None})

        records.append(record)

    return pd.DataFrame(records)


def summarize_inventory(df: pd.DataFrame, output_path: Path, roots: List[Path]) -> None:
    lines: List[str] = []
    lines.append("# Forecast Inventory Summary")
    lines.append("")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append("")
    lines.append("## Scan roots")
    for root in roots:
        lines.append(f"- {root}")
    lines.append("")

    if df.empty:
        lines.append("No matching files found.")
        output_path.write_text("\n".join(lines))
        return

    lines.append(f"Total matched files: {len(df)}")
    lines.append("")

    group_cols = ["provider", "product"]
    summary = (
        df.groupby(group_cols)
        .agg(
            files=("path", "count"),
            date_min=("date_min", "min"),
            date_max=("date_max", "max"),
            variables=("variable", lambda s: ", ".join(sorted({v for v in s if pd.notna(v)})) or "unknown"),
            spatial_ids=("spatial_id", lambda s: ", ".join(sorted({v for v in s if pd.notna(v)})) or "unknown"),
            ensembles=("ensemble_members", lambda s: ", ".join(sorted({str(v) for v in s if pd.notna(v)})) or "unknown"),
        )
        .reset_index()
    )

    lines.append("## Coverage by provider/product")
    lines.append("")
    lines.append("| provider | product | files | date_min | date_max | variables | spatial_ids | ensembles |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['provider']} | {row['product']} | {row['files']} | {row['date_min']} | {row['date_max']} | {row['variables']} | {row['spatial_ids']} | {row['ensembles']} |"
        )

    lines.append("")
    lines.append("## Directory patterns")
    lines.append("")
    parents = Counter(str(Path(p).parent) for p in df["path"])  # type: ignore[arg-type]
    for parent, count in parents.most_common(10):
        lines.append(f"- {parent}: {count} files")

    missing_dates = df[df["date_min"].isna() & df["date_max"].isna()]
    if not missing_dates.empty:
        lines.append("")
        lines.append("## Files without date inference")
        for path in missing_dates["path"].head(20):
            lines.append(f"- {path}")

    output_path.write_text("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory local forecast datasets.")
    parser.add_argument("--config", default=None, help="Path to config/paths.yaml")
    args = parser.parse_args()

    paths = load_paths(args.config)
    roots = [paths["data_root"]] + paths.get("extra_data_roots", [])

    inventory_dir = paths["output_root"] / "inventory"
    ensure_dirs(inventory_dir)

    files = collect_files([Path(r) for r in roots if r is not None])
    df = build_inventory(files)

    parquet_path = inventory_dir / "forecast_inventory.parquet"
    csv_path = inventory_dir / "forecast_inventory.csv"
    summary_path = inventory_dir / "forecast_inventory_summary.md"

    wrote_parquet = False
    try:
        df.to_parquet(parquet_path, index=False)
        wrote_parquet = True
    except Exception as exc:
        df.to_csv(csv_path, index=False)
        df.attrs["parquet_error"] = str(exc)

    summarize_inventory(df, summary_path, roots)

    if wrote_parquet:
        print(f"Wrote inventory to {parquet_path}")
    else:
        print(f"Parquet unavailable; wrote inventory to {csv_path}")
    print(f"Wrote summary to {summary_path}")


if __name__ == "__main__":
    main()

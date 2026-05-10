#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import platform
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
import yaml
from scipy.interpolate import CubicSpline, interp1d

ROOT = Path(__file__).resolve().parents[1]
NA_VALUES = {-99.99, -99.90, -99.9, -9.90, -999.0, 9999.00, -9, -9.99, 9.9, 9.99}
MONTH_COLUMNS = [f"Month_{idx}" for idx in range(1, 13)]


@dataclass(frozen=True)
class CanonicalPaths:
    root: Path
    input_root: Path
    raw_text_root: Path
    monthly_csv_root: Path
    intermediate_root: Path
    outputs_root: Path
    metadata_root: Path
    review_root: Path


def compact_date(date_text: str) -> str:
    return str(date_text).replace("-", "")


def load_config(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Config root is not a mapping: {path}")
    return data


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_paths(cfg: dict[str, Any]) -> CanonicalPaths:
    root = (ROOT / cfg["artifact_root"]).resolve()
    input_root = ensure_dir(root / "inputs")
    return CanonicalPaths(
        root=root,
        input_root=input_root,
        raw_text_root=ensure_dir(input_root / "raw_psl_text"),
        monthly_csv_root=ensure_dir(input_root / "monthly_csv"),
        intermediate_root=ensure_dir(root / "intermediate"),
        outputs_root=ensure_dir(root / "outputs"),
        metadata_root=ensure_dir(root / "metadata"),
        review_root=ensure_dir(root / "review"),
    )


def canonical_window_token(cfg: dict[str, Any]) -> str:
    start = compact_date(cfg["canonical_window"]["start_date"])
    end = compact_date(cfg["canonical_window"]["end_date"])
    return f"{start}_{end}"


def raw_daily_matrix_path(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    paths = paths or canonical_paths(cfg)
    return paths.intermediate_root / f"combined_climate_indices_daily_{canonical_window_token(cfg)}.csv"


def standardized_daily_matrix_path(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    paths = paths or canonical_paths(cfg)
    return paths.intermediate_root / f"combined_climate_indices_daily_standardized_{canonical_window_token(cfg)}.csv"


def gdpc_factor_output_path(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    paths = paths or canonical_paths(cfg)
    return paths.outputs_root / f"gdpc_master_component_01_{canonical_window_token(cfg)}.csv"


def gdpc_alpha_output_path(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    paths = paths or canonical_paths(cfg)
    return paths.outputs_root / f"gdpc_master_component_01_alpha_{canonical_window_token(cfg)}.csv"


def gdpc_beta_output_path(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    paths = paths or canonical_paths(cfg)
    return paths.outputs_root / f"gdpc_master_component_01_beta_{canonical_window_token(cfg)}.csv"


def gdpc_initial_factor_output_path(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    paths = paths or canonical_paths(cfg)
    return paths.outputs_root / f"gdpc_master_component_01_initial_f_{canonical_window_token(cfg)}.csv"


def gdpc_metadata_output_path(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    paths = paths or canonical_paths(cfg)
    return paths.metadata_root / "gdpc_build_metadata.json"


def gdpc_review_output_path(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    paths = paths or canonical_paths(cfg)
    return paths.review_root / "CANONICAL_GDPC_BUILD_REVIEW.md"


def gdpc_stationarity_review_path(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    paths = paths or canonical_paths(cfg)
    return paths.review_root / "stationarity" / "CANONICAL_GDPC_STATIONARITY_AUDIT.md"


def gdpc_screening_root(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    paths = paths or canonical_paths(cfg)
    return ensure_dir(paths.review_root / "lag_screening")


def gdpc_screening_run_root(cfg: dict[str, Any], k: int, paths: CanonicalPaths | None = None) -> Path:
    return ensure_dir(gdpc_screening_root(cfg, paths) / f"k_{int(k)}")


def gdpc_screening_factor_output_path(cfg: dict[str, Any], k: int, paths: CanonicalPaths | None = None) -> Path:
    return gdpc_screening_run_root(cfg, k, paths) / f"gdpc_master_component_01_k{int(k)}_{canonical_window_token(cfg)}.csv"


def gdpc_screening_alpha_output_path(cfg: dict[str, Any], k: int, paths: CanonicalPaths | None = None) -> Path:
    return gdpc_screening_run_root(cfg, k, paths) / f"gdpc_master_component_01_alpha_k{int(k)}_{canonical_window_token(cfg)}.csv"


def gdpc_screening_beta_output_path(cfg: dict[str, Any], k: int, paths: CanonicalPaths | None = None) -> Path:
    return gdpc_screening_run_root(cfg, k, paths) / f"gdpc_master_component_01_beta_k{int(k)}_{canonical_window_token(cfg)}.csv"


def gdpc_screening_initial_factor_output_path(cfg: dict[str, Any], k: int, paths: CanonicalPaths | None = None) -> Path:
    return gdpc_screening_run_root(cfg, k, paths) / f"gdpc_master_component_01_initial_f_k{int(k)}_{canonical_window_token(cfg)}.csv"


def gdpc_screening_metadata_output_path(cfg: dict[str, Any], k: int, paths: CanonicalPaths | None = None) -> Path:
    return gdpc_screening_run_root(cfg, k, paths) / "gdpc_screening_metadata.json"


def gdpc_screening_summary_csv_path(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    return gdpc_screening_root(cfg, paths) / "gdpc_k_screening_summary.csv"


def gdpc_screening_summary_json_path(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    return gdpc_screening_root(cfg, paths) / "gdpc_k_screening_summary.json"


def gdpc_screening_review_path(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    return gdpc_screening_root(cfg, paths) / "CANONICAL_GDPC_K_SCREENING_REVIEW.md"


def gdpc_compat_root(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> Path:
    paths = paths or canonical_paths(cfg)
    return ensure_dir(paths.outputs_root / "compat")


def gdpc_compat_alias_paths(cfg: dict[str, Any], paths: CanonicalPaths | None = None) -> dict[str, Path]:
    root = gdpc_compat_root(cfg, paths)
    aliases: dict[str, Path] = {}
    for item in cfg.get("compatibility_aliases", []):
        alias_filename = str(item["alias_filename"])
        aliases[alias_filename] = root / alias_filename
    return aliases


def package_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "pyyaml": yaml.__version__,
        "requests": requests.__version__,
        "scipy": getattr(sys.modules.get("scipy"), "__version__", "unknown"),
    }


def request_text(url: str, *, timeout_seconds: int, retries: int, user_agent: str, session: requests.Session | None = None) -> str:
    own_session = session is None
    sess = session or requests.Session()
    try:
        headers = {"User-Agent": user_agent}
        last_err: Exception | None = None
        for attempt in range(retries):
            try:
                response = sess.get(url, timeout=timeout_seconds, headers=headers)
                response.raise_for_status()
                response.encoding = response.encoding or "utf-8"
                return response.text
            except Exception as err:  # noqa: BLE001
                last_err = err
                if attempt == retries - 1:
                    break
        assert last_err is not None
        raise last_err
    finally:
        if own_session:
            sess.close()


def is_data_line(line: str) -> bool:
    parts = line.strip().split()
    if len(parts) != 13:
        return False
    try:
        int(parts[0])
        return True
    except ValueError:
        return False


def parse_psl_monthly_text(text: str) -> pd.DataFrame:
    lines = text.splitlines()
    start_idx = None
    for idx, line in enumerate(lines):
        if is_data_line(line):
            start_idx = idx
            break
    if start_idx is None:
        raise ValueError("Could not find monthly data block in upstream text payload")

    cleaned_lines: list[str] = []
    for line in lines[start_idx:]:
        parts = line.strip().split()
        if len(parts) == 13 and parts[0].isdigit():
            cleaned_lines.append(" ".join(parts))
        elif len(parts) > 13 and parts[0].isdigit():
            cleaned_lines.append(" ".join(parts[:13]))

    if not cleaned_lines:
        raise ValueError("Upstream text payload did not yield any clean monthly rows")

    df = pd.read_csv(pd.io.common.StringIO("\n".join(cleaned_lines)), sep=r"\s+", header=None)
    df.columns = ["Year"] + MONTH_COLUMNS
    df = df.replace(list(NA_VALUES), np.nan)
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")
    for col in MONTH_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["Year"]).copy()
    df["Year"] = df["Year"].astype(int)
    return df


def monthly_wide_to_long(df: pd.DataFrame, *, start_month: str, end_month: str) -> pd.DataFrame:
    melted = df.melt(id_vars=["Year"], value_vars=MONTH_COLUMNS, var_name="month_col", value_name="value")
    melted["month_num"] = melted["month_col"].str.replace("Month_", "", regex=False).astype(int)
    melted["month_start"] = pd.to_datetime(
        {
            "year": melted["Year"],
            "month": melted["month_num"],
            "day": 1,
        },
        errors="coerce",
    )
    out = melted[["month_start", "value"]].copy()
    out["value"] = pd.to_numeric(out["value"], errors="coerce")
    out = out.dropna(subset=["month_start", "value"]).sort_values("month_start").reset_index(drop=True)
    mask = (out["month_start"] >= pd.Timestamp(start_month)) & (out["month_start"] <= pd.Timestamp(end_month))
    out = out.loc[mask].copy().reset_index(drop=True)
    if out.empty:
        raise ValueError(f"No monthly data remained after filtering to {start_month}..{end_month}")
    return out


def interpolate_monthly_to_daily(
    monthly_long: pd.DataFrame,
    *,
    start_date: str,
    end_date: str,
    linear_tail_days: int,
) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    x = monthly_long["month_start"].map(pd.Timestamp.toordinal).to_numpy(dtype=float)
    y = monthly_long["value"].to_numpy(dtype=float)
    if len(x) < 2:
        raise ValueError("Need at least two monthly points for daily interpolation")
    eval_x = dates.map(pd.Timestamp.toordinal).to_numpy(dtype=float)

    if len(x) >= 3:
        cubic = CubicSpline(x, y, extrapolate=False)
        values = cubic(eval_x)
    else:
        linear = interp1d(x, y, kind="linear", fill_value="extrapolate", bounds_error=False)
        values = linear(eval_x)

    linear = interp1d(x, y, kind="linear", fill_value="extrapolate", bounds_error=False)
    tail_n = max(0, min(int(linear_tail_days), len(dates)))
    if tail_n > 0:
        values[-tail_n:] = linear(eval_x[-tail_n:])

    missing = np.isnan(values)
    if missing.any():
        values[missing] = linear(eval_x[missing])

    if np.isnan(values).any():
        raise ValueError("Daily interpolation still contains NaN values after linear fallback")

    return pd.DataFrame({"time": dates.strftime("%Y-%m-%d"), "value": values})


def standardize_daily_matrix(df: pd.DataFrame, *, date_col: str = "time", ddof: int = 1) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    out = df.copy()
    stats: list[dict[str, Any]] = []
    covariate_cols = [col for col in out.columns if col != date_col]
    for col in covariate_cols:
        series = pd.to_numeric(out[col], errors="coerce")
        mean = float(series.mean())
        std = float(series.std(ddof=ddof))
        if not np.isfinite(std) or std == 0.0:
            raise ValueError(f"Cannot standardize {col}: standard deviation is {std}")
        out[col] = (series - mean) / std
        stats.append(
            {
                "index_id": col,
                "raw_mean": mean,
                "raw_std": std,
                "std_mean": float(out[col].mean()),
                "std_std": float(out[col].std(ddof=ddof)),
                "ddof": ddof,
            }
        )
    return out, stats


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_index_catalog(path: Path, indices: list[dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["index_id", "display_name", "url"])
        writer.writeheader()
        for row in indices:
            writer.writerow({"index_id": row["index_id"], "display_name": row["display_name"], "url": row["url"]})


def snapshot_config(config_path: Path, output_path: Path) -> None:
    ensure_dir(output_path.parent)
    shutil.copyfile(config_path, output_path)


def render_download_review(cfg: dict[str, Any], manifest_rows: list[dict[str, Any]], paths: CanonicalPaths) -> None:
    lines = [
        "# Canonical Climate Index Download Review",
        "",
        f"- generated_at_utc: `{utc_now_iso()}`",
        f"- lineage_version: `{cfg['version']}`",
        f"- indices_requested: `{len(cfg['indices'])}`",
        f"- raw_text_root: `{paths.raw_text_root}`",
        f"- monthly_csv_root: `{paths.monthly_csv_root}`",
        "",
        "| index_id | display_name | year_min | year_max | month_start_min | month_start_max | parsed_rows |",
        "| --- | --- | ---: | ---: | --- | --- | ---: |",
    ]
    for row in manifest_rows:
        lines.append(
            f"| `{row['index_id']}` | {row['display_name']} | {row['year_min']} | {row['year_max']} | {row['month_start_min']} | {row['month_start_max']} | {row['parsed_rows']} |"
        )
    (paths.review_root / "CANONICAL_CLIMATE_INDEX_DOWNLOAD_REVIEW.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_postprocess_review(
    cfg: dict[str, Any],
    validation: dict[str, Any],
    standardization_stats: list[dict[str, Any]],
    paths: CanonicalPaths,
) -> None:
    lines = [
        "# Canonical Climate Index Postprocess Review",
        "",
        f"- generated_at_utc: `{utc_now_iso()}`",
        f"- lineage_version: `{cfg['version']}`",
        f"- canonical_window: `{validation['canonical_window']['start_date']}` -> `{validation['canonical_window']['end_date']}`",
        f"- daily_rows: `{validation['daily_row_count']}`",
        f"- interpolation_method: `{validation['interpolation']['method']}`",
        f"- linear_tail_days: `{validation['interpolation']['linear_tail_days']}`",
        f"- standardization_ddof: `{validation['standardization']['ddof']}`",
        "",
        "## Monthly Coverage",
        "",
        "| index_id | month_start_min | month_start_max | monthly_rows | daily_min | daily_max | missing_daily |",
        "| --- | --- | --- | ---: | --- | --- | ---: |",
    ]
    for row in validation["per_index_coverage"]:
        lines.append(
            f"| `{row['index_id']}` | {row['month_start_min']} | {row['month_start_max']} | {row['monthly_rows']} | {row['daily_min']} | {row['daily_max']} | {row['missing_daily']} |"
        )
    lines.extend([
        "",
        "## Standardization Summary",
        "",
        "| index_id | raw_mean | raw_std | std_mean | std_std |",
        "| --- | ---: | ---: | ---: | ---: |",
    ])
    for row in standardization_stats:
        lines.append(
            f"| `{row['index_id']}` | {row['raw_mean']:.6f} | {row['raw_std']:.6f} | {row['std_mean']:.6f} | {row['std_std']:.6f} |"
        )
    (paths.review_root / "CANONICAL_CLIMATE_INDEX_POSTPROCESS_REVIEW.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

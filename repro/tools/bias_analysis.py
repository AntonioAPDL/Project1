#!/usr/bin/env python3
"""Build bias analysis tables/plots from existing forecats bundles and retros data.

This tool is intentionally read-only on existing pipeline artifacts. It creates a
new run-scoped output tree under ``repro/bias_runs/<RUN_ID>/``.

Bias definitions (cms):
- Bias_retro(t, c) = USGS(t) - Retro_c(t)
- Bias_forecast(t, c, h) = USGS(t) - MeanEnsemble_c(issue=t-h, target=t)
- Delta(t, c, h) = Bias_forecast(t, c, h) - Bias_retro(t, c)
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import yaml
except Exception as exc:
    print(f"ERROR: Missing required dependency for bias_analysis.py: {exc}", file=sys.stderr)
    sys.exit(2)


DEFAULT_INTERVALS: List[Dict[str, str]] = [
    {"start": "2019-11-05", "end": "2020-03-11"},
    {"start": "2020-03-17", "end": "2020-07-28"},
    {"start": "2020-07-30", "end": "2020-11-13"},
    {"start": "2020-11-15", "end": "2022-07-13"},
    {"start": "2022-07-15", "end": "2023-01-31"},
]

DEFAULT_CONFIG: Dict[str, Any] = {
    "run": {
        "run_id": None,
        "out_root": "repro/bias_runs",
        "overwrite": False,
    },
    "inputs": {
        "forecats_root": "data/forecats_inputs/site=11160500",
        "retros_path": "retros_2023-06-01.csv",
        "retros_scale": "log1p_cms",
        "usgs_col": "USGS",
        "run_id_selector": "latest_mtime",
        "explicit_run_id": None,
    },
    "analysis": {
        "horizons_days": [1, 7],
        "intervals": DEFAULT_INTERVALS,
    },
    "centers": [
        {
            "key": "NWS_NWM",
            "label": "NWS/NWM",
            "retros_col": "NWS3.0",
            "forecast_file": "nws_weighted_daily.csv",
        },
        {
            "key": "GLOFAS",
            "label": "GloFAS",
            "retros_col": "GloFAS",
            "forecast_file": "glofas_weighted_daily.csv",
        },
    ],
    "plots": {
        "dpi": 180,
        "width": 14,
        "height": 7,
        "line_width": 0.9,
        "marker_size": 3.0,
        "y_limits_cms": [-30.0, 30.0],
        "scatter_limits_cms": [-30.0, 30.0],
        "center_palette": [
            "#1f77b4",
            "#ff7f0e",
            "#2ca02c",
            "#9467bd",
            "#17becf",
            "#8c564b",
        ],
        # Optional explicit center groups. If omitted, defaults are:
        # - all centers
        # - one group per center
        "center_groups": None,
    },
}

METRIC_META: Dict[str, Dict[str, str]] = {
    "bias_retro_cms": {"label": "Bias retro", "linestyle": "-", "marker": "o", "color": "#1b9e77"},
    "bias_forecast_cms": {"label": "Bias forecast", "linestyle": "--", "marker": "s", "color": "#7570b3"},
    "delta_bias_cms": {"label": "Bias delta (forecast-retro)", "linestyle": ":", "marker": "^", "color": "#d95f02"},
}


@dataclass(frozen=True)
class IntervalSpec:
    index: int
    start: date
    end: date
    window_id: str
    label: str


@dataclass(frozen=True)
class CenterSpec:
    key: str
    label: str
    retros_col: str
    forecast_file: str


@dataclass(frozen=True)
class CenterGroupSpec:
    key: str
    label: str
    center_keys: Tuple[str, ...]


def utc_now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bias analysis from forecats bundles and retros data")
    parser.add_argument(
        "--config",
        default="config/bias_analysis.template.yaml",
        help="Path to YAML config (default: config/bias_analysis.template.yaml)",
    )
    return parser.parse_args(argv)


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def load_resolved_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    cfg = deep_merge(DEFAULT_CONFIG, raw)
    validate_config(cfg)
    return cfg


def validate_config(cfg: Dict[str, Any]) -> None:
    run = cfg.get("run")
    inputs = cfg.get("inputs")
    analysis = cfg.get("analysis")
    centers = cfg.get("centers")

    if not isinstance(run, dict):
        raise ValueError("config.run must be a mapping")
    if not isinstance(inputs, dict):
        raise ValueError("config.inputs must be a mapping")
    if not isinstance(analysis, dict):
        raise ValueError("config.analysis must be a mapping")
    if not isinstance(centers, list) or not centers:
        raise ValueError("config.centers must be a non-empty list")

    selector = str(inputs.get("run_id_selector", "latest_mtime"))
    if selector not in {"latest_mtime", "explicit"}:
        raise ValueError("inputs.run_id_selector must be 'latest_mtime' or 'explicit'")
    if selector == "explicit" and not str(inputs.get("explicit_run_id") or "").strip():
        raise ValueError("inputs.explicit_run_id is required when inputs.run_id_selector=explicit")

    scale = str(inputs.get("retros_scale", "log1p_cms"))
    if scale not in {"raw_cms", "log1p_cms"}:
        raise ValueError("inputs.retros_scale must be one of: raw_cms, log1p_cms")

    horizons = analysis.get("horizons_days")
    if not isinstance(horizons, list) or not horizons:
        raise ValueError("analysis.horizons_days must be a non-empty list of positive ints")
    parsed_horizons: List[int] = []
    for h in horizons:
        try:
            hv = int(h)
        except Exception as exc:
            raise ValueError(f"Invalid horizon value {h}: {exc}") from exc
        if hv <= 0:
            raise ValueError("analysis.horizons_days must contain only positive ints")
        parsed_horizons.append(hv)
    analysis["horizons_days"] = sorted(set(parsed_horizons))

    intervals = analysis.get("intervals")
    if not isinstance(intervals, list) or not intervals:
        raise ValueError("analysis.intervals must be a non-empty list")

    plots = cfg.get("plots")
    if not isinstance(plots, dict):
        raise ValueError("config.plots must be a mapping")

    parse_numeric_limits(plots.get("y_limits_cms"), "plots.y_limits_cms")
    parse_numeric_limits(plots.get("scatter_limits_cms"), "plots.scatter_limits_cms")

    palette = plots.get("center_palette")
    if not isinstance(palette, list) or not palette or not all(str(x).strip() for x in palette):
        raise ValueError("plots.center_palette must be a non-empty list of colors")

    groups = plots.get("center_groups")
    if groups is not None:
        if not isinstance(groups, list) or not groups:
            raise ValueError("plots.center_groups must be null or a non-empty list")
        for group in groups:
            if not isinstance(group, dict):
                raise ValueError("Each plots.center_groups entry must be a mapping")
            if not str(group.get("key") or "").strip():
                raise ValueError("Each center group requires non-empty key")
            if not str(group.get("label") or "").strip():
                raise ValueError("Each center group requires non-empty label")
            ckeys = group.get("centers")
            if not isinstance(ckeys, list) or not ckeys:
                raise ValueError("Each center group requires non-empty centers list")

    keys_seen: set[str] = set()
    for center in centers:
        if not isinstance(center, dict):
            raise ValueError("Each center entry must be a mapping")
        for req in ("key", "label", "retros_col", "forecast_file"):
            if not str(center.get(req) or "").strip():
                raise ValueError(f"Center field '{req}' is required")
        ckey = str(center["key"])
        if ckey in keys_seen:
            raise ValueError(f"Duplicate center key: {ckey}")
        keys_seen.add(ckey)


def parse_date(s: Any) -> date:
    return date.fromisoformat(str(s))


def parse_numeric_limits(raw: Any, field_name: str) -> Optional[Tuple[float, float]]:
    if raw is None:
        return None
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ValueError(f"{field_name} must be null or [min, max]")
    lo = float(raw[0])
    hi = float(raw[1])
    if not np.isfinite(lo) or not np.isfinite(hi):
        raise ValueError(f"{field_name} must contain finite numeric limits")
    if lo >= hi:
        raise ValueError(f"{field_name} requires min < max")
    return (lo, hi)


def parse_intervals(items: Sequence[Dict[str, Any]]) -> List[IntervalSpec]:
    intervals: List[IntervalSpec] = []
    for idx, raw in enumerate(items, start=1):
        if not isinstance(raw, dict):
            raise ValueError("Each interval must be a mapping with start/end")
        start = parse_date(raw.get("start"))
        end = parse_date(raw.get("end"))
        if start > end:
            raise ValueError(f"Interval start must be <= end: {start} > {end}")
        window_id = f"w{idx:02d}_{start.isoformat()}_to_{end.isoformat()}"
        label = f"{start.isoformat()} to {end.isoformat()}"
        intervals.append(IntervalSpec(index=idx, start=start, end=end, window_id=window_id, label=label))

    # Enforce no overlap to keep window mapping unambiguous.
    intervals_sorted = sorted(intervals, key=lambda x: (x.start, x.end))
    for prev, cur in zip(intervals_sorted[:-1], intervals_sorted[1:]):
        if cur.start <= prev.end:
            raise ValueError(
                "Intervals overlap, which is not allowed for deterministic window mapping: "
                f"{prev.window_id} and {cur.window_id}"
            )
    return intervals_sorted


def build_window_lookup(intervals: Sequence[IntervalSpec]) -> Dict[date, IntervalSpec]:
    lookup: Dict[date, IntervalSpec] = {}
    for iv in intervals:
        d = iv.start
        while d <= iv.end:
            if d in lookup:
                raise ValueError(f"Date appears in multiple intervals: {d}")
            lookup[d] = iv
            d += timedelta(days=1)
    return lookup


def scale_to_cms(series: pd.Series, scale: str) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if scale == "raw_cms":
        return values
    if scale == "log1p_cms":
        return np.expm1(values)
    raise ValueError(f"Unsupported scale: {scale}")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def slugify_token(s: str) -> str:
    out = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in s.strip())
    out = out.strip("_")
    return out or "group"


def resolve_center_groups(
    plots_cfg: Dict[str, Any],
    centers: Sequence[CenterSpec],
) -> List[CenterGroupSpec]:
    center_keys = [c.key for c in centers]
    center_map = {c.key: c for c in centers}

    raw_groups = plots_cfg.get("center_groups")
    groups: List[CenterGroupSpec] = []
    if raw_groups is None:
        groups.append(CenterGroupSpec(key="all", label="All centers", center_keys=tuple(center_keys)))
        for c in centers:
            groups.append(
                CenterGroupSpec(
                    key=slugify_token(c.key.lower()),
                    label=f"{c.label} only",
                    center_keys=(c.key,),
                )
            )
        return groups

    seen_group_keys: set[str] = set()
    for raw in raw_groups:
        key = slugify_token(str(raw["key"]))
        label = str(raw["label"]).strip()
        ckeys = tuple(str(x).strip() for x in raw["centers"] if str(x).strip())
        if not ckeys:
            raise ValueError(f"Center group '{key}' has no valid centers")
        unknown = [k for k in ckeys if k not in center_map]
        if unknown:
            raise ValueError(f"Center group '{key}' references unknown centers: {unknown}")
        if key in seen_group_keys:
            raise ValueError(f"Duplicate center group key: {key}")
        seen_group_keys.add(key)
        groups.append(CenterGroupSpec(key=key, label=label, center_keys=ckeys))
    return groups


def build_center_color_map(centers: Sequence[CenterSpec], palette: Sequence[str]) -> Dict[str, str]:
    return {center.key: str(palette[i % len(palette)]) for i, center in enumerate(centers)}


def markevery_for_length(n: int) -> int:
    if n <= 0:
        return 1
    return max(1, n // 24)


def select_run_dir(cutoff_dir: Path, selector: str, explicit_run_id: Optional[str]) -> Path:
    run_dirs = [p for p in cutoff_dir.iterdir() if p.is_dir() and p.name.startswith("run_id=")]
    if not run_dirs:
        raise FileNotFoundError(f"No run_id=* directories under {cutoff_dir}")

    if selector == "explicit":
        assert explicit_run_id is not None
        expected_a = f"run_id={explicit_run_id}"
        expected_b = explicit_run_id
        matches = [p for p in run_dirs if p.name in {expected_a, expected_b}]
        if not matches:
            raise FileNotFoundError(
                f"Requested explicit run id '{explicit_run_id}' not found under {cutoff_dir}"
            )
        return sorted(matches, key=lambda p: p.name)[-1]

    # latest_mtime default
    run_dirs_sorted = sorted(run_dirs, key=lambda p: (p.stat().st_mtime, p.name))
    return run_dirs_sorted[-1]


def collect_cutoff_run_map(
    forecats_root: Path,
    selector: str,
    explicit_run_id: Optional[str],
) -> pd.DataFrame:
    if not forecats_root.exists():
        raise FileNotFoundError(f"Forecats root not found: {forecats_root}")

    rows: List[Dict[str, Any]] = []
    for cutoff_dir in sorted(forecats_root.glob("cutoff_date=*")):
        if not cutoff_dir.is_dir():
            continue
        name = cutoff_dir.name
        try:
            cutoff_date = parse_date(name.split("=", 1)[1])
        except Exception:
            continue
        run_dir = select_run_dir(cutoff_dir, selector=selector, explicit_run_id=explicit_run_id)
        rows.append({"cutoff_date": cutoff_date, "run_dir": str(run_dir)})

    if not rows:
        raise ValueError(f"No cutoff_date=* directories found under {forecats_root}")

    out = pd.DataFrame(rows).sort_values("cutoff_date").reset_index(drop=True)
    return out


def load_retros_wide(
    retros_path: Path,
    retros_scale: str,
    usgs_col: str,
    centers: Sequence[CenterSpec],
) -> pd.DataFrame:
    if not retros_path.exists():
        raise FileNotFoundError(f"Retros file not found: {retros_path}")

    df = pd.read_csv(retros_path)
    date_col = "Date" if "Date" in df.columns else "date" if "date" in df.columns else None
    if date_col is None:
        raise ValueError(f"Retros file must contain Date/date column: {retros_path}")

    required_cols = [usgs_col] + [c.retros_col for c in centers]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Retros file missing columns {missing}: {retros_path}")

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[date_col], errors="coerce").dt.date
    out["usgs_cms"] = scale_to_cms(df[usgs_col], retros_scale)

    for center in centers:
        col_name = f"retro_{center.key}_cms"
        out[col_name] = scale_to_cms(df[center.retros_col], retros_scale)

    out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return out


def assign_windows(df: pd.DataFrame, date_col: str, lookup: Dict[date, IntervalSpec]) -> pd.DataFrame:
    df = df.copy()
    mapped = df[date_col].map(lookup)
    df["window_id"] = mapped.map(lambda x: x.window_id if isinstance(x, IntervalSpec) else None)
    df["window_label"] = mapped.map(lambda x: x.label if isinstance(x, IntervalSpec) else None)
    df["window_start"] = mapped.map(lambda x: x.start if isinstance(x, IntervalSpec) else None)
    df["window_end"] = mapped.map(lambda x: x.end if isinstance(x, IntervalSpec) else None)
    return df


def build_retro_bias(
    retros_wide: pd.DataFrame,
    centers: Sequence[CenterSpec],
    window_lookup: Dict[date, IntervalSpec],
) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for center in centers:
        retro_col = f"retro_{center.key}_cms"
        piece = pd.DataFrame(
            {
                "target_date": retros_wide["date"],
                "center_key": center.key,
                "center_label": center.label,
                "usgs_cms": retros_wide["usgs_cms"],
                "retro_cms": retros_wide[retro_col],
            }
        )
        piece["bias_retro_cms"] = piece["usgs_cms"] - piece["retro_cms"]
        frames.append(piece)

    out = pd.concat(frames, ignore_index=True)
    out = assign_windows(out, "target_date", window_lookup)
    out = out[out["window_id"].notna()].reset_index(drop=True)
    return out


def detect_target_date_col(columns: Iterable[str]) -> str:
    cols = set(columns)
    if "target_date" in cols:
        return "target_date"
    if "Date" in cols:
        return "Date"
    if "date" in cols:
        return "date"
    raise ValueError("Forecast file missing date column: expected target_date or Date/date")


def detect_member_cols(df: pd.DataFrame, date_col: str) -> List[str]:
    member_cols = [c for c in df.columns if c.startswith("member_")]
    if member_cols:
        return member_cols
    fallback_exclusions = {date_col, "target_date", "Date", "date"}
    fallback = [c for c in df.columns if c not in fallback_exclusions]
    if not fallback:
        raise ValueError("No ensemble member columns found")
    return fallback


def read_forecast_means_for_center(
    run_dir: Path,
    cutoff_date: date,
    center: CenterSpec,
    horizons: Sequence[int],
) -> pd.DataFrame:
    path = run_dir / "inputs" / center.forecast_file
    if not path.exists():
        return pd.DataFrame(columns=["issue_date", "target_date", "lead_days", "center_key", "center_label", "ensemble_mean_cms"])

    raw = pd.read_csv(path)
    if raw.empty:
        return pd.DataFrame(columns=["issue_date", "target_date", "lead_days", "center_key", "center_label", "ensemble_mean_cms"])

    date_col = detect_target_date_col(raw.columns)
    member_cols = detect_member_cols(raw, date_col)

    target_dates = pd.to_datetime(raw[date_col], errors="coerce").dt.date
    members = raw[member_cols].apply(pd.to_numeric, errors="coerce")
    ens_mean = members.mean(axis=1, skipna=True)

    out = pd.DataFrame(
        {
            "issue_date": cutoff_date,
            "target_date": target_dates,
            "center_key": center.key,
            "center_label": center.label,
            "ensemble_mean_cms": ens_mean,
        }
    )
    out = out.dropna(subset=["target_date"]).copy()
    out["lead_days"] = out["target_date"].map(lambda d: (d - cutoff_date).days)
    out = out[out["lead_days"].isin(list(horizons))]

    # Protect against accidental duplicate target rows by averaging.
    out = (
        out.groupby(["issue_date", "target_date", "lead_days", "center_key", "center_label"], as_index=False)[
            "ensemble_mean_cms"
        ]
        .mean()
        .sort_values(["target_date", "center_key"])
        .reset_index(drop=True)
    )
    return out


def build_forecast_means(
    cutoff_run_map: pd.DataFrame,
    centers: Sequence[CenterSpec],
    horizons: Sequence[int],
) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for rec in cutoff_run_map.itertuples(index=False):
        cutoff_date = rec.cutoff_date
        run_dir = Path(rec.run_dir)
        for center in centers:
            piece = read_forecast_means_for_center(run_dir, cutoff_date, center, horizons)
            if not piece.empty:
                frames.append(piece)

    if not frames:
        return pd.DataFrame(
            columns=["issue_date", "target_date", "lead_days", "center_key", "center_label", "ensemble_mean_cms"]
        )

    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values(["target_date", "center_key", "lead_days"]).reset_index(drop=True)
    return out


def build_forecast_bias(
    forecast_means: pd.DataFrame,
    retros_wide: pd.DataFrame,
    window_lookup: Dict[date, IntervalSpec],
) -> pd.DataFrame:
    if forecast_means.empty:
        out = forecast_means.copy()
        out["usgs_cms"] = np.nan
        out["bias_forecast_cms"] = np.nan
        return out

    usgs = retros_wide[["date", "usgs_cms"]].rename(columns={"date": "target_date"})
    out = forecast_means.merge(usgs, how="left", on="target_date")
    out["bias_forecast_cms"] = out["usgs_cms"] - out["ensemble_mean_cms"]
    out = assign_windows(out, "target_date", window_lookup)
    out = out[out["window_id"].notna()].reset_index(drop=True)
    return out


def build_bias_compare(forecast_bias: pd.DataFrame, retro_bias: pd.DataFrame) -> pd.DataFrame:
    retro_cols = retro_bias[["target_date", "center_key", "retro_cms", "bias_retro_cms"]]
    out = forecast_bias.merge(retro_cols, how="left", on=["target_date", "center_key"])
    out["delta_bias_cms"] = out["bias_forecast_cms"] - out["bias_retro_cms"]
    out = out.sort_values(["target_date", "center_key", "lead_days"]).reset_index(drop=True)
    return out


def compute_coverage(
    compare_df: pd.DataFrame,
    cutoff_dates: Sequence[date],
    centers: Sequence[CenterSpec],
    horizons: Sequence[int],
    intervals: Sequence[IntervalSpec],
) -> pd.DataFrame:
    cutoff_set = set(cutoff_dates)
    rows: List[Dict[str, Any]] = []

    for iv in intervals:
        target_dates: List[date] = []
        d = iv.start
        while d <= iv.end:
            target_dates.append(d)
            d += timedelta(days=1)

        for horizon in horizons:
            eligible = [t for t in target_dates if (t - timedelta(days=horizon)) in cutoff_set]
            for center in centers:
                mask = (
                    (compare_df["window_id"] == iv.window_id)
                    & (compare_df["lead_days"] == horizon)
                    & (compare_df["center_key"] == center.key)
                    & compare_df["bias_forecast_cms"].notna()
                    & compare_df["bias_retro_cms"].notna()
                )
                actual = int(mask.sum())
                expected = len(eligible)
                rows.append(
                    {
                        "window_id": iv.window_id,
                        "window_label": iv.label,
                        "center_key": center.key,
                        "center_label": center.label,
                        "lead_days": horizon,
                        "expected_count": expected,
                        "actual_count": actual,
                        "missing_count": max(expected - actual, 0),
                        "coverage_ratio": (actual / expected) if expected > 0 else np.nan,
                    }
                )

    return pd.DataFrame(rows)


def plot_time_series_group(
    compare_df: pd.DataFrame,
    interval: IntervalSpec,
    horizon: int,
    centers_by_key: Dict[str, CenterSpec],
    group: CenterGroupSpec,
    metric_cols: Sequence[str],
    metric_title: str,
    out_path: Path,
    width: float,
    height: float,
    dpi: int,
    line_width: float,
    marker_size: float,
    center_color_map: Dict[str, str],
    y_limits: Optional[Tuple[float, float]],
) -> None:
    subset = compare_df[
        (compare_df["window_id"] == interval.window_id)
        & (compare_df["lead_days"] == horizon)
        & (compare_df["center_key"].isin(list(group.center_keys)))
    ].copy()

    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
    if subset.empty:
        ax.set_title(f"No data: {group.label} | {interval.label} | horizon={horizon}d")
        ax.text(0.5, 0.5, "No rows", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(out_path)
        plt.close(fig)
        return

    is_single_center = len(group.center_keys) == 1
    subset = subset.sort_values("target_date")

    for center_key in group.center_keys:
        cdf = subset[subset["center_key"] == center_key]
        if cdf.empty:
            continue
        center_label = centers_by_key[center_key].label
        markevery = markevery_for_length(len(cdf))
        for metric_col in metric_cols:
            meta = METRIC_META[metric_col]
            if is_single_center:
                color = meta["color"]
                label = meta["label"]
            else:
                color = center_color_map[center_key]
                label = f"{center_label} | {meta['label']}"

            ax.plot(
                cdf["target_date"],
                cdf[metric_col],
                linestyle=meta["linestyle"],
                marker=meta["marker"],
                markevery=markevery,
                markersize=marker_size,
                linewidth=line_width,
                color=color,
                alpha=0.9,
                label=label,
            )

    ax.axhline(0.0, color="black", linewidth=0.9, alpha=0.8)
    if y_limits is not None:
        ax.set_ylim(y_limits)
    ax.set_xlabel("Target date")
    ax.set_ylabel("Bias (cms)")
    ax.set_title(f"{group.label} | {metric_title} | {interval.label} | h={horizon}d")
    ax.grid(True, alpha=0.25)

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ncol = 1 if len(labels) <= 6 else 2
        ax.legend(loc="upper left", fontsize=8, ncol=ncol)
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_scatter_group(
    compare_df: pd.DataFrame,
    interval: IntervalSpec,
    horizon: int,
    centers_by_key: Dict[str, CenterSpec],
    group: CenterGroupSpec,
    out_path: Path,
    width: float,
    height: float,
    dpi: int,
    center_color_map: Dict[str, str],
    scatter_limits: Optional[Tuple[float, float]],
) -> None:
    subset = compare_df[
        (compare_df["window_id"] == interval.window_id)
        & (compare_df["lead_days"] == horizon)
        & (compare_df["center_key"].isin(list(group.center_keys)))
    ].copy()

    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
    if subset.empty:
        ax.set_title(f"No data: {group.label} | {interval.label} | horizon={horizon}d")
        ax.text(0.5, 0.5, "No rows", ha="center", va="center", transform=ax.transAxes)
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(out_path)
        plt.close(fig)
        return

    markers = ["o", "s", "^", "D", "v", "P", "X", "<", ">"]
    for i, center_key in enumerate(group.center_keys):
        cdf = subset[subset["center_key"] == center_key].copy()
        cdf = cdf.dropna(subset=["bias_retro_cms", "bias_forecast_cms"])
        if cdf.empty:
            continue

        x = pd.to_numeric(cdf["bias_retro_cms"], errors="coerce")
        y = pd.to_numeric(cdf["bias_forecast_cms"], errors="coerce")
        mask = x.notna() & y.notna()
        x = x[mask]
        y = y[mask]
        if x.empty:
            continue

        corr = float(np.corrcoef(x, y)[0, 1]) if len(x) > 1 else np.nan
        corr_txt = f"{corr:.2f}" if np.isfinite(corr) else "NA"
        label = f"{centers_by_key[center_key].label} (n={len(x)}, r={corr_txt})"
        ax.scatter(
            x,
            y,
            s=20,
            alpha=0.65,
            color=center_color_map[center_key],
            marker=markers[i % len(markers)],
            edgecolor="none",
            label=label,
        )

    if scatter_limits is not None:
        lo, hi = scatter_limits
        ax.set_xlim((lo, hi))
        ax.set_ylim((lo, hi))
        diag_lo, diag_hi = lo, hi
    else:
        vals = pd.concat([subset["bias_retro_cms"], subset["bias_forecast_cms"]], ignore_index=True)
        vals = pd.to_numeric(vals, errors="coerce").dropna()
        if vals.empty:
            diag_lo, diag_hi = -1.0, 1.0
        else:
            diag_lo, diag_hi = float(vals.min()), float(vals.max())

    if np.isfinite(diag_lo) and np.isfinite(diag_hi) and diag_lo < diag_hi:
        ax.plot([diag_lo, diag_hi], [diag_lo, diag_hi], color="black", linestyle="--", linewidth=0.9, alpha=0.9)

    ax.axhline(0.0, color="#595959", linewidth=0.8, alpha=0.7)
    ax.axvline(0.0, color="#595959", linewidth=0.8, alpha=0.7)
    ax.set_xlabel("Bias retro (cms)")
    ax.set_ylabel("Bias forecast (cms)")
    ax.set_title(f"{group.label} | Bias relation | {interval.label} | h={horizon}d")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def make_summary(
    cfg: Dict[str, Any],
    run_id: str,
    cutoff_run_map: pd.DataFrame,
    retro_bias: pd.DataFrame,
    forecast_bias: pd.DataFrame,
    compare_df: pd.DataFrame,
    coverage: pd.DataFrame,
    center_groups: Sequence[CenterGroupSpec],
) -> Dict[str, Any]:
    coverage_rows = coverage.to_dict(orient="records") if not coverage.empty else []
    return {
        "generated_at_utc": utc_now_str(),
        "run_id": run_id,
        "inputs": {
            "forecats_root": cfg["inputs"]["forecats_root"],
            "retros_path": cfg["inputs"]["retros_path"],
            "retros_scale": cfg["inputs"]["retros_scale"],
            "run_id_selector": cfg["inputs"]["run_id_selector"],
            "explicit_run_id": cfg["inputs"].get("explicit_run_id"),
        },
        "analysis": {
            "horizons_days": cfg["analysis"]["horizons_days"],
            "intervals": cfg["analysis"]["intervals"],
            "center_groups": [
                {"key": g.key, "label": g.label, "centers": list(g.center_keys)} for g in center_groups
            ],
        },
        "counts": {
            "cutoff_runs_selected": int(len(cutoff_run_map)),
            "retro_bias_rows": int(len(retro_bias)),
            "forecast_bias_rows": int(len(forecast_bias)),
            "compare_rows": int(len(compare_df)),
        },
        "coverage": coverage_rows,
    }


def run_pipeline(cfg: Dict[str, Any]) -> Path:
    run_cfg = cfg["run"]
    inputs_cfg = cfg["inputs"]
    analysis_cfg = cfg["analysis"]
    plot_cfg = cfg["plots"]

    run_id = str(run_cfg.get("run_id") or f"bias_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    out_root = Path(str(run_cfg.get("out_root"))).expanduser().resolve()
    run_dir = out_root / run_id

    if run_dir.exists():
        if bool(run_cfg.get("overwrite", False)):
            shutil.rmtree(run_dir)
        else:
            raise FileExistsError(
                f"Output run directory already exists (set run.overwrite=true to replace): {run_dir}"
            )

    tables_dir = run_dir / "tables"
    plots_dir = run_dir / "plots"
    logs_dir = run_dir / "logs"
    ensure_dir(tables_dir)
    ensure_dir(plots_dir)
    ensure_dir(logs_dir)

    logger = logging.getLogger("bias_analysis")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(logs_dir / "bias_analysis.log")
    file_handler.setFormatter(fmt)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    logger.info("Starting bias analysis run_id=%s", run_id)

    intervals = parse_intervals(analysis_cfg["intervals"])
    window_lookup = build_window_lookup(intervals)
    horizons = [int(x) for x in analysis_cfg["horizons_days"]]
    centers = [CenterSpec(**c) for c in cfg["centers"]]
    centers_by_key = {c.key: c for c in centers}
    center_groups = resolve_center_groups(plot_cfg, centers)
    center_color_map = build_center_color_map(centers, [str(x) for x in plot_cfg["center_palette"]])

    forecats_root = Path(str(inputs_cfg["forecats_root"])).expanduser().resolve()
    retros_path = Path(str(inputs_cfg["retros_path"])).expanduser().resolve()

    cutoff_run_map = collect_cutoff_run_map(
        forecats_root=forecats_root,
        selector=str(inputs_cfg.get("run_id_selector", "latest_mtime")),
        explicit_run_id=(str(inputs_cfg["explicit_run_id"]).strip() if inputs_cfg.get("explicit_run_id") else None),
    )
    logger.info("Selected %d cutoff bundles from %s", len(cutoff_run_map), forecats_root)

    retros_wide = load_retros_wide(
        retros_path=retros_path,
        retros_scale=str(inputs_cfg.get("retros_scale", "log1p_cms")),
        usgs_col=str(inputs_cfg.get("usgs_col", "USGS")),
        centers=centers,
    )
    logger.info("Loaded retros rows=%d from %s", len(retros_wide), retros_path)

    retro_bias = build_retro_bias(retros_wide, centers, window_lookup)
    forecast_means = build_forecast_means(cutoff_run_map, centers, horizons)
    forecast_bias = build_forecast_bias(forecast_means, retros_wide, window_lookup)
    compare_df = build_bias_compare(forecast_bias, retro_bias)

    coverage = compute_coverage(
        compare_df=compare_df,
        cutoff_dates=list(cutoff_run_map["cutoff_date"]),
        centers=centers,
        horizons=horizons,
        intervals=intervals,
    )

    retro_bias.to_csv(tables_dir / "bias_retro.csv", index=False)
    forecast_bias.to_csv(tables_dir / "bias_forecast.csv", index=False)
    compare_df.to_csv(tables_dir / "bias_compare.csv", index=False)
    coverage.to_csv(tables_dir / "coverage.csv", index=False)
    cutoff_run_map.to_csv(tables_dir / "cutoff_run_map.csv", index=False)

    width = float(plot_cfg.get("width", 14))
    height = float(plot_cfg.get("height", 7))
    dpi = int(plot_cfg.get("dpi", 180))
    line_width = float(plot_cfg.get("line_width", 0.9))
    marker_size = float(plot_cfg.get("marker_size", 3.0))
    y_limits = parse_numeric_limits(plot_cfg.get("y_limits_cms"), "plots.y_limits_cms")
    scatter_limits = parse_numeric_limits(plot_cfg.get("scatter_limits_cms"), "plots.scatter_limits_cms")

    for interval in intervals:
        interval_plot_dir = plots_dir / interval.window_id
        ensure_dir(interval_plot_dir)
        for horizon in horizons:
            for group in center_groups:
                # 1) Full overlap view (retro + forecast + delta)
                plot_time_series_group(
                    compare_df=compare_df,
                    interval=interval,
                    horizon=horizon,
                    centers_by_key=centers_by_key,
                    group=group,
                    metric_cols=["bias_retro_cms", "bias_forecast_cms", "delta_bias_cms"],
                    metric_title="Retro + Forecast + Delta",
                    out_path=interval_plot_dir / f"ts_{group.key}_all_metrics_h{horizon:02d}.png",
                    width=width,
                    height=height,
                    dpi=dpi,
                    line_width=line_width,
                    marker_size=marker_size,
                    center_color_map=center_color_map,
                    y_limits=y_limits,
                )

                # 2) Metric-specific views for clearer comparisons
                plot_time_series_group(
                    compare_df=compare_df,
                    interval=interval,
                    horizon=horizon,
                    centers_by_key=centers_by_key,
                    group=group,
                    metric_cols=["bias_retro_cms"],
                    metric_title="Retro bias",
                    out_path=interval_plot_dir / f"ts_{group.key}_retro_h{horizon:02d}.png",
                    width=width,
                    height=height,
                    dpi=dpi,
                    line_width=line_width,
                    marker_size=marker_size,
                    center_color_map=center_color_map,
                    y_limits=y_limits,
                )
                plot_time_series_group(
                    compare_df=compare_df,
                    interval=interval,
                    horizon=horizon,
                    centers_by_key=centers_by_key,
                    group=group,
                    metric_cols=["bias_forecast_cms"],
                    metric_title="Forecast bias",
                    out_path=interval_plot_dir / f"ts_{group.key}_forecast_h{horizon:02d}.png",
                    width=width,
                    height=height,
                    dpi=dpi,
                    line_width=line_width,
                    marker_size=marker_size,
                    center_color_map=center_color_map,
                    y_limits=y_limits,
                )
                plot_time_series_group(
                    compare_df=compare_df,
                    interval=interval,
                    horizon=horizon,
                    centers_by_key=centers_by_key,
                    group=group,
                    metric_cols=["delta_bias_cms"],
                    metric_title="Forecast minus retro bias",
                    out_path=interval_plot_dir / f"ts_{group.key}_delta_h{horizon:02d}.png",
                    width=width,
                    height=height,
                    dpi=dpi,
                    line_width=line_width,
                    marker_size=marker_size,
                    center_color_map=center_color_map,
                    y_limits=y_limits,
                )

                # 3) Retro vs forecast relation scatter
                plot_scatter_group(
                    compare_df=compare_df,
                    interval=interval,
                    horizon=horizon,
                    centers_by_key=centers_by_key,
                    group=group,
                    out_path=interval_plot_dir / f"scatter_{group.key}_h{horizon:02d}.png",
                    width=width,
                    height=height,
                    dpi=dpi,
                    center_color_map=center_color_map,
                    scatter_limits=scatter_limits,
                )

                # Backward-compatible aliases for the all-centers view.
                if group.key == "all":
                    src_overlay = interval_plot_dir / f"ts_{group.key}_all_metrics_h{horizon:02d}.png"
                    src_scatter = interval_plot_dir / f"scatter_{group.key}_h{horizon:02d}.png"
                    shutil.copyfile(src_overlay, interval_plot_dir / f"bias_overlay_h{horizon:02d}.png")
                    shutil.copyfile(src_scatter, interval_plot_dir / f"bias_scatter_h{horizon:02d}.png")

    summary = make_summary(
        cfg,
        run_id,
        cutoff_run_map,
        retro_bias,
        forecast_bias,
        compare_df,
        coverage,
        center_groups=center_groups,
    )
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (run_dir / "resolved_config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    logger.info("Completed bias analysis run_id=%s", run_id)
    logger.info("Outputs written to %s", run_dir)
    return run_dir


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    config_path = Path(args.config).expanduser().resolve()
    cfg = load_resolved_config(config_path)
    run_dir = run_pipeline(cfg)
    print(str(run_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

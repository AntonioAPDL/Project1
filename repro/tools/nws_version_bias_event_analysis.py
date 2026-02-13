#!/usr/bin/env python3
"""NWS-only bias analysis by version windows with event-focused outputs.

This script does not modify the unified pipeline. It reads existing forecats bundles
and retrospective files, then writes a standalone analysis run under
``repro/bias_version_runs/<RUN_ID>/``.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import yaml
except Exception as exc:
    print(f"ERROR: Missing required dependency for nws_version_bias_event_analysis.py: {exc}", file=sys.stderr)
    sys.exit(2)


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    import bias_analysis
except Exception as exc:
    print(f"ERROR: Unable to import repro/tools/bias_analysis.py: {exc}", file=sys.stderr)
    sys.exit(2)


DEFAULT_CONFIG: Dict[str, Any] = {
    "run": {
        "run_id": None,
        "out_root": "repro/bias_version_runs",
        "overwrite": False,
    },
    "inputs": {
        "forecats_root": "data/forecats_inputs/site=11160500",
        "run_id_selector": "latest_mtime",
        "explicit_run_id": None,
        "nws_forecast_file": "nws_weighted_daily.csv",
        "retros_daily_path": "retros_2023-06-01.csv",
        "retros_daily_scale": "log1p_cms",
        "usgs_col": "USGS",
        "canonical_nws_col": "NWS3.0",
        "nws_hourly_sources": [
            {
                "key": "NWS2.1_source",
                "label": "NWM retrospective 2.1",
                "path": "11160500_nws_retro_old.csv",
                "datetime_col": "Date",
                "value_col": "streamflow",
                "value_scale": "raw_cms",
            },
            {
                "key": "NWS3.0_source",
                "label": "NWM retrospective 3.0",
                "path": "11160500_nws_retro.csv",
                "datetime_col": "Date",
                "value_col": "streamflow",
                "value_scale": "raw_cms",
            },
        ],
    },
    "analysis": {
        "allow_overlapping_versions": True,
        "horizons_days": [1, 7],
        "focus_dates": [
            "2021-01-23",
            "2021-01-27",
            "2021-11-12",
            "2021-12-10",
            "2021-12-17",
            "2021-12-21",
            "2022-05-10",
            "2022-12-25",
        ],
        "window_days_before": 14,
        "window_days_after": 14,
        "local_stat_days": 3,
        "version_windows": [
            {
                "version": "NWS2.1",
                "start": "1979-02-01",
                "end": "2020-12-31",
                "source_key": "NWS2.1_source",
            },
            {
                "version": "NWS3.0",
                "start": "1979-02-01",
                "end": "2023-02-01",
                "source_key": "NWS3.0_source",
            },
        ],
    },
    "plots": {
        "dpi": 180,
        "width": 14,
        "height": 9,
        "line_width": 0.85,
        "marker_size": 2.4,
        "y_limits_cms": [-30.0, 30.0],
        "retro_overlay_start": "2018-01-01",
        "retro_overlay_end": "2023-02-01",
        "source_palette": {
            "NWS2.1_source": "#1f77b4",
            "NWS3.0_source": "#d62728",
            "canonical_daily": "#2ca02c",
        },
        "version_palette": {
            "NWS1.0": "#1f77b4",
            "NWS2.0": "#ff7f0e",
            "NWS2.1": "#2ca02c",
            "NWS3.0": "#9467bd",
        },
    },
}


@dataclass(frozen=True)
class EventDate:
    raw: str
    parsed: date
    sanitized: bool
    note: str


@dataclass(frozen=True)
class HourlySourceSpec:
    key: str
    label: str
    path: str
    datetime_col: str
    value_col: str
    value_scale: str


@dataclass(frozen=True)
class VersionWindow:
    version: str
    start: date
    end: Optional[date]
    source_key: str


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NWS versioned bias event analysis")
    parser.add_argument("--config", default="config/nws_version_bias_event_analysis.template.yaml")
    return parser.parse_args(argv)


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_event_date(raw: Any) -> EventDate:
    text = str(raw).strip()
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if not m:
        raise ValueError(f"Invalid focus date '{text}'")
    parsed = date.fromisoformat(m.group(1))
    return EventDate(raw=text, parsed=parsed, sanitized=(m.group(1) != text), note="sanitized" if m.group(1) != text else "as_provided")


def parse_limit(raw: Any, name: str) -> Optional[Tuple[float, float]]:
    if raw is None:
        return None
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ValueError(f"{name} must be null or [min,max]")
    lo = float(raw[0])
    hi = float(raw[1])
    if not np.isfinite(lo) or not np.isfinite(hi) or lo >= hi:
        raise ValueError(f"{name} must be finite and min < max")
    return (lo, hi)


def scale_to_cms(values: pd.Series, scale: str) -> pd.Series:
    v = pd.to_numeric(values, errors="coerce")
    if scale == "raw_cms":
        return v
    if scale == "log1p_cms":
        return np.expm1(v)
    raise ValueError(f"Unsupported scale: {scale}")


def parse_version_windows(raw_items: Sequence[Dict[str, Any]], allow_overlap: bool = False) -> List[VersionWindow]:
    out: List[VersionWindow] = []
    for item in raw_items:
        if not isinstance(item, dict):
            raise ValueError("Each analysis.version_windows entry must be a mapping")
        version = str(item.get("version") or "").strip()
        source_key = str(item.get("source_key") or "").strip()
        if not version:
            raise ValueError("analysis.version_windows[].version is required")
        if not source_key:
            raise ValueError("analysis.version_windows[].source_key is required")
        start_raw = str(item.get("start") or "").strip()
        end_raw = item.get("end")
        if not start_raw:
            raise ValueError(f"Version window '{version}' missing start")
        start = date.fromisoformat(start_raw)
        end = date.fromisoformat(str(end_raw)) if end_raw not in (None, "", "null") else None
        if end is not None and end < start:
            raise ValueError(f"Version window '{version}' has end < start")
        out.append(VersionWindow(version=version, start=start, end=end, source_key=source_key))

    out_sorted = sorted(out, key=lambda x: (x.start, x.end or date.max, x.version))
    if not allow_overlap:
        for prev, cur in zip(out_sorted[:-1], out_sorted[1:]):
            prev_end = prev.end or date.max
            if cur.start <= prev_end:
                raise ValueError(f"Overlapping version windows: {prev.version} and {cur.version}")
    return out_sorted


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError("Config root must be a mapping")
    cfg = deep_merge(DEFAULT_CONFIG, raw)
    validate_config(cfg)
    return cfg


def validate_config(cfg: Dict[str, Any]) -> None:
    for k in ("run", "inputs", "analysis", "plots"):
        if not isinstance(cfg.get(k), dict):
            raise ValueError(f"{k} must be a mapping")

    inputs = cfg["inputs"]
    analysis = cfg["analysis"]
    plots = cfg["plots"]

    selector = str(inputs.get("run_id_selector", "latest_mtime"))
    if selector not in {"latest_mtime", "explicit"}:
        raise ValueError("inputs.run_id_selector must be latest_mtime or explicit")
    if selector == "explicit" and not str(inputs.get("explicit_run_id") or "").strip():
        raise ValueError("inputs.explicit_run_id is required when run_id_selector=explicit")

    scale = str(inputs.get("retros_daily_scale", "log1p_cms"))
    if scale not in {"raw_cms", "log1p_cms"}:
        raise ValueError("inputs.retros_daily_scale must be raw_cms or log1p_cms")

    if not isinstance(inputs.get("nws_hourly_sources"), list) or not inputs["nws_hourly_sources"]:
        raise ValueError("inputs.nws_hourly_sources must be a non-empty list")

    source_keys: set[str] = set()
    for raw in inputs["nws_hourly_sources"]:
        if not isinstance(raw, dict):
            raise ValueError("Each inputs.nws_hourly_sources entry must be a mapping")
        for req in ("key", "label", "path", "datetime_col", "value_col", "value_scale"):
            if not str(raw.get(req) or "").strip():
                raise ValueError(f"Missing required source field: {req}")
        value_scale = str(raw["value_scale"])
        if value_scale not in {"raw_cms", "log1p_cms"}:
            raise ValueError("inputs.nws_hourly_sources[].value_scale must be raw_cms or log1p_cms")
        key = str(raw["key"])
        if key in source_keys:
            raise ValueError(f"Duplicate source key: {key}")
        source_keys.add(key)

    horizons = analysis.get("horizons_days")
    if not isinstance(horizons, list) or not horizons:
        raise ValueError("analysis.horizons_days must be a non-empty list")
    analysis["horizons_days"] = sorted(set(int(x) for x in horizons))
    if any(int(x) <= 0 for x in analysis["horizons_days"]):
        raise ValueError("analysis.horizons_days must contain positive integers")

    focus_dates = analysis.get("focus_dates")
    if not isinstance(focus_dates, list) or not focus_dates:
        raise ValueError("analysis.focus_dates must be a non-empty list")
    _ = [parse_event_date(x) for x in focus_dates]

    for key in ("window_days_before", "window_days_after", "local_stat_days"):
        v = int(analysis.get(key, 0))
        if v < 0:
            raise ValueError(f"analysis.{key} must be >= 0")
        analysis[key] = v

    windows_raw = analysis.get("version_windows")
    if not isinstance(windows_raw, list) or not windows_raw:
        raise ValueError("analysis.version_windows must be a non-empty list")
    allow_overlap = bool(analysis.get("allow_overlapping_versions", False))
    windows = parse_version_windows(windows_raw, allow_overlap=allow_overlap)
    unknown = [w.source_key for w in windows if w.source_key not in source_keys]
    if unknown:
        raise ValueError(f"Version windows reference unknown source_key values: {sorted(set(unknown))}")

    parse_limit(plots.get("y_limits_cms"), "plots.y_limits_cms")


def load_daily_canonical(cfg: Dict[str, Any]) -> pd.DataFrame:
    inputs = cfg["inputs"]
    path = Path(str(inputs["retros_daily_path"]))
    if not path.exists():
        raise FileNotFoundError(f"Canonical retros daily file not found: {path}")

    df = pd.read_csv(path)
    date_col = "Date" if "Date" in df.columns else "date" if "date" in df.columns else None
    if date_col is None:
        raise ValueError(f"Retros daily file requires Date/date column: {path}")

    usgs_col = str(inputs.get("usgs_col", "USGS"))
    nws_col = str(inputs.get("canonical_nws_col", "NWS3.0"))
    missing = [c for c in (usgs_col, nws_col) if c not in df.columns]
    if missing:
        raise ValueError(f"Retros daily file missing required columns {missing}: {path}")

    scale = str(inputs.get("retros_daily_scale", "log1p_cms"))

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[date_col], errors="coerce").dt.date
    out["usgs_cms"] = scale_to_cms(df[usgs_col], scale)
    out["nws_canonical_cms"] = scale_to_cms(df[nws_col], scale)
    out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    out = out.drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    return out


def load_hourly_source_daily_log1p(source: HourlySourceSpec) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    path = Path(source.path)
    audit: Dict[str, Any] = {
        "source_key": source.key,
        "source_label": source.label,
        "path": str(path),
        "path_exists": bool(path.exists()),
        "rows_raw": 0,
        "rows_with_datetime": 0,
        "rows_with_value": 0,
        "datetime_min": None,
        "datetime_max": None,
        "date_min": None,
        "date_max": None,
        "n_missing_values": 0,
        "n_days": 0,
        "n_days_missing": 0,
        "daily_date_min": None,
        "daily_date_max": None,
    }

    if not path.exists():
        return pd.DataFrame(columns=["date", "retro_cms", "retro_log1p"]), audit

    df = pd.read_csv(path)
    audit["rows_raw"] = int(len(df))

    if source.datetime_col not in df.columns:
        raise ValueError(f"Source {source.key} missing datetime column '{source.datetime_col}': {path}")
    if source.value_col not in df.columns:
        raise ValueError(f"Source {source.key} missing value column '{source.value_col}': {path}")

    dt = pd.to_datetime(df[source.datetime_col], errors="coerce")
    v_cms = scale_to_cms(df[source.value_col], source.value_scale)

    audit["rows_with_datetime"] = int(dt.notna().sum())
    audit["rows_with_value"] = int(v_cms.notna().sum())
    audit["n_missing_values"] = int(v_cms.isna().sum())

    valid = pd.DataFrame({"datetime": dt, "retro_cms": v_cms}).dropna(subset=["datetime"]).copy()
    if valid.empty:
        return pd.DataFrame(columns=["date", "retro_cms", "retro_log1p"]), audit

    audit["datetime_min"] = valid["datetime"].min().isoformat()
    audit["datetime_max"] = valid["datetime"].max().isoformat()

    valid = valid.sort_values("datetime")
    valid["date"] = valid["datetime"].dt.date
    # Daily series in the same log1p domain used by existing retros tables.
    daily = (
        valid.assign(retro_log1p=np.log1p(pd.to_numeric(valid["retro_cms"], errors="coerce")))
        .groupby("date", as_index=False)[["retro_cms", "retro_log1p"]]
        .mean()
    )

    audit["n_days"] = int(len(daily))
    audit["daily_date_min"] = daily["date"].min().isoformat() if len(daily) else None
    audit["daily_date_max"] = daily["date"].max().isoformat() if len(daily) else None
    audit["date_min"] = audit["daily_date_min"]
    audit["date_max"] = audit["daily_date_max"]

    if len(daily):
        date_range = pd.date_range(daily["date"].min(), daily["date"].max(), freq="D")
        missing_days = len(set(date_range.date) - set(daily["date"]))
        audit["n_days_missing"] = int(missing_days)

    return daily, audit


def select_source_specs(cfg: Dict[str, Any]) -> List[HourlySourceSpec]:
    specs: List[HourlySourceSpec] = []
    for raw in cfg["inputs"]["nws_hourly_sources"]:
        specs.append(
            HourlySourceSpec(
                key=str(raw["key"]),
                label=str(raw["label"]),
                path=str(raw["path"]),
                datetime_col=str(raw["datetime_col"]),
                value_col=str(raw["value_col"]),
                value_scale=str(raw["value_scale"]),
            )
        )
    return specs


def version_for_date(target: date, windows: Sequence[VersionWindow]) -> Optional[VersionWindow]:
    for w in windows:
        if target < w.start:
            continue
        if w.end is None or target <= w.end:
            return w
    return None


def build_forecast_bias_nws(
    cfg: Dict[str, Any],
    horizons: Sequence[int],
    canonical_daily: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    inputs = cfg["inputs"]
    forecats_root = Path(str(inputs["forecats_root"])).resolve()
    selector = str(inputs.get("run_id_selector", "latest_mtime"))
    explicit_raw = inputs.get("explicit_run_id")
    explicit = str(explicit_raw).strip() if explicit_raw not in (None, "", "null") else None

    cutoff_map = bias_analysis.collect_cutoff_run_map(
        forecats_root=forecats_root,
        selector=selector,
        explicit_run_id=explicit,
    )

    center = bias_analysis.CenterSpec(
        key="NWS_NWM",
        label="NWS/NWM",
        retros_col=str(inputs.get("canonical_nws_col", "NWS3.0")),
        forecast_file=str(inputs.get("nws_forecast_file", "nws_weighted_daily.csv")),
    )

    forecast_means = bias_analysis.build_forecast_means(cutoff_map, [center], list(horizons))
    if forecast_means.empty:
        forecast_bias = forecast_means.copy()
        forecast_bias["usgs_cms"] = np.nan
        forecast_bias["bias_forecast_cms"] = np.nan
        return cutoff_map, forecast_bias

    usgs = canonical_daily[["date", "usgs_cms"]].rename(columns={"date": "target_date"})
    out = forecast_means.merge(usgs, how="left", on="target_date")
    out["bias_forecast_cms"] = out["usgs_cms"] - out["ensemble_mean_cms"]
    out = out.sort_values(["target_date", "lead_days"]).reset_index(drop=True)
    return cutoff_map, out


def build_bias_compare_by_version(
    forecast_bias: pd.DataFrame,
    canonical_daily: pd.DataFrame,
    windows: Sequence[VersionWindow],
    source_daily: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    usgs = canonical_daily[["date", "usgs_cms"]].rename(columns={"date": "target_date"})
    pieces: List[pd.DataFrame] = []

    for w in windows:
        src_daily = source_daily.get(w.source_key)
        if src_daily is None or src_daily.empty:
            continue
        retro = src_daily[["date", "retro_log1p"]].rename(columns={"date": "target_date", "retro_log1p": "retro_cms"})
        retro = retro.merge(usgs, how="left", on="target_date")
        retro["bias_retro_cms"] = retro["usgs_cms"] - retro["retro_cms"]

        f = forecast_bias.copy()
        f = f[(f["target_date"] >= w.start) & ((w.end is None) | (f["target_date"] <= w.end))]
        if f.empty:
            continue

        m = f.merge(retro[["target_date", "retro_cms", "bias_retro_cms"]], how="left", on="target_date")
        m["delta_bias_cms"] = m["bias_forecast_cms"] - m["bias_retro_cms"]
        m["nws_version"] = w.version
        m["source_key"] = w.source_key
        pieces.append(m)

    if not pieces:
        return pd.DataFrame(
            columns=[
                "issue_date",
                "target_date",
                "lead_days",
                "center_key",
                "center_label",
                "ensemble_mean_cms",
                "usgs_cms",
                "bias_forecast_cms",
                "retro_cms",
                "bias_retro_cms",
                "delta_bias_cms",
                "nws_version",
                "source_key",
            ]
        )

    out = pd.concat(pieces, ignore_index=True)
    out = out.sort_values(["target_date", "lead_days", "nws_version"]).reset_index(drop=True)
    return out


def compute_version_coverage(
    compare_df: pd.DataFrame,
    windows: Sequence[VersionWindow],
    source_audit_df: pd.DataFrame,
    focus_events: Sequence[EventDate],
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    events = [ev.parsed for ev in focus_events]

    for w in windows:
        sub = compare_df[compare_df["nws_version"] == w.version] if not compare_df.empty else pd.DataFrame()
        row: Dict[str, Any] = {
            "nws_version": w.version,
            "source_key": w.source_key,
            "window_start": w.start.isoformat(),
            "window_end": w.end.isoformat() if w.end else None,
            "n_compare_rows": int(len(sub)),
            "n_target_days": int(sub["target_date"].nunique()) if len(sub) else 0,
            "target_min": sub["target_date"].min().isoformat() if len(sub) else None,
            "target_max": sub["target_date"].max().isoformat() if len(sub) else None,
            "n_focus_dates_in_window": 0,
            "focus_dates_in_window": "",
            "n_focus_dates_with_rows": 0,
            "focus_dates_with_rows": "",
        }

        in_window: List[str] = []
        with_rows: List[str] = []
        for ev in events:
            if ev >= w.start and (w.end is None or ev <= w.end):
                in_window.append(ev.isoformat())
                if len(sub) and (sub["target_date"] == ev).any():
                    with_rows.append(ev.isoformat())
        row["n_focus_dates_in_window"] = len(in_window)
        row["focus_dates_in_window"] = ",".join(in_window)
        row["n_focus_dates_with_rows"] = len(with_rows)
        row["focus_dates_with_rows"] = ",".join(with_rows)

        s = source_audit_df[source_audit_df["source_key"] == w.source_key]
        if not s.empty:
            row["source_path"] = str(s.iloc[0].get("path"))
            row["source_date_min"] = s.iloc[0].get("daily_date_min")
            row["source_date_max"] = s.iloc[0].get("daily_date_max")
            row["source_days_missing"] = int(s.iloc[0].get("n_days_missing", 0) or 0)
        else:
            row["source_path"] = None
            row["source_date_min"] = None
            row["source_date_max"] = None
            row["source_days_missing"] = None

        rows.append(row)

    return pd.DataFrame(rows)


def event_subset(
    df: pd.DataFrame,
    event_date: date,
    horizon: int,
    version: str,
    window_before: int,
    window_after: int,
) -> pd.DataFrame:
    lo = event_date - timedelta(days=window_before)
    hi = event_date + timedelta(days=window_after)
    sub = df[
        (df["target_date"] >= lo)
        & (df["target_date"] <= hi)
        & (df["lead_days"] == horizon)
        & (df["nws_version"] == version)
    ].copy()
    return sub.sort_values("target_date").reset_index(drop=True)


def event_stats(sub: pd.DataFrame, event_date: date, local_days: int) -> Dict[str, Any]:
    metrics = ["bias_retro_cms", "bias_forecast_cms", "delta_bias_cms"]
    out: Dict[str, Any] = {"n_rows_window": int(len(sub))}

    if sub.empty:
        out["event_row_available"] = False
        for m in metrics:
            out[f"event_{m}"] = np.nan
            out[f"pre_mean_{m}"] = np.nan
            out[f"post_mean_{m}"] = np.nan
            out[f"post_minus_pre_{m}"] = np.nan
            out[f"max_abs_{m}"] = np.nan
        return out

    sub = sub.copy()
    sub["target_date_date"] = pd.to_datetime(sub["target_date"]).dt.date
    ev = sub[sub["target_date_date"] == event_date]
    pre_lo = event_date - timedelta(days=local_days)
    pre_hi = event_date - timedelta(days=1)
    post_lo = event_date + timedelta(days=1)
    post_hi = event_date + timedelta(days=local_days)

    pre = sub[(sub["target_date_date"] >= pre_lo) & (sub["target_date_date"] <= pre_hi)]
    post = sub[(sub["target_date_date"] >= post_lo) & (sub["target_date_date"] <= post_hi)]

    out["event_row_available"] = bool(len(ev) > 0)
    for m in metrics:
        out[f"event_{m}"] = float(ev[m].iloc[0]) if len(ev) > 0 and pd.notna(ev[m].iloc[0]) else np.nan
        out[f"pre_mean_{m}"] = float(pd.to_numeric(pre[m], errors="coerce").mean()) if len(pre) else np.nan
        out[f"post_mean_{m}"] = float(pd.to_numeric(post[m], errors="coerce").mean()) if len(post) else np.nan
        if pd.notna(out[f"pre_mean_{m}"]) and pd.notna(out[f"post_mean_{m}"]):
            out[f"post_minus_pre_{m}"] = float(out[f"post_mean_{m}"] - out[f"pre_mean_{m}"])
        else:
            out[f"post_minus_pre_{m}"] = np.nan
        out[f"max_abs_{m}"] = float(pd.to_numeric(sub[m], errors="coerce").abs().max()) if len(sub) else np.nan

    return out


def plot_retro_sources_overlay(
    source_daily: Dict[str, pd.DataFrame],
    canonical_daily: pd.DataFrame,
    windows: Sequence[VersionWindow],
    out_path: Path,
    start: Optional[date],
    end: Optional[date],
    palette: Dict[str, str],
    width: float,
    height: float,
    dpi: int,
    line_width: float,
) -> None:
    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)

    for key, daily in source_daily.items():
        if daily.empty:
            continue
        d = daily.copy()
        d["date"] = pd.to_datetime(d["date"])
        if start is not None:
            d = d[d["date"] >= pd.Timestamp(start)]
        if end is not None:
            d = d[d["date"] <= pd.Timestamp(end)]
        if d.empty:
            continue
        ax.plot(
            d["date"],
            d["retro_log1p"],
            linewidth=line_width,
            alpha=0.9,
            color=palette.get(key, "#333333"),
            label=key,
        )

    c = canonical_daily.copy()
    c["date"] = pd.to_datetime(c["date"])
    if start is not None:
        c = c[c["date"] >= pd.Timestamp(start)]
    if end is not None:
        c = c[c["date"] <= pd.Timestamp(end)]
    if not c.empty:
        ax.plot(
            c["date"],
            c["nws_canonical_cms"],
            linewidth=line_width,
            alpha=0.9,
            color=palette.get("canonical_daily", "#2ca02c"),
            linestyle="--",
            label="canonical_daily",
        )

    for w in windows:
        x = pd.Timestamp(w.start)
        if start is not None and x < pd.Timestamp(start):
            continue
        if end is not None and x > pd.Timestamp(end):
            continue
        ax.axvline(x, color="#666666", linestyle=":", linewidth=0.8, alpha=0.9)
        ax.text(x, ax.get_ylim()[1], w.version, rotation=90, va="top", ha="right", fontsize=8, color="#444444")

    ax.set_title("NWS retrospective sources (daily log1p) with version boundaries")
    ax.set_xlabel("Date")
    ax.set_ylabel("log1p(discharge cms)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", fontsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_version_timeline(
    coverage_df: pd.DataFrame,
    out_path: Path,
    palette: Dict[str, str],
    width: float,
    height: float,
    dpi: int,
) -> None:
    fig, ax = plt.subplots(figsize=(width, max(height * 0.55, 4.0)), dpi=dpi)

    if coverage_df.empty:
        ax.text(0.5, 0.5, "No version coverage rows", transform=ax.transAxes, ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(out_path)
        plt.close(fig)
        return

    rows = coverage_df.reset_index(drop=True)
    y_positions = np.arange(len(rows))

    for i, row in rows.iterrows():
        w_start = pd.to_datetime(row["window_start"], errors="coerce")
        w_end = pd.to_datetime(row["window_end"], errors="coerce")
        if pd.isna(w_end):
            w_end = pd.Timestamp.today().normalize()
        color = palette.get(str(row["nws_version"]), "#777777")

        ax.plot([w_start, w_end], [i, i], color=color, linewidth=6, alpha=0.35, solid_capstyle="butt")

        t_min = pd.to_datetime(row.get("target_min"), errors="coerce")
        t_max = pd.to_datetime(row.get("target_max"), errors="coerce")
        if pd.notna(t_min) and pd.notna(t_max):
            ax.plot([t_min, t_max], [i, i], color=color, linewidth=3.5, solid_capstyle="butt")

    ax.set_yticks(y_positions)
    ax.set_yticklabels([f"{r['nws_version']} ({r['source_key']})" for _, r in rows.iterrows()])
    ax.set_xlabel("Date")
    ax.set_title("Configured version windows vs available target-date coverage")
    ax.grid(True, axis="x", alpha=0.25)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate(rotation=30)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_event_panels_version(
    sub: pd.DataFrame,
    event_date: date,
    version: str,
    horizon: int,
    out_path: Path,
    width: float,
    height: float,
    dpi: int,
    line_width: float,
    marker_size: float,
    y_limits: Optional[Tuple[float, float]],
    version_color: str,
) -> None:
    metrics = [
        ("bias_retro_cms", "Bias retro"),
        ("bias_forecast_cms", "Bias forecast"),
        ("delta_bias_cms", "Bias delta (forecast-retro)"),
    ]
    styles = {
        "bias_retro_cms": ("-", "o"),
        "bias_forecast_cms": ("--", "s"),
        "delta_bias_cms": (":", "^"),
    }

    fig, axes = plt.subplots(3, 1, figsize=(width, height), dpi=dpi, sharex=True)

    if sub.empty:
        axes[0].text(0.5, 0.5, "No rows in this event/version window", transform=axes[0].transAxes, ha="center", va="center")
        for ax in axes:
            ax.axis("off")
        fig.suptitle(f"{version} | Event {event_date.isoformat()} | h={horizon}d")
        fig.tight_layout()
        fig.savefig(out_path)
        plt.close(fig)
        return

    sub = sub.sort_values("target_date")
    for ax, (metric, title) in zip(axes, metrics):
        ls, mk = styles[metric]
        ax.plot(
            pd.to_datetime(sub["target_date"]),
            pd.to_numeric(sub[metric], errors="coerce"),
            color=version_color,
            linestyle=ls,
            marker=mk,
            markersize=marker_size,
            linewidth=line_width,
            alpha=0.95,
            label=version,
        )
        ax.axhline(0.0, color="black", linewidth=0.8, alpha=0.8)
        ax.axvline(pd.Timestamp(event_date), color="#666666", linewidth=1.0, linestyle="--", alpha=0.9)
        if y_limits is not None:
            ax.set_ylim(y_limits)
        ax.set_title(title)
        ax.set_ylabel("Bias (cms)")
        ax.grid(True, alpha=0.25)
        ax.legend(loc="upper left", fontsize=8)

    axes[-1].set_xlabel("Target date")
    fig.suptitle(f"{version} | Event {event_date.isoformat()} | Horizon {horizon}d", y=0.995)
    fig.autofmt_xdate(rotation=25)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def fmt(x: Any) -> str:
    try:
        xv = float(x)
    except Exception:
        return "NA"
    if not np.isfinite(xv):
        return "NA"
    return f"{xv:.3f}"


def build_event_report_md(
    run_dir: Path,
    summary_df: pd.DataFrame,
    focus_events: Sequence[EventDate],
    horizons: Sequence[int],
    windows: Sequence[VersionWindow],
) -> Path:
    lines: List[str] = []
    lines.append("# NWS Versioned Bias Event Report")
    lines.append("")
    lines.append(f"Generated at UTC: {utc_now()}")
    lines.append("")
    lines.append("## Focus Dates")
    lines.append("")
    for ev in focus_events:
        note = f" (sanitized from `{ev.raw}`)" if ev.sanitized else ""
        lines.append(f"- `{ev.parsed.isoformat()}`{note}")
    lines.append("")
    lines.append("## Version Windows")
    lines.append("")
    for w in windows:
        end_txt = w.end.isoformat() if w.end else "open"
        lines.append(f"- `{w.version}`: `{w.start.isoformat()}` to `{end_txt}` (source `{w.source_key}`)")
    lines.append("")

    for ev in focus_events:
        lines.append(f"## Event {ev.parsed.isoformat()}")
        lines.append("")
        for h in horizons:
            lines.append(f"### Horizon h={h}d")
            lines.append("")
            hdf = summary_df[(summary_df["event_date"] == ev.parsed.isoformat()) & (summary_df["lead_days"] == h)].copy()
            if hdf.empty:
                lines.append("No rows for this horizon.")
                lines.append("")
                continue

            lines.append("| Version | In Window | Event Row | Event Retro | Event Forecast | Event Delta | Post-Pre Delta | Max |Delta| |")
            lines.append("|---|---|---|---:|---:|---:|---:|---:|")
            for _, r in hdf.sort_values("nws_version").iterrows():
                lines.append(
                    "| "
                    + f"{r['nws_version']} | {bool(r['event_in_version_window'])} | {bool(r['event_row_available'])} | "
                    + f"{fmt(r['event_bias_retro_cms'])} | {fmt(r['event_bias_forecast_cms'])} | "
                    + f"{fmt(r['event_delta_bias_cms'])} | {fmt(r['post_minus_pre_delta_bias_cms'])} | "
                    + f"{fmt(r['max_abs_delta_bias_cms'])} |"
                )
            lines.append("")

    out = run_dir / "event_report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def run_pipeline(cfg: Dict[str, Any]) -> Path:
    run_cfg = cfg["run"]
    inputs_cfg = cfg["inputs"]
    analysis_cfg = cfg["analysis"]
    plots_cfg = cfg["plots"]

    run_id = str(run_cfg.get("run_id") or f"nws_versions_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    out_root = Path(str(run_cfg.get("out_root", "repro/bias_version_runs"))).resolve()
    run_dir = out_root / run_id

    if run_dir.exists():
        if bool(run_cfg.get("overwrite", False)):
            shutil.rmtree(run_dir)
        else:
            raise FileExistsError(f"Run directory already exists: {run_dir}")

    tables_dir = run_dir / "tables"
    plots_dir = run_dir / "plots"
    logs_dir = run_dir / "logs"
    ensure_dir(tables_dir)
    ensure_dir(plots_dir)
    ensure_dir(logs_dir)

    logger = logging.getLogger("nws_version_bias_event_analysis")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    log_fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = logging.FileHandler(logs_dir / "nws_version_bias_event_analysis.log")
    fh.setFormatter(log_fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(log_fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)

    logger.info("Starting NWS versioned bias analysis run_id=%s", run_id)

    source_specs = select_source_specs(cfg)
    windows = parse_version_windows(
        analysis_cfg["version_windows"],
        allow_overlap=bool(analysis_cfg.get("allow_overlapping_versions", False)),
    )
    horizons = [int(x) for x in analysis_cfg["horizons_days"]]
    focus_events = [parse_event_date(x) for x in analysis_cfg["focus_dates"]]

    canonical_daily = load_daily_canonical(cfg)
    canonical_daily.to_csv(tables_dir / "canonical_daily_nws_usgs.csv", index=False)

    source_daily: Dict[str, pd.DataFrame] = {}
    source_audit_rows: List[Dict[str, Any]] = []
    for spec in source_specs:
        daily, audit = load_hourly_source_daily_log1p(spec)
        source_daily[spec.key] = daily
        source_audit_rows.append(audit)
        if not daily.empty:
            daily.to_csv(tables_dir / f"source_daily_{spec.key}.csv", index=False)

    source_audit_df = pd.DataFrame(source_audit_rows).sort_values("source_key")
    source_audit_df.to_csv(tables_dir / "source_audit.csv", index=False)

    cutoff_map, forecast_bias = build_forecast_bias_nws(cfg, horizons, canonical_daily)
    cutoff_map.to_csv(tables_dir / "cutoff_run_map.csv", index=False)
    forecast_bias.to_csv(tables_dir / "bias_forecast_nws.csv", index=False)

    compare_df = build_bias_compare_by_version(
        forecast_bias=forecast_bias,
        canonical_daily=canonical_daily,
        windows=windows,
        source_daily=source_daily,
    )
    compare_df.to_csv(tables_dir / "bias_compare_nws_by_version.csv", index=False)

    coverage_df = compute_version_coverage(compare_df, windows, source_audit_df, focus_events)
    coverage_df.to_csv(tables_dir / "version_coverage.csv", index=False)

    width = float(plots_cfg.get("width", 14))
    height = float(plots_cfg.get("height", 9))
    dpi = int(plots_cfg.get("dpi", 180))
    line_width = float(plots_cfg.get("line_width", 0.85))
    marker_size = float(plots_cfg.get("marker_size", 2.4))
    y_limits = parse_limit(plots_cfg.get("y_limits_cms"), "plots.y_limits_cms")

    source_palette = {str(k): str(v) for k, v in dict(plots_cfg.get("source_palette", {})).items()}
    version_palette = {str(k): str(v) for k, v in dict(plots_cfg.get("version_palette", {})).items()}

    overlay_start_raw = plots_cfg.get("retro_overlay_start")
    overlay_end_raw = plots_cfg.get("retro_overlay_end")
    overlay_start = date.fromisoformat(str(overlay_start_raw)) if overlay_start_raw else None
    overlay_end = date.fromisoformat(str(overlay_end_raw)) if overlay_end_raw else None

    plot_retro_sources_overlay(
        source_daily=source_daily,
        canonical_daily=canonical_daily,
        windows=windows,
        out_path=plots_dir / "retros_sources_overlay.png",
        start=overlay_start,
        end=overlay_end,
        palette=source_palette,
        width=width,
        height=height,
        dpi=dpi,
        line_width=line_width,
    )

    plot_version_timeline(
        coverage_df=coverage_df,
        out_path=plots_dir / "version_timeline.png",
        palette=version_palette,
        width=width,
        height=height,
        dpi=dpi,
    )

    summary_rows: List[Dict[str, Any]] = []
    window_before = int(analysis_cfg["window_days_before"])
    window_after = int(analysis_cfg["window_days_after"])
    local_days = int(analysis_cfg["local_stat_days"])

    for ev in focus_events:
        event_dir = plots_dir / f"event_{ev.parsed.isoformat()}"
        ensure_dir(event_dir)

        for h in horizons:
            for w in windows:
                in_window = bool(ev.parsed >= w.start and (w.end is None or ev.parsed <= w.end))
                sub = event_subset(
                    df=compare_df,
                    event_date=ev.parsed,
                    horizon=h,
                    version=w.version,
                    window_before=window_before,
                    window_after=window_after,
                )

                plot_event_panels_version(
                    sub=sub,
                    event_date=ev.parsed,
                    version=w.version,
                    horizon=h,
                    out_path=event_dir / f"panels_{w.version.lower().replace('.', '_')}_h{h:02d}.png",
                    width=width,
                    height=height,
                    dpi=dpi,
                    line_width=line_width,
                    marker_size=marker_size,
                    y_limits=y_limits,
                    version_color=version_palette.get(w.version, "#333333"),
                )

                row = event_stats(sub, ev.parsed, local_days)
                row.update(
                    {
                        "event_date": ev.parsed.isoformat(),
                        "event_raw": ev.raw,
                        "event_sanitized": ev.sanitized,
                        "event_parse_note": ev.note,
                        "lead_days": h,
                        "nws_version": w.version,
                        "source_key": w.source_key,
                        "event_in_version_window": in_window,
                    }
                )
                summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    summary_df = summary_df.sort_values(["event_date", "lead_days", "nws_version"]).reset_index(drop=True)
    summary_df.to_csv(tables_dir / "event_version_summary.csv", index=False)
    pd.DataFrame(
        [{"event_raw": ev.raw, "event_date": ev.parsed.isoformat(), "sanitized": ev.sanitized, "note": ev.note} for ev in focus_events]
    ).to_csv(tables_dir / "focus_date_notes.csv", index=False)

    event_report = build_event_report_md(
        run_dir=run_dir,
        summary_df=summary_df,
        focus_events=focus_events,
        horizons=horizons,
        windows=windows,
    )

    summary_payload = {
        "generated_at_utc": utc_now(),
        "run_id": run_id,
        "inputs": {
            "forecats_root": str(inputs_cfg.get("forecats_root")),
            "retros_daily_path": str(inputs_cfg.get("retros_daily_path")),
            "nws_hourly_sources": [dict(x) for x in inputs_cfg.get("nws_hourly_sources", [])],
        },
        "analysis": {
            "focus_dates": [ev.raw for ev in focus_events],
            "parsed_focus_dates": [ev.parsed.isoformat() for ev in focus_events],
            "horizons_days": horizons,
            "version_windows": [
                {
                    "version": w.version,
                    "start": w.start.isoformat(),
                    "end": w.end.isoformat() if w.end else None,
                    "source_key": w.source_key,
                }
                for w in windows
            ],
        },
        "counts": {
            "cutoff_runs_selected": int(len(cutoff_map)),
            "forecast_bias_rows": int(len(forecast_bias)),
            "compare_rows": int(len(compare_df)),
            "coverage_rows": int(len(coverage_df)),
            "event_summary_rows": int(len(summary_df)),
        },
        "paths": {
            "source_audit": str(tables_dir / "source_audit.csv"),
            "version_coverage": str(tables_dir / "version_coverage.csv"),
            "compare_table": str(tables_dir / "bias_compare_nws_by_version.csv"),
            "event_summary": str(tables_dir / "event_version_summary.csv"),
            "retro_overlay_plot": str(plots_dir / "retros_sources_overlay.png"),
            "version_timeline_plot": str(plots_dir / "version_timeline.png"),
            "event_report": str(event_report),
        },
    }

    (run_dir / "summary.json").write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    (run_dir / "resolved_config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    logger.info("Completed run_id=%s", run_id)
    logger.info("Outputs written to %s", run_dir)
    return run_dir


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    cfg_path = Path(args.config).resolve()
    cfg = load_config(cfg_path)
    out = run_pipeline(cfg)
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Event-focused bias analysis from precomputed bias_compare tables.

This tool is read-only on existing bias outputs and creates a new run directory
with event-window plots and summaries.
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
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import yaml
except Exception as exc:
    print(f"ERROR: Missing required dependency for bias_event_analysis.py: {exc}", file=sys.stderr)
    sys.exit(2)


DEFAULT_CONFIG: Dict[str, Any] = {
    "run": {
        "run_id": None,
        "out_root": "repro/bias_event_runs",
        "overwrite": False,
    },
    "inputs": {
        "bias_compare_path": "repro/bias_runs/bias_20260212_171950/tables/bias_compare.csv",
    },
    "analysis": {
        "focus_dates": [
            "2021-01-23",
            "2021-01-27",
            "c2021-11-12",
            "2021-12-10",
            "2021-12-17",
            "2021-12-21",
            "2022-05-10",
            "2022-12-25",
        ],
        "horizons_days": [1, 7],
        "window_days_before": 14,
        "window_days_after": 14,
        "local_stat_days": 3,
        "centers": ["NWS_NWM", "GLOFAS"],
    },
    "plots": {
        "dpi": 180,
        "width": 14,
        "height": 10,
        "line_width": 1.0,
        "marker_size": 3.0,
        "y_limits_cms": [-30.0, 30.0],
        "center_palette": {
            "NWS_NWM": "#1f77b4",
            "GLOFAS": "#ff7f0e",
        },
        "metric_style": {
            "bias_retro_cms": {"label": "Bias retro", "linestyle": "-", "marker": "o", "color": "#1b9e77"},
            "bias_forecast_cms": {"label": "Bias forecast", "linestyle": "--", "marker": "s", "color": "#7570b3"},
            "delta_bias_cms": {
                "label": "Bias delta (forecast-retro)",
                "linestyle": ":",
                "marker": "^",
                "color": "#d95f02",
            },
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
class GroupSpec:
    key: str
    label: str
    centers: Tuple[str, ...]


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Event-focused bias analysis")
    parser.add_argument("--config", default="config/bias_event_analysis.template.yaml")
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


def parse_numeric_limits(raw: Any, field_name: str) -> Optional[Tuple[float, float]]:
    if raw is None:
        return None
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise ValueError(f"{field_name} must be null or [min, max]")
    lo = float(raw[0])
    hi = float(raw[1])
    if not np.isfinite(lo) or not np.isfinite(hi) or lo >= hi:
        raise ValueError(f"{field_name} must be finite with min < max")
    return (lo, hi)


def parse_event_date(raw: Any) -> EventDate:
    text = str(raw).strip()
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if not m:
        raise ValueError(f"Invalid focus date '{text}'. Expected YYYY-MM-DD or token containing that pattern")
    parsed = date.fromisoformat(m.group(1))
    sanitized = m.group(1) != text
    note = "sanitized" if sanitized else "as_provided"
    return EventDate(raw=text, parsed=parsed, sanitized=sanitized, note=note)


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
    if not isinstance(cfg.get("run"), dict):
        raise ValueError("run must be a mapping")
    if not isinstance(cfg.get("inputs"), dict):
        raise ValueError("inputs must be a mapping")
    if not isinstance(cfg.get("analysis"), dict):
        raise ValueError("analysis must be a mapping")
    if not isinstance(cfg.get("plots"), dict):
        raise ValueError("plots must be a mapping")

    analysis = cfg["analysis"]
    focus_dates = analysis.get("focus_dates")
    if not isinstance(focus_dates, list) or not focus_dates:
        raise ValueError("analysis.focus_dates must be a non-empty list")
    _ = [parse_event_date(x) for x in focus_dates]

    horizons = analysis.get("horizons_days")
    if not isinstance(horizons, list) or not horizons:
        raise ValueError("analysis.horizons_days must be a non-empty list")
    hvals = sorted(set(int(x) for x in horizons))
    if any(h <= 0 for h in hvals):
        raise ValueError("analysis.horizons_days must be positive")
    analysis["horizons_days"] = hvals

    for k in ("window_days_before", "window_days_after", "local_stat_days"):
        v = int(analysis.get(k))
        if v < 0:
            raise ValueError(f"analysis.{k} must be >= 0")
        analysis[k] = v

    centers = analysis.get("centers")
    if not isinstance(centers, list) or not centers:
        raise ValueError("analysis.centers must be a non-empty list")

    parse_numeric_limits(cfg["plots"].get("y_limits_cms"), "plots.y_limits_cms")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_groups(centers: Sequence[str]) -> List[GroupSpec]:
    uniq = [c for c in centers]
    out: List[GroupSpec] = [GroupSpec(key="all", label="All centers", centers=tuple(uniq))]
    for c in uniq:
        label = "NWS/NWM only" if c == "NWS_NWM" else "GloFAS only" if c == "GLOFAS" else f"{c} only"
        out.append(GroupSpec(key=c.lower(), label=label, centers=(c,)))
    return out


def slugify_date(d: date) -> str:
    return d.isoformat()


def metric_label(metric: str, metric_style: Dict[str, Any]) -> str:
    spec = metric_style.get(metric, {})
    return str(spec.get("label", metric))


def event_subset(
    df: pd.DataFrame,
    event_date: date,
    horizon: int,
    centers: Sequence[str],
    window_before: int,
    window_after: int,
) -> pd.DataFrame:
    lo = event_date - timedelta(days=window_before)
    hi = event_date + timedelta(days=window_after)
    sub = df[
        (df["target_date"] >= pd.Timestamp(lo))
        & (df["target_date"] <= pd.Timestamp(hi))
        & (df["lead_days"] == horizon)
        & (df["center_key"].isin(list(centers)))
    ].copy()
    return sub.sort_values(["target_date", "center_key"]).reset_index(drop=True)


def event_stats_for_center(
    sub: pd.DataFrame,
    event_date: date,
    center: str,
    local_days: int,
) -> Dict[str, Any]:
    cdf = sub[sub["center_key"] == center].copy()
    metrics = ["bias_retro_cms", "bias_forecast_cms", "delta_bias_cms"]

    out: Dict[str, Any] = {
        "center_key": center,
        "n_rows_window": int(len(cdf)),
    }

    if cdf.empty:
        for m in metrics:
            out[f"event_{m}"] = np.nan
            out[f"pre_mean_{m}"] = np.nan
            out[f"post_mean_{m}"] = np.nan
            out[f"post_minus_pre_{m}"] = np.nan
            out[f"max_abs_{m}"] = np.nan
        out["event_row_available"] = False
        return out

    cdf["target_date_date"] = cdf["target_date"].dt.date
    ev = cdf[cdf["target_date_date"] == event_date]
    pre_lo = event_date - timedelta(days=local_days)
    pre_hi = event_date - timedelta(days=1)
    post_lo = event_date + timedelta(days=1)
    post_hi = event_date + timedelta(days=local_days)

    pre = cdf[(cdf["target_date_date"] >= pre_lo) & (cdf["target_date_date"] <= pre_hi)]
    post = cdf[(cdf["target_date_date"] >= post_lo) & (cdf["target_date_date"] <= post_hi)]

    out["event_row_available"] = bool(len(ev) > 0)
    for m in metrics:
        out[f"event_{m}"] = float(ev[m].iloc[0]) if len(ev) > 0 and pd.notna(ev[m].iloc[0]) else np.nan
        out[f"pre_mean_{m}"] = float(pd.to_numeric(pre[m], errors="coerce").mean()) if len(pre) > 0 else np.nan
        out[f"post_mean_{m}"] = float(pd.to_numeric(post[m], errors="coerce").mean()) if len(post) > 0 else np.nan
        if pd.notna(out[f"pre_mean_{m}"]) and pd.notna(out[f"post_mean_{m}"]):
            out[f"post_minus_pre_{m}"] = float(out[f"post_mean_{m}"] - out[f"pre_mean_{m}"])
        else:
            out[f"post_minus_pre_{m}"] = np.nan
        out[f"max_abs_{m}"] = float(pd.to_numeric(cdf[m], errors="coerce").abs().max()) if len(cdf) > 0 else np.nan

    return out


def plot_event_panels(
    sub: pd.DataFrame,
    event_date: date,
    horizon: int,
    group: GroupSpec,
    out_path: Path,
    width: float,
    height: float,
    dpi: int,
    line_width: float,
    marker_size: float,
    y_limits: Optional[Tuple[float, float]],
    center_palette: Dict[str, str],
    metric_style: Dict[str, Any],
) -> None:
    metrics = ["bias_retro_cms", "bias_forecast_cms", "delta_bias_cms"]
    fig, axes = plt.subplots(3, 1, figsize=(width, height), dpi=dpi, sharex=True)

    if sub.empty:
        axes[0].text(0.5, 0.5, "No rows in window", transform=axes[0].transAxes, ha="center", va="center")
        for ax in axes:
            ax.axis("off")
        fig.suptitle(f"{group.label} | event {event_date.isoformat()} | h={horizon}")
        fig.tight_layout()
        fig.savefig(out_path)
        plt.close(fig)
        return

    sub = sub.sort_values("target_date")
    for ax, metric in zip(axes, metrics):
        for center in group.centers:
            cdf = sub[sub["center_key"] == center]
            if cdf.empty:
                continue
            color = center_palette.get(center, "#333333")
            label = "NWS/NWM" if center == "NWS_NWM" else "GloFAS" if center == "GLOFAS" else center
            style = metric_style.get(metric, {})
            ax.plot(
                cdf["target_date"],
                cdf[metric],
                color=color,
                linestyle=str(style.get("linestyle", "-")),
                marker=str(style.get("marker", "o")),
                markersize=marker_size,
                linewidth=line_width,
                alpha=0.92,
                label=label,
            )

        ax.axhline(0.0, color="black", linewidth=0.8, alpha=0.8)
        ax.axvline(pd.Timestamp(event_date), color="#666666", linewidth=1.0, linestyle="--", alpha=0.9)
        if y_limits is not None:
            ax.set_ylim(y_limits)
        ax.set_ylabel("Bias (cms)")
        ax.set_title(metric_label(metric, metric_style))
        ax.grid(True, alpha=0.25)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(loc="upper left", fontsize=8)

    axes[-1].set_xlabel("Target date")
    fig.suptitle(f"{group.label} | Event {event_date.isoformat()} | Horizon {horizon}d", y=0.995)
    fig.autofmt_xdate(rotation=25)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_event_scatter(
    sub: pd.DataFrame,
    event_date: date,
    horizon: int,
    group: GroupSpec,
    out_path: Path,
    width: float,
    height: float,
    dpi: int,
    y_limits: Optional[Tuple[float, float]],
    center_palette: Dict[str, str],
) -> None:
    fig, ax = plt.subplots(figsize=(width, height * 0.68), dpi=dpi)

    if sub.empty:
        ax.text(0.5, 0.5, "No rows in window", transform=ax.transAxes, ha="center", va="center")
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(out_path)
        plt.close(fig)
        return

    markers = ["o", "s", "^", "D"]
    for i, center in enumerate(group.centers):
        cdf = sub[sub["center_key"] == center].copy()
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
        r = float(np.corrcoef(x, y)[0, 1]) if len(x) > 1 else np.nan
        rtxt = f"{r:.2f}" if np.isfinite(r) else "NA"
        label = ("NWS/NWM" if center == "NWS_NWM" else "GloFAS" if center == "GLOFAS" else center) + f" (n={len(x)}, r={rtxt})"
        ax.scatter(
            x,
            y,
            s=20,
            alpha=0.68,
            marker=markers[i % len(markers)],
            color=center_palette.get(center, "#333333"),
            edgecolor="none",
            label=label,
        )

    if y_limits is not None:
        lo, hi = y_limits
        ax.set_xlim((lo, hi))
        ax.set_ylim((lo, hi))
        diag_lo, diag_hi = lo, hi
    else:
        vals = pd.concat([sub["bias_retro_cms"], sub["bias_forecast_cms"]], ignore_index=True)
        vals = pd.to_numeric(vals, errors="coerce").dropna()
        diag_lo, diag_hi = (float(vals.min()), float(vals.max())) if not vals.empty else (-1.0, 1.0)

    if np.isfinite(diag_lo) and np.isfinite(diag_hi) and diag_lo < diag_hi:
        ax.plot([diag_lo, diag_hi], [diag_lo, diag_hi], color="black", linestyle="--", linewidth=0.8)

    ax.axhline(0.0, color="#595959", linewidth=0.8, alpha=0.7)
    ax.axvline(0.0, color="#595959", linewidth=0.8, alpha=0.7)
    ax.set_xlabel("Bias retro (cms)")
    ax.set_ylabel("Bias forecast (cms)")
    ax.set_title(f"{group.label} | Event {event_date.isoformat()} | h={horizon}d")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def generate_report_md(
    run_dir: Path,
    summary_df: pd.DataFrame,
    focus_events: Sequence[EventDate],
    horizons: Sequence[int],
    centers: Sequence[str],
) -> Path:
    lines: List[str] = []
    lines.append("# Bias Event Analysis Report")
    lines.append("")
    lines.append(f"Generated at UTC: {utc_now()}")
    lines.append("")
    lines.append("## Focus Dates")
    lines.append("")
    for ev in focus_events:
        note = f" (sanitized from `{ev.raw}`)" if ev.sanitized else ""
        lines.append(f"- `{ev.parsed.isoformat()}`{note}")
    lines.append("")

    for ev in focus_events:
        lines.append(f"## Event {ev.parsed.isoformat()}")
        lines.append("")
        sub_ev = summary_df[summary_df["event_date"] == ev.parsed.isoformat()].copy()
        if sub_ev.empty:
            lines.append("No rows found for this event.")
            lines.append("")
            continue

        for h in horizons:
            lines.append(f"### Horizon h={h}d")
            lines.append("")
            hdf = sub_ev[sub_ev["lead_days"] == h].copy()
            if hdf.empty:
                lines.append("No rows for this horizon.")
                lines.append("")
                continue

            lines.append("| Center | Event Retro | Event Forecast | Event Delta | Shift Delta (post-pre) | Max |Delta| in window |")
            lines.append("|---|---:|---:|---:|---:|---:|")
            for center in centers:
                cdf = hdf[hdf["center_key"] == center]
                if cdf.empty:
                    continue
                r = cdf.iloc[0]
                cname = "NWS/NWM" if center == "NWS_NWM" else "GloFAS" if center == "GLOFAS" else center
                lines.append(
                    "| "
                    + f"{cname} | {fmt(r['event_bias_retro_cms'])} | {fmt(r['event_bias_forecast_cms'])} | "
                    + f"{fmt(r['event_delta_bias_cms'])} | {fmt(r['post_minus_pre_delta_bias_cms'])} | {fmt(r['max_abs_delta_bias_cms'])} |"
                )
            lines.append("")

    out = run_dir / "event_report.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def fmt(x: Any) -> str:
    try:
        xv = float(x)
    except Exception:
        return "NA"
    if not np.isfinite(xv):
        return "NA"
    return f"{xv:.3f}"


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    header = "| " + " | ".join(cols) + " |"
    sep = "|" + "|".join(["---" for _ in cols]) + "|"
    lines = [header, sep]
    for _, row in df.iterrows():
        vals = []
        for c in cols:
            v = row[c]
            if isinstance(v, (float, np.floating)):
                vals.append(fmt(v))
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines) + "\n"


def run_pipeline(cfg: Dict[str, Any]) -> Path:
    run_cfg = cfg["run"]
    analysis_cfg = cfg["analysis"]
    plots_cfg = cfg["plots"]

    run_id = str(run_cfg.get("run_id") or f"bias_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    out_root = Path(str(run_cfg.get("out_root", "repro/bias_event_runs"))).resolve()
    run_dir = out_root / run_id

    if run_dir.exists():
        if bool(run_cfg.get("overwrite", False)):
            shutil.rmtree(run_dir)
        else:
            raise FileExistsError(f"Run directory already exists: {run_dir}")

    plots_dir = run_dir / "plots"
    tables_dir = run_dir / "tables"
    logs_dir = run_dir / "logs"
    ensure_dir(plots_dir)
    ensure_dir(tables_dir)
    ensure_dir(logs_dir)

    logger = logging.getLogger("bias_event_analysis")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    fmt_log = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = logging.FileHandler(logs_dir / "bias_event_analysis.log")
    fh.setFormatter(fmt_log)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt_log)
    logger.addHandler(fh)
    logger.addHandler(sh)

    bias_path = Path(str(cfg["inputs"]["bias_compare_path"]))
    if not bias_path.exists():
        raise FileNotFoundError(f"bias_compare path not found: {bias_path}")

    df = pd.read_csv(bias_path, parse_dates=["target_date"])
    required_cols = {
        "target_date",
        "lead_days",
        "center_key",
        "bias_retro_cms",
        "bias_forecast_cms",
        "delta_bias_cms",
    }
    missing = sorted(required_cols - set(df.columns))
    if missing:
        raise ValueError(f"bias_compare missing required columns: {missing}")

    centers = [str(c) for c in analysis_cfg["centers"]]
    df = df[df["center_key"].isin(centers)].copy()
    df["lead_days"] = pd.to_numeric(df["lead_days"], errors="coerce").astype("Int64")

    focus_events = [parse_event_date(x) for x in analysis_cfg["focus_dates"]]
    horizons = [int(x) for x in analysis_cfg["horizons_days"]]
    groups = build_groups(centers)

    window_before = int(analysis_cfg["window_days_before"])
    window_after = int(analysis_cfg["window_days_after"])
    local_days = int(analysis_cfg["local_stat_days"])

    width = float(plots_cfg.get("width", 14))
    height = float(plots_cfg.get("height", 10))
    dpi = int(plots_cfg.get("dpi", 180))
    line_width = float(plots_cfg.get("line_width", 1.0))
    marker_size = float(plots_cfg.get("marker_size", 3.0))
    y_limits = parse_numeric_limits(plots_cfg.get("y_limits_cms"), "plots.y_limits_cms")
    center_palette = {str(k): str(v) for k, v in dict(plots_cfg.get("center_palette", {})).items()}
    metric_style = dict(plots_cfg.get("metric_style", {}))

    summary_rows: List[Dict[str, Any]] = []

    for ev in focus_events:
        event_dir = plots_dir / f"event_{slugify_date(ev.parsed)}"
        ensure_dir(event_dir)

        for h in horizons:
            sub_all = event_subset(
                df=df,
                event_date=ev.parsed,
                horizon=h,
                centers=centers,
                window_before=window_before,
                window_after=window_after,
            )

            for group in groups:
                sub_group = sub_all[sub_all["center_key"].isin(list(group.centers))].copy()
                plot_event_panels(
                    sub=sub_group,
                    event_date=ev.parsed,
                    horizon=h,
                    group=group,
                    out_path=event_dir / f"panels_{group.key}_h{h:02d}.png",
                    width=width,
                    height=height,
                    dpi=dpi,
                    line_width=line_width,
                    marker_size=marker_size,
                    y_limits=y_limits,
                    center_palette=center_palette,
                    metric_style=metric_style,
                )
                plot_event_scatter(
                    sub=sub_group,
                    event_date=ev.parsed,
                    horizon=h,
                    group=group,
                    out_path=event_dir / f"scatter_{group.key}_h{h:02d}.png",
                    width=width,
                    height=height,
                    dpi=dpi,
                    y_limits=y_limits,
                    center_palette=center_palette,
                )

            for center in centers:
                row = event_stats_for_center(sub_all, ev.parsed, center, local_days)
                row.update(
                    {
                        "event_date": ev.parsed.isoformat(),
                        "event_raw": ev.raw,
                        "event_sanitized": ev.sanitized,
                        "event_parse_note": ev.note,
                        "lead_days": h,
                    }
                )
                summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows).sort_values(["event_date", "lead_days", "center_key"]).reset_index(drop=True)
    summary_df.to_json(tables_dir / "event_summary.json", orient="records", indent=2)
    (tables_dir / "event_summary.md").write_text(dataframe_to_markdown(summary_df), encoding="utf-8")

    notes = pd.DataFrame(
        [
            {
                "event_raw": ev.raw,
                "event_date": ev.parsed.isoformat(),
                "sanitized": ev.sanitized,
                "note": ev.note,
            }
            for ev in focus_events
        ]
    )
    notes.to_json(tables_dir / "event_date_notes.json", orient="records", indent=2)

    report_md = generate_report_md(
        run_dir=run_dir,
        summary_df=summary_df,
        focus_events=focus_events,
        horizons=horizons,
        centers=centers,
    )

    summary_payload = {
        "generated_at_utc": utc_now(),
        "run_id": run_id,
        "inputs": {"bias_compare_path": str(bias_path)},
        "analysis": {
            "focus_dates": [ev.raw for ev in focus_events],
            "parsed_focus_dates": [ev.parsed.isoformat() for ev in focus_events],
            "horizons_days": horizons,
            "window_days_before": window_before,
            "window_days_after": window_after,
            "local_stat_days": local_days,
            "centers": centers,
        },
        "counts": {
            "summary_rows": int(len(summary_df)),
            "events": int(len(focus_events)),
            "groups": int(len(groups)),
        },
        "paths": {
            "event_summary_json": str(tables_dir / "event_summary.json"),
            "event_summary_md": str(tables_dir / "event_summary.md"),
            "event_report_md": str(report_md),
        },
    }
    (run_dir / "summary.json").write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
    (run_dir / "resolved_config.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    logger.info("Completed bias event analysis run_id=%s", run_id)
    logger.info("Outputs: %s", run_dir)
    return run_dir


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    cfg_path = Path(args.config).resolve()
    cfg = load_config(cfg_path)
    run_dir = run_pipeline(cfg)
    print(str(run_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Render an input-context review for the representative exAL-M-T1 cutoff window.

This figure is designed to answer a very specific audit question:
is the USGS series shown in the central location-dynamics review exactly the same
historical USGS series that entered fit, and how do the retrospective inputs,
forecast inputs, held-out future USGS, and central location curves line up?
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd


CENTRAL_QS = ["q20", "q35", "q50", "q65", "q80"]
Q_COLORS = {
    "q20": "#C45D38",
    "q35": "#E38D2C",
    "q50": "#6A3D9A",
    "q65": "#2E86AB",
    "q80": "#1F9E89",
}
INPUT_COLORS = {
    "usgs_hist": "#1B7F3B",
    "usgs_future": "#B22222",
    "glofas_hist": "#E67E22",
    "nws_hist": "#756BB1",
    "glofas_fore": "#D95F0E",
    "nws_fore": "#6A51A3",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--location-csv", required=True)
    parser.add_argument("--report-dir", required=True)
    return parser.parse_args()


def date_tick_setup(ax, dates: pd.Series) -> None:
    span = (dates.max() - dates.min()).days
    if span > 120:
        locator = mdates.MonthLocator()
        formatter = mdates.DateFormatter("%Y-%m")
    else:
        locator = mdates.WeekdayLocator(interval=1)
        formatter = mdates.DateFormatter("%b %d")
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")


def load_inputs(run_root: Path, location_csv: Path) -> dict[str, pd.DataFrame]:
    loc = pd.read_csv(location_csv, parse_dates=["date"])
    fit_retros = pd.read_csv(run_root / "fit" / "inputs" / "retros_fit_adapter.csv", parse_dates=["Date"]).rename(
        columns={"Date": "date", "USGS": "fit_usgs", "GloFAS": "fit_glofas_retro", "NWS3.0": "fit_nws_retro"}
    )
    glofas_fore = pd.read_csv(run_root / "fit" / "inputs" / "glofas_fit_adapter.csv", parse_dates=["target_date"]).rename(
        columns={"target_date": "date"}
    )
    nws_fore = pd.read_csv(run_root / "fit" / "inputs" / "nws_fit_adapter.csv", parse_dates=["target_date"]).rename(
        columns={"target_date": "date"}
    )
    quant_csv = pd.read_csv(
        run_root / "post" / "outputs" / run_root.name / "exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv",
        parse_dates=["date"],
    )
    return {
        "loc": loc,
        "fit_retros": fit_retros,
        "glofas_fore": glofas_fore,
        "nws_fore": nws_fore,
        "quant_csv": quant_csv,
    }


def build_window_df(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    loc = data["loc"].copy()
    fit_retros = data["fit_retros"][["date", "fit_usgs", "fit_glofas_retro", "fit_nws_retro"]].copy()
    quant_obs = data["quant_csv"][["date", "segment", "observed"]].rename(columns={"observed": "quantile_csv_observed"})
    out = loc.merge(fit_retros, on="date", how="left").merge(quant_obs, on=["date", "segment"], how="left")
    return out


def write_contract_checks(report_dir: Path, df: pd.DataFrame) -> None:
    hist = df[df["segment"] == "history"].copy()
    checks = [
        ("history_max_abs_diff_plotted_observed_vs_fit_usgs", float((hist["observed"] - hist["fit_usgs"]).abs().max())),
        ("history_max_abs_diff_plotted_observed_vs_quantile_csv_observed", float((hist["observed"] - hist["quantile_csv_observed"]).abs().max())),
        ("forecast_max_abs_diff_plotted_observed_vs_quantile_csv_observed", float((df[df["segment"] == "forecast"]["observed"] - df[df["segment"] == "forecast"]["quantile_csv_observed"]).abs().max())),
    ]
    out = report_dir / "input_vs_plotted_contract_checks.csv"
    with out.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        writer.writerows(checks)


def write_source_manifest(report_dir: Path, run_root: Path, location_csv: Path) -> None:
    rows = [
        ("location_csv", str(location_csv)),
        ("fit_retros_input", str(run_root / "fit" / "inputs" / "retros_fit_adapter.csv")),
        ("fit_glofas_forecast_input", str(run_root / "fit" / "inputs" / "glofas_fit_adapter.csv")),
        ("fit_nws_forecast_input", str(run_root / "fit" / "inputs" / "nws_fit_adapter.csv")),
        ("cutoff_quantiles_csv", str(run_root / "post" / "outputs" / run_root.name / "exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv")),
    ]
    out = report_dir / "source_manifest.csv"
    with out.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["artifact_role", "path"])
        writer.writerows(rows)


def plot_inputs_and_locations(report_dir: Path, df: pd.DataFrame, data: dict[str, pd.DataFrame]) -> None:
    fig, ax = plt.subplots(figsize=(15, 8))
    hist = df[df["segment"] == "history"].copy()
    fc = df[df["segment"] == "forecast"].copy()

    # Historical inputs actually used in fit.
    ax.plot(hist["date"], hist["fit_usgs"], color=INPUT_COLORS["usgs_hist"], linewidth=2.2, label="USGS fit input")
    ax.plot(hist["date"], hist["fit_glofas_retro"], color=INPUT_COLORS["glofas_hist"], linewidth=1.8, alpha=0.95, label="GloFAS retros input")
    ax.plot(hist["date"], hist["fit_nws_retro"], color=INPUT_COLORS["nws_hist"], linewidth=1.8, alpha=0.95, label="NWS retros input")

    # Forecast inputs actually used in fit.
    glofas_fore = data["glofas_fore"]
    nws_fore = data["nws_fore"]
    glo_member_cols = [c for c in glofas_fore.columns if c.startswith("member_")]
    nws_member_cols = [c for c in nws_fore.columns if c.startswith("member_")]
    for c in glo_member_cols:
        ax.plot(glofas_fore["date"], glofas_fore[c], color=INPUT_COLORS["glofas_fore"], alpha=0.12, linewidth=0.8)
    for c in nws_member_cols:
        ax.plot(nws_fore["date"], nws_fore[c], color=INPUT_COLORS["nws_fore"], alpha=0.18, linewidth=0.9)
    ax.plot(glofas_fore["date"], glofas_fore[glo_member_cols].mean(axis=1), color=INPUT_COLORS["glofas_fore"], linewidth=2.0, linestyle="--", label="GloFAS forecast mean input")
    ax.plot(nws_fore["date"], nws_fore[nws_member_cols].mean(axis=1), color=INPUT_COLORS["nws_fore"], linewidth=2.0, linestyle="--", label="NWS forecast mean input")

    # Held-out future USGS, not used in fit.
    ax.plot(fc["date"], fc["observed"], color=INPUT_COLORS["usgs_future"], linewidth=2.2, marker="o", markersize=3.2, markerfacecolor="white", label="Held-out future USGS")

    # Central location means.
    for q in CENTRAL_QS:
        col = f"loc_{q}_mean"
        ax.plot(df["date"], df[col], color=Q_COLORS[q], linewidth=2.0 if q == "q50" else 1.7, label=f"{q} mean location")

    cutoff_date = hist["date"].max()
    ax.axvline(cutoff_date, color="#444444", linestyle=":", linewidth=1.2)
    ax.axvspan(fc["date"].min(), fc["date"].max(), color="#d8ecff", alpha=0.35)
    ax.set_title("Representative exAL-M-T1 cutoff window: exact fit inputs + central location means")
    ax.set_xlabel("Date")
    ax.set_ylabel("log1p(cms)")
    ax.grid(alpha=0.25, linewidth=0.6)
    date_tick_setup(ax, df["date"])
    handles, labels = ax.get_legend_handles_labels()
    # Deduplicate labels while preserving order.
    seen = set()
    uniq_handles = []
    uniq_labels = []
    for h, l in zip(handles, labels):
        if l in seen:
            continue
        seen.add(l)
        uniq_handles.append(h)
        uniq_labels.append(l)
    ax.legend(uniq_handles, uniq_labels, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(report_dir / f"cutoff_window_inputs_and_central_location_dynamics_log1p.{ext}", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_inputs_only(report_dir: Path, df: pd.DataFrame, data: dict[str, pd.DataFrame]) -> None:
    fig, ax = plt.subplots(figsize=(15, 8))
    hist = df[df["segment"] == "history"].copy()
    fc = df[df["segment"] == "forecast"].copy()
    ax.plot(hist["date"], hist["fit_usgs"], color=INPUT_COLORS["usgs_hist"], linewidth=2.2, label="USGS fit input")
    ax.plot(hist["date"], hist["fit_glofas_retro"], color=INPUT_COLORS["glofas_hist"], linewidth=1.8, label="GloFAS retros input")
    ax.plot(hist["date"], hist["fit_nws_retro"], color=INPUT_COLORS["nws_hist"], linewidth=1.8, label="NWS retros input")
    glofas_fore = data["glofas_fore"]
    nws_fore = data["nws_fore"]
    glo_member_cols = [c for c in glofas_fore.columns if c.startswith("member_")]
    nws_member_cols = [c for c in nws_fore.columns if c.startswith("member_")]
    for c in glo_member_cols:
        ax.plot(glofas_fore["date"], glofas_fore[c], color=INPUT_COLORS["glofas_fore"], alpha=0.12, linewidth=0.8)
    for c in nws_member_cols:
        ax.plot(nws_fore["date"], nws_fore[c], color=INPUT_COLORS["nws_fore"], alpha=0.18, linewidth=0.9)
    ax.plot(glofas_fore["date"], glofas_fore[glo_member_cols].mean(axis=1), color=INPUT_COLORS["glofas_fore"], linewidth=2.0, linestyle="--", label="GloFAS forecast mean input")
    ax.plot(nws_fore["date"], nws_fore[nws_member_cols].mean(axis=1), color=INPUT_COLORS["nws_fore"], linewidth=2.0, linestyle="--", label="NWS forecast mean input")
    ax.plot(fc["date"], fc["observed"], color=INPUT_COLORS["usgs_future"], linewidth=2.2, marker="o", markersize=3.2, markerfacecolor="white", label="Held-out future USGS")
    cutoff_date = hist["date"].max()
    ax.axvline(cutoff_date, color="#444444", linestyle=":", linewidth=1.2)
    ax.axvspan(fc["date"].min(), fc["date"].max(), color="#d8ecff", alpha=0.35)
    ax.set_title("Representative exAL-M-T1 cutoff window: exact fit inputs only")
    ax.set_xlabel("Date")
    ax.set_ylabel("log1p(cms)")
    ax.grid(alpha=0.25, linewidth=0.6)
    date_tick_setup(ax, df["date"])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(report_dir / f"cutoff_window_fit_inputs_only_log1p.{ext}", dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_readme(report_dir: Path, run_root: Path, location_csv: Path) -> None:
    text = f"""# exAL-M-T1 Input Context Review

- run root: `{run_root}`
- location csv source: `{location_csv}`
- objective: confirm whether the USGS series plotted in the location-dynamics figure matches the exact fit input series, then show the full cutoff-window input context

## Outputs

- `cutoff_window_inputs_and_central_location_dynamics_log1p.png`
- `cutoff_window_fit_inputs_only_log1p.png`
- `input_vs_plotted_contract_checks.csv`
- `source_manifest.csv`

## Interpretation

- `USGS fit input`: the exact historical USGS series used by fit from `fit/inputs/retros_fit_adapter.csv`
- `GloFAS retros input` and `NWS retros input`: the exact historical retrospective predictors used by fit
- `GloFAS forecast mean input` and `NWS forecast mean input`: means of the exact forecast-member matrices used by fit
- `Held-out future USGS`: actual post-cutoff USGS used only for checking, not for fit
- `q20`..`q80 mean location`: the central row-level USGS location means used before `rexal()` sampling
"""
    (report_dir / "README.md").write_text(text)


def main() -> None:
    args = parse_args()
    run_root = Path(args.run_root)
    location_csv = Path(args.location_csv)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    data = load_inputs(run_root, location_csv)
    df = build_window_df(data)
    plot_inputs_and_locations(report_dir, df, data)
    plot_inputs_only(report_dir, df, data)
    write_contract_checks(report_dir, df)
    write_source_manifest(report_dir, run_root, location_csv)
    write_readme(report_dir, run_root, location_csv)
    df.to_csv(report_dir / "cutoff_window_input_context.csv", index=False)


if __name__ == "__main__":
    main()

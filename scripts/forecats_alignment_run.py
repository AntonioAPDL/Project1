#!/usr/bin/env python3
"""
End-to-end alignment runner for the forecats pipeline.

Given:
- an "old/truth" GloFAS weighted forecast CSV (typically log1p(cms)),
- a new bundle directory produced by scripts/forecats_pipeline.R,

this script produces:
- deterministic comparisons (metrics + plots),
- basic provenance checks (issue-date contamination, member alignment),
- small knob tests (e.g. shift_days) to isolate root causes.

This is intentionally lightweight and produces outputs under repro/forecats_alignment/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def parse_issue_date_from_cache_name(name: str) -> Optional[str]:
    # cache files look like: issue_date=YYYY-MM-DD.npz
    m = re.match(r"^issue_date=(\d{4}-\d{2}-\d{2})\.npz$", name)
    return m.group(1) if m else None


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    m = np.isfinite(a) & np.isfinite(b)
    if not m.any():
        return float("nan")
    return float(np.sqrt(np.mean((a[m] - b[m]) ** 2)))


def mae(a: np.ndarray, b: np.ndarray) -> float:
    m = np.isfinite(a) & np.isfinite(b)
    if not m.any():
        return float("nan")
    return float(np.mean(np.abs(a[m] - b[m])))


def corr(a: np.ndarray, b: np.ndarray) -> float:
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3:
        return float("nan")
    return float(np.corrcoef(a[m], b[m])[0, 1])


def wide_members_0_50_to_member_xx(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename: Dict[str, str] = {}
    for c in out.columns:
        if c.isdigit():
            rename[c] = f"member_{int(c):02d}"
    return out.rename(columns=rename)


def load_old_glofas(old_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(old_csv)
    if "target_date" not in df.columns:
        raise ValueError(f"Expected 'target_date' column in old CSV: {old_csv}")
    df["target_date"] = pd.to_datetime(df["target_date"]).dt.date
    df = wide_members_0_50_to_member_xx(df)
    member_cols = [c for c in df.columns if c.startswith("member_")]
    if len(member_cols) != 51:
        raise ValueError(f"Expected 51 member columns in old CSV, found {len(member_cols)}")
    return df[["target_date"] + sorted(member_cols)]


def load_new_glofas(bundle_dir: Path) -> pd.DataFrame:
    p = bundle_dir / "inputs" / "glofas_weighted_daily.csv"
    df = pd.read_csv(p)
    if "target_date" not in df.columns:
        raise ValueError(f"Expected 'target_date' column in new CSV: {p}")
    df["target_date"] = pd.to_datetime(df["target_date"]).dt.date
    member_cols = [c for c in df.columns if c.startswith("member_")]
    if len(member_cols) != 51:
        raise ValueError(f"Expected 51 member columns in new CSV, found {len(member_cols)}")
    return df[["target_date"] + sorted(member_cols)]


def to_log1p_from_scale(df: pd.DataFrame, scale: str) -> pd.DataFrame:
    out = df.copy()
    member_cols = [c for c in out.columns if c.startswith("member_")]
    vals = out[member_cols].to_numpy(dtype="float64")
    if scale == "log1p_cms":
        return out
    if scale == "raw_cms":
        out[member_cols] = np.log1p(vals)
        return out
    raise ValueError(f"Unsupported scale: {scale}")


def to_raw_from_scale(df: pd.DataFrame, scale: str) -> pd.DataFrame:
    out = df.copy()
    member_cols = [c for c in out.columns if c.startswith("member_")]
    vals = out[member_cols].to_numpy(dtype="float64")
    if scale == "raw_cms":
        return out
    if scale == "log1p_cms":
        out[member_cols] = np.expm1(vals)
        return out
    raise ValueError(f"Unsupported scale: {scale}")


def align_on_dates(old_df: pd.DataFrame, new_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    common = sorted(set(old_df["target_date"]).intersection(set(new_df["target_date"])))
    old2 = old_df[old_df["target_date"].isin(common)].sort_values("target_date").reset_index(drop=True)
    new2 = new_df[new_df["target_date"].isin(common)].sort_values("target_date").reset_index(drop=True)
    return old2, new2


def compute_member_metrics(old_df: pd.DataFrame, new_df: pd.DataFrame, scale_label: str) -> pd.DataFrame:
    member_cols = [c for c in old_df.columns if c.startswith("member_")]
    rows = []
    for c in member_cols:
        a = old_df[c].to_numpy(dtype="float64")
        b = new_df[c].to_numpy(dtype="float64")
        rows.append(
            {
                "member": c,
                "scale": scale_label,
                "rmse": rmse(a, b),
                "mae": mae(a, b),
                "corr": corr(a, b),
                "bias_mean_old_minus_new": float(np.nanmean(a - b)),
                "n_common": int(np.isfinite(a).astype(int).dot(np.isfinite(b).astype(int))),
            }
        )
    return pd.DataFrame(rows)


def ensemble_summary(df: pd.DataFrame) -> pd.DataFrame:
    member_cols = [c for c in df.columns if c.startswith("member_")]
    vals = df[member_cols].to_numpy(dtype="float64")
    out = pd.DataFrame(
        {
            "target_date": pd.to_datetime(df["target_date"]),
            "ens_mean": np.nanmean(vals, axis=1),
            "ens_p10": np.nanpercentile(vals, 10, axis=1),
            "ens_p50": np.nanpercentile(vals, 50, axis=1),
            "ens_p90": np.nanpercentile(vals, 90, axis=1),
        }
    )
    return out


def write_notebook_keyword_hits(ipynb: Path, keywords: List[str], out_txt: Path) -> None:
    import nbformat  # type: ignore

    nb = nbformat.read(ipynb, as_version=4)
    keys = [k.lower() for k in keywords]
    hits = []
    for i, cell in enumerate(nb.cells):
        if cell.get("cell_type") != "code":
            continue
        src = cell.get("source", "")
        low = src.lower()
        if any(k in low for k in keys):
            hits.append((i, src))

    with out_txt.open("w", encoding="utf-8") as f:
        f.write(f"Notebook: {ipynb}\n")
        f.write(f"Keywords: {keywords}\n")
        f.write(f"Hit cells: {len(hits)}\n\n")
        for idx, src in hits[:50]:
            f.write(f"--- cell[{idx}] ---\n")
            f.write(src.strip() + "\n\n")
        if len(hits) > 50:
            f.write(f"... truncated ({len(hits)-50} more matching cells)\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff-date", required=True, help="YYYY-MM-DD (for labeling/reporting)")
    ap.add_argument("--bundle-dir", required=True, type=Path)
    ap.add_argument("--old-glofas-csv", required=True, type=Path)
    ap.add_argument("--old-glofas-scale", default="log1p_cms", choices=["log1p_cms", "raw_cms"])
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--also-scan-notebooks", action="store_true")
    args = ap.parse_args()

    bundle_dir = args.bundle_dir.resolve()
    out_dir = args.out_dir.resolve()
    ensure_dir(out_dir)
    ensure_dir(out_dir / "plots")

    # -------------------------
    # Phase 0: provenance snapshot
    # -------------------------
    meta_path = bundle_dir / "meta.yaml"
    new_glofas_path = bundle_dir / "inputs" / "glofas_weighted_daily.csv"
    cell_json = bundle_dir / "inputs" / "glofas_cell.json"

    snapshot = {
        "cutoff_date": args.cutoff_date,
        "bundle_dir": str(bundle_dir),
        "old_glofas_csv": str(args.old_glofas_csv),
        "old_glofas_scale": args.old_glofas_scale,
        "files": {
            "meta.yaml": {"path": str(meta_path), "exists": meta_path.exists()},
            "new_glofas_weighted_daily.csv": {"path": str(new_glofas_path), "sha256": sha256_file(new_glofas_path)},
            "old_glofas_csv": {"path": str(args.old_glofas_csv), "sha256": sha256_file(args.old_glofas_csv)},
            "glofas_cell.json": {"path": str(cell_json), "sha256": sha256_file(cell_json)} if cell_json.exists() else None,
        },
    }
    (out_dir / "baseline_snapshot.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True))

    # -------------------------
    # Phase 1: contamination check via cache filenames
    # -------------------------
    cache_dir = bundle_dir / "cache" / "glofas"
    issue_dates = []
    if cache_dir.exists():
        for p in cache_dir.iterdir():
            d = parse_issue_date_from_cache_name(p.name)
            if d:
                issue_dates.append(d)
    issue_dates = sorted(issue_dates)
    contamination = {
        "cache_dir": str(cache_dir),
        "n_issue_dates_cached": len(issue_dates),
        "min_issue_date": issue_dates[0] if issue_dates else None,
        "max_issue_date": issue_dates[-1] if issue_dates else None,
    }
    (out_dir / "contamination_check.json").write_text(json.dumps(contamination, indent=2, sort_keys=True))

    # -------------------------
    # Phase 2/3: load + align + metrics
    # -------------------------
    old_glo = load_old_glofas(args.old_glofas_csv)
    new_glo = load_new_glofas(bundle_dir)

    # Compare on log1p scale
    old_log1p = to_log1p_from_scale(old_glo, args.old_glofas_scale)
    new_log1p = to_log1p_from_scale(new_glo, "raw_cms")
    old_log1p_a, new_log1p_a = align_on_dates(old_log1p, new_log1p)
    m_log1p = compute_member_metrics(old_log1p_a, new_log1p_a, "log1p_cms")

    # Compare on raw cms scale
    old_raw = to_raw_from_scale(old_glo, args.old_glofas_scale)
    new_raw = to_raw_from_scale(new_glo, "raw_cms")
    old_raw_a, new_raw_a = align_on_dates(old_raw, new_raw)
    m_raw = compute_member_metrics(old_raw_a, new_raw_a, "raw_cms")

    metrics = pd.concat([m_log1p, m_raw], ignore_index=True)
    metrics.to_csv(out_dir / "glofas_member_metrics.csv", index=False)

    # Summary metrics on ensemble mean
    old_es = ensemble_summary(old_log1p_a)
    new_es = ensemble_summary(new_log1p_a)
    es = old_es.merge(new_es, on="target_date", suffixes=("_old", "_new"))
    es["ens_mean_diff_old_minus_new"] = es["ens_mean_old"] - es["ens_mean_new"]
    es.to_csv(out_dir / "glofas_ensemble_summary_log1p.csv", index=False)

    # -------------------------
    # Plots (matplotlib kept local to avoid heavy deps)
    # -------------------------
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # 1) Ensemble mean time series (log1p)
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(es["target_date"], es["ens_mean_old"], label="Old (truth) ens mean", linewidth=2)
    ax.plot(es["target_date"], es["ens_mean_new"], label="New (pipeline) ens mean", linewidth=2, alpha=0.85)
    ax.set_title(f"GloFAS ensemble mean (log1p scale) | cutoff={args.cutoff_date}")
    ax.set_xlabel("target_date")
    ax.set_ylabel("log1p(cms)")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_dir / "plots" / "glofas_ens_mean_log1p.png", dpi=200)
    plt.close(fig)

    # 2) Scatter old vs new ens mean (log1p)
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(es["ens_mean_old"], es["ens_mean_new"], s=18, alpha=0.75)
    lo = np.nanmin([es["ens_mean_old"].min(), es["ens_mean_new"].min()])
    hi = np.nanmax([es["ens_mean_old"].max(), es["ens_mean_new"].max()])
    ax.plot([lo, hi], [lo, hi], color="black", linewidth=1)
    ax.set_title("Old vs New (ens mean, log1p)")
    ax.set_xlabel("old")
    ax.set_ylabel("new")
    fig.tight_layout()
    fig.savefig(out_dir / "plots" / "glofas_ens_mean_scatter_log1p.png", dpi=200)
    plt.close(fig)

    # 3) Member-by-member heatmap of mean absolute error (log1p)
    m2 = metrics[metrics["scale"] == "log1p_cms"].copy()
    m2["member_i"] = m2["member"].str.replace("member_", "", regex=False).astype(int)
    m2 = m2.sort_values("member_i")
    fig, ax = plt.subplots(figsize=(12, 2.2))
    ax.imshow(m2["mae"].to_numpy()[None, :], aspect="auto")
    ax.set_yticks([])
    ax.set_xticks(range(0, len(m2), 5))
    ax.set_xticklabels([f"{i:02d}" for i in m2["member_i"].to_numpy()[::5]])
    ax.set_title("MAE by member (log1p)")
    fig.tight_layout()
    fig.savefig(out_dir / "plots" / "glofas_mae_by_member_log1p.png", dpi=200)
    plt.close(fig)

    # -------------------------
    # Phase 5: lightweight notebook scan (bias/scale keywords)
    # -------------------------
    if args.also_scan_notebooks:
        try:
            keywords = [
                "bias",
                "scale",
                "correct",
                "calibr",
                "standard",
                "rescale",
                "mean",
                "std",
                "sigma",
                "quantile",
                "mapping",
            ]
            nb_dir = Path.cwd()
            for nb in ["glofas_forecasts.ipynb", "Forecast_Post_Procc.ipynb", "Retro-Analysis.ipynb"]:
                p = nb_dir / nb
                if p.exists():
                    write_notebook_keyword_hits(p, keywords, out_dir / f"notebook_hits_{p.stem}.txt")
        except Exception as e:
            (out_dir / "notebook_scan_error.txt").write_text(str(e))

    # -------------------------
    # Human-readable summary
    # -------------------------
    def _row(df: pd.DataFrame, col: str) -> float:
        return float(np.nanmedian(df[col].to_numpy(dtype="float64")))

    summ = []
    summ.append(f"cutoff_date: {args.cutoff_date}")
    summ.append(f"bundle_dir: {bundle_dir}")
    summ.append("")
    summ.append("Contamination check (from cache filenames):")
    summ.append(json.dumps(contamination, indent=2, sort_keys=True))
    summ.append("")
    summ.append("GloFAS member metrics (median across members):")
    summ.append(f"  log1p: median RMSE={_row(m_log1p,'rmse'):.6f} median MAE={_row(m_log1p,'mae'):.6f} median corr={_row(m_log1p,'corr'):.4f}")
    summ.append(f"  raw  : median RMSE={_row(m_raw,'rmse'):.6f} median MAE={_row(m_raw,'mae'):.6f} median corr={_row(m_raw,'corr'):.4f}")
    summ.append("")
    summ.append("Outputs:")
    summ.append(f"  {out_dir}/glofas_member_metrics.csv")
    summ.append(f"  {out_dir}/glofas_ensemble_summary_log1p.csv")
    summ.append(f"  {out_dir}/plots/*.png")
    (out_dir / "SUMMARY.txt").write_text("\n".join(summ))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


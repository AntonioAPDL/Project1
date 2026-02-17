#!/usr/bin/env python3
"""Generate unified trace summary figures for univariate, multivariate, and NDLM logs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import matplotlib.pyplot as plt
import numpy as np


KV_RE = re.compile(r"(\w+)=((?:\[[^\]]*\])|(?:[^ ]+))")


def parse_float(value: Optional[str]) -> float:
    if value is None:
        return np.nan
    token = value.strip()
    if token in {"NA", "NaN", "nan", "NULL", "Inf", "-Inf"}:
        return np.nan
    try:
        return float(token)
    except ValueError:
        return np.nan


def parse_progress_rows(log_path: Path) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    if not log_path.exists():
        return rows
    for line in log_path.read_text(errors="ignore").splitlines():
        if "[gamsig_progress]" not in line:
            continue
        kv_pairs = dict(KV_RE.findall(line))
        if not kv_pairs:
            continue
        rows.append(
            {
                "iter": parse_float(kv_pairs.get("iter")),
                "elbo": parse_float(kv_pairs.get("elbo")),
                "sigma_exp": parse_float(kv_pairs.get("sigma_exp")),
                "gamma_exp": parse_float(kv_pairs.get("gamma_exp")),
                "state_norm_sq": parse_float(kv_pairs.get("state_norm_sq")),
                "w_hist": parse_float(kv_pairs.get("w_hist")),
                "w_fore": parse_float(kv_pairs.get("w_fore")),
            }
        )
    return rows


def quantile_sort_key(label: str) -> float:
    try:
        return float(label) / 100.0
    except ValueError:
        return float("inf")


def iter_and_value(rows: Iterable[Dict[str, float]], key: str) -> tuple[np.ndarray, np.ndarray]:
    rows_list = list(rows)
    iters = np.array([r["iter"] for r in rows_list], dtype=float)
    vals = np.array([r.get(key, np.nan) for r in rows_list], dtype=float)
    mask = np.isfinite(iters) & np.isfinite(vals)
    return iters[mask], vals[mask]


def save_univar_or_multivar_figure(
    series_by_quantile: Dict[str, List[Dict[str, float]]],
    run_id: str,
    model_label: str,
    out_path: Path,
) -> None:
    quantiles = sorted(series_by_quantile.keys(), key=quantile_sort_key)
    colors = plt.cm.tab10(np.linspace(0, 1, max(1, len(quantiles))))
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=False)
    metrics = [
        ("elbo", "ELBO"),
        ("sigma_exp", "E[sigma]"),
        ("gamma_exp", "E[gamma]"),
        ("state_norm_sq", "||state||^2"),
    ]
    handles = []
    labels = []

    for color, q in zip(colors, quantiles):
        rows = series_by_quantile[q]
        label = f"q={q}"
        for ax, (metric_key, metric_label) in zip(axes.flat, metrics):
            xs, ys = iter_and_value(rows, metric_key)
            if xs.size == 0:
                continue
            line, = ax.plot(xs, ys, lw=1.8, color=color, alpha=0.95)
            if metric_key == "elbo":
                handles.append(line)
                labels.append(label)
            ax.set_xlabel("Iteration")
            ax.set_ylabel(metric_label)
            ax.grid(alpha=0.25, linewidth=0.5)

    title = f"{run_id} | {model_label} Trace Summary"
    fig.suptitle(title, fontsize=13, fontweight="bold", y=0.98)
    if handles:
        ncol = min(4, len(handles))
        fig.legend(
            handles,
            labels,
            loc="upper center",
            ncol=ncol,
            frameon=False,
            bbox_to_anchor=(0.5, 0.945),
        )
    fig.tight_layout(rect=[0.02, 0.02, 0.98, 0.90])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def save_ndlm_figure(rows: List[Dict[str, float]], run_id: str, out_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.5), constrained_layout=False)
    metrics = [
        ("elbo", "ELBO"),
        ("sigma_exp", "E[sigma]"),
        ("state_norm_sq", "||state||^2"),
    ]
    for ax, (metric_key, metric_label) in zip(axes.flat[:3], metrics):
        xs, ys = iter_and_value(rows, metric_key)
        if xs.size > 0:
            ax.plot(xs, ys, lw=2.0, color="#1f77b4")
        ax.set_xlabel("Iteration")
        ax.set_ylabel(metric_label)
        ax.grid(alpha=0.25, linewidth=0.5)

    ax = axes.flat[3]
    x_hist, y_hist = iter_and_value(rows, "w_hist")
    x_fore, y_fore = iter_and_value(rows, "w_fore")
    if x_hist.size > 0:
        ax.plot(x_hist, y_hist, lw=2.0, label="w_hist", color="#2ca02c")
    if x_fore.size > 0:
        ax.plot(x_fore, y_fore, lw=2.0, label="w_fore", color="#d62728")
    ax.set_xlabel("Iteration")
    ax.set_ylabel("W terms")
    ax.grid(alpha=0.25, linewidth=0.5)
    ax.legend(frameon=False)

    fig.suptitle(f"{run_id} | NDLM Trace Summary", fontsize=13, fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0.02, 0.02, 0.98, 0.95])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220)
    plt.close(fig)


def gather_series(run_root: Path) -> tuple[Dict[str, List[Dict[str, float]]], Dict[str, List[Dict[str, float]]], List[Dict[str, float]]]:
    fit_root = run_root / "fit"
    multivar: Dict[str, List[Dict[str, float]]] = {}
    for q_dir in sorted(fit_root.glob("q=*"), key=lambda p: quantile_sort_key(p.name.split("=")[1])):
        q = q_dir.name.split("=")[1]
        rows = parse_progress_rows(q_dir / "logs" / "fit.log")
        if rows:
            multivar[q] = rows

    univar: Dict[str, List[Dict[str, float]]] = {}
    univar_root = fit_root / "exdqlm_univar"
    if univar_root.exists():
        for q_dir in sorted(univar_root.glob("q=*"), key=lambda p: quantile_sort_key(p.name.split("=")[1])):
            q = q_dir.name.split("=")[1]
            rows = parse_progress_rows(q_dir / "logs" / "univar_theory.log")
            if rows:
                univar[q] = rows

    ndlm_rows = parse_progress_rows(fit_root / "ndlm_main" / "logs" / "ndlm_theory.log")
    return multivar, univar, ndlm_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot unified run trace summaries.")
    parser.add_argument(
        "--run-root",
        required=True,
        help="Path to unified run root (e.g., repro/runs/<RUN_ID>).",
    )
    parser.add_argument(
        "--out-dir",
        default="repro/reports/figures",
        help="Output directory for PNG figures.",
    )
    args = parser.parse_args()

    run_root = Path(args.run_root).resolve()
    run_id = run_root.name
    out_dir = Path(args.out_dir)

    multivar, univar, ndlm_rows = gather_series(run_root)

    if univar:
        out_path = out_dir / f"{run_id}_univar_trace_summary_latest.png"
        save_univar_or_multivar_figure(univar, run_id, "exDQLM Univariate", out_path)
        print(out_path.as_posix())
    else:
        print(f"[warn] no univariate traces found under {run_root.as_posix()}")

    if multivar:
        out_path = out_dir / f"{run_id}_multivar_trace_summary_latest.png"
        save_univar_or_multivar_figure(multivar, run_id, "exDQLM Multivariate", out_path)
        print(out_path.as_posix())
    else:
        print(f"[warn] no multivariate traces found under {run_root.as_posix()}")

    if ndlm_rows:
        out_path = out_dir / f"{run_id}_ndlm_trace_summary_latest.png"
        save_ndlm_figure(ndlm_rows, run_id, out_path)
        print(out_path.as_posix())
    else:
        print(f"[warn] no NDLM traces found under {run_root.as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

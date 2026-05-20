#!/usr/bin/env python3
"""Render representative exAL-M-T1 fit-trace comparison plots.

This script parses the emitted `gamsig_progress` lines from the per-quantile
fit logs and renders one comparison plot per recorded optimizer trace:
ELBO, sigma_exp, gamma_exp, and a TT-standardized state norm trace.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


PROGRESS_RE = re.compile(
    r"iter=(?P<iter>\d+).*?"
    r"elbo=(?P<elbo>[-+0-9.eE]+).*?"
    r"sigma_exp=(?P<sigma_exp>[-+0-9.eE]+).*?"
    r"gamma_exp=(?P<gamma_exp>[-+0-9.eE]+).*?"
    r"state_norm_sq=(?P<state_norm_sq>[-+0-9.eE]+).*?"
    r"conv_check=(?P<conv_check>[-+0-9.eE]+|NA).*?"
    r"frozen=(?P<frozen>true|false)"
)

SAMPLING_RE = re.compile(r"\[sampling_phase\].*?phase=sampling_start.*?vb_iter=(?P<vb_iter>\d+)")

QUANTILES = ["05", "20", "35", "50", "65", "80", "95"]
COLORS = {
    "05": "#c0392b",
    "20": "#e67e22",
    "35": "#f1c40f",
    "50": "#27ae60",
    "65": "#16a085",
    "80": "#2980b9",
    "95": "#8e44ad",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--report-dir", required=True)
    return parser.parse_args()


def infer_tt(run_root: Path) -> int:
    retros_path = run_root / "fit" / "inputs" / "retros_fit_adapter.csv"
    if not retros_path.exists():
        raise FileNotFoundError(f"Missing retros adapter CSV: {retros_path}")
    with retros_path.open(errors="ignore") as handle:
        row_count = sum(1 for _ in handle) - 1
    if row_count <= 0:
        raise ValueError(f"Could not infer TT from {retros_path}")
    return row_count


def parse_fit_log(path: Path, quantile: str) -> tuple[list[dict[str, object]], int | None]:
    rows: list[dict[str, object]] = []
    sampling_iter = None
    with path.open(errors="ignore") as handle:
        for line in handle:
            if "gamsig_progress" in line:
                match = PROGRESS_RE.search(line)
                if not match:
                    continue
                conv_text = match.group("conv_check")
                rows.append(
                    {
                        "quantile": quantile,
                        "iter": int(match.group("iter")),
                        "elbo": float(match.group("elbo")),
                        "sigma_exp": float(match.group("sigma_exp")),
                        "gamma_exp": float(match.group("gamma_exp")),
                        "state_norm_sq": float(match.group("state_norm_sq")),
                        "state_norm_sq_per_tt": math.nan,
                        "conv_check": float(conv_text) if conv_text != "NA" else math.nan,
                        "frozen": match.group("frozen") == "true",
                    }
                )
            elif "sampling_phase" in line and sampling_iter is None:
                match = SAMPLING_RE.search(line)
                if match:
                    sampling_iter = int(match.group("vb_iter"))
    return rows, sampling_iter


def write_trace_csv(report_dir: Path, rows: list[dict[str, object]]) -> None:
    out_path = report_dir / "fit_trace_progress.csv"
    fieldnames = [
        "quantile",
        "iter",
        "elbo",
        "sigma_exp",
        "gamma_exp",
        "state_norm_sq",
        "state_norm_sq_per_tt",
        "conv_check",
        "frozen",
    ]
    with out_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_summary_csv(report_dir: Path, final_rows: list[dict[str, object]]) -> None:
    out_path = report_dir / "fit_trace_summary.csv"
    fieldnames = [
        "quantile",
        "last_iter",
        "last_elbo",
        "last_sigma_exp",
        "last_gamma_exp",
        "last_state_norm_sq",
        "last_state_norm_sq_per_tt",
        "last_conv_check",
        "last_frozen",
        "sampling_started",
        "sampling_start_iter",
        "tt",
    ]
    with out_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in final_rows:
            writer.writerow(row)


def render_metric_plot(
    report_dir: Path,
    rows_by_q: dict[str, list[dict[str, object]]],
    metric: str,
    y_label: str,
    title: str,
    max_iter: int,
    sampling_iters: dict[str, int | None],
) -> None:
    fig, ax = plt.subplots(figsize=(13, 7))
    for q in QUANTILES:
        rows = rows_by_q.get(q, [])
        if not rows:
            continue
        xs = [int(row["iter"]) for row in rows]
        ys = [float(row[metric]) for row in rows]
        ax.plot(xs, ys, color=COLORS[q], linewidth=2.2, label=f"q{q}")
        ax.scatter([xs[-1]], [ys[-1]], color=COLORS[q], s=28, zorder=3)
        if sampling_iters.get(q) is not None:
            ax.axvline(
                sampling_iters[q],
                color=COLORS[q],
                alpha=0.12,
                linewidth=1.2,
            )
    ax.axvline(max_iter, color="#555555", linestyle="--", linewidth=1.2, alpha=0.7)
    ax.text(
        max_iter + 1,
        ax.get_ylim()[1],
        "iter ceiling",
        va="top",
        ha="left",
        fontsize=9,
        color="#555555",
    )
    ax.set_title(title)
    ax.set_xlabel("Iteration")
    ax.set_ylabel(y_label)
    ax.grid(alpha=0.25, linewidth=0.6)
    ax.legend(ncol=4, frameon=False)
    fig.tight_layout()
    stem = {
        "elbo": "all_quantiles_elbo_trace",
        "sigma_exp": "all_quantiles_sigma_exp_trace",
        "gamma_exp": "all_quantiles_gamma_exp_trace",
        "state_norm_sq_per_tt": "all_quantiles_state_norm_sq_per_tt_trace",
    }[metric]
    for ext in ("png", "pdf"):
        fig.savefig(report_dir / f"{stem}.{ext}", dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_readme(report_dir: Path, run_root: Path, final_rows: list[dict[str, object]]) -> None:
    readme = report_dir / "README.md"
    generated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    lines = [
        "# exAL-M-T1 Fit Trace Review",
        "",
        f"- Generated at: `{generated}`",
        f"- Run root: `{run_root}`",
        "- Source: per-quantile `fit.log` `gamsig_progress` lines",
        "- Traces plotted: `ELBO`, `sigma_exp`, `gamma_exp`, `state_norm_sq / TT`",
        "- Note: this family does not emit a separate multivariate `seq.scale` trace in the saved review path; `sigma_exp` is the recorded scale-like optimizer trace and `gamma_exp` is the recorded asymmetry trace.",
        "- State note: the fit logs record `state_norm_sq = sum(new.theta.out$sm^2)`. This review adds a standardized state trace using `state_norm_sq / TT`.",
        "",
        "## Final Snapshot",
        "",
        f"- Historical length `TT`: `{final_rows[0]['tt']}`",
        "",
        "| q | last_iter | frozen | sampling_started | sigma_exp | gamma_exp | state_norm_sq/TT | conv_check |",
        "|---|---:|---|---|---:|---:|---:|---:|",
    ]
    for row in final_rows:
        lines.append(
            f"| `q{row['quantile']}` | `{row['last_iter']}` | `{row['last_frozen']}` | "
            f"`{row['sampling_started']}` | `{row['last_sigma_exp']}` | "
            f"`{row['last_gamma_exp']}` | `{row['last_state_norm_sq_per_tt']}` | `{row['last_conv_check']}` |"
        )
    readme.write_text("\n".join(lines) + "\n")


def main() -> None:
    args = parse_args()
    run_root = Path(args.run_root)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    tt = infer_tt(run_root)

    all_rows: list[dict[str, object]] = []
    rows_by_q: dict[str, list[dict[str, object]]] = {}
    sampling_iters: dict[str, int | None] = {}
    final_rows: list[dict[str, object]] = []

    for q in QUANTILES:
        log_path = run_root / "fit" / "exdqlm_multivar" / "keep" / f"q={q}" / "logs" / "fit.log"
        rows, sampling_iter = parse_fit_log(log_path, q)
        rows_by_q[q] = rows
        for row in rows:
            row["state_norm_sq_per_tt"] = float(row["state_norm_sq"]) / float(tt)
        sampling_iters[q] = sampling_iter
        all_rows.extend(rows)
        if rows:
            last = rows[-1]
            final_rows.append(
                {
                    "quantile": q,
                    "last_iter": last["iter"],
                    "last_elbo": last["elbo"],
                    "last_sigma_exp": last["sigma_exp"],
                    "last_gamma_exp": last["gamma_exp"],
                    "last_state_norm_sq": last["state_norm_sq"],
                    "last_state_norm_sq_per_tt": last["state_norm_sq_per_tt"],
                    "last_conv_check": last["conv_check"],
                    "last_frozen": str(last["frozen"]).lower(),
                    "sampling_started": "yes" if sampling_iter is not None else "no",
                    "sampling_start_iter": sampling_iter if sampling_iter is not None else "",
                    "tt": tt,
                }
            )

    if not all_rows:
        raise SystemExit("No gamsig_progress traces found.")

    write_trace_csv(report_dir, all_rows)
    write_summary_csv(report_dir, final_rows)
    write_readme(report_dir, run_root, final_rows)

    max_iter = max(int(row["iter"]) for row in all_rows)
    render_metric_plot(
        report_dir,
        rows_by_q,
        "elbo",
        "ELBO",
        "Representative exAL-M-T1 ELBO traces by quantile",
        max_iter,
        sampling_iters,
    )
    render_metric_plot(
        report_dir,
        rows_by_q,
        "sigma_exp",
        "sigma_exp",
        "Representative exAL-M-T1 sigma traces by quantile",
        max_iter,
        sampling_iters,
    )
    render_metric_plot(
        report_dir,
        rows_by_q,
        "gamma_exp",
        "gamma_exp",
        "Representative exAL-M-T1 gamma traces by quantile",
        max_iter,
        sampling_iters,
    )
    render_metric_plot(
        report_dir,
        rows_by_q,
        "state_norm_sq_per_tt",
        "state_norm_sq / TT",
        "Representative exAL-M-T1 standardized state traces by quantile",
        max_iter,
        sampling_iters,
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Evaluate completed HE2 N-M-T1 broad screen outputs."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from multimodel_v8_lib import runs_dir  # noqa: E402
from run_multimodel_v8_queue import manifest_path_for, stage_status  # noqa: E402

DEFAULT_ARTIFACT_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_ndlm_main_keep_broad_screen_20260625"
)
DEFAULT_MATRIX_DIR = DEFAULT_ARTIFACT_ROOT / "control" / "ndlm_main_keep_broad_screen"
DEFAULT_AUTHORITY_ROWS = ROOT / "reports" / "nmt1_static_parity_audit_20260625" / "authority_rows.csv"
TARGET_MODEL_ID = "ndlm_main_synth_keep"
TARGET_MODEL_VARIANT = "ndlm_main_keep"
TARGET_SCORE_SCALE = "log_cms_plus1"


def read_csv_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def count_rdata(path: Path) -> int:
    if not path.exists():
        return 0
    return len(list(path.rglob("*.RData"))) + len(list(path.rglob("*.rda")))


def load_authority(authority_rows: Path) -> pd.DataFrame:
    df = pd.read_csv(authority_rows, dtype=str)
    subset = df.loc[
        (df["authority_class"] == "article_crps_table")
        & (df["row_label"] == "N-M-T1")
        & (df["source_class"] == TARGET_MODEL_VARIANT)
    ].copy()
    subset["authority_mean_crps"] = pd.to_numeric(subset["mean_crps"], errors="coerce")
    return subset.loc[:, ["cutoff", "authority_mean_crps", "run_id"]].rename(columns={"run_id": "authority_run_id"})


def collect(plan: pd.DataFrame, artifact_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    gate_rows: list[dict[str, Any]] = []
    crps_rows: list[pd.DataFrame] = []
    for _, row in plan.iterrows():
        run_id = str(row["run_id"])
        run_root = runs_dir(artifact_root) / run_id
        phase, status = stage_status(manifest_path_for(run_id, artifact_root))
        out_root = run_root / "post" / "outputs" / run_id
        crps_path = out_root / "tables" / "crps_forecast_per_time.csv"
        crps = read_csv_optional(crps_path)
        target = pd.DataFrame()
        if not crps.empty:
            target = crps.loc[
                (crps.get("model_id", pd.Series(dtype=str)).astype(str) == TARGET_MODEL_ID)
                & (crps.get("model_variant", pd.Series(dtype=str)).astype(str) == TARGET_MODEL_VARIANT)
                & (crps.get("score_scale", pd.Series(dtype=str)).astype(str) == TARGET_SCORE_SCALE)
            ].copy()
            if not target.empty:
                for col in [
                    "cutoff",
                    "grid_spec_id",
                    "discount_case_id",
                    "epsilon_value",
                    "df_t",
                    "df_s1",
                    "df_s2",
                    "df_s67",
                    "df_discrep",
                    "lambda",
                    "df_trans",
                    "df_covs",
                    "c_factor",
                    "forecast_cov_epsilon",
                    "run_id",
                ]:
                    target[col] = row.get(col, "")
                crps_rows.append(target)
        rdata_count = count_rdata(run_root)
        failure_reason = []
        if status != "pass":
            failure_reason.append(f"run_status={phase}/{status}")
        if target.empty:
            failure_reason.append("missing_target_crps")
        if rdata_count != 0:
            failure_reason.append("rdata_not_cleaned")
        gate = row.to_dict()
        gate.update(
            {
                "run_phase": phase,
                "run_status": status,
                "post_output_root": str(out_root),
                "target_crps_rows": int(len(target)),
                "run_rdata_count": int(rdata_count),
                "eligible": len(failure_reason) == 0,
                "failure_reason": "|".join(failure_reason),
            }
        )
        gate_rows.append(gate)
    crps_all = pd.concat(crps_rows, ignore_index=True) if crps_rows else pd.DataFrame()
    return pd.DataFrame(gate_rows), crps_all


def summarize(gates: pd.DataFrame, crps: pd.DataFrame, authority: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if crps.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    crps = crps.copy()
    crps["crps"] = pd.to_numeric(crps["crps"], errors="coerce")
    group_cols = [
        "cutoff",
        "grid_spec_id",
        "discount_case_id",
        "epsilon_value",
        "df_t",
        "df_s1",
        "df_s2",
        "df_s67",
        "df_discrep",
        "lambda",
        "df_trans",
        "df_covs",
        "c_factor",
        "forecast_cov_epsilon",
        "run_id",
    ]
    summary = (
        crps.groupby(group_cols, dropna=False)["crps"]
        .agg(n_days="count", mean_crps="mean", median_crps="median", min_crps="min", max_crps="max", sd_crps="std")
        .reset_index()
    )
    gate_cols = ["run_id", "eligible", "failure_reason", "run_status", "run_rdata_count"]
    summary = summary.merge(gates.loc[:, [c for c in gate_cols if c in gates.columns]], on="run_id", how="left")
    summary = summary.merge(authority, on="cutoff", how="left")
    summary["crps_delta_vs_authority"] = summary["mean_crps"] - summary["authority_mean_crps"]
    summary["improves_authority"] = summary["crps_delta_vs_authority"] < 0
    summary = summary.sort_values(["cutoff", "eligible", "mean_crps", "median_crps"], ascending=[True, False, True, True])

    winners = []
    for cutoff, group in summary.loc[summary["eligible"]].groupby("cutoff", dropna=False):
        ranked = group.sort_values(["mean_crps", "median_crps", "max_crps", "grid_spec_id"]).reset_index(drop=True)
        if ranked.empty:
            continue
        winner = ranked.iloc[0].to_dict()
        runner = ranked.iloc[1].to_dict() if len(ranked) > 1 else {}
        winner["rank"] = 1
        winner["runner_up_grid_spec_id"] = runner.get("grid_spec_id", "")
        winner["runner_up_mean_crps"] = runner.get("mean_crps", pd.NA)
        winner["eligible_specs_for_cutoff"] = int(len(ranked))
        winners.append(winner)
    winners_df = pd.DataFrame(winners)

    pooled = (
        summary.loc[summary["eligible"]]
        .groupby(["grid_spec_id", "discount_case_id", "epsilon_value"], dropna=False)
        .agg(
            eligible_cutoffs=("cutoff", "nunique"),
            mean_crps_pooled=("mean_crps", "mean"),
            median_crps_pooled=("mean_crps", "median"),
            worst_cutoff_mean_crps=("mean_crps", "max"),
            improved_cutoffs=("improves_authority", "sum"),
        )
        .reset_index()
        .sort_values(["eligible_cutoffs", "mean_crps_pooled"], ascending=[False, True])
    )
    return summary, winners_df, pooled


def write_report(out_dir: Path, gates: pd.DataFrame, summary: pd.DataFrame, winners: pd.DataFrame, pooled: pd.DataFrame) -> None:
    status_counts = gates["run_status"].astype(str).value_counts(dropna=False).to_dict() if "run_status" in gates else {}
    lines = [
        "# HE2 N-M-T1 Broad Screen Evaluation",
        "",
        f"- generated_at_utc: `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        f"- matrix rows: `{len(gates)}`",
        f"- eligible rows: `{int(gates['eligible'].sum()) if 'eligible' in gates else 0}`",
        f"- status counts: `{json.dumps(status_counts, sort_keys=True)}`",
        f"- target model: `{TARGET_MODEL_ID}`",
        f"- target score scale: `{TARGET_SCORE_SCALE}`",
        "",
        "## Winners By Cutoff",
        "",
    ]
    if winners.empty:
        lines.append("No eligible winners yet.")
    else:
        for _, row in winners.sort_values("cutoff").iterrows():
            lines.append(
                f"- `{row['cutoff']}`: `{row['grid_spec_id']}` mean_crps={float(row['mean_crps']):.6f}; "
                f"delta_vs_authority={float(row['crps_delta_vs_authority']):.6f}"
            )
    lines.extend(["", "## Output Tables", ""])
    for name in [
        "ndlm_main_keep_broad_screen_gate_summary.csv",
        "ndlm_main_keep_broad_screen_crps_per_time.csv",
        "ndlm_main_keep_broad_screen_crps_summary_by_spec_cutoff.csv",
        "ndlm_main_keep_broad_screen_winners_by_cutoff.csv",
        "ndlm_main_keep_broad_screen_pooled_summary.csv",
    ]:
        lines.append(f"- `{name}`")
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Evaluate completed HE2 N-M-T1 broad screen rows.")
    ap.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    ap.add_argument("--matrix-dir", default=str(DEFAULT_MATRIX_DIR))
    ap.add_argument("--authority-rows", default=str(DEFAULT_AUTHORITY_ROWS))
    ap.add_argument("--out-dir", default="")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    artifact_root = Path(args.artifact_root).expanduser().resolve()
    matrix_dir = Path(args.matrix_dir).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else ROOT / "reports" / f"he2_ndlm_main_keep_broad_screen_eval_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    plan = pd.read_csv(matrix_dir / "matrix_plan.csv", dtype=str)
    authority = load_authority(Path(args.authority_rows).expanduser().resolve())
    gates, crps = collect(plan, artifact_root)
    summary, winners, pooled = summarize(gates, crps, authority)

    gates.to_csv(out_dir / "ndlm_main_keep_broad_screen_gate_summary.csv", index=False)
    crps.to_csv(out_dir / "ndlm_main_keep_broad_screen_crps_per_time.csv", index=False)
    summary.to_csv(out_dir / "ndlm_main_keep_broad_screen_crps_summary_by_spec_cutoff.csv", index=False)
    winners.to_csv(out_dir / "ndlm_main_keep_broad_screen_winners_by_cutoff.csv", index=False)
    pooled.to_csv(out_dir / "ndlm_main_keep_broad_screen_pooled_summary.csv", index=False)
    write_report(out_dir, gates, summary, winners, pooled)

    print(f"out_dir={out_dir}")
    print(f"rows={len(gates)}")
    print(f"eligible={int(gates['eligible'].sum()) if 'eligible' in gates else 0}")
    print(f"winners={len(winners)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from multimodel_v8_lib import runs_dir  # noqa: E402
from run_multimodel_v8_queue import manifest_path_for, stage_status  # noqa: E402

DEFAULT_ARTIFACT_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524"
)
DEFAULT_MATRIX_DIR = DEFAULT_ARTIFACT_ROOT / "control" / "publication_relaunch_matrix"
TARGET_MODEL_ID = "exdqlm_multivar_synth_keep"
TARGET_SCORE_SCALE = "log_cms_plus1"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_csv_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def count_run_rdata(run_root: Path) -> int:
    if not run_root.exists():
        return 0
    return len(list(run_root.rglob("*.RData"))) + len(list(run_root.rglob("*.rda")))


def collect_run_stability_diagnostics(run_root: Path) -> dict[str, Any]:
    fit_root = run_root / "fit" / "exdqlm_multivar" / "keep"
    logs = sorted(fit_root.glob("q=*/logs/fit.log")) if fit_root.exists() else []
    counts = {
        "quantile_log_count": len(logs),
        "gamsig_rollback_count": 0,
        "gamsig_guard_count": 0,
        "latent_parameter_guard_count": 0,
        "pseudodata_guard_event_count": 0,
        "pseudodata_guard_fail_count": 0,
        "state_guard_count": 0,
        "near_zero_fallback_count": 0,
        "fatal_error_count": 0,
        "sampling_finalize_count": 0,
    }
    first_event = ""
    for log in logs:
        try:
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for line in lines:
            if "[gamsig_rollback]" in line:
                counts["gamsig_rollback_count"] += 1
                if not first_event:
                    first_event = f"{log.parent.parent.name}:{line}"
            if "[gamsig_guard]" in line:
                counts["gamsig_guard_count"] += 1
            if "[latent_parameter_guard]" in line:
                counts["latent_parameter_guard_count"] += 1
                if not first_event:
                    first_event = f"{log.parent.parent.name}:{line}"
            if "[pseudodata_guard]" in line and "policy" not in line:
                counts["pseudodata_guard_event_count"] += 1
                if not first_event:
                    first_event = f"{log.parent.parent.name}:{line}"
            if "[pseudodata_guard_fail]" in line or "[pseudodata_guard_violation]" in line:
                counts["pseudodata_guard_fail_count"] += 1
                if not first_event:
                    first_event = f"{log.parent.parent.name}:{line}"
            if "[state_guard]" in line:
                counts["state_guard_count"] += 1
            if "[gamsig_near_zero_fallback]" in line:
                counts["near_zero_fallback_count"] += 1
            if line.startswith("Error") or "Execution halted" in line or "Traceback (most recent call last)" in line:
                counts["fatal_error_count"] += 1
                if not first_event:
                    first_event = f"{log.parent.parent.name}:{line}"
            if "phase=sampling_finalize" in line:
                counts["sampling_finalize_count"] += 1

    manifest = load_yaml(run_root / "run_manifest.yaml")
    cleanup_after_post = ((manifest.get("rdata_cleanup") or {}).get("after_post") or {})
    rdata_count = count_run_rdata(run_root)
    cleanup_remaining = cleanup_after_post.get("remaining", pd.NA)
    cleanup_removed = cleanup_after_post.get("removed", pd.NA)
    cleanup_before = cleanup_after_post.get("before", pd.NA)
    cleanup_recorded = bool(cleanup_after_post)
    cleanup_ok = rdata_count == 0
    if cleanup_recorded and pd.notna(cleanup_remaining):
        try:
            cleanup_ok = cleanup_ok and int(cleanup_remaining) == 0
        except Exception:
            cleanup_ok = False

    hard_failures: list[str] = []
    if counts["fatal_error_count"] > 0:
        hard_failures.append("fatal_error")
    if counts["pseudodata_guard_fail_count"] > 0:
        hard_failures.append("pseudodata_guard_fail")
    if not cleanup_ok:
        hard_failures.append("rdata_not_cleaned")

    guarded = (
        counts["gamsig_rollback_count"] > 0
        or counts["latent_parameter_guard_count"] > 0
        or counts["pseudodata_guard_event_count"] > 0
    )
    if hard_failures:
        stability_status = "failed"
    elif guarded:
        stability_status = "guarded_pass"
    else:
        stability_status = "clean"

    warning_parts = []
    for key in [
        "gamsig_rollback_count",
        "latent_parameter_guard_count",
        "pseudodata_guard_event_count",
        "near_zero_fallback_count",
    ]:
        if counts[key] > 0:
            warning_parts.append(f"{key}={counts[key]}")

    return {
        **counts,
        "run_rdata_count": rdata_count,
        "rdata_cleanup_recorded": cleanup_recorded,
        "rdata_cleanup_after_post_before": cleanup_before,
        "rdata_cleanup_after_post_removed": cleanup_removed,
        "rdata_cleanup_after_post_remaining": cleanup_remaining,
        "rdata_cleanup_ok": cleanup_ok,
        "stability_status": stability_status,
        "stability_gate_ok": not hard_failures,
        "stability_warning": ";".join(warning_parts),
        "stability_failure_reason": ";".join(hard_failures),
        "first_guard_event": first_event,
    }


def output_root(artifact_root: Path, run_id: str) -> Path:
    return runs_dir(artifact_root) / run_id / "post" / "outputs" / run_id


def add_metadata(df: pd.DataFrame, row: pd.Series, source_path: Path) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    for col in [
        "cutoff",
        "grid_spec_id",
        "discount_case_id",
        "epsilon_value",
        "forecast_cov_epsilon",
        "c_factor",
        "df_t",
        "df_s1",
        "df_s2",
        "df_s67",
        "df_discrep",
        "lambda",
        "df_trans",
        "df_covs",
        "run_id",
    ]:
        if col in row.index:
            out[col] = row[col]
    out["source_path"] = str(source_path)
    return out


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "t", "1", "yes", "y", "pass"}


def component_contract_pass(df: pd.DataFrame) -> tuple[bool, str]:
    if df.empty:
        return False, "missing component contract"
    row = df.iloc[0]
    checks = {
        "transfer_mode_keep": str(row.get("transfer_mode", "")) == "keep",
        "forecast_has_transfer": truthy(row.get("forecast_has_transfer", False)),
        "positive_forecast_rows": float(row.get("n_forecast_rows", 0) or 0) > 0,
        "finite_zeta_forecast": float(row.get("finite_zeta_forecast", 0) or 0) > 0,
        "finite_mu_without_transfer_forecast": float(row.get("finite_mu_without_transfer_forecast", 0) or 0) > 0,
    }
    failed = [name for name, ok in checks.items() if not ok]
    return not failed, ";".join(failed)


def quantile_synthesis_pass(df: pd.DataFrame, tol: float = 1e-12) -> tuple[bool, str]:
    if df.empty:
        return False, "missing quantile synthesis summary"
    failed: list[str] = []
    for col in ["anchor_curve_crossing_share", "empirical_curve_crossing_share"]:
        if col not in df.columns:
            failed.append(f"missing {col}")
            continue
        vals = pd.to_numeric(df[col], errors="coerce")
        if vals.isna().any() or (vals.abs() > tol).any():
            failed.append(f"{col}>tol")
    return not failed, ";".join(failed)


def synth_health_pass(df: pd.DataFrame) -> tuple[bool, str]:
    if df.empty:
        return False, "missing input health"
    subset = df.loc[df.get("model_id", pd.Series(dtype=str)).astype(str) == TARGET_MODEL_ID].copy()
    if subset.empty:
        return False, "missing synth input-health row"
    if "status" not in subset.columns:
        return False, "missing synth input-health status"
    bad = subset.loc[subset["status"].astype(str).str.lower() != "pass"]
    if not bad.empty:
        return False, "synth input-health status not pass"
    return True, ""


def build_gate_summary(plan: pd.DataFrame, artifact_root: Path) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    gate_rows: list[dict[str, Any]] = []
    tables: dict[str, list[pd.DataFrame]] = {
        "crps_per_time": [],
        "input_health": [],
        "quantile_synthesis": [],
        "component_contract": [],
        "trace_health": [],
        "stability_diagnostics": [],
    }
    for _, row in plan.iterrows():
        run_id = str(row["run_id"])
        run_root = runs_dir(artifact_root) / run_id
        out_root = output_root(artifact_root, run_id)
        phase, status = stage_status(manifest_path_for(run_id, artifact_root))
        stability = collect_run_stability_diagnostics(run_root)
        tables["stability_diagnostics"].append(add_metadata(pd.DataFrame([stability]), row, run_root / "run_manifest.yaml"))
        post_summary = load_json(out_root / "post_artifacts_summary.json")
        contract = post_summary.get("contract", {}) if isinstance(post_summary.get("contract"), dict) else {}
        post_contract_ok = bool(contract.get("status", False))

        crps_path = out_root / "tables" / "crps_forecast_per_time.csv"
        crps = read_csv_optional(crps_path)
        tables["crps_per_time"].append(add_metadata(crps, row, crps_path))
        synth_crps = crps.loc[
            (crps.get("model_id", pd.Series(dtype=str)).astype(str) == TARGET_MODEL_ID)
            & (crps.get("score_scale", pd.Series(dtype=str)).astype(str) == TARGET_SCORE_SCALE)
        ].copy() if not crps.empty else pd.DataFrame()

        health_path = out_root / "tables" / "crps_input_health.csv"
        health = read_csv_optional(health_path)
        tables["input_health"].append(add_metadata(health, row, health_path))
        health_ok, health_reason = synth_health_pass(health)

        synth_path = out_root / f"{TARGET_MODEL_ID}_forecast_quantile_synthesis_summary.csv"
        synth = read_csv_optional(synth_path)
        tables["quantile_synthesis"].append(add_metadata(synth, row, synth_path))
        synth_ok, synth_reason = quantile_synthesis_pass(synth)

        component_path = out_root / "multivar_transfer_contract_q50.csv"
        component = read_csv_optional(component_path)
        tables["component_contract"].append(add_metadata(component, row, component_path))
        component_ok, component_reason = component_contract_pass(component)

        trace_path = out_root / "multivar_trace_summary_q50.csv"
        trace = read_csv_optional(trace_path)
        tables["trace_health"].append(add_metadata(trace, row, trace_path))

        failures = []
        if status != "pass":
            failures.append(f"run_status={phase}/{status}")
        if not post_contract_ok:
            failures.append("post_contract")
        if synth_crps.empty:
            failures.append("missing_synth_crps")
        if not health_ok:
            failures.append(health_reason)
        if not synth_ok:
            failures.append(synth_reason)
        if not component_ok:
            failures.append(component_reason)
        if trace.empty:
            failures.append("missing_trace_q50")
        if not bool(stability["stability_gate_ok"]):
            failures.append(stability["stability_failure_reason"])

        gate = row.to_dict()
        gate.update({
            "run_phase": phase,
            "run_status": status,
            "post_output_root": str(out_root),
            "post_contract_ok": post_contract_ok,
            "synth_crps_rows": int(len(synth_crps)),
            "input_health_ok": health_ok,
            "quantile_synthesis_ok": synth_ok,
            "component_contract_ok": component_ok,
            "trace_q50_present": not trace.empty,
            **stability,
            "eligible": len(failures) == 0,
            "failure_reason": "|".join([f for f in failures if f]),
        })
        gate_rows.append(gate)

    frames = {
        name: pd.concat([df for df in dfs if not df.empty], ignore_index=True) if any(not df.empty for df in dfs) else pd.DataFrame()
        for name, dfs in tables.items()
    }
    return pd.DataFrame(gate_rows), frames


def summarize_crps(crps: pd.DataFrame, gates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if crps.empty:
        empty = pd.DataFrame()
        return empty, empty, empty
    target = crps.loc[
        (crps["model_id"].astype(str) == TARGET_MODEL_ID)
        & (crps["score_scale"].astype(str) == TARGET_SCORE_SCALE)
    ].copy()
    if target.empty:
        empty = pd.DataFrame()
        return empty, empty, empty
    target["crps"] = pd.to_numeric(target["crps"], errors="coerce")
    group_cols = [
        "cutoff",
        "grid_spec_id",
        "discount_case_id",
        "epsilon_value",
        "forecast_cov_epsilon",
        "c_factor",
        "df_t",
        "df_s1",
        "df_s2",
        "df_s67",
        "df_discrep",
        "lambda",
        "df_trans",
        "df_covs",
        "run_id",
    ]
    summary = (
        target.groupby(group_cols, dropna=False)["crps"]
        .agg(n_days="count", mean_crps="mean", median_crps="median", min_crps="min", max_crps="max", sd_crps="std")
        .reset_index()
    )
    eligible_cols = [
        "run_id",
        "eligible",
        "failure_reason",
        "stability_status",
        "stability_warning",
        "stability_failure_reason",
        "gamsig_rollback_count",
        "latent_parameter_guard_count",
        "pseudodata_guard_event_count",
        "pseudodata_guard_fail_count",
        "fatal_error_count",
        "run_rdata_count",
        "rdata_cleanup_ok",
    ]
    eligible = gates.loc[:, [col for col in eligible_cols if col in gates.columns]].drop_duplicates()
    summary = summary.merge(eligible, on="run_id", how="left")
    summary["eligible"] = summary["eligible"].fillna(False).astype(bool)
    stability_rank = {"clean": 0, "guarded_pass": 1, "failed": 9}
    summary["selection_tier"] = summary["stability_status"].map(stability_rank).fillna(9).astype(int)
    summary = summary.sort_values(
        ["cutoff", "eligible", "selection_tier", "mean_crps", "median_crps", "max_crps"],
        ascending=[True, False, True, True, True, True],
    )

    winners = []
    for cutoff, group in summary.loc[summary["eligible"]].groupby("cutoff", dropna=False):
        ranked = group.sort_values(["selection_tier", "mean_crps", "median_crps", "max_crps", "grid_spec_id"]).reset_index(drop=True)
        if ranked.empty:
            continue
        winner = ranked.iloc[0].to_dict()
        runner = ranked.iloc[1].to_dict() if len(ranked) > 1 else {}
        winner.update({
            "rank": 1,
            "runner_up_grid_spec_id": runner.get("grid_spec_id", ""),
            "runner_up_mean_crps": runner.get("mean_crps", pd.NA),
            "winner_runner_abs_diff": (runner.get("mean_crps", pd.NA) - winner["mean_crps"]) if runner else pd.NA,
            "eligible_specs_for_cutoff": int(len(ranked)),
        })
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
        )
        .reset_index()
        .sort_values(["eligible_cutoffs", "mean_crps_pooled"], ascending=[False, True])
    )
    return summary, winners_df, pooled


def maybe_write_figures(out_dir: Path, summary: pd.DataFrame, winners: pd.DataFrame) -> None:
    if summary.empty:
        return
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    eligible = summary.loc[summary["eligible"]].copy()
    if eligible.empty:
        return
    pivot = eligible.pivot_table(index="cutoff", columns="grid_spec_id", values="mean_crps", aggfunc="mean")
    if not pivot.empty:
        fig, ax = plt.subplots(figsize=(max(10, 0.35 * len(pivot.columns)), 4.5))
        im = ax.imshow(pivot.values, aspect="auto")
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns, rotation=90, fontsize=7)
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index)
        ax.set_title("Mean forecast-window CRPS by cutoff/spec")
        fig.colorbar(im, ax=ax, label="mean CRPS")
        fig.tight_layout()
        fig.savefig(fig_dir / "grid_mean_crps_heatmap.png", dpi=180)
        plt.close(fig)
    if not winners.empty and "winner_runner_abs_diff" in winners.columns:
        fig, ax = plt.subplots(figsize=(7, 4))
        plot_df = winners.sort_values("cutoff")
        ax.bar(plot_df["cutoff"].astype(str), pd.to_numeric(plot_df["winner_runner_abs_diff"], errors="coerce"))
        ax.set_title("Winner vs runner-up mean CRPS gap")
        ax.set_ylabel("runner-up - winner")
        ax.tick_params(axis="x", rotation=30)
        fig.tight_layout()
        fig.savefig(fig_dir / "winner_runner_crps_gap.png", dpi=180)
        plt.close(fig)


def write_report(out_dir: Path, gates: pd.DataFrame, summary: pd.DataFrame, winners: pd.DataFrame, pooled: pd.DataFrame) -> None:
    eligible_count = int(gates["eligible"].sum()) if "eligible" in gates else 0
    stability_counts = (
        gates["stability_status"].astype(str).value_counts(dropna=False).to_dict()
        if "stability_status" in gates
        else {}
    )
    stability_text = ", ".join(f"{k}={v}" for k, v in sorted(stability_counts.items())) or "none"
    lines = [
        "# HE2 exDQLM Multivar Keep Grid Evaluation",
        "",
        f"- generated_at_utc: `{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}`",
        f"- run rows evaluated: `{len(gates)}`",
        f"- eligible rows: `{eligible_count}`",
        f"- failed/ineligible rows: `{len(gates) - eligible_count}`",
        f"- stability statuses: `{stability_text}`",
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
                f"- `{row['cutoff']}`: `{row['grid_spec_id']}` mean_crps={float(row['mean_crps']):.6f}, "
                f"runner_up=`{row.get('runner_up_grid_spec_id', '')}`"
            )
    lines.extend(["", "## Outputs", ""])
    for name in [
        "grid_artifact_gate_summary.csv",
        "grid_crps_per_time.csv",
        "grid_crps_summary_by_spec_cutoff.csv",
        "grid_crps_winners_by_cutoff.csv",
        "grid_crps_summary_by_spec_pooled.csv",
        "grid_stability_diagnostics.csv",
        "grid_guarded_candidate_log.csv",
        "grid_failure_log.csv",
    ]:
        lines.append(f"- `{name}`")
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Evaluate HE2 exDQLM multivar keep epsilon/discount grid outputs.")
    ap.add_argument("--matrix-dir", default=str(DEFAULT_MATRIX_DIR))
    ap.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    ap.add_argument("--out-dir", default="")
    ap.add_argument("--tag", default="")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    matrix_dir = Path(args.matrix_dir).expanduser().resolve()
    artifact_root = Path(args.artifact_root).expanduser().resolve()
    tag = args.tag.strip() or utc_stamp()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else ROOT / "reports" / f"exdqlm_multivar_keep_grid_eval_{tag}"
    out_dir.mkdir(parents=True, exist_ok=True)

    plan = pd.read_csv(matrix_dir / "matrix_plan.csv", dtype=str)
    gates, tables = build_gate_summary(plan, artifact_root)
    crps = tables["crps_per_time"]
    summary, winners, pooled = summarize_crps(crps, gates)

    gates.to_csv(out_dir / "grid_artifact_gate_summary.csv", index=False)
    crps.to_csv(out_dir / "grid_crps_per_time.csv", index=False)
    summary.to_csv(out_dir / "grid_crps_summary_by_spec_cutoff.csv", index=False)
    winners.to_csv(out_dir / "grid_crps_winners_by_cutoff.csv", index=False)
    pooled.to_csv(out_dir / "grid_crps_summary_by_spec_pooled.csv", index=False)
    tables["input_health"].to_csv(out_dir / "grid_input_health_summary.csv", index=False)
    tables["quantile_synthesis"].to_csv(out_dir / "grid_quantile_synthesis_summary.csv", index=False)
    tables["component_contract"].to_csv(out_dir / "grid_component_contract_summary.csv", index=False)
    tables["trace_health"].to_csv(out_dir / "grid_trace_health_summary.csv", index=False)
    tables["stability_diagnostics"].to_csv(out_dir / "grid_stability_diagnostics.csv", index=False)
    gates.loc[~gates["eligible"]].to_csv(out_dir / "grid_failure_log.csv", index=False)
    gates.loc[
        gates["eligible"] & gates["stability_status"].astype(str).eq("guarded_pass")
    ].to_csv(out_dir / "grid_guarded_candidate_log.csv", index=False)
    maybe_write_figures(out_dir, summary, winners)
    write_report(out_dir, gates, summary, winners, pooled)

    print(f"out_dir={out_dir}")
    print(f"rows={len(gates)}")
    print(f"eligible={int(gates['eligible'].sum()) if 'eligible' in gates else 0}")
    print(f"winners={len(winners)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

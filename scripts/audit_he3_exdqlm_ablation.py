#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from he3_exdqlm_ablation_lib import (
    HE3_REPORT_DIR_DEFAULT,
    build_status_frame,
    crps_summary_path,
    deep_merge,
    read_model_mean_crps,
)
from multimodel_v8_lib import load_yaml

DEFAULT_STRUCTURE = {
    "include_trend": True,
    "enabled_harmonic_indices": [1, 2, 3],
}

SCIENTIFIC_INVARIANT_PATHS: list[tuple[str, ...]] = [
    ("models", "exdqlm_multivar", "state_evolution"),
    ("fit", "exdqlm_multivar", "gamma_sigma"),
    ("fit", "exdqlm_multivar", "legacy", "lam1"),
    ("fit", "exdqlm_multivar", "legacy", "lam2"),
    ("fit", "exdqlm_multivar", "legacy", "n_samp"),
    ("fit", "exdqlm_multivar", "legacy", "sims_enabled"),
    ("fit", "exdqlm_multivar", "legacy", "forecast_cov"),
]

EXECUTION_PATHS: list[tuple[str, ...]] = [
    ("run", "threads"),
    ("fit", "parallel"),
]

RUNTIME_HASH_PATHS = [
    "inputs/shared/covariates/covariate_features.csv",
    "inputs/shared/covariates/cov_01_PPT.csv",
    "inputs/shared/covariates/cov_02_SOIL.csv",
    "inputs/shared/covariates/cov_03_PCA.csv",
    "fit/inputs/parameters.txt",
    "fit/inputs/retros_fit_adapter.csv",
    "fit/inputs/nws_fit_adapter.csv",
    "fit/inputs/glofas_fit_adapter.csv",
]

LEAD_BUCKETS = [
    ("lead_01_07", 1, 7),
    ("lead_08_14", 8, 14),
    ("lead_15_21", 15, 21),
    ("lead_22_28", 22, 28),
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Audit HE3 ablation inheritance and runtime inputs.")
    ap.add_argument("--matrix-dir", required=True)
    ap.add_argument("--output-dir", default=None)
    ap.add_argument(
        "--best-by-cutoff-csv",
        default=None,
        help="Optional override for the HE2 best-by-cutoff file used for noTF/T0 comparison.",
    )
    return ap.parse_args()


def get_in(mapping: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def normalize_structure(cfg: dict[str, Any]) -> dict[str, Any]:
    structure = get_in(cfg, ("models", "exdqlm_multivar", "structure"), {}) or {}
    return {
        "include_trend": bool(structure.get("include_trend", DEFAULT_STRUCTURE["include_trend"])),
        "enabled_harmonic_indices": [
            int(x)
            for x in structure.get(
                "enabled_harmonic_indices",
                DEFAULT_STRUCTURE["enabled_harmonic_indices"],
            )
        ],
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare_runtime_hashes(source_run_dir: Path, run_dir: Path) -> tuple[bool, list[str]]:
    mismatches: list[str] = []
    for rel_path in RUNTIME_HASH_PATHS:
        source_path = source_run_dir / rel_path
        run_path = run_dir / rel_path
        if not source_path.exists() or not run_path.exists():
            mismatches.append(f"missing:{rel_path}")
            continue
        if sha256_file(source_path) != sha256_file(run_path):
            mismatches.append(f"hash:{rel_path}")
    return not mismatches, mismatches


def compare_paths(
    source_cfg: dict[str, Any],
    ablation_cfg: dict[str, Any],
    paths: list[tuple[str, ...]],
) -> tuple[bool, list[str]]:
    mismatches: list[str] = []
    for path in paths:
        src_value = get_in(source_cfg, path)
        abl_value = get_in(ablation_cfg, path)
        if src_value != abl_value:
            mismatches.append(".".join(path))
    return not mismatches, mismatches


def compare_forecast_health(
    source_cfg: dict[str, Any],
    ablation_cfg: dict[str, Any],
    variant: str,
) -> tuple[bool, list[str]]:
    source_health = get_in(source_cfg, ("fit", "exdqlm_multivar", "forecast_health"), {}) or {}
    ablation_health = get_in(ablation_cfg, ("fit", "exdqlm_multivar", "forecast_health"), {}) or {}
    overrides = get_in(ablation_cfg, ("he3_ablation", "forecast_health_overrides"), {}) or {}
    mismatches: list[str] = []
    if not isinstance(overrides, dict):
        mismatches.append("fit.exdqlm_multivar.forecast_health:override_not_mapping")
        overrides = {}
    if overrides and variant != "noTF":
        mismatches.append("fit.exdqlm_multivar.forecast_health:override_not_allowed")
    if variant == "noTF" and overrides not in ({}, {"fail_fast": False}):
        mismatches.append("fit.exdqlm_multivar.forecast_health:unexpected_noTF_override")
    expected_health = deep_merge(source_health, overrides)
    if ablation_health != expected_health:
        mismatches.append("fit.exdqlm_multivar.forecast_health")
    return not mismatches, mismatches


def target_model_present(run_dir: Path, target_model_id: str) -> tuple[bool, float | None]:
    summary_csv = crps_summary_path(run_dir)
    if not summary_csv.exists():
        return False, None
    try:
        mean_crps = read_model_mean_crps(summary_csv, target_model_id)
    except Exception:
        return False, None
    return True, mean_crps


def read_leadwise_crps(run_dir: Path, target_model_id: str) -> pd.DataFrame:
    per_time_csv = run_dir / "post" / "outputs" / run_dir.name / "tables" / "crps_forecast_per_time.csv"
    df = pd.read_csv(per_time_csv)
    df = df[df["model_id"] == target_model_id].copy()
    grouped = df.groupby("lead_day", as_index=False)["crps"].mean()
    return grouped.sort_values("lead_day").reset_index(drop=True)


def bucketize_leads(df: pd.DataFrame, value_col: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for label, lo, hi in LEAD_BUCKETS:
        subset = df[(df["lead_day"] >= lo) & (df["lead_day"] <= hi)]
        result[label] = float(subset[value_col].mean()) if not subset.empty else float("nan")
    return result


def render_markdown(audit_df: pd.DataFrame, lead_df: pd.DataFrame) -> str:
    lines = [
        "# HE3 ablation audit",
        "",
        "This audit checks that each launched HE3 ablation row is a structural simplification",
        "of the cutoff-specific winning full model rather than a different data/configuration run.",
        "",
        "## Launch-row audit",
        "",
        "| Cutoff | Variant | Config inheritance | Runtime input hashes | Target model id | Overall | Mean CRPS | Delta vs full | Delta vs HE2 drop | Notes |",
        "|---|---|---|---|---|---|---:|---:|---:|---|",
    ]
    for _, row in audit_df.iterrows():
        delta_drop = ""
        if pd.notna(row["delta_vs_he2_drop"]):
            delta_drop = f"{row['delta_vs_he2_drop']:.6f}"
        lines.append(
            f"| {row['cutoff_display']} | `{row['variant']}` | `{row['config_ok']}` | "
            f"`{row['runtime_hashes_ok']}` | `{row['target_model_ok']}` | `{row['overall_ok']}` | "
            f"{row['mean_crps']:.6f} | {row['delta_vs_full']:.6f} | {delta_drop} | {row['notes']} |"
        )
    lines.extend(
        [
            "",
            "## Lead-bucket diagnostics",
            "",
            "The table below summarizes mean lead-wise CRPS over four lead buckets.",
            "This helps distinguish a true performance degradation from a malformed run.",
            "",
        ]
    )
    for cutoff, cutoff_df in lead_df.groupby("cutoff", sort=False):
        display = cutoff_df["cutoff_display"].iloc[0]
        lines.append(f"### Cutoff {display}")
        lines.append("")
        lines.append("| Variant | 01-07 | 08-14 | 15-21 | 22-28 |")
        lines.append("|---|---:|---:|---:|---:|")
        for _, row in cutoff_df.iterrows():
            lines.append(
                f"| `{row['variant']}` | {row['lead_01_07']:.3f} | {row['lead_08_14']:.3f} | "
                f"{row['lead_15_21']:.3f} | {row['lead_22_28']:.3f} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    matrix_dir = Path(args.matrix_dir).resolve()
    metadata = load_yaml(matrix_dir / "matrix_metadata.yaml")
    artifact_root = Path(metadata["artifact_root"]).resolve()
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else artifact_root / "reports" / "he3_exdqlm_ablation" / "audit"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    plan = pd.read_csv(matrix_dir / "matrix_plan.csv")
    status = build_status_frame(plan, artifact_root)
    merged = plan.merge(
        status.loc[:, ["run_id", "variant", "status"]],
        on=["run_id", "variant"],
        how="left",
    )
    launch_rows = merged[merged["launch_mode"] == "launch"].copy()

    best_by_cutoff_csv = (
        Path(args.best_by_cutoff_csv).resolve()
        if args.best_by_cutoff_csv
        else Path(metadata["best_by_cutoff_csv"]).resolve()
    )
    best_targets = pd.read_csv(best_by_cutoff_csv)
    best_targets["cutoff"] = best_targets["cutoff"].astype(str).str.zfill(8)
    drop_targets = best_targets[best_targets["model_variant"] == "exdqlm_multivar_drop"].copy()
    drop_targets = drop_targets.loc[:, ["cutoff", "forecast_window_crps"]].rename(
        columns={"forecast_window_crps": "he2_drop_best_crps"}
    )

    audit_rows: list[dict[str, Any]] = []
    lead_rows: list[dict[str, Any]] = []

    for _, row in launch_rows.iterrows():
        source_cfg = load_yaml(Path(str(row["source_config_path"])))
        ablation_cfg = load_yaml(Path(str(row["config_path"])))
        run_dir = artifact_root / "runs" / str(row["run_id"])
        source_run_dir = Path(str(row["source_run_dir"]))

        structure = normalize_structure(ablation_cfg)
        structure_ok = (
            structure["include_trend"] == bool(row["include_trend"])
            and structure["enabled_harmonic_indices"]
            == [int(x) for x in str(row["enabled_harmonic_indices"]).split(",") if str(x).strip()]
        )
        transfer_ok = get_in(ablation_cfg, ("models", "exdqlm_multivar", "forecast_transfer_mode")) == str(
            row["forecast_transfer_mode"]
        )
        covariate_ok = bool(
            get_in(ablation_cfg, ("fit", "exdqlm_multivar", "legacy", "use_covariates"))
        ) == bool(row["use_covariates"])
        scientific_ok, scientific_mismatches = compare_paths(source_cfg, ablation_cfg, SCIENTIFIC_INVARIANT_PATHS)
        forecast_health_ok, forecast_health_mismatches = compare_forecast_health(
            source_cfg,
            ablation_cfg,
            str(row["variant"]),
        )
        scientific_ok = scientific_ok and forecast_health_ok
        scientific_mismatches.extend(forecast_health_mismatches)
        execution_ok, execution_mismatches = compare_paths(source_cfg, ablation_cfg, EXECUTION_PATHS)
        runtime_hashes_ok, runtime_mismatches = compare_runtime_hashes(source_run_dir, run_dir)
        target_ok, mean_crps = target_model_present(run_dir, str(row["target_model_id"]))
        overall_ok = (
            structure_ok
            and transfer_ok
            and covariate_ok
            and scientific_ok
            and runtime_hashes_ok
            and target_ok
        )
        note_parts: list[str] = []
        if not structure_ok:
            note_parts.append("structure")
        if not transfer_ok:
            note_parts.append("transfer_mode")
        if not covariate_ok:
            note_parts.append("use_covariates")
        if scientific_mismatches:
            note_parts.append("config:" + ",".join(scientific_mismatches))
        if execution_mismatches:
            note_parts.append("exec:" + ",".join(execution_mismatches))
        if runtime_mismatches:
            note_parts.append("inputs:" + ",".join(runtime_mismatches))
        if not target_ok:
            note_parts.append("target_model_id")
        notes = "; ".join(note_parts) if note_parts else "ok"

        delta_vs_he2_drop = None
        he2_drop_best_crps = None
        drop_match = drop_targets[drop_targets["cutoff"].astype(str).str.zfill(8) == str(row["cutoff"]).zfill(8)]
        if not drop_match.empty and mean_crps is not None:
            he2_drop_best_crps = float(drop_match["he2_drop_best_crps"].iloc[0])
            if str(row["variant"]) == "noTF":
                delta_vs_he2_drop = float(mean_crps) - he2_drop_best_crps

        audit_rows.append(
            {
                "cutoff": str(row["cutoff"]).zfill(8),
                "cutoff_display": str(row["cutoff_display"]),
                "variant": str(row["variant"]),
                "run_id": str(row["run_id"]),
                "status": str(row["status"]),
                "config_ok": structure_ok and transfer_ok and covariate_ok and scientific_ok,
                "execution_ok": execution_ok,
                "runtime_hashes_ok": runtime_hashes_ok,
                "target_model_ok": target_ok,
                "overall_ok": overall_ok,
                "mean_crps": float(mean_crps) if mean_crps is not None else float("nan"),
                "delta_vs_full": float(mean_crps) - float(row["source_full_crps"]) if mean_crps is not None else float("nan"),
                "he2_drop_best_crps": he2_drop_best_crps,
                "delta_vs_he2_drop": delta_vs_he2_drop,
                "notes": notes,
            }
        )

        if target_ok:
            lead_df = read_leadwise_crps(run_dir, str(row["target_model_id"]))
            bucket_values = bucketize_leads(lead_df, "crps")
            lead_rows.append(
                {
                    "cutoff": str(row["cutoff"]).zfill(8),
                    "cutoff_display": str(row["cutoff_display"]),
                    "variant": str(row["variant"]),
                    **bucket_values,
                }
            )

    audit_df = pd.DataFrame(audit_rows).sort_values(["cutoff", "variant"]).reset_index(drop=True)
    lead_df = pd.DataFrame(lead_rows).sort_values(["cutoff", "variant"]).reset_index(drop=True)

    full_rows = merged[merged["variant"] == "full"].copy()
    for _, row in full_rows.iterrows():
        run_dir = Path(str(row["source_run_dir"]))
        target_ok, mean_crps = target_model_present(run_dir, str(row["target_model_id"]))
        if target_ok:
            leadwise = read_leadwise_crps(run_dir, str(row["target_model_id"]))
            lead_rows.append(
                {
                    "cutoff": str(row["cutoff"]).zfill(8),
                    "cutoff_display": str(row["cutoff_display"]),
                    "variant": "full",
                    **bucketize_leads(leadwise, "crps"),
                }
            )
    lead_df = pd.DataFrame(lead_rows).sort_values(["cutoff", "variant"]).reset_index(drop=True)

    audit_df.to_csv(output_dir / "he3_ablation_audit.csv", index=False)
    lead_df.to_csv(output_dir / "he3_ablation_lead_buckets.csv", index=False)
    (output_dir / "he3_ablation_audit.md").write_text(render_markdown(audit_df, lead_df), encoding="utf-8")
    (output_dir / "he3_ablation_audit.json").write_text(
        json.dumps(
            {
                "audit_rows": audit_df.to_dict(orient="records"),
                "lead_bucket_rows": lead_df.to_dict(orient="records"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(output_dir / "he3_ablation_audit.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

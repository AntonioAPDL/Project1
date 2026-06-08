#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from multimodel_v8_lib import ROOT, ensure_dir, load_yaml, write_yaml

PROJECT_RUNTIME_ROOT = ROOT.parent / "project1_ucsc_phd_runtime"
CF1_SWEEP_ROOT_DEFAULT = PROJECT_RUNTIME_ROOT / "multimodel_v8_featurecov_cf1_eps_sweep_20260416"
BEST_BY_CUTOFF_CSV_DEFAULT = (
    CF1_SWEEP_ROOT_DEFAULT
    / "reports"
    / "final_featurecov_cf1_eps_analysis"
    / "best_by_cutoff_long.csv"
)
HE3_ARTIFACT_ROOT_DEFAULT = PROJECT_RUNTIME_ROOT / "multimodel_v8_he3_exdqlm_ablation_20260420"
HE3_MATRIX_DIR_DEFAULT = HE3_ARTIFACT_ROOT_DEFAULT / "control" / "he3_exdqlm_ablation_v1"
HE3_REPORT_DIR_DEFAULT = HE3_ARTIFACT_ROOT_DEFAULT / "reports" / "he3_exdqlm_ablation"
HE3_CONFIG_OUTPUT_DIR_DEFAULT = ROOT / "config" / "unified_runs_he3_exdqlm_ablation_20260420"
HE3_TEMPLATE_DEFAULT = ROOT / "config" / "multimodel_v8_he3_exdqlm_ablation.template.yaml"

SOURCE_MODEL_VARIANT = "exdqlm_multivar_keep"
SOURCE_INTERNAL_MODEL_ID = "exdqlm_multivar_synth_keep"
TARGET_MODEL_ID_KEEP = "exdqlm_multivar_synth_keep"
TARGET_MODEL_ID_DROP = "exdqlm_multivar_synth_drop"
HEAVY_CUTOFF = "20221225"
STAGE_ORDER = ["forecats", "data_prep_shared", "fit", "post", "validate", "report"]


@dataclass(frozen=True)
class VariantSpec:
    key: str
    manuscript_label: str
    reuse_reference: bool
    include_trend: bool
    enabled_harmonic_indices: tuple[int, ...]
    use_covariates: bool
    forecast_transfer_mode: str
    forecast_health_overrides: dict[str, Any]

    @property
    def target_model_id(self) -> str:
        return TARGET_MODEL_ID_DROP if self.forecast_transfer_mode == "drop" else TARGET_MODEL_ID_KEEP


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cutoff_to_display(cutoff: str) -> str:
    return datetime.strptime(str(cutoff), "%Y%m%d").strftime("%m/%d/%Y")


def load_template(path: Path) -> dict[str, Any]:
    return load_yaml(path)


def load_variant_specs(template_cfg: dict[str, Any]) -> list[VariantSpec]:
    variants_cfg = template_cfg.get("variants", {})
    if not isinstance(variants_cfg, dict) or not variants_cfg:
        raise ValueError("Template must define at least one HE3 variant.")
    specs: list[VariantSpec] = []
    for key, raw in variants_cfg.items():
        if not isinstance(raw, dict) or not bool(raw.get("enabled", True)):
            continue
        harmonic_indices = tuple(int(x) for x in raw.get("enabled_harmonic_indices", [1, 2, 3]))
        forecast_transfer_mode = str(raw.get("forecast_transfer_mode", "keep")).strip().lower() or "keep"
        if forecast_transfer_mode not in {"keep", "drop"}:
            raise ValueError(f"Unsupported forecast_transfer_mode for variant={key}: {forecast_transfer_mode}")
        forecast_health_overrides = raw.get("forecast_health", {}) or {}
        if not isinstance(forecast_health_overrides, dict):
            raise ValueError(f"variants.{key}.forecast_health must be a mapping when provided.")
        specs.append(
            VariantSpec(
                key=str(key),
                manuscript_label=str(raw.get("manuscript_label", key)),
                reuse_reference=bool(raw.get("reuse_reference", False)),
                include_trend=bool(raw.get("include_trend", True)),
                enabled_harmonic_indices=harmonic_indices,
                use_covariates=bool(raw.get("use_covariates", True)),
                forecast_transfer_mode=forecast_transfer_mode,
                forecast_health_overrides=dict(forecast_health_overrides),
            )
        )
    if not specs:
        raise ValueError("No enabled HE3 variants found in template.")
    return specs


def source_run_id(cutoff: str, epsilon_label: str) -> str:
    return f"multimodel_{cutoff}_v8_{epsilon_label}_exdqlm_multivar_keep_featurecov_cf1"


def he3_run_id(cutoff: str, epsilon_label: str, variant_key: str) -> str:
    return f"multimodel_{cutoff}_v8_{epsilon_label}_exdqlm_multivar_keep_he3_{variant_key}"


def source_config_path(cf1_config_dir: Path, cutoff: str, epsilon_label: str) -> Path:
    return cf1_config_dir / f"{source_run_id(cutoff, epsilon_label)}.yaml"


def source_run_dir(cf1_sweep_root: Path, cutoff: str, epsilon_label: str) -> Path:
    return cf1_sweep_root / "runs" / source_run_id(cutoff, epsilon_label)


def load_best_targets(best_by_cutoff_csv: Path, selected_model_variant: str = SOURCE_MODEL_VARIANT) -> pd.DataFrame:
    df = pd.read_csv(best_by_cutoff_csv)
    rows = df[df["model_variant"] == selected_model_variant].copy()
    if rows.empty:
        raise ValueError(
            f"No rows found for selected_model_variant={selected_model_variant} in {best_by_cutoff_csv}"
        )
    rows["cutoff"] = rows["cutoff"].astype(str).str.zfill(8)
    rows["best_epsilon_label"] = rows["best_epsilon_label"].astype(str)
    rows["forecast_window_crps"] = pd.to_numeric(rows["forecast_window_crps"])
    rows["best_c_factor"] = pd.to_numeric(rows["best_c_factor"])
    rows["cutoff_display"] = rows["cutoff"].map(cutoff_to_display)
    rows = rows.sort_values("cutoff").reset_index(drop=True)
    return rows


def stage_status(manifest_path: Path) -> tuple[str, str]:
    if not manifest_path.exists():
        return "not_started", "not_started"
    manifest = load_yaml(manifest_path)
    stages = manifest.get("stages", {}) if isinstance(manifest, dict) else {}
    for stage in STAGE_ORDER:
        entry = stages.get(stage, {}) if isinstance(stages, dict) else {}
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status", "")).strip().lower()
        if status in {"pending", "fail"}:
            return stage, status
    report_entry = stages.get("report", {}) if isinstance(stages, dict) else {}
    report_status = str(report_entry.get("status", "")).strip().lower() if isinstance(report_entry, dict) else ""
    if report_status == "pass":
        return "report", "pass"
    return "unknown", report_status or "unknown"


def read_model_mean_crps(summary_csv: Path, target_model_id: str) -> float:
    if not summary_csv.exists():
        raise FileNotFoundError(f"Missing CRPS summary: {summary_csv}")
    df = pd.read_csv(summary_csv)
    rows = df[df["model_id"] == target_model_id]
    if rows.empty:
        raise ValueError(f"{target_model_id} not found in {summary_csv}")
    if len(rows) != 1:
        raise ValueError(f"Expected one row for {target_model_id} in {summary_csv}, found {len(rows)}")
    return float(rows["mean_crps"].iloc[0])


def crps_summary_path(run_dir: Path) -> Path:
    return run_dir / "post" / "outputs" / run_dir.name / "tables" / "crps_forecast_summary.csv"


def manifest_path(run_dir: Path) -> Path:
    return run_dir / "run_manifest.yaml"


def ensure_parent(path: Path) -> Path:
    return ensure_dir(path.parent)


def normalize_harmonic_string(values: tuple[int, ...] | list[int] | Any) -> str:
    if values is None:
        return ""
    return ",".join(str(int(v)) for v in values)


def deep_merge(base: dict[str, Any] | None, override: dict[str, Any] | None) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base or {})
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def write_launch_settings(
    path: Path,
    artifact_root: Path,
    matrix_dir: Path,
    ordinary_max_concurrent: int,
    heavy_cutoff_max_concurrent: int,
    pause_free_gb: float,
    launch_free_gb: float,
    heavy_free_gb: float,
    poll_seconds: int,
) -> None:
    ensure_parent(path)
    lines = [
        f"ARTIFACT_ROOT={artifact_root}",
        f"MATRIX_DIR={matrix_dir}",
        f"ORDINARY_MAX_CONCURRENT={ordinary_max_concurrent}",
        f"HEAVY_CUTOFF_MAX_CONCURRENT={heavy_cutoff_max_concurrent}",
        f"PAUSE_FREE_GB={pause_free_gb}",
        f"LAUNCH_FREE_GB={launch_free_gb}",
        f"HEAVY_FREE_GB={heavy_free_gb}",
        f"POLL_SECONDS={poll_seconds}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_plan_summary(plan: pd.DataFrame) -> str:
    counts = plan["launch_mode"].value_counts().to_dict()
    lines = [
        "# HE3 exdqlm multivar ablation plan",
        "",
        f"- Generated: `{utc_now()}`",
        "",
        "## Counts",
        "",
        f"- total rows: `{len(plan)}`",
        f"- reuse_reference rows: `{int(counts.get('reuse_reference', 0))}`",
        f"- launch rows: `{int(counts.get('launch', 0))}`",
        "",
        "## Variants",
        "",
    ]
    variant_counts = plan.groupby(["variant", "launch_mode"]).size().reset_index(name="n")
    for _, row in variant_counts.iterrows():
        lines.append(f"- `{row['variant']}` ({row['launch_mode']}): `{int(row['n'])}`")
    lines.extend(["", "## Order Groups", ""])
    group_counts = plan.groupby(["order_group"]).size().reset_index(name="n")
    for _, row in group_counts.iterrows():
        lines.append(f"- group `{int(row['order_group'])}`: `{int(row['n'])}` rows")
    return "\n".join(lines) + "\n"


def status_row_from_plan(plan_row: pd.Series, artifact_root: Path) -> dict[str, Any]:
    launch_mode = str(plan_row["launch_mode"])
    if launch_mode == "reuse_reference":
        run_dir = Path(str(plan_row["source_run_dir"]))
    else:
        run_dir = artifact_root / "runs" / str(plan_row["run_id"])
    phase, status = stage_status(manifest_path(run_dir))
    if launch_mode == "reuse_reference" and status == "not_started":
        phase, status = "report", "fail"
    return {
        "cutoff": str(plan_row["cutoff"]),
        "epsilon": str(plan_row["epsilon"]),
        "lane": str(plan_row["variant"]),
        "variant": str(plan_row["variant"]),
        "run_id": str(plan_row["run_id"]),
        "launch_mode": launch_mode,
        "phase": phase,
        "status": "pass" if launch_mode == "reuse_reference" and status == "pass" else status,
        "target_model_id": str(plan_row["target_model_id"]),
        "order_group": int(plan_row["order_group"]),
        "config_path": str(plan_row.get("config_path", "")),
        "source_run_dir": str(plan_row["source_run_dir"]),
    }


def build_status_frame(plan: pd.DataFrame, artifact_root: Path) -> pd.DataFrame:
    rows = [status_row_from_plan(row, artifact_root) for _, row in plan.iterrows()]
    return pd.DataFrame(rows).sort_values(["order_group", "cutoff", "variant"]).reset_index(drop=True)


def write_status_markdown(status_df: pd.DataFrame, out_path: Path) -> None:
    counts = status_df["status"].value_counts().to_dict()
    lines = [
        "# HE3 exdqlm ablation status",
        "",
        "## Counts",
        "",
    ]
    for key in sorted(counts):
        lines.append(f"- {key}: {int(counts[key])}")
    lines.extend(["", "## Incomplete Rows", ""])
    incomplete = status_df[status_df["status"] != "pass"]
    if incomplete.empty:
        lines.append("- None.")
    else:
        for _, row in incomplete.iterrows():
            lines.append(
                f"- `{row['run_id']}`: variant={row['variant']}, phase={row['phase']}, status={row['status']}"
            )
    ensure_parent(out_path)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def dump_yaml(path: Path, payload: dict[str, Any]) -> None:
    write_yaml(path, payload)

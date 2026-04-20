#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any

import pandas as pd

from he3_exdqlm_ablation_lib import (
    BEST_BY_CUTOFF_CSV_DEFAULT,
    HE3_CONFIG_OUTPUT_DIR_DEFAULT,
    HE3_TEMPLATE_DEFAULT,
    cutoff_to_display,
    dump_yaml,
    ensure_parent,
    he3_run_id,
    load_best_targets,
    load_template,
    load_variant_specs,
    normalize_harmonic_string,
    render_plan_summary,
    source_config_path,
    source_run_dir,
    source_run_id,
    write_launch_settings,
)
from multimodel_v8_lib import ensure_dir, load_yaml


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build the HE3 exdqlm multivar ablation matrix and configs.")
    ap.add_argument("--template", default=str(HE3_TEMPLATE_DEFAULT))
    ap.add_argument("--best-by-cutoff-csv", default=str(BEST_BY_CUTOFF_CSV_DEFAULT))
    ap.add_argument("--matrix-dir")
    ap.add_argument("--artifact-root")
    ap.add_argument("--config-output-dir")
    return ap.parse_args()


def resolve_order_group(cutoff: str, pilot_sequence: list[str]) -> int:
    if cutoff in pilot_sequence:
        return pilot_sequence.index(cutoff) + 1
    return len(pilot_sequence) + 1


def reset_run_metadata(cfg: dict[str, Any]) -> dict[str, Any]:
    cfg = copy.deepcopy(cfg)
    cfg.setdefault("run", {})
    cfg["run"].pop("resolved_run_root", None)
    cfg["run"].pop("resolved_config_path", None)
    return cfg


def build_launch_config(
    source_cfg: dict[str, Any],
    run_id: str,
    artifact_root: Path,
    fit_workers: int,
    variant: Any,
    cutoff: str,
    best_epsilon_label: str,
    best_crps: float,
    source_run_name: str,
) -> dict[str, Any]:
    cfg = reset_run_metadata(source_cfg)
    cfg.setdefault("run", {})
    cfg["run"]["run_id"] = run_id
    cfg["run"]["run_root"] = str(artifact_root / "runs")
    cfg["run"]["overwrite"] = False
    cfg["run"]["auto_suffix_on_collision"] = False
    cfg["run"]["dry_run"] = False
    cfg["run"].setdefault("threads", {})
    cfg["run"]["threads"]["mc_cores"] = int(fit_workers)

    cfg.setdefault("stages", {})
    cfg["stages"]["forecats"] = False
    cfg["stages"]["data_prep_shared"] = True
    cfg["stages"]["fit"] = True
    cfg["stages"]["post"] = True
    cfg["stages"]["validate"] = True
    cfg["stages"]["report"] = True

    cfg.setdefault("models", {})
    cfg["models"]["run_exdqlm_multivar"] = True
    cfg["models"]["run_exdqlm_univar"] = False
    cfg["models"]["run_ndlm_main"] = False
    cfg["models"]["run_ndlm_univar"] = False
    cfg["models"].setdefault("exdqlm_multivar", {})
    cfg["models"]["exdqlm_multivar"]["implementation_mode"] = "legacy_bridge"
    cfg["models"]["exdqlm_multivar"]["likelihood_mode"] = "exal"
    cfg["models"]["exdqlm_multivar"]["forecast_transfer_mode"] = variant.forecast_transfer_mode
    cfg["models"]["exdqlm_multivar"]["structure"] = {
        "include_trend": bool(variant.include_trend),
        "enabled_harmonic_indices": [int(x) for x in variant.enabled_harmonic_indices],
    }

    cfg.setdefault("fit", {})
    cfg["fit"].setdefault("parallel", {})
    cfg["fit"]["parallel"]["mode"] = "global_models"
    cfg["fit"]["parallel"]["workers"] = int(fit_workers)
    cfg["fit"].setdefault("warm_start", {})
    cfg["fit"]["warm_start"]["enabled"] = False
    cfg["fit"].setdefault("exdqlm_multivar", {})
    cfg["fit"]["exdqlm_multivar"].setdefault("legacy", {})
    cfg["fit"]["exdqlm_multivar"]["legacy"]["use_covariates"] = bool(variant.use_covariates)

    cfg["he3_ablation"] = {
        "study_id": "he3_exdqlm_ablation_v1",
        "variant": variant.key,
        "manuscript_label": variant.manuscript_label,
        "source_model_variant": "exdqlm_multivar_keep",
        "source_run_id": source_run_name,
        "source_cutoff": cutoff,
        "source_best_epsilon_label": best_epsilon_label,
        "source_best_crps": float(best_crps),
        "include_trend": bool(variant.include_trend),
        "enabled_harmonic_indices": [int(x) for x in variant.enabled_harmonic_indices],
        "use_covariates": bool(variant.use_covariates),
        "forecast_transfer_mode": variant.forecast_transfer_mode,
        "target_model_id": variant.target_model_id,
    }
    return cfg


def main() -> int:
    args = parse_args()
    template_path = Path(args.template).resolve()
    template_cfg = load_template(template_path)

    campaign_cfg = template_cfg.get("campaign", {})
    artifact_root = Path(args.artifact_root or campaign_cfg.get("artifact_root", "")).resolve()
    matrix_dir = Path(args.matrix_dir or campaign_cfg.get("matrix_dir", "")).resolve()
    config_output_dir = Path(args.config_output_dir or campaign_cfg.get("config_output_dir", "")).resolve()
    if not config_output_dir.is_absolute():
        config_output_dir = (template_path.parents[1] / config_output_dir).resolve()
    ensure_dir(matrix_dir)
    ensure_dir(config_output_dir)
    ensure_dir(artifact_root / "runs")
    ensure_dir(artifact_root / "reports")
    ensure_dir(matrix_dir / "reference_configs")
    ensure_dir(matrix_dir / "source_snapshots")

    source_cfg = template_cfg.get("source", {})
    cf1_sweep_root = Path(source_cfg.get("cf1_sweep_root", "")).resolve()
    cf1_config_dir = Path(source_cfg.get("cf1_config_dir", "")).resolve()
    if not cf1_config_dir.is_absolute():
        cf1_config_dir = (template_path.parents[1] / cf1_config_dir).resolve()
    best_by_cutoff_csv = Path(args.best_by_cutoff_csv or source_cfg.get("best_by_cutoff_csv", "")).resolve()
    selected_model_variant = str(source_cfg.get("selected_model_variant", "exdqlm_multivar_keep"))

    variant_specs = load_variant_specs(template_cfg)
    targets = load_best_targets(best_by_cutoff_csv, selected_model_variant=selected_model_variant)
    fit_workers = int(template_cfg.get("fit_parallel", {}).get("workers", 7))
    pilot_sequence = [str(x) for x in template_cfg.get("pilot_sequence", [])]

    rows: list[dict[str, Any]] = []
    for _, target in targets.iterrows():
        cutoff = str(target["cutoff"])
        best_epsilon_label = str(target["best_epsilon_label"])
        source_run_name = source_run_id(cutoff, best_epsilon_label)
        source_cfg_path = source_config_path(cf1_config_dir, cutoff, best_epsilon_label)
        source_run_root = source_run_dir(cf1_sweep_root, cutoff, best_epsilon_label)
        if not source_cfg_path.exists():
            raise FileNotFoundError(f"Missing source config for HE3 cutoff={cutoff}: {source_cfg_path}")
        if not source_run_root.exists():
            raise FileNotFoundError(f"Missing source run directory for HE3 cutoff={cutoff}: {source_run_root}")
        frozen_cfg_copy = matrix_dir / "reference_configs" / source_cfg_path.name
        frozen_cfg_copy.write_text(source_cfg_path.read_text(encoding="utf-8"), encoding="utf-8")
        base_cfg = load_yaml(source_cfg_path)
        order_group = resolve_order_group(cutoff, pilot_sequence)

        for variant_order, variant in enumerate(variant_specs):
            plan_run_id = he3_run_id(cutoff, best_epsilon_label, variant.key)
            launch_mode = "reuse_reference" if variant.reuse_reference else "launch"
            cfg_path: Path | None = None
            if launch_mode == "launch":
                cfg = build_launch_config(
                    source_cfg=base_cfg,
                    run_id=plan_run_id,
                    artifact_root=artifact_root,
                    fit_workers=fit_workers,
                    variant=variant,
                    cutoff=cutoff,
                    best_epsilon_label=best_epsilon_label,
                    best_crps=float(target["forecast_window_crps"]),
                    source_run_name=source_run_name,
                )
                cfg_path = config_output_dir / f"{plan_run_id}.yaml"
                dump_yaml(cfg_path, cfg)

            rows.append(
                {
                    "cutoff": cutoff,
                    "cutoff_display": cutoff_to_display(cutoff),
                    "epsilon": best_epsilon_label,
                    "best_epsilon_label": best_epsilon_label,
                    "best_c_factor": float(target["best_c_factor"]),
                    "variant": variant.key,
                    "variant_order": variant_order,
                    "manuscript_label": variant.manuscript_label,
                    "launch_mode": launch_mode,
                    "order_group": 0 if launch_mode == "reuse_reference" else order_group,
                    "run_id": plan_run_id,
                    "config_path": str(cfg_path) if cfg_path is not None else "",
                    "source_run_id": source_run_name,
                    "source_run_dir": str(source_run_root),
                    "source_config_path": str(source_cfg_path),
                    "include_trend": bool(variant.include_trend),
                    "enabled_harmonic_indices": normalize_harmonic_string(variant.enabled_harmonic_indices),
                    "use_covariates": bool(variant.use_covariates),
                    "forecast_transfer_mode": variant.forecast_transfer_mode,
                    "target_model_id": variant.target_model_id,
                    "source_full_crps": float(target["forecast_window_crps"]),
                    "selection_basis": str(target.get("selection_basis", "")),
                }
            )

    plan = pd.DataFrame(rows)
    plan = plan.sort_values(["order_group", "cutoff", "variant_order"]).reset_index(drop=True)
    plan["order_index"] = plan.index + 1
    plan_path = matrix_dir / "matrix_plan.csv"
    plan.to_csv(plan_path, index=False)
    plan.to_csv(matrix_dir / "selection_manifest.csv", index=False)

    source_snapshot = matrix_dir / "source_snapshots" / "best_by_cutoff_long.snapshot.csv"
    source_snapshot.write_text(best_by_cutoff_csv.read_text(encoding="utf-8"), encoding="utf-8")

    metadata = {
        "generated_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "template_path": str(template_path),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "cf1_sweep_root": str(cf1_sweep_root),
        "cf1_config_dir": str(cf1_config_dir),
        "best_by_cutoff_csv": str(best_by_cutoff_csv),
        "selected_model_variant": selected_model_variant,
        "fit_workers": fit_workers,
        "pilot_sequence": pilot_sequence,
        "variant_keys": [variant.key for variant in variant_specs],
    }
    dump_yaml(matrix_dir / "matrix_metadata.yaml", metadata)

    queue_cfg = template_cfg.get("queue", {})
    write_launch_settings(
        path=matrix_dir / "launch_settings.env",
        artifact_root=artifact_root,
        matrix_dir=matrix_dir,
        ordinary_max_concurrent=int(queue_cfg.get("ordinary_max_concurrent", 4)),
        heavy_cutoff_max_concurrent=int(queue_cfg.get("heavy_cutoff_max_concurrent", 1)),
        pause_free_gb=float(queue_cfg.get("pause_free_gb", 180)),
        launch_free_gb=float(queue_cfg.get("launch_free_gb", 220)),
        heavy_free_gb=float(queue_cfg.get("heavy_free_gb", 240)),
        poll_seconds=int(queue_cfg.get("poll_seconds", 60)),
    )

    summary_path = matrix_dir / "plan_summary.md"
    ensure_parent(summary_path)
    summary_path.write_text(render_plan_summary(plan), encoding="utf-8")

    print(plan_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

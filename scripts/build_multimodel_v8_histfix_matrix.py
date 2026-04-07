#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from build_multimodel_v8_matrix_configs import build_v8_config
from multimodel_v8_lib import (
    CUTOFFS,
    ensure_dir,
    load_yaml,
    resolve_artifact_root,
    reports_dir,
    runs_dir,
    v7_template_config_path,
    v8_compare_dir,
    v8_run_id,
    write_yaml,
)

DEFAULT_HISTFIX_CUTOFFS = ["20211221", "20220511"]
DEFAULT_DATA_START = "1987-05-29"
DEFAULT_BUNDLE_RUN_ID = "20260407_long_history_r01"

PHASE_EPSILONS: dict[str, dict[str, float | None]] = {
    "tt": {"epsTT": None},
    "c100": {
        "eps30": 30.0,
        "eps90": 90.0,
        "eps180": 180.0,
        "eps360": 360.0,
    },
    "cf1": {
        "epsTTcf1": None,
        "eps30cf1": 30.0,
        "eps90cf1": 90.0,
        "eps180cf1": 180.0,
        "eps360cf1": 360.0,
    },
}


@dataclass(frozen=True)
class HistfixLanePlan:
    cutoff: str
    epsilon_label: str
    epsilon_value: float | None
    lane: str
    run_scope: str
    run_id: str
    config_path: Path
    priority_group: int
    max_concurrent_class: str


def _set_nested(cfg: dict[str, Any], path: list[str], value: Any) -> None:
    cur = cfg
    for key in path[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[path[-1]] = value


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build isolated config/matrix plans for the v8 hist-fix rerun campaign.")
    ap.add_argument("--phase", choices=sorted(PHASE_EPSILONS), required=True)
    ap.add_argument("--artifact-root", default="/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_histfix_20260407")
    ap.add_argument("--matrix-dir", required=True)
    ap.add_argument("--config-dir", default="config/unified_runs_histfix_20260407")
    ap.add_argument("--cutoffs", nargs="*", default=DEFAULT_HISTFIX_CUTOFFS)
    ap.add_argument("--bundle-run-id", default=DEFAULT_BUNDLE_RUN_ID)
    ap.add_argument("--data-start", default=DEFAULT_DATA_START)
    return ap.parse_args()


def worker_count_for_lane(lane: str) -> int:
    if lane == "l1":
        return 23
    if lane == "l2":
        return 22
    return 14


def lane_plans_for_phase(cutoffs: list[str], phase: str, config_dir: Path) -> list[HistfixLanePlan]:
    rows: list[HistfixLanePlan] = []
    epsilon_map = PHASE_EPSILONS[phase]
    if phase == "tt":
        for cutoff in cutoffs:
            for lane in ("l1", "l2"):
                eps_label = "epsTT"
                rows.append(
                    HistfixLanePlan(
                        cutoff=cutoff,
                        epsilon_label=eps_label,
                        epsilon_value=None,
                        lane=lane,
                        run_scope="full_tt",
                        run_id=v8_run_id(cutoff, eps_label, lane),
                        config_path=config_dir / f"{v8_run_id(cutoff, eps_label, lane)}.yaml",
                        priority_group=1,
                        max_concurrent_class="ordinary",
                    )
                )
        return rows

    priority_group = 2 if phase == "c100" else 3
    for cutoff in cutoffs:
        for eps_label, eps_value in epsilon_map.items():
            for lane in ("l1_mv", "l2_mv"):
                run_id = v8_run_id(cutoff, eps_label, lane)
                rows.append(
                    HistfixLanePlan(
                        cutoff=cutoff,
                        epsilon_label=eps_label,
                        epsilon_value=eps_value,
                        lane=lane,
                        run_scope="multivar_only",
                        run_id=run_id,
                        config_path=config_dir / f"{run_id}.yaml",
                        priority_group=priority_group,
                        max_concurrent_class="ordinary",
                    )
                )
    return rows


def initialize_matrix_dir(matrix_dir: Path) -> None:
    ensure_dir(matrix_dir)
    status_path = matrix_dir / "matrix_status.csv"
    if not status_path.exists():
        with status_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "cutoff", "epsilon", "lane", "run_id", "phase", "status", "started_at", "finished_at",
                "manifest_path", "latest_log_mtime", "disk_free_gb", "note",
            ])
    (matrix_dir / "queue.log").touch()


def build_dependency_table(config_paths: list[Path], matrix_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for cfg_path in config_paths:
        cfg = load_yaml(cfg_path)
        dep_specs = [
            ("forecats_existing_bundle", cfg.get("inputs", {}).get("forecats", {}).get("existing_bundle_path", "")),
            ("fit_parameters", cfg.get("inputs", {}).get("fit", {}).get("parameters_path", "")),
            ("fit_retros", cfg.get("inputs", {}).get("fit", {}).get("retros_path", "")),
            ("fit_nws_forecast", cfg.get("inputs", {}).get("fit", {}).get("nws_forecast_path", "")),
            ("fit_glofas_forecast", cfg.get("inputs", {}).get("fit", {}).get("glofas_forecast_path", "")),
        ]
        for cov in cfg.get("inputs", {}).get("fit", {}).get("covariates", []):
            if isinstance(cov, dict):
                dep_specs.append((f"covariate:{cov.get('name', '')}", cov.get("path", "")))
        for dep_type, dep_path in dep_specs:
            rows.append(
                {
                    "consumer_config": str(cfg_path),
                    "dependency_type": dep_type,
                    "dependency_path": str(dep_path or ""),
                }
            )
    df = pd.DataFrame(rows).sort_values(["consumer_config", "dependency_type"]).reset_index(drop=True)
    df.to_csv(matrix_dir / "dependency_preservation.csv", index=False)
    return df


def write_matrix_plan(matrix_dir: Path, lane_plans: list[HistfixLanePlan], artifact_root: Path) -> pd.DataFrame:
    rows = []
    for order_index, plan in enumerate(lane_plans, start=1):
        rows.append(
            {
                "order_index": order_index,
                "cutoff": plan.cutoff,
                "epsilon": plan.epsilon_label,
                "epsilon_value": "TT" if plan.epsilon_value is None else int(plan.epsilon_value),
                "lane": plan.lane,
                "run_scope": plan.run_scope,
                "run_id": plan.run_id,
                "config_path": str(plan.config_path),
                "compare_outdir": str(v8_compare_dir(plan.cutoff, plan.epsilon_label, artifact_root)),
                "priority_group": plan.priority_group,
                "max_concurrent_class": plan.max_concurrent_class,
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(matrix_dir / "matrix_plan.csv", index=False)
    return df


def build_scope_markdown(matrix_dir: Path, phase: str, cutoffs: list[str], lane_plans: list[HistfixLanePlan], bundle_run_id: str, data_start: str) -> None:
    lines = [
        f"# multimodel v8 hist-fix matrix ({phase})",
        "",
        f"- phase: `{phase}`",
        f"- cutoffs: {', '.join(f'`{c}`' for c in cutoffs)}",
        f"- data_start: `{data_start}`",
        f"- stable bundle run id: `{bundle_run_id}`",
        f"- plan rows: `{len(lane_plans)}`",
        "",
        "## Run Surface",
    ]
    for plan in lane_plans:
        lines.append(
            f"- `{plan.run_id}`: cutoff=`{plan.cutoff}` epsilon=`{plan.epsilon_label}` lane=`{plan.lane}` workers=`{worker_count_for_lane(plan.lane)}`"
        )
    (matrix_dir / "histfix_scope.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_configs(args: argparse.Namespace) -> tuple[list[Path], list[HistfixLanePlan], Path]:
    artifact_root = Path(resolve_artifact_root(args.artifact_root))
    matrix_dir = Path(args.matrix_dir).resolve()
    config_dir = ensure_dir(Path(args.config_dir).resolve())
    ensure_dir(runs_dir(artifact_root))
    ensure_dir(reports_dir(artifact_root))
    initialize_matrix_dir(matrix_dir)

    supported_cutoffs = {cutoff for cutoff, _ in CUTOFFS}
    cutoffs = [str(c) for c in args.cutoffs]
    unsupported = sorted(set(cutoffs) - supported_cutoffs)
    if unsupported:
        raise SystemExit(f"Unsupported cutoffs: {unsupported}")

    support_root = artifact_root / "supporting_inputs"
    bundle_base = artifact_root / "stable_inputs" / f"site=11160500"
    support_manifest = support_root / "support_manifest.json"
    if not support_manifest.exists():
        raise SystemExit(f"Missing supporting input manifest: {support_manifest}. Run build_multimodel_v8_histfix_bundles.py first.")

    lane_plans = lane_plans_for_phase(cutoffs, args.phase, config_dir)
    generated: list[Path] = []

    for plan in lane_plans:
        template_lane = "l1" if plan.lane.startswith("l1") else "l2"
        template = load_yaml(v7_template_config_path(plan.cutoff, template_lane))
        bundle_meta = bundle_base / f"cutoff_date={plan.cutoff[:4]}-{plan.cutoff[4:6]}-{plan.cutoff[6:]}" / f"run_id={args.bundle_run_id}" / "meta.yaml"
        if not bundle_meta.exists():
            raise SystemExit(f"Missing hist-fix bundle meta for cutoff {plan.cutoff}: {bundle_meta}")
        bundle_root = bundle_meta.parent
        multivar_c_factor = 1.0 if args.phase == "cf1" else None
        workers = worker_count_for_lane(plan.lane)
        cfg = build_v8_config(
            template_cfg=template,
            run_id=plan.run_id,
            epsilon_label=plan.epsilon_label,
            epsilon_value=plan.epsilon_value,
            lane=plan.lane,
            cutoff=plan.cutoff,
            artifact_root=artifact_root,
            multivar_c_factor=multivar_c_factor,
            fit_parallel_mode="global_models",
            fit_parallel_workers=workers,
        )
        _set_nested(cfg, ["dates", "data_start"], args.data_start)
        _set_nested(cfg, ["inputs", "forecats", "existing_bundle_path"], str(bundle_meta))
        _set_nested(cfg, ["inputs", "fit", "parameters_path"], str(support_root / "parameters" / "parameters.txt"))
        _set_nested(cfg, ["inputs", "fit", "retros_path"], str(bundle_root / "retros.csv"))
        _set_nested(cfg, ["inputs", "fit", "retros_storage_scale"], "log1p_cms")
        _set_nested(cfg, ["inputs", "fit", "nws_forecast_path"], str(bundle_root / "nws_forecast.csv"))
        _set_nested(cfg, ["inputs", "fit", "nws_storage_scale"], "raw_cms")
        _set_nested(cfg, ["inputs", "fit", "glofas_forecast_path"], str(bundle_root / "glofas_forecast.csv"))
        _set_nested(cfg, ["inputs", "fit", "glofas_storage_scale"], "raw_cms")
        _set_nested(
            cfg,
            ["inputs", "fit", "covariates"],
            [
                {"name": "ELI", "path": str(support_root / "covariates" / "cov_01_ELI.csv")},
                {"name": "ONI", "path": str(support_root / "covariates" / "cov_02_ONI.csv")},
                {"name": "PPT", "path": str(support_root / "covariates" / "cov_03_PPT.csv")},
                {"name": "SOIL", "path": str(support_root / "covariates" / "cov_04_SOIL.csv")},
                {"name": "PCA", "path": str(support_root / "covariates" / "cov_05_PCA.csv")},
            ],
        )
        _set_nested(cfg, ["fit", "parallel", "mode"], "global_models")
        _set_nested(cfg, ["fit", "parallel", "workers"], workers)
        _set_nested(cfg, ["run", "threads", "mc_cores"], workers)
        cfg["debug_histfix"] = {
            "phase": args.phase,
            "data_start": args.data_start,
            "histfix_bundle_path": str(bundle_meta),
            "support_manifest": str(support_manifest),
            "intended_nws_policy": "nws_retro_v21 with v30 tail fill after 2020-12-31",
            "intended_glofas_policy": "glofas_hist_v31_lisflood_cons",
            "fit_parallel_mode": "global_models",
            "fit_parallel_workers": workers,
        }
        write_yaml(plan.config_path, cfg)
        generated.append(plan.config_path)

    write_matrix_plan(matrix_dir, lane_plans, artifact_root)
    build_dependency_table(generated, matrix_dir)
    build_scope_markdown(matrix_dir, args.phase, cutoffs, lane_plans, args.bundle_run_id, args.data_start)
    (matrix_dir / "pilot_summary.md").write_text(
        f"# hist-fix pilot summary ({args.phase})\n\nQueue not complete yet.\n",
        encoding="utf-8",
    )
    (matrix_dir / "final_matrix_summary.md").write_text(
        f"# hist-fix matrix summary ({args.phase})\n\nQueue not complete yet.\n",
        encoding="utf-8",
    )
    return generated, lane_plans, matrix_dir


def main() -> int:
    args = parse_args()
    generated, lane_plans, matrix_dir = build_configs(args)
    print(f"phase={args.phase}")
    print(f"matrix_dir={matrix_dir}")
    print(f"generated_configs={len(generated)}")
    print(f"plan_rows={len(lane_plans)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

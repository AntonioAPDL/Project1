#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CONFIG_DIR = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522/"
    "control/generated_configs"
)
DEFAULT_SMOKE_ARTIFACT_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "exdqlm_multivar_keep_near_zero_gamsig_smoke_20260523"
)
DEFAULT_REPAIR_ARTIFACT_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "exdqlm_multivar_keep_near_zero_gamsig_repair_20260523"
)
DEFAULT_SMOKE_REPORT_DIR = ROOT / "reports" / "exdqlm_multivar_keep_near_zero_gamsig_smoke_20260523"
DEFAULT_REPAIR_REPORT_DIR = ROOT / "reports" / "exdqlm_multivar_keep_near_zero_gamsig_repair_runtime_20260523"

DEFAULT_QUANTILES = [0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95]
FAILED_CUTOFFS = ["20210123", "20211221", "20220511"]
SMOKE_CASES = [
    ("20210123", 0.35, "failed_q35_primary"),
    ("20211221", 0.20, "failed_q20_primary"),
    ("20220511", 0.20, "failed_q20_secondary"),
    ("20221225", 0.20, "healthy_q20_control"),
    ("20211112", 0.35, "healthy_q35_control"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root is not a mapping: {path}")
    return data


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, default_flow_style=False)


def q_label(q: float) -> str:
    return f"{int(round(100.0 * float(q))):02d}"


def cutoff_config_path(source_config_dir: Path, cutoff: str) -> Path:
    return source_config_dir / f"multimodel_{cutoff}_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml"


def matrix_status_header() -> list[str]:
    return [
        "cutoff",
        "lane",
        "run_id",
        "phase",
        "status",
        "started_at",
        "finished_at",
        "returncode",
        "config_path",
        "run_root",
        "log_path",
        "note",
    ]


def matrix_plan_header() -> list[str]:
    return [
        "order_index",
        "package",
        "role",
        "cutoff",
        "lane",
        "run_id",
        "active_quantiles",
        "workers",
        "mc_cores",
        "config_path",
        "run_root",
        "source_config_path",
    ]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def ensure_nested(mapping: dict[str, Any], path: list[str]) -> dict[str, Any]:
    cursor = mapping
    for key in path:
        child = cursor.get(key)
        if not isinstance(child, dict):
            child = {}
            cursor[key] = child
        cursor = child
    return cursor


def set_stage_flags(cfg: dict[str, Any], *, post: bool, validate: bool, report: bool) -> None:
    stages = ensure_nested(cfg, ["stages"])
    stages["forecats"] = False
    stages["data_prep_shared"] = True
    stages["fit"] = True
    stages["post"] = bool(post)
    stages["validate"] = bool(validate)
    stages["report"] = bool(report)


def force_near_zero_fallback(cfg: dict[str, Any]) -> None:
    gamma_sigma = ensure_nested(cfg, ["fit", "exdqlm_multivar", "gamma_sigma"])
    gamma_sigma["near_zero_fallback"] = {
        "enabled": True,
        "mode": "sigma_only",
        "gamma_anchor": "full_candidate",
    }
    # Keep the already audited split thresholds explicit in regenerated configs.
    split = gamma_sigma.get("laplace_split_near_zero")
    if not isinstance(split, dict):
        gamma_sigma["laplace_split_near_zero"] = {
            "enabled": True,
            "abs_gamma_threshold": 0.05,
            "rel_support_threshold": 0.02,
            "zero_margin_abs_gamma": 1e-6,
            "split_on_guard": True,
        }


def normalize_debug_block(cfg: dict[str, Any], quantiles: list[float], workers: int, mc_cores: int) -> None:
    debug = ensure_nested(cfg, ["debug_he2_publication_relaunch"])
    debug["active_quantiles"] = [float(q) for q in quantiles]
    debug["fit_parallel_workers_effective"] = int(workers)
    debug["mc_cores_effective"] = int(mc_cores)
    fit_patch = ensure_nested(debug, ["config_patch_json", "fit"])
    fit_patch["quantiles"] = [float(q) for q in quantiles]
    run_patch = ensure_nested(debug, ["config_patch_json", "run", "threads"])
    run_patch["mc_cores"] = int(mc_cores)
    fit_model_patch = ensure_nested(debug, ["config_patch_json", "fit", "exdqlm_multivar", "gamma_sigma"])
    fit_model_patch["near_zero_fallback"] = {
        "enabled": True,
        "mode": "sigma_only",
        "gamma_anchor": "full_candidate",
    }


def mutate_config(
    source_cfg: dict[str, Any],
    *,
    artifact_root: Path,
    run_id: str,
    quantiles: list[float],
    workers: int,
    mc_cores: int,
    post: bool,
    validate: bool,
    report: bool,
) -> dict[str, Any]:
    cfg = deepcopy(source_cfg)
    run = ensure_nested(cfg, ["run"])
    run["run_id"] = run_id
    run["run_root"] = str(artifact_root / "runs")
    run["overwrite"] = True
    run["auto_suffix_on_collision"] = False
    run["dry_run"] = False
    run.pop("resolved_run_root", None)
    run.pop("resolved_config_path", None)
    threads = ensure_nested(run, ["threads"])
    for key in ["omp", "openblas", "mkl", "veclib", "numexpr"]:
        threads[key] = 1
    threads["mc_cores"] = int(mc_cores)

    set_stage_flags(cfg, post=post, validate=validate, report=report)
    fit = ensure_nested(cfg, ["fit"])
    fit["quantiles"] = [float(q) for q in quantiles]
    parallel = ensure_nested(fit, ["parallel"])
    parallel["mode"] = parallel.get("mode") or "global_models"
    parallel["workers"] = int(workers)
    force_near_zero_fallback(cfg)
    normalize_debug_block(cfg, quantiles=quantiles, workers=workers, mc_cores=mc_cores)
    return cfg


def build_smoke_package(source_config_dir: Path, artifact_root: Path, report_dir: Path, tag: str) -> dict[str, Any]:
    config_dir = artifact_root / "control" / "generated_configs"
    matrix_dir = artifact_root / "control" / "smoke_matrix"
    rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    for idx, (cutoff, q, role) in enumerate(SMOKE_CASES, start=1):
        source_path = cutoff_config_path(source_config_dir, cutoff)
        source_cfg = load_yaml(source_path)
        qlab = q_label(q)
        run_id = f"smoke_nearzero_{cutoff}_q{qlab}_exdqlm_multivar_keep_{tag}"
        config_path = config_dir / f"{run_id}.yaml"
        run_root = artifact_root / "runs" / run_id
        cfg = mutate_config(
            source_cfg,
            artifact_root=artifact_root,
            run_id=run_id,
            quantiles=[q],
            workers=1,
            mc_cores=1,
            post=False,
            validate=False,
            report=False,
        )
        write_yaml(config_path, cfg)
        rows.append({
            "order_index": idx,
            "package": "smoke",
            "role": role,
            "cutoff": cutoff,
            "lane": f"q{qlab}",
            "run_id": run_id,
            "active_quantiles": qlab,
            "workers": 1,
            "mc_cores": 1,
            "config_path": str(config_path),
            "run_root": str(run_root),
            "source_config_path": str(source_path),
        })
        status_rows.append({
            "cutoff": cutoff,
            "lane": f"q{qlab}",
            "run_id": run_id,
            "phase": "prepared",
            "status": "pending",
            "config_path": str(config_path),
            "run_root": str(run_root),
            "note": role,
        })
    write_csv(matrix_dir / "matrix_plan.csv", rows, matrix_plan_header())
    write_csv(matrix_dir / "matrix_status.csv", status_rows, matrix_status_header())
    payload = {
        "created_at_utc": utc_now(),
        "package": "smoke",
        "artifact_root": str(artifact_root),
        "report_dir": str(report_dir),
        "source_config_dir": str(source_config_dir),
        "matrix_dir": str(matrix_dir),
        "cases": rows,
    }
    (artifact_root / "control" / "manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (artifact_root / "control" / "manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "smoke_plan.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(report_dir / "smoke_plan.csv", rows, matrix_plan_header())
    return payload


def build_repair_package(source_config_dir: Path, artifact_root: Path, report_dir: Path, tag: str) -> dict[str, Any]:
    config_dir = artifact_root / "control" / "generated_configs"
    matrix_dir = artifact_root / "control" / "repair_matrix"
    rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    for idx, cutoff in enumerate(FAILED_CUTOFFS, start=1):
        source_path = cutoff_config_path(source_config_dir, cutoff)
        source_cfg = load_yaml(source_path)
        run_id = f"repair_nearzero_{cutoff}_exdqlm_multivar_keep_{tag}"
        config_path = config_dir / f"{run_id}.yaml"
        run_root = artifact_root / "runs" / run_id
        cfg = mutate_config(
            source_cfg,
            artifact_root=artifact_root,
            run_id=run_id,
            quantiles=DEFAULT_QUANTILES,
            workers=7,
            mc_cores=7,
            post=True,
            validate=True,
            report=True,
        )
        write_yaml(config_path, cfg)
        rows.append({
            "order_index": idx,
            "package": "repair",
            "role": "failed_cutoff_row_repair",
            "cutoff": cutoff,
            "lane": "all7",
            "run_id": run_id,
            "active_quantiles": ",".join(q_label(q) for q in DEFAULT_QUANTILES),
            "workers": 7,
            "mc_cores": 7,
            "config_path": str(config_path),
            "run_root": str(run_root),
            "source_config_path": str(source_path),
        })
        status_rows.append({
            "cutoff": cutoff,
            "lane": "all7",
            "run_id": run_id,
            "phase": "prepared",
            "status": "pending",
            "config_path": str(config_path),
            "run_root": str(run_root),
            "note": "failed_cutoff_row_repair",
        })
    write_csv(matrix_dir / "matrix_plan.csv", rows, matrix_plan_header())
    write_csv(matrix_dir / "matrix_status.csv", status_rows, matrix_status_header())
    payload = {
        "created_at_utc": utc_now(),
        "package": "repair",
        "artifact_root": str(artifact_root),
        "report_dir": str(report_dir),
        "source_config_dir": str(source_config_dir),
        "matrix_dir": str(matrix_dir),
        "cases": rows,
    }
    (artifact_root / "control" / "manifest.json").parent.mkdir(parents=True, exist_ok=True)
    (artifact_root / "control" / "manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "repair_plan.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_csv(report_dir / "repair_plan.csv", rows, matrix_plan_header())
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", choices=["smoke", "repair", "both"], default="smoke")
    parser.add_argument("--source-config-dir", type=Path, default=DEFAULT_SOURCE_CONFIG_DIR)
    parser.add_argument("--smoke-artifact-root", type=Path, default=DEFAULT_SMOKE_ARTIFACT_ROOT)
    parser.add_argument("--repair-artifact-root", type=Path, default=DEFAULT_REPAIR_ARTIFACT_ROOT)
    parser.add_argument("--smoke-report-dir", type=Path, default=DEFAULT_SMOKE_REPORT_DIR)
    parser.add_argument("--repair-report-dir", type=Path, default=DEFAULT_REPAIR_REPORT_DIR)
    parser.add_argument("--tag", default="20260523")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_config_dir = args.source_config_dir.resolve()
    for cutoff in sorted({case[0] for case in SMOKE_CASES} | set(FAILED_CUTOFFS)):
        source_path = cutoff_config_path(source_config_dir, cutoff)
        if not source_path.exists():
            raise FileNotFoundError(source_path)

    payloads = []
    if args.package in {"smoke", "both"}:
        payloads.append(build_smoke_package(
            source_config_dir=source_config_dir,
            artifact_root=args.smoke_artifact_root.resolve(),
            report_dir=args.smoke_report_dir.resolve(),
            tag=args.tag,
        ))
    if args.package in {"repair", "both"}:
        payloads.append(build_repair_package(
            source_config_dir=source_config_dir,
            artifact_root=args.repair_artifact_root.resolve(),
            report_dir=args.repair_report_dir.resolve(),
            tag=args.tag,
        ))

    for payload in payloads:
        print(json.dumps({
            "package": payload["package"],
            "artifact_root": payload["artifact_root"],
            "matrix_dir": payload["matrix_dir"],
            "cases": len(payload["cases"]),
        }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

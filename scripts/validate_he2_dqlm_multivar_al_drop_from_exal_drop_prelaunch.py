#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_he2_dqlm_multivar_al_drop_from_exal_drop import (  # noqa: E402
    DEFAULT_ARTIFACT_ROOT,
    EXPECTED_CUTOFFS,
    SOURCE_ARTIFACT_ROOT,
    SOURCE_FAMILY,
    TARGET_FAMILY,
    TARGET_MODEL_KEY,
    build_package,
    source_config_path,
    source_run_id,
    target_run_id,
)


HEAVY_RDATA_SUFFIXES = {".rdata", ".rda"}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, default_flow_style=False)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def nested(payload: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def strip_operational(payload: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(payload)
    for key in [
        "run",
        "debug_v8_matrix",
        "debug_featurecov_cf1_eps_campaign",
        "debug_he2_publication_relaunch",
        "debug_he2_dqlm_al_drop_from_exal_drop",
    ]:
        out.pop(key, None)
    if isinstance(out.get("models"), dict) and isinstance(out["models"].get(TARGET_MODEL_KEY), dict):
        out["models"][TARGET_MODEL_KEY].pop("likelihood_mode", None)
    return out


def find_heavy_rdata_artifacts(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in HEAVY_RDATA_SUFFIXES]


def run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False, env=env)


def write_smoke_config(src_config: Path, smoke_root: Path) -> Path:
    payload = load_yaml(src_config)
    run_id = "smoke_al_drop_from_exal_drop_20210123_q50"
    payload["run"]["run_id"] = run_id
    payload["run"]["run_root"] = str(smoke_root)
    payload["run"]["resolved_run_root"] = str(smoke_root / run_id)
    payload["run"]["overwrite"] = True
    payload["run"]["auto_suffix_on_collision"] = True
    payload.setdefault("run", {}).setdefault("threads", {})
    payload["run"]["threads"]["mc_cores"] = 1
    payload.setdefault("fit", {})
    payload["fit"]["quantiles"] = [0.5]
    payload["fit"].setdefault("parallel", {})
    payload["fit"]["parallel"]["workers"] = 1
    payload["fit"] = deep_merge(
        payload["fit"],
        {
            TARGET_MODEL_KEY: {
                "gamma_sigma": {
                    "min_update_iters": 6,
                    "min_total_iters": 12,
                    "max_iter": 18,
                },
                "legacy": {
                    "n_samp": 512,
                },
            }
        },
    )
    for stage in ["forecats", "data_prep_shared", "fit", "post", "validate", "report"]:
        payload["stages"][stage] = stage != "forecats"
    smoke_cfg = smoke_root / f"{run_id}.yaml"
    write_yaml(smoke_cfg, payload)
    return smoke_cfg


def validate_configs(artifact_root: Path, source_root: Path) -> dict[str, Any]:
    matrix_dir = artifact_root / "control" / "publication_relaunch_matrix"
    config_dir = artifact_root / "control" / "generated_configs"
    rows = []
    for cutoff in EXPECTED_CUTOFFS:
        src_path = source_config_path(source_root, cutoff)
        tgt_path = config_dir / f"{target_run_id(cutoff)}.yaml"
        assert_true(src_path.exists(), f"{cutoff}: missing source config {src_path}")
        assert_true(tgt_path.exists(), f"{cutoff}: missing target config {tgt_path}")
        source_cfg = load_yaml(src_path)
        target_cfg = load_yaml(tgt_path)
        assert_true(nested(source_cfg, ["models", TARGET_MODEL_KEY, "likelihood_mode"]) == "exal", f"{cutoff}: source is not exAL")
        assert_true(nested(target_cfg, ["models", TARGET_MODEL_KEY, "likelihood_mode"]) == "al", f"{cutoff}: target is not AL")
        assert_true(nested(target_cfg, ["models", TARGET_MODEL_KEY, "forecast_transfer_mode"]) == "drop", f"{cutoff}: target is not drop")
        assert_true(nested(target_cfg, ["models", "run_exdqlm_multivar"]) is True, f"{cutoff}: target multivar flag off")
        assert_true(nested(target_cfg, ["models", "run_exdqlm_univar"]) is False, f"{cutoff}: target univar flag on")
        preserved_paths = [
            ["dates", "data_start"],
            ["dates", "cutoff_date"],
            ["inputs", "fit", "parameters_path"],
            ["inputs", "fit", "retros_path"],
            ["inputs", "fit", "nws_forecast_path"],
            ["inputs", "fit", "glofas_forecast_path"],
            ["inputs", "fit", "covariates"],
            ["inputs", "forecats", "existing_bundle_path"],
            ["inputs", "deterministic_climate"],
            ["inputs", "covariate_features"],
            ["scale_contract"],
            ["models", TARGET_MODEL_KEY, "state_evolution"],
            ["models", TARGET_MODEL_KEY, "structure"],
            ["fit", TARGET_MODEL_KEY, "legacy", "forecast_cov"],
            ["fit", TARGET_MODEL_KEY, "gamma_sigma", "max_iter"],
            ["fit", "quantiles"],
        ]
        for keys in preserved_paths:
            assert_true(nested(source_cfg, keys) == nested(target_cfg, keys), f"{cutoff}: did not preserve {'.'.join(keys)}")
        src_stripped = strip_operational(source_cfg)
        tgt_stripped = strip_operational(target_cfg)
        assert_true(src_stripped == tgt_stripped, f"{cutoff}: unexpected non-operational diff beyond likelihood/run/debug")
        rows.append(
            {
                "cutoff": cutoff,
                "source_run_id": source_run_id(cutoff),
                "target_run_id": target_run_id(cutoff),
                "source_config": str(src_path),
                "target_config": str(tgt_path),
                "status": "passed",
            }
        )
    assert_true((matrix_dir / "source_clone_manifest.csv").exists(), "missing source_clone_manifest.csv")
    assert_true((matrix_dir / "frozen_spec_manifest.csv").exists(), "missing frozen_spec_manifest.csv")
    assert_true((matrix_dir / "matrix_plan.csv").exists(), "missing matrix_plan.csv")
    return {"config_rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AL-M-T0 clone configs before launch.")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--source-artifact-root", type=Path, default=SOURCE_ARTIFACT_ROOT)
    parser.add_argument("--outdir", type=Path)
    parser.add_argument("--skip-smoke", action="store_true")
    args = parser.parse_args()

    artifact_root = args.artifact_root.resolve()
    source_root = args.source_artifact_root.resolve()
    outdir = (args.outdir.resolve() if args.outdir else artifact_root / "control" / f"prelaunch_validation_{utc_stamp()}")
    outdir.mkdir(parents=True, exist_ok=True)

    metadata = build_package(artifact_root, source_artifact_root=source_root, reset_status=True)
    summary: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_root": str(artifact_root),
        "source_artifact_root": str(source_root),
        "metadata": metadata,
        "checks": {},
        "smoke_runs": [],
    }

    compile_proc = run(
        [
            "python3",
            "-m",
            "py_compile",
            "scripts/build_he2_dqlm_multivar_al_drop_from_exal_drop.py",
            "scripts/validate_he2_dqlm_multivar_al_drop_from_exal_drop_prelaunch.py",
        ],
        cwd=ROOT,
    )
    (outdir / "py_compile.stdout.log").write_text(compile_proc.stdout, encoding="utf-8")
    (outdir / "py_compile.stderr.log").write_text(compile_proc.stderr, encoding="utf-8")
    assert_true(compile_proc.returncode == 0, compile_proc.stderr)
    summary["checks"]["py_compile"] = "passed"

    config_summary = validate_configs(artifact_root, source_root)
    summary["checks"]["clone_contract"] = config_summary

    source_r_artifacts = find_heavy_rdata_artifacts(source_root)
    assert_true(not source_r_artifacts, f"promoted exAL-M-T0 source root still has R artifacts: {source_r_artifacts[:5]}")
    summary["checks"]["source_rdata_cleanup"] = "passed"

    if args.skip_smoke:
        summary["smoke_runs"].append({"scope": "full_pipeline_q50", "status": "skipped"})
    else:
        smoke_root = outdir / "smoke_runs"
        shutil.rmtree(smoke_root, ignore_errors=True)
        smoke_root.mkdir(parents=True, exist_ok=True)
        smoke_cfg = write_smoke_config(
            artifact_root / "control" / "generated_configs" / f"{target_run_id('20210123')}.yaml",
            smoke_root,
        )
        env = dict(os.environ)
        env["CLEANUP_RDATA_AFTER_POST"] = "1"
        smoke_proc = run(["Rscript", "--vanilla", "scripts/unified_run.R", "--config", str(smoke_cfg)], cwd=ROOT, env=env)
        (outdir / "smoke_al_drop_q50.stdout.log").write_text(smoke_proc.stdout, encoding="utf-8")
        (outdir / "smoke_al_drop_q50.stderr.log").write_text(smoke_proc.stderr, encoding="utf-8")
        assert_true(
            smoke_proc.returncode == 0,
            f"AL-drop q50 full-pipeline smoke failed\nSTDOUT:\n{smoke_proc.stdout}\nSTDERR:\n{smoke_proc.stderr}",
        )
        run_dir = smoke_root / "smoke_al_drop_from_exal_drop_20210123_q50"
        manifest = load_yaml(run_dir / "run_manifest.yaml")
        stages = manifest.get("stages", {}) if isinstance(manifest, dict) else {}
        assert_true((stages.get("report") or {}).get("status") == "pass", "smoke report stage did not pass")
        removed = find_heavy_rdata_artifacts(run_dir)
        assert_true(not removed, f"smoke retained R artifacts after cleanup: {removed[:5]}")
        summary["smoke_runs"].append(
            {
                "scope": "full_pipeline_q50",
                "status": "passed",
                "family": TARGET_FAMILY,
                "cutoff": "20210123",
                "run_root": str(run_dir),
            }
        )

    smoke_status_counts = Counter(row["status"] for row in summary["smoke_runs"])
    summary["checks"]["smoke_runs"] = {
        "count": len(summary["smoke_runs"]),
        "passed": int(smoke_status_counts.get("passed", 0)),
        "skipped": int(smoke_status_counts.get("skipped", 0)),
    }
    (outdir / "prelaunch_validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (outdir / "PRELAUNCH_VALIDATION_SUMMARY.md").write_text(
        "\n".join(
            [
                "# AL-M-T0 From exAL-M-T0 Prelaunch Validation",
                "",
                f"- artifact_root: `{artifact_root}`",
                f"- source_artifact_root: `{source_root}`",
                "- py_compile: `passed`",
                "- clone_contract: `passed`",
                "- source_rdata_cleanup: `passed`",
                f"- smoke_runs: `{summary['checks']['smoke_runs']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary["checks"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

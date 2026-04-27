#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FAMILIES = [
    "exdqlm_univar",
    "dqlm_univar_al",
]
EXPECTED_CUTOFFS = ["20210123", "20211112", "20211221", "20220511", "20221225"]


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def parse_builder_stdout(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in {"artifact_root", "matrix_dir", "config_output_dir", "generated_configs", "plan_rows", "selection_rows"}:
            out[key.strip()] = value.strip()
    return out


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def write_temp_smoke_config(src_config: Path, *, run_id: str, run_root: Path) -> Path:
    payload = load_yaml(src_config)
    payload["run"]["run_id"] = run_id
    payload["run"]["run_root"] = str(run_root)
    payload["run"]["overwrite"] = True
    payload["stages"]["forecats"] = False
    for stage in ["data_prep_shared", "fit", "post", "validate", "report"]:
        payload["stages"][stage] = True
    tmp = run_root / f"{run_id}.yaml"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return tmp


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate the HE2 univariate featurecov rerun campaign without launching it.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--outdir")
    args = ap.parse_args()

    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config).resolve()
    cfg = load_yaml(config_path)

    artifact_root = Path(cfg["campaign"]["artifact_root"]).resolve()
    default_outdir = artifact_root / "control" / f"prelaunch_validation_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    outdir = Path(args.outdir).resolve() if args.outdir else default_outdir
    outdir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "config": str(config_path),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "checks": {},
        "smoke_runs": [],
    }

    detclim = cfg.get("inputs", {}).get("deterministic_climate", {})
    handoff_root = Path(detclim.get("handoff_root", "")).resolve()
    usgs_cache_path = Path(cfg.get("inputs", {}).get("fit", {}).get("usgs_cache_path", "")).resolve()
    assert_true(detclim.get("enabled") is True, "deterministic climate must be enabled")
    assert_true(handoff_root.exists(), f"handoff_root missing: {handoff_root}")
    assert_true((handoff_root / "handoff_meta.json").exists(), f"handoff_meta.json missing under {handoff_root}")
    assert_true(usgs_cache_path.exists() and usgs_cache_path.is_file(), f"usgs_cache_path missing: {usgs_cache_path}")
    queue = cfg.get("queue", {})
    assert_true(int(queue.get("ordinary_max_concurrent", 0)) == 4, "ordinary_max_concurrent must be 4")
    assert_true(int(queue.get("heavy_cutoff_max_concurrent", 0)) == 4, "heavy_cutoff_max_concurrent must be 4")
    assert_true(bool(queue.get("heavy_cutoff_blocks_ordinary", True)) is False, "heavy_cutoff_blocks_ordinary must be false")
    summary["checks"]["config_sanity"] = "passed"

    build = run(
        [
            "python3",
            "scripts/build_multimodel_v8_all9_feature_matrix_configs.py",
            "--config",
            str(config_path),
        ],
        cwd=ROOT,
    )
    (outdir / "build_stdout.log").write_text(build.stdout, encoding="utf-8")
    (outdir / "build_stderr.log").write_text(build.stderr, encoding="utf-8")
    assert_true(build.returncode == 0, f"builder failed: {build.stderr}")
    build_info = parse_builder_stdout(build.stdout)
    matrix_dir = Path(build_info["matrix_dir"]).resolve()
    config_output_dir = Path(build_info["config_output_dir"]).resolve()
    assert_true(int(build_info["generated_configs"]) == 10, "unexpected generated config count")
    assert_true(int(build_info["plan_rows"]) == 10, "unexpected plan row count")
    summary["checks"]["builder"] = build_info

    plan_rows = list(csv.DictReader((matrix_dir / "matrix_plan.csv").open("r", encoding="utf-8")))
    selection_rows = list(csv.DictReader((matrix_dir / "selection_summary.csv").open("r", encoding="utf-8")))
    assert_true(len(plan_rows) == 10, "matrix_plan row count mismatch")
    assert_true(len(selection_rows) == 10, "selection_summary row count mismatch")
    family_counts = Counter(r["lane"] for r in plan_rows)
    cutoff_counts = Counter(r["cutoff"] for r in plan_rows)
    for family in EXPECTED_FAMILIES:
        assert_true(family_counts[family] == 5, f"unexpected family count for {family}: {family_counts[family]}")
    for cutoff in EXPECTED_CUTOFFS:
        assert_true(cutoff_counts[cutoff] == 2, f"unexpected cutoff count for {cutoff}: {cutoff_counts[cutoff]}")
    for row in selection_rows:
        assert_true(row["selected_source_type"] == "baseline_tt", f"unexpected source type in selection row: {row}")
    summary["checks"]["selection_manifest"] = "passed"

    configs = sorted(config_output_dir.glob("*.yaml"))
    assert_true(len(configs) == 10, "config output dir does not contain 10 yaml files")
    for path in configs:
        payload = load_yaml(path)
        run_flags = {
            key: bool(value)
            for key, value in payload["models"].items()
            if key.startswith("run_")
        }
        assert_true(sum(1 for value in run_flags.values() if value) == 1, f"{path.name}: expected exactly one enabled model family")
        assert_true(run_flags.get("run_exdqlm_univar") is True, f"{path.name}: run_exdqlm_univar must be true")
        covs = payload["inputs"]["fit"]["covariates"]
        names = [row["name"] for row in covs]
        assert_true(names == ["PPT", "SOIL", "PCA"], f"{path.name}: unexpected covariates {names}")
        for row in covs:
            cov_path = Path(row["path"])
            assert_true(cov_path.exists(), f"{path.name}: missing covariate path {cov_path}")
        assert_true(payload["inputs"]["deterministic_climate"]["enabled"] is True, f"{path.name}: deterministic climate must stay enabled")
        assert_true(payload["inputs"]["covariate_features"]["enabled"] is True, f"{path.name}: covariate features must stay enabled")
        assert_true(payload["inputs"]["shared"]["prefer_forecats_snapshot"] is False, f"{path.name}: prefer_forecats_snapshot must be false")
        assert_true(Path(payload["inputs"]["fit"]["usgs_cache_path"]).exists(), f"{path.name}: missing usgs cache path")
        assert_true(int(payload["run"]["threads"]["mc_cores"]) == 7, f"{path.name}: mc_cores must be 7")
        assert_true(int(payload["fit"]["parallel"]["workers"]) == 7, f"{path.name}: fit.parallel.workers must be 7")
        assert_true(payload["fit"]["parallel"]["mode"] == "global_models", f"{path.name}: unexpected fit.parallel.mode")
    summary["checks"]["generated_configs"] = {
        "count": len(configs),
        "family_counts": dict(family_counts),
        "cutoff_counts": dict(cutoff_counts),
    }

    test_cmds = [
        ["python3", "-m", "pytest", "tests/python/test_univar_featurecov_he2_rerun_tooling.py", "-q"],
        ["Rscript", "-e", 'library(testthat); test_file("tests/testthat/test_univar_featurecov_design_contract.R"); test_file("tests/testthat/test_covariate_feature_engineering.R")'],
    ]
    test_results = []
    for idx, cmd in enumerate(test_cmds, start=1):
        proc = run(cmd, cwd=ROOT)
        (outdir / f"test_{idx}.stdout.log").write_text(proc.stdout, encoding="utf-8")
        (outdir / f"test_{idx}.stderr.log").write_text(proc.stderr, encoding="utf-8")
        assert_true(proc.returncode == 0, f"test command failed: {cmd}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        test_results.append({"cmd": cmd, "returncode": proc.returncode})
    summary["checks"]["unit_tests"] = test_results

    smoke_root = outdir / "smoke_runs"
    smoke_root.mkdir(parents=True, exist_ok=True)
    first_by_family: dict[str, dict[str, str]] = {}
    for row in plan_rows:
        first_by_family.setdefault(row["lane"], row)
    for family in EXPECTED_FAMILIES:
        row = first_by_family[family]
        src_cfg = Path(row["config_path"])
        run_id = f"smoke_{family}"
        run_root = smoke_root / family
        shutil.rmtree(run_root, ignore_errors=True)
        smoke_cfg = write_temp_smoke_config(src_cfg, run_id=run_id, run_root=run_root)
        proc = run(["Rscript", "scripts/unified_run.R", "--config", str(smoke_cfg)], cwd=ROOT)
        (outdir / f"{family}.stdout.log").write_text(proc.stdout, encoding="utf-8")
        (outdir / f"{family}.stderr.log").write_text(proc.stderr, encoding="utf-8")
        assert_true(proc.returncode == 0, f"full smoke failed for {family}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        manifest = load_yaml(run_root / run_id / "run_manifest.yaml")
        for stage in ["data_prep_shared", "fit", "post", "validate", "report"]:
            status = manifest["stages"][stage]["status"]
            assert_true(status == "pass", f"{family}: stage {stage} did not pass (status={status})")
        summary["smoke_runs"].append({"family": family, "config": str(src_cfg), "run_root": str(run_root / run_id)})
    summary["checks"]["smoke_runs"] = {"count": len(summary["smoke_runs"])}

    summary_path = outdir / "prelaunch_validation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_lines = [
        "# HE2 Univariate Featurecov Rerun Prelaunch Validation",
        "",
        f"- config: `{config_path}`",
        f"- timestamp_utc: `{summary['timestamp_utc']}`",
        "",
        "## Result",
        "",
        "- status: `passed`",
        "- launch_state: `not launched by this validation`",
        "",
        "## Checks",
        "",
        f"- config sanity: `{summary['checks']['config_sanity']}`",
        f"- generated configs: `{summary['checks']['generated_configs']['count']}`",
        f"- selection manifest: `{summary['checks']['selection_manifest']}`",
        f"- smoke runs: `{summary['checks']['smoke_runs']['count']}`",
        "",
        "## Families smoke-tested",
        "",
    ]
    for row in summary["smoke_runs"]:
        md_lines.append(f"- `{row['family']}` via `{Path(row['config']).name}`")
    md_lines.append("")
    md_lines.append(f"- summary_json: `{summary_path}`")
    (outdir / "prelaunch_validation_summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"validation_outdir={outdir}")
    print(f"summary_json={summary_path}")
    print("status=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

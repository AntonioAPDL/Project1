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
    "ndlm_main_keep",
    "ndlm_main_drop",
    "ndlm_univar_keep",
]
EXPECTED_CUTOFFS = ["20210123", "20211112", "20211221", "20220511", "20221225"]
PREFERRED_SMOKE_CUTOFF = "20211112"


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def parse_builder_stdout(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() in {
            "artifact_root",
            "matrix_dir",
            "config_output_dir",
            "generated_configs",
            "plan_rows",
            "selection_rows",
            "spec_rows",
        }:
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
    for stage in ["forecats", "validate", "report"]:
        payload["stages"][stage] = False
    payload["stages"]["data_prep_shared"] = True
    payload["stages"]["fit"] = True
    payload["stages"]["post"] = True
    tmp = run_root / f"{run_id}.yaml"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return tmp


def choose_smoke_row(plan_rows: list[dict[str, str]], family: str) -> dict[str, str]:
    family_rows = [row for row in plan_rows if row["lane"] == family]
    preferred = [row for row in family_rows if row["cutoff"] == PREFERRED_SMOKE_CUTOFF]
    if preferred:
        return preferred[0]
    return family_rows[0]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Validate the corrected NDLM-only featurecov rerun without launching the queue."
    )
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
    fallback_usgs = Path(cfg.get("inputs", {}).get("fit", {}).get("usgs_cache_path", "")).resolve()
    assert_true(detclim.get("enabled") is True, "deterministic climate must be enabled")
    assert_true(handoff_root.exists(), f"handoff_root missing: {handoff_root}")
    assert_true((handoff_root / "handoff_meta.json").exists(), "handoff_meta.json missing")
    assert_true(fallback_usgs.exists() and fallback_usgs.is_file(), f"fallback usgs_cache_path missing: {fallback_usgs}")
    cov_features = cfg.get("inputs", {}).get("covariate_features", {})
    assert_true(cov_features.get("enabled") is True, "covariate_features must be enabled")
    assert_true(cov_features.get("lag_orders") == [1, 2, 3], "unexpected lag orders")
    assert_true(cov_features.get("include_squares") is True, "include_squares must be enabled")
    assert_true(cov_features.get("include_interaction") is True, "include_interaction must be enabled")
    summary["checks"]["config_sanity"] = "passed"

    build = run(
        [
            "python3",
            "scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py",
            "--config",
            str(config_path),
        ],
        cwd=ROOT,
    )
    (outdir / "build_stdout.log").write_text(build.stdout, encoding="utf-8")
    (outdir / "build_stderr.log").write_text(build.stderr, encoding="utf-8")
    assert_true(build.returncode == 0, f"builder failed\nSTDOUT:\n{build.stdout}\nSTDERR:\n{build.stderr}")
    build_info = parse_builder_stdout(build.stdout)
    matrix_dir = Path(build_info["matrix_dir"]).resolve()
    config_output_dir = Path(build_info["config_output_dir"]).resolve()
    assert_true(int(build_info["generated_configs"]) == 15, "unexpected generated config count")
    assert_true(int(build_info["plan_rows"]) == 15, "unexpected plan row count")
    assert_true(int(build_info["selection_rows"]) == 15, "unexpected selection_summary row count")
    summary["checks"]["builder"] = build_info

    plan_rows = list(csv.DictReader((matrix_dir / "matrix_plan.csv").open("r", encoding="utf-8")))
    selection_rows = list(csv.DictReader((matrix_dir / "selection_summary.csv").open("r", encoding="utf-8")))
    spec_rows = list(csv.DictReader((matrix_dir / "spec_parameter_table.csv").open("r", encoding="utf-8")))
    assert_true(len(plan_rows) == 15, "matrix_plan row count mismatch")
    assert_true(len(selection_rows) == 15, "selection_summary row count mismatch")
    assert_true(len(spec_rows) >= 20, "spec_parameter_table looks too small")

    family_counts = Counter(row["lane"] for row in plan_rows)
    cutoff_counts = Counter(row["cutoff"] for row in plan_rows)
    for family in EXPECTED_FAMILIES:
        assert_true(family_counts[family] == 5, f"unexpected family count for {family}: {family_counts[family]}")
    for cutoff in EXPECTED_CUTOFFS:
        assert_true(cutoff_counts[cutoff] == 3, f"unexpected cutoff count for {cutoff}: {cutoff_counts[cutoff]}")

    configs = sorted(config_output_dir.glob("*.yaml"))
    assert_true(len(configs) == 15, "config output dir does not contain 15 yaml files")
    for path in configs:
        payload = load_yaml(path)
        covs = payload["inputs"]["fit"]["covariates"]
        names = [row["name"] for row in covs]
        assert_true(names == ["PPT", "SOIL", "PCA"], f"{path.name}: unexpected covariates {names}")
        for row in covs:
            cov_path = Path(row["path"])
            assert_true(cov_path.exists(), f"{path.name}: missing covariate path {cov_path}")
        usgs_cache_path = Path(payload["inputs"]["fit"]["usgs_cache_path"])
        assert_true(
            usgs_cache_path.exists() and usgs_cache_path.is_file(),
            f"{path.name}: missing usgs_cache_path {usgs_cache_path}",
        )
        assert_true(payload["inputs"]["deterministic_climate"]["enabled"] is True, f"{path.name}: deterministic climate disabled")
        assert_true(payload["inputs"]["deterministic_climate"]["handoff_root"] == str(handoff_root), f"{path.name}: handoff_root mismatch")
        assert_true(payload["inputs"]["covariate_features"]["enabled"] is True, f"{path.name}: covariate_features disabled")
        assert_true(payload["inputs"]["covariate_features"]["lag_orders"] == [1, 2, 3], f"{path.name}: lag orders mismatch")
        if payload["models"]["run_ndlm_main"]:
            prior = payload["models"]["ndlm_main"]["prior"]["forecast_cov"]
            assert_true(prior["dof_offset"] == 4, f"{path.name}: dof_offset mismatch")
            assert_true(float(prior["scale_mult"]) == 1.0, f"{path.name}: scale_mult mismatch")
            assert_true(
                float(payload["models"]["ndlm_main"]["state_evolution"]["df_covs"]) == 0.99999999,
                f"{path.name}: ndlm_main df_covs mismatch",
            )
        if payload["models"]["run_ndlm_univar"]:
            prior = payload["models"]["ndlm_univar"]["prior"]
            assert_true(prior["n0"] == 20, f"{path.name}: n0 mismatch")
            assert_true(prior["S0"] == 1, f"{path.name}: S0 mismatch")
            assert_true(
                float(payload["models"]["ndlm_univar"]["state_evolution"]["df_covs"]) == 0.99999999,
                f"{path.name}: ndlm_univar df_covs mismatch",
            )
    summary["checks"]["generated_configs"] = {
        "count": len(configs),
        "family_counts": dict(family_counts),
        "cutoff_counts": dict(cutoff_counts),
    }

    test_cmds = [
        [
            "python3",
            "-m",
            "unittest",
            "tests.python.test_ndlm_wishart_prior_audit",
            "tests.python.test_ndlm_featurecov_rerun_builder",
        ],
        [
            "Rscript",
            "-e",
            'testthat::test_file("tests/testthat/test_ndlm_fitloop_contract.R");'
            'testthat::test_file("tests/testthat/test_ndlm_save_state.R")',
        ],
    ]
    test_results = []
    for idx, cmd in enumerate(test_cmds, start=1):
        proc = run(cmd, cwd=ROOT)
        (outdir / f"test_{idx}.stdout.log").write_text(proc.stdout, encoding="utf-8")
        (outdir / f"test_{idx}.stderr.log").write_text(proc.stderr, encoding="utf-8")
        assert_true(
            proc.returncode == 0,
            f"test command failed: {cmd}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )
        test_results.append({"cmd": cmd, "returncode": proc.returncode})
    summary["checks"]["unit_tests"] = test_results

    smoke_root = outdir / "smoke_runs"
    smoke_root.mkdir(parents=True, exist_ok=True)
    for family in EXPECTED_FAMILIES:
        row = choose_smoke_row(plan_rows, family)
        src_cfg = Path(row["config_path"])
        run_id = f"smoke_{family}"
        run_root = smoke_root / family
        shutil.rmtree(run_root, ignore_errors=True)
        smoke_cfg = write_temp_smoke_config(src_cfg, run_id=run_id, run_root=run_root)
        proc = run(["Rscript", "scripts/unified_run.R", "--config", str(smoke_cfg)], cwd=ROOT)
        (outdir / f"{family}.stdout.log").write_text(proc.stdout, encoding="utf-8")
        (outdir / f"{family}.stderr.log").write_text(proc.stderr, encoding="utf-8")
        assert_true(
            proc.returncode == 0,
            f"smoke failed for {family}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )
        shared_root = run_root / run_id / "inputs" / "shared"
        assert_true(
            (shared_root / "covariates" / "covariate_features.csv").exists(),
            f"{family}: missing engineered covariate features",
        )
        assert_true(
            (shared_root / "deterministic_climate" / "deterministic_climate_summary.txt").exists(),
            f"{family}: missing deterministic-climate summary",
        )
        assert_true(
            (run_root / run_id / "post" / "logs" / "post_runner.log").exists(),
            f"{family}: missing post runner log",
        )
        summary["smoke_runs"].append(
            {
                "family": family,
                "cutoff": row["cutoff"],
                "config": str(src_cfg),
                "shared_root": str(shared_root),
                "post_log": str(run_root / run_id / "post" / "logs" / "post_runner.log"),
            }
        )
    summary["checks"]["smoke_runs"] = {"count": len(summary["smoke_runs"])}

    summary_path = outdir / "prelaunch_validation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_lines = [
        "# NDLM Featurecov Rerun Prelaunch Validation",
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
        f"- smoke runs: `{summary['checks']['smoke_runs']['count']}`",
        "",
        "## Families smoke-tested through post",
        "",
    ]
    for row in summary["smoke_runs"]:
        md_lines.append(f"- `{row['family']}` via cutoff `{row['cutoff']}`")
    md_lines.extend(
        [
            "",
            f"- summary_json: `{summary_path}`",
        ]
    )
    (outdir / "prelaunch_validation_summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"validation_outdir={outdir}")
    print(f"summary_json={summary_path}")
    print("status=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

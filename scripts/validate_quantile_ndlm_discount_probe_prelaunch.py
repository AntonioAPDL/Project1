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

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FAMILIES = [
    "exdqlm_multivar_keep",
    "exdqlm_multivar_drop",
    "dqlm_multivar_al_keep",
    "dqlm_multivar_al_drop",
    "exdqlm_univar",
    "dqlm_univar_al",
]
EXPECTED_CUTOFFS = ["20210123", "20211112", "20211221", "20220511", "20221225"]
EXPECTED_EPSILON = {
    ("20210123", "dqlm_multivar_al_drop"): "eps30cf1",
    ("20210123", "exdqlm_multivar_drop"): "eps30cf1",
    ("20210123", "dqlm_multivar_al_keep"): "eps180cf1",
    ("20210123", "exdqlm_multivar_keep"): "eps360cf1",
    ("20210123", "dqlm_univar_al"): "univar_featurecov_he2_v1",
    ("20210123", "exdqlm_univar"): "univar_featurecov_he2_v1",
    ("20211112", "dqlm_multivar_al_drop"): "eps30cf1",
    ("20211112", "exdqlm_multivar_drop"): "eps30cf1",
    ("20211112", "dqlm_multivar_al_keep"): "eps180cf1",
    ("20211112", "exdqlm_multivar_keep"): "eps180cf1",
    ("20211112", "dqlm_univar_al"): "univar_featurecov_he2_v1",
    ("20211112", "exdqlm_univar"): "univar_featurecov_he2_v1",
    ("20211221", "dqlm_multivar_al_drop"): "eps360cf1",
    ("20211221", "exdqlm_multivar_drop"): "eps1cf1",
    ("20211221", "dqlm_multivar_al_keep"): "eps1cf1",
    ("20211221", "exdqlm_multivar_keep"): "eps1cf1",
    ("20211221", "dqlm_univar_al"): "univar_featurecov_he2_v1",
    ("20211221", "exdqlm_univar"): "univar_featurecov_he2_v1",
    ("20220511", "dqlm_multivar_al_drop"): "eps30cf1",
    ("20220511", "exdqlm_multivar_drop"): "eps30cf1",
    ("20220511", "dqlm_multivar_al_keep"): "eps90cf1",
    ("20220511", "exdqlm_multivar_keep"): "eps180cf1",
    ("20220511", "dqlm_univar_al"): "univar_featurecov_he2_v1",
    ("20220511", "exdqlm_univar"): "univar_featurecov_he2_v1",
    ("20221225", "dqlm_multivar_al_drop"): "eps1cf1",
    ("20221225", "exdqlm_multivar_drop"): "eps1cf1",
    ("20221225", "dqlm_multivar_al_keep"): "eps360cf1",
    ("20221225", "exdqlm_multivar_keep"): "eps360cf1",
    ("20221225", "dqlm_univar_al"): "univar_featurecov_he2_v1",
    ("20221225", "exdqlm_univar"): "univar_featurecov_he2_v1",
}
EXPECTED_FEATURE_COLS = {
    "PPT",
    "SOIL",
    "PCA",
    "PPT_sq",
    "SOIL_sq",
    "PPT_x_SOIL",
    "PPT_lag1",
    "PPT_lag2",
    "PPT_lag3",
    "SOIL_lag1",
    "SOIL_lag2",
    "SOIL_lag3",
}


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def parse_builder_stdout(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in {"artifact_root", "matrix_dir", "config_output_dir", "generated_configs", "plan_rows", "selection_rows", "spec_rows"}:
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
    for stage in ["forecats", "fit", "post", "validate", "report"]:
        payload["stages"][stage] = False
    payload["stages"]["data_prep_shared"] = True
    tmp = run_root / f"{run_id}.yaml"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return tmp


def _expected_state_overrides(cfg: dict[str, Any], *, family_id: str) -> dict[str, Any]:
    model_overrides = cfg.get("model_overrides", {}) or {}
    if "multivar" in family_id:
        return (
            model_overrides.get("exdqlm_multivar", {}) or {}
        ).get("state_evolution", {}) or {}
    return (
        model_overrides.get("exdqlm_univar", {}) or {}
    ).get("state_evolution", {}) or {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate the corrected quantile NDLM-discount probe campaign without launching it.")
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

    selection_cfg = cfg.get("selection", {})
    parity_matrix_path = (ROOT / selection_cfg["parity_matrix_path"]).resolve()
    fallback_usgs = Path(cfg["inputs"]["fit"]["usgs_cache_path"]).resolve()
    multivar_artifact_root = Path(selection_cfg["multivar_artifact_root"]).resolve()
    univar_artifact_root = Path(selection_cfg["univar_artifact_root"]).resolve()
    univar_compare_root = Path(selection_cfg["univar_compare_root"]).resolve()
    assert_true(parity_matrix_path.exists(), f"parity matrix missing: {parity_matrix_path}")
    assert_true(fallback_usgs.exists() and fallback_usgs.is_file(), f"fallback usgs_cache_path missing: {fallback_usgs}")
    assert_true(multivar_artifact_root.exists(), f"missing multivar artifact root: {multivar_artifact_root}")
    assert_true(univar_artifact_root.exists(), f"missing univar artifact root: {univar_artifact_root}")
    assert_true(univar_compare_root.exists(), f"missing univar compare root: {univar_compare_root}")
    for cutoff in EXPECTED_CUTOFFS:
        compare_dir = Path(cfg["cutoffs"][cutoff]["authoritative_compare_dir"]).resolve()
        assert_true(compare_dir.exists(), f"authoritative compare dir missing: {compare_dir}")
        assert_true((compare_dir / "crps_forecast_summary_all_models.csv").exists(), f"compare bundle incomplete: {compare_dir}")
    summary["checks"]["config_sanity"] = "passed"

    build = run(
        [
            "python3",
            "scripts/build_multimodel_v8_quantile_ndlm_discount_probe_matrix_configs.py",
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
    assert_true(int(build_info["generated_configs"]) == 30, "unexpected generated config count")
    assert_true(int(build_info["plan_rows"]) == 30, "unexpected plan row count")
    summary["checks"]["builder"] = build_info

    plan_rows = list(csv.DictReader((matrix_dir / "matrix_plan.csv").open("r", encoding="utf-8")))
    selection_rows = list(csv.DictReader((matrix_dir / "selection_summary.csv").open("r", encoding="utf-8")))
    assert_true(len(plan_rows) == 30, "matrix_plan row count mismatch")
    assert_true(len(selection_rows) == 30, "selection_summary row count mismatch")
    family_counts = Counter(r["lane"] for r in plan_rows)
    cutoff_counts = Counter(r["cutoff"] for r in plan_rows)
    for family in EXPECTED_FAMILIES:
        assert_true(family_counts[family] == 5, f"unexpected family count for {family}: {family_counts[family]}")
    for cutoff in EXPECTED_CUTOFFS:
        assert_true(cutoff_counts[cutoff] == 6, f"unexpected cutoff count for {cutoff}: {cutoff_counts[cutoff]}")

    observed_eps = {(row["cutoff"], row["family_id"]): row["epsilon"] for row in selection_rows}
    assert_true(observed_eps == EXPECTED_EPSILON, f"best-epsilon selections drifted: {observed_eps}")
    source_types = {(row["cutoff"], row["family_id"]): row["selected_source_type"] for row in selection_rows}
    for cutoff in EXPECTED_CUTOFFS:
        for family in EXPECTED_FAMILIES:
            source_type = source_types[(cutoff, family)]
            if "univar" in family:
                assert_true(source_type == "featurecov_relaunch", f"{cutoff}/{family}: expected featurecov_relaunch, got {source_type}")
            else:
                assert_true(source_type == "featurecov_cf1_eps_sweep", f"{cutoff}/{family}: expected featurecov_cf1_eps_sweep, got {source_type}")
    summary["checks"]["selection_manifest"] = "passed"

    configs = sorted(config_output_dir.glob("*.yaml"))
    assert_true(len(configs) == 30, "config output dir does not contain 30 yaml files")
    for path in configs:
        payload = load_yaml(path)
        family_id = payload["debug_quantile_ndlm_discount_probe"]["family_id"]
        covs = payload["inputs"]["fit"]["covariates"]
        names = [row["name"] for row in covs]
        usgs_cache_path = Path(payload["inputs"]["fit"]["usgs_cache_path"])
        covfeat = payload["inputs"]["covariate_features"]
        assert_true(usgs_cache_path.exists() and usgs_cache_path.is_file(), f"{path.name}: missing usgs_cache_path {usgs_cache_path}")
        assert_true(payload["run"]["repro_mode"] == "strict", f"{path.name}: repro_mode should be strict")
        assert_true(int(payload["run"]["threads"]["mc_cores"]) == 7, f"{path.name}: mc_cores should be 7")
        assert_true(int(payload["fit"]["parallel"]["workers"]) == 7, f"{path.name}: fit.parallel.workers should be 7")
        assert_true(payload["fit"]["parallel"]["mode"] == "global_models", f"{path.name}: unexpected fit.parallel.mode")
        assert_true(names == ["PPT", "SOIL", "PCA"], f"{path.name}: covariates drifted {names}")
        assert_true(payload["inputs"]["deterministic_climate"]["enabled"] is True, f"{path.name}: deterministic climate must stay enabled")
        assert_true(covfeat["enabled"] is True, f"{path.name}: covariate_features must stay enabled")
        assert_true(covfeat["lag_orders"] == [1, 2, 3], f"{path.name}: lag orders mismatch")
        assert_true(covfeat["include_squares"] is True, f"{path.name}: squares disabled")
        assert_true(covfeat["include_interaction"] is True, f"{path.name}: interaction disabled")

        run_flags = {key: bool(value) for key, value in payload["models"].items() if key.startswith("run_")}
        assert_true(sum(1 for value in run_flags.values() if value) == 1, f"{path.name}: expected exactly one enabled model family")

        expected_state = _expected_state_overrides(cfg, family_id=family_id)

        if "multivar" in family_id:
            state = payload["models"]["exdqlm_multivar"]["state_evolution"]
        else:
            state = payload["models"]["exdqlm_univar"]["state_evolution"]
            assert_true("df_discrep" not in state, f"{path.name}: univar should not gain df_discrep")

        for key, expected_value in expected_state.items():
            assert_true(key in state, f"{path.name}: missing expected state override {key}")
            assert_true(float(state[key]) == float(expected_value), f"{path.name}: {key} drifted")
    summary["checks"]["generated_configs"] = {
        "count": len(configs),
        "family_counts": dict(family_counts),
        "cutoff_counts": dict(cutoff_counts),
    }

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
        assert_true(proc.returncode == 0, f"smoke failed for {family}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        shared_root = run_root / run_id / "inputs" / "shared"
        feature_path = shared_root / "covariates" / "covariate_features.csv"
        assert_true((shared_root / "parameters" / "parameters.txt").exists(), f"{family}: missing shared parameters")
        assert_true((shared_root / "retros" / "retros.csv").exists(), f"{family}: missing shared retros")
        assert_true((shared_root / "forecasts" / "nws_forecast.csv").exists(), f"{family}: missing shared nws")
        assert_true((shared_root / "forecasts" / "glofas_forecast.csv").exists(), f"{family}: missing shared glofas")
        assert_true((shared_root / "usgs" / "usgs_daily.csv").exists(), f"{family}: missing shared usgs")
        assert_true(feature_path.exists(), f"{family}: missing engineered covariate features")
        columns = set(pd.read_csv(feature_path, nrows=1).columns)
        assert_true(EXPECTED_FEATURE_COLS.issubset(columns), f"{family}: engineered feature columns drifted {columns}")
        summary["smoke_runs"].append({"family": family, "config": str(src_cfg), "shared_root": str(shared_root)})
    summary["checks"]["smoke_runs"] = {"count": len(summary["smoke_runs"])}

    summary_path = outdir / "prelaunch_validation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_lines = [
        "# Quantile Discount-Probe Prelaunch Validation",
        "",
        f"- config: `{config_path}`",
        f"- timestamp_utc: `{summary['timestamp_utc']}`",
        f"- campaign_id: `{cfg['campaign']['campaign_id']}`",
        f"- spec_id: `{cfg['campaign']['spec_id']}`",
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
        f"- selection manifest parity: `{summary['checks']['selection_manifest']}`",
        f"- smoke runs: `{summary['checks']['smoke_runs']['count']}`",
        "",
        "## Selection contract",
        "",
        "- multivariate rows come from the actual executed `featurecov_cf1_eps_sweep` HE2 source runs for the best epsilon of each cutoff/family.",
        "- univariate rows come from the finished `univar_featurecov_he2_v1` rerun compare bundles.",
        "- every generated config stays on the proper blended-featurecov contract: `PPT`, `SOIL`, `PCA`, deterministic climate on, lag/square/interaction engineered terms on.",
        "- the applied discount overrides are validated directly against the template `model_overrides` block.",
        "",
        "## Parallelism contract",
        "",
        "- one core per quantile model: `fit_parallel_workers = 7`",
        "- row batching: `ordinary_max_concurrent = 4`",
        "- peak fit-core budget: `28`",
    ]
    (outdir / "prelaunch_validation_summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(json.dumps({"outdir": str(outdir), "summary": str(summary_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

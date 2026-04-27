#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
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
FAMILY_ID = "exdqlm_multivar_keep"
MODEL_ID = "exdqlm_multivar_synth_keep"
EXPECTED_CUTOFFS = ["20210123", "20211112", "20211221", "20220511", "20221225"]
EXPECTED_SOURCE_EPSILON = {
    "20210123": "eps360cf1",
    "20211112": "eps180cf1",
    "20211221": "eps1cf1",
    "20220511": "eps180cf1",
    "20221225": "eps360cf1",
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
SMOKE_CASES = [
    ("set01", "20210123"),
    ("set04", "20211221"),
    ("set09", "20221225"),
]


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def parse_builder_stdout(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    keys = {"artifact_root", "matrix_dir", "config_output_dir", "generated_configs", "plan_rows", "selection_rows", "spec_rows"}
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in keys:
            out[key.strip()] = value.strip()
    return out


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def write_temp_smoke_config(
    src_config: Path,
    *,
    run_id: str,
    run_root: Path,
    enabled_stages: list[str] | None = None,
) -> Path:
    payload = load_yaml(src_config)
    payload["run"]["run_id"] = run_id
    payload["run"]["run_root"] = str(run_root)
    payload["run"]["overwrite"] = True
    enabled = set(enabled_stages or ["data_prep_shared"])
    for stage in ["forecats", "fit", "post", "validate", "report"]:
        payload["stages"][stage] = stage in enabled
    payload["stages"]["data_prep_shared"] = "data_prep_shared" in enabled
    tmp = run_root / f"{run_id}.yaml"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return tmp


def _profile_state_by_name(cfg: dict[str, Any]) -> dict[str, dict[str, float]]:
    profiles = cfg.get("discount_profiles", [])
    out: dict[str, dict[str, float]] = {}
    for raw in profiles:
        name = str(raw["name"])
        out[name] = {key: float(value) for key, value in raw["state_evolution"].items()}
    return out


def _scientific_contract_view(cfg: dict[str, Any]) -> dict[str, Any]:
    model_cfg = cfg["models"]["exdqlm_multivar"]
    model_nonstate = {
        key: value
        for key, value in model_cfg.items()
        if key != "state_evolution" and not (key == "forecast_transfer_modes" and value is None)
    }
    return {
        "fit_parallel": cfg["fit"]["parallel"],
        "fit_quantiles": cfg["fit"]["quantiles"],
        "fit_legacy": cfg["fit"]["exdqlm_multivar"]["legacy"],
        "inputs_fit_covariate_names": [row["name"] for row in cfg["inputs"]["fit"]["covariates"]],
        "inputs_deterministic_climate": cfg["inputs"]["deterministic_climate"],
        "inputs_covariate_features": cfg["inputs"]["covariate_features"],
        "model_multivar_nonstate": model_nonstate,
        "scale_contract": cfg["scale_contract"],
    }


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_tree(root: Path) -> dict[str, str]:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    return {str(path.relative_to(root)): _file_sha256(path) for path in files}


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate the exAL-M-T1 discount-grid campaign before launching it.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--outdir")
    ap.add_argument("--with-fit-smoke", action="store_true")
    args = ap.parse_args()

    config_path = (ROOT / args.config).resolve() if not Path(args.config).is_absolute() else Path(args.config).resolve()
    cfg = load_yaml(config_path)
    profile_state = _profile_state_by_name(cfg)
    profile_names = list(profile_state)

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
    compare_builder = (ROOT / cfg["compare"]["builder"]).resolve()
    assert_true(parity_matrix_path.exists(), f"parity matrix missing: {parity_matrix_path}")
    assert_true(fallback_usgs.exists() and fallback_usgs.is_file(), f"fallback usgs_cache_path missing: {fallback_usgs}")
    assert_true(multivar_artifact_root.exists(), f"missing multivar artifact root: {multivar_artifact_root}")
    assert_true(compare_builder.exists() and compare_builder.is_file(), f"compare builder missing: {compare_builder}")
    assert_true(profile_names == [f"set{i:02d}" for i in range(1, 10)], f"unexpected discount profile names: {profile_names}")
    assert_true(cfg["queue"]["ordinary_max_concurrent"] == 4, "ordinary_max_concurrent must stay 4")
    assert_true(cfg["queue"]["heavy_cutoff_max_concurrent"] == 4, "heavy_cutoff_max_concurrent must stay 4")
    assert_true(cfg["queue"]["heavy_cutoff_blocks_ordinary"] is False, "heavy cutoff should not block ordinary rows")
    for cutoff in EXPECTED_CUTOFFS:
        compare_dir = Path(cfg["cutoffs"][cutoff]["authoritative_compare_dir"]).resolve()
        assert_true(compare_dir.exists(), f"authoritative compare dir missing: {compare_dir}")
        assert_true((compare_dir / "crps_forecast_summary_all_models.csv").exists(), f"compare bundle incomplete: {compare_dir}")
    enabled_families = [name for name, fam in cfg["families"].items() if fam.get("enabled", True)]
    assert_true(enabled_families == [FAMILY_ID], f"only {FAMILY_ID} should be enabled; got {enabled_families}")
    summary["checks"]["config_sanity"] = "passed"

    build = run(
        [
            "python3",
            "scripts/build_multimodel_v8_exalm_t1_discount_grid_configs.py",
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
    expected_rows = len(EXPECTED_CUTOFFS) * len(profile_names)
    assert_true(int(build_info["generated_configs"]) == expected_rows, "unexpected generated config count")
    assert_true(int(build_info["plan_rows"]) == expected_rows, "unexpected plan row count")
    summary["checks"]["builder"] = build_info

    plan_rows = list(csv.DictReader((matrix_dir / "matrix_plan.csv").open("r", encoding="utf-8")))
    selection_rows = list(csv.DictReader((matrix_dir / "selection_summary.csv").open("r", encoding="utf-8")))
    assert_true(len(plan_rows) == expected_rows, "matrix_plan row count mismatch")
    assert_true(len(selection_rows) == expected_rows, "selection_summary row count mismatch")
    family_counts = Counter(r["lane"] for r in plan_rows)
    cutoff_counts = Counter(r["cutoff"] for r in plan_rows)
    profile_counts = Counter(r["discount_set"] for r in plan_rows)
    source_eps = {(row["cutoff"], row["discount_set"]): row["source_epsilon"] for row in plan_rows}
    assert_true(family_counts == Counter({FAMILY_ID: expected_rows}), f"unexpected family counts: {family_counts}")
    assert_true(cutoff_counts == Counter({cutoff: len(profile_names) for cutoff in EXPECTED_CUTOFFS}), f"unexpected cutoff counts: {cutoff_counts}")
    assert_true(profile_counts == Counter({profile: len(EXPECTED_CUTOFFS) for profile in profile_names}), f"unexpected profile counts: {profile_counts}")
    for cutoff in EXPECTED_CUTOFFS:
        for profile in profile_names:
            assert_true(source_eps[(cutoff, profile)] == EXPECTED_SOURCE_EPSILON[cutoff], f"{cutoff}/{profile}: source epsilon drifted")
    compare_cells = {(row["cutoff"], row["epsilon"]) for row in plan_rows}
    assert_true(len(compare_cells) == expected_rows, "compare cells must be unique by cutoff/profile source label")
    summary["checks"]["selection_manifest"] = "passed"

    configs = sorted(config_output_dir.glob("*.yaml"))
    assert_true(len(configs) == expected_rows, f"config output dir does not contain {expected_rows} yaml files")
    config_by_case: dict[tuple[str, str], Path] = {}
    source_contract_checks: list[dict[str, Any]] = []
    for path in configs:
        payload = load_yaml(path)
        debug = payload["debug_exalm_t1_discount_grid"]
        discount_set = debug["discount_set"]
        source_epsilon = debug["source_epsilon_label"]
        cutoff = str(payload["run"]["run_id"]).split("_")[1]
        config_by_case[(discount_set, cutoff)] = path
        source_cfg_path = Path(payload["debug_quantile_ndlm_discount_probe"]["selected_source_config"])
        source_cfg = load_yaml(source_cfg_path)
        expected_snapshot_root = source_cfg_path.parent / "inputs" / "shared"
        covs = payload["inputs"]["fit"]["covariates"]
        names = [row["name"] for row in covs]
        covfeat = payload["inputs"]["covariate_features"]
        exact_snapshot_root = Path(payload["inputs"]["shared"]["exact_source_snapshot_root"])
        assert_true(payload["run"]["repro_mode"] == "strict", f"{path.name}: repro_mode should be strict")
        assert_true(exact_snapshot_root == expected_snapshot_root, f"{path.name}: exact snapshot root drifted")
        assert_true(exact_snapshot_root.exists() and exact_snapshot_root.is_dir(), f"{path.name}: exact snapshot root missing")
        assert_true(names == ["PPT", "SOIL", "PCA"], f"{path.name}: covariates drifted {names}")
        assert_true(payload["inputs"]["deterministic_climate"]["enabled"] is True, f"{path.name}: deterministic climate must stay enabled")
        assert_true(covfeat["enabled"] is True, f"{path.name}: covariate_features must stay enabled")
        assert_true(covfeat["lag_orders"] == [1, 2, 3], f"{path.name}: lag orders mismatch")
        assert_true(covfeat["include_squares"] is True, f"{path.name}: squares disabled")
        assert_true(covfeat["include_interaction"] is True, f"{path.name}: interaction disabled")
        assert_true(source_epsilon == EXPECTED_SOURCE_EPSILON[cutoff], f"{path.name}: source epsilon drifted")

        run_flags = {key: bool(value) for key, value in payload["models"].items() if key.startswith("run_")}
        assert_true(run_flags == {
            "run_exdqlm_multivar": True,
            "run_exdqlm_univar": False,
            "run_ndlm_main": False,
            "run_ndlm_univar": False,
        }, f"{path.name}: expected only exdqlm_multivar enabled, got {run_flags}")
        assert_true(payload["models"]["exdqlm_multivar"]["likelihood_mode"] == "exal", f"{path.name}: likelihood must be exal")
        assert_true(payload["models"]["exdqlm_multivar"]["forecast_transfer_mode"] == "keep", f"{path.name}: transfer must be keep")
        state = payload["models"]["exdqlm_multivar"]["state_evolution"]
        for key, expected_value in profile_state[discount_set].items():
            assert_true(key in state, f"{path.name}: missing state override {key}")
            assert_true(float(state[key]) == float(expected_value), f"{path.name}: {key} drifted")
        assert_true(
            _scientific_contract_view(payload) == _scientific_contract_view(source_cfg),
            f"{path.name}: scientific contract drifted from selected HE source config",
        )
        source_contract_checks.append(
            {
                "discount_set": discount_set,
                "cutoff": cutoff,
                "source_config": str(source_cfg_path),
                "exact_snapshot_root": str(exact_snapshot_root),
                "fit_parallel_workers": int(payload["fit"]["parallel"]["workers"]),
                "source_fit_parallel_workers": int(source_cfg["fit"]["parallel"]["workers"]),
            }
        )
    summary["checks"]["generated_configs"] = {
        "count": len(configs),
        "family_counts": dict(family_counts),
        "cutoff_counts": dict(cutoff_counts),
        "profile_counts": dict(profile_counts),
        "source_contract_checks": source_contract_checks,
    }

    smoke_root = outdir / "smoke_runs"
    smoke_root.mkdir(parents=True, exist_ok=True)
    for discount_set, cutoff in SMOKE_CASES:
        src_cfg = config_by_case[(discount_set, cutoff)]
        src_payload = load_yaml(src_cfg)
        source_cfg_path = Path(src_payload["debug_quantile_ndlm_discount_probe"]["selected_source_config"])
        source_shared_root = source_cfg_path.parent / "inputs" / "shared"
        run_id = f"smoke_exalm_t1_{discount_set}_{cutoff}"
        run_root = smoke_root / f"{discount_set}_{cutoff}"
        shutil.rmtree(run_root, ignore_errors=True)
        smoke_cfg = write_temp_smoke_config(src_cfg, run_id=run_id, run_root=run_root)
        proc = run(["Rscript", "scripts/unified_run.R", "--config", str(smoke_cfg)], cwd=ROOT)
        (outdir / f"{discount_set}_{cutoff}.stdout.log").write_text(proc.stdout, encoding="utf-8")
        (outdir / f"{discount_set}_{cutoff}.stderr.log").write_text(proc.stderr, encoding="utf-8")
        assert_true(proc.returncode == 0, f"smoke failed for {discount_set}/{cutoff}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        shared_root = run_root / run_id / "inputs" / "shared"
        smoke_manifest = load_yaml(run_root / run_id / "run_manifest.yaml")
        feature_path = shared_root / "covariates" / "covariate_features.csv"
        assert_true((shared_root / "parameters" / "parameters.txt").exists(), f"{discount_set}/{cutoff}: missing shared parameters")
        assert_true((shared_root / "retros" / "retros.csv").exists(), f"{discount_set}/{cutoff}: missing shared retros")
        assert_true((shared_root / "forecasts" / "nws_forecast.csv").exists(), f"{discount_set}/{cutoff}: missing shared nws")
        assert_true((shared_root / "forecasts" / "glofas_forecast.csv").exists(), f"{discount_set}/{cutoff}: missing shared glofas")
        assert_true((shared_root / "usgs" / "usgs_daily.csv").exists(), f"{discount_set}/{cutoff}: missing shared usgs")
        assert_true(feature_path.exists(), f"{discount_set}/{cutoff}: missing engineered covariate features")
        manifest_inputs = {
            Path(row["path"]).resolve(): row["storage_scale"]
            for row in smoke_manifest.get("inputs", [])
            if isinstance(row, dict) and row.get("path") and row.get("storage_scale")
        }
        assert_true(
            manifest_inputs.get((shared_root / "retros" / "retros.csv").resolve()) == src_payload["inputs"]["fit"]["retros_storage_scale"],
            f"{discount_set}/{cutoff}: retros storage_scale drifted in manifest",
        )
        assert_true(
            manifest_inputs.get((shared_root / "forecasts" / "nws_forecast.csv").resolve()) == src_payload["inputs"]["fit"]["nws_storage_scale"],
            f"{discount_set}/{cutoff}: nws storage_scale drifted in manifest",
        )
        assert_true(
            manifest_inputs.get((shared_root / "forecasts" / "glofas_forecast.csv").resolve()) == src_payload["inputs"]["fit"]["glofas_storage_scale"],
            f"{discount_set}/{cutoff}: glofas storage_scale drifted in manifest",
        )
        assert_true(
            manifest_inputs.get((shared_root / "usgs" / "usgs_daily.csv").resolve()) == "raw_cms",
            f"{discount_set}/{cutoff}: usgs storage_scale drifted in manifest",
        )
        columns = set(pd.read_csv(feature_path, nrows=1).columns)
        assert_true(EXPECTED_FEATURE_COLS.issubset(columns), f"{discount_set}/{cutoff}: engineered feature columns drifted {columns}")
        source_hashes = _hash_tree(source_shared_root)
        smoke_hashes = _hash_tree(shared_root)
        source_has_usgs = "usgs/usgs_daily.csv" in source_hashes
        if source_has_usgs:
            assert_true(
                smoke_hashes == source_hashes,
                f"{discount_set}/{cutoff}: shared snapshot hashes drifted from source",
            )
        else:
            smoke_no_usgs = {k: v for k, v in smoke_hashes.items() if k != "usgs/usgs_daily.csv"}
            assert_true(
                smoke_no_usgs == source_hashes,
                f"{discount_set}/{cutoff}: non-USGS shared snapshot hashes drifted from source",
            )
            expected_usgs = Path(src_payload["inputs"]["fit"]["usgs_cache_path"])
            assert_true(expected_usgs.exists(), f"{discount_set}/{cutoff}: missing fallback usgs_cache_path {expected_usgs}")
            assert_true(
                smoke_hashes["usgs/usgs_daily.csv"] == _file_sha256(expected_usgs),
                f"{discount_set}/{cutoff}: supplemented USGS truth does not match fallback cache",
            )
        summary["smoke_runs"].append(
            {
                "discount_set": discount_set,
                "cutoff": cutoff,
                "config": str(src_cfg),
                "shared_root": str(shared_root),
                "source_shared_root": str(source_shared_root),
                "shared_file_count": len(smoke_hashes),
                "source_has_usgs": source_has_usgs,
            }
        )
    summary["checks"]["smoke_runs"] = {"count": len(summary["smoke_runs"])}

    if args.with_fit_smoke:
        fit_discount_set, fit_cutoff = SMOKE_CASES[0]
        fit_src_cfg = config_by_case[(fit_discount_set, fit_cutoff)]
        fit_run_id = f"fit_smoke_exalm_t1_{fit_discount_set}_{fit_cutoff}"
        fit_run_root = smoke_root / f"fit_{fit_discount_set}_{fit_cutoff}"
        shutil.rmtree(fit_run_root, ignore_errors=True)
        fit_cfg = write_temp_smoke_config(
            fit_src_cfg,
            run_id=fit_run_id,
            run_root=fit_run_root,
            enabled_stages=["data_prep_shared", "fit"],
        )
        fit_proc = run(["Rscript", "scripts/unified_run.R", "--config", str(fit_cfg)], cwd=ROOT)
        (outdir / f"{fit_discount_set}_{fit_cutoff}.fit.stdout.log").write_text(fit_proc.stdout, encoding="utf-8")
        (outdir / f"{fit_discount_set}_{fit_cutoff}.fit.stderr.log").write_text(fit_proc.stderr, encoding="utf-8")
        assert_true(
            fit_proc.returncode == 0,
            f"fit smoke failed for {fit_discount_set}/{fit_cutoff}\nSTDOUT:\n{fit_proc.stdout}\nSTDERR:\n{fit_proc.stderr}",
        )
        fit_manifest = load_yaml(fit_run_root / fit_run_id / "run_manifest.yaml")
        assert_true(fit_manifest["stages"]["data_prep_shared"]["status"] == "pass", "fit smoke data_prep_shared did not pass")
        assert_true(fit_manifest["stages"]["fit"]["status"] == "pass", "fit smoke fit stage did not pass")
        summary["checks"]["fit_smoke"] = {
            "discount_set": fit_discount_set,
            "cutoff": fit_cutoff,
            "run_root": str(fit_run_root / fit_run_id),
        }

    summary_path = outdir / "prelaunch_validation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md_lines = [
        "# exAL-M-T1 Discount Grid Prelaunch Validation",
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
        f"- fit smoke: `{'enabled' if 'fit_smoke' in summary['checks'] else 'not run'}`",
        "",
        "## Contract",
        "",
        "- all rows are `exAL-M-T1` / `exdqlm_multivar_keep`.",
        "- cutoff-specific best epsilon values come from the corrected HE2 parity matrix.",
        "- every generated config preserves the selected source run's scientific contract and stores `inputs.shared.exact_source_snapshot_root` pointing at the source `inputs/shared` tree.",
        "- representative `data_prep_shared` smoke runs reproduced the full shared snapshot byte-for-byte, including forecast-window PPT/SOIL, deterministic-climate futures, and `covariate_features.csv`.",
        "- representative smoke manifests preserved the semantic storage scales for `retros`, `nws`, `glofas`, and `usgs`.",
        "- optional fit smoke can be enabled with `--with-fit-smoke` when a full prelaunch fit check is worth the extra runtime.",
        "- fit parallelism is inherited from the selected source config for each cutoff; the queue cap still limits launch concurrency to `4` rows.",
    ]
    (outdir / "prelaunch_validation_summary.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(json.dumps({"outdir": str(outdir), "summary": str(summary_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate post-only replay configs for authoritative exAL-M-T1 source runs."
    )
    parser.add_argument(
        "--manifest",
        default="repro/manifests/exalm_t1_authoritative_runs_20260505.csv",
        help="CSV manifest listing authoritative source runs.",
    )
    parser.add_argument(
        "--out-dir",
        default="config/unified_runs_exalm_t1_postreplay_20260505",
        help="Directory where replay configs will be written.",
    )
    parser.add_argument(
        "--run-root",
        default="repro/runs",
        help="Run root for replay runs.",
    )
    parser.add_argument(
        "--suffix",
        default="20260505",
        help="Suffix appended to replay run_ids.",
    )
    parser.add_argument(
        "--snapshot-root",
        default="repro/frozen_shared_inputs/exalm_t1_authoritative_20260505",
        help="Root directory containing prepared frozen shared-input snapshots.",
    )
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def replay_run_id(cutoff_date: str, suffix: str) -> str:
    compact = cutoff_date.replace("-", "")
    return f"paper_exalm_t1_postreplay_{compact}_{suffix}"


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = (repo_root / args.manifest).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    snapshot_root = (repo_root / args.snapshot_root).resolve()

    rows = load_rows(manifest_path)
    if not rows:
        raise SystemExit(f"No rows found in manifest: {manifest_path}")

    for row in rows:
        base_config = Path(row["base_config"]).resolve()
        source_run_dir = Path(row["source_run_root"]).resolve() / row["source_run_id"]
        with base_config.open("r", encoding="utf-8") as handle:
            cfg = yaml.safe_load(handle) or {}

        run_id = replay_run_id(row["cutoff_date"], args.suffix)
        cfg.setdefault("run", {})
        cfg["run"]["run_id"] = run_id
        cfg["run"]["run_root"] = args.run_root
        cfg["run"]["overwrite"] = True
        cfg["run"]["auto_suffix_on_collision"] = False

        cfg["stages"] = {
            "forecats": False,
            "data_prep_shared": True,
            "fit": False,
            "post": True,
            "validate": True,
            "report": True,
        }

        inputs = cfg.setdefault("inputs", {})
        fit_inputs = inputs.setdefault("fit", {})
        fit_inputs["parameters_path"] = str(source_run_dir / "inputs" / "shared" / "parameters" / "parameters.txt")
        fit_inputs["retros_path"] = str(source_run_dir / "inputs" / "shared" / "retros" / "retros.csv")
        fit_inputs["nws_forecast_path"] = str(source_run_dir / "inputs" / "shared" / "forecasts" / "nws_forecast.csv")
        fit_inputs["glofas_forecast_path"] = str(source_run_dir / "inputs" / "shared" / "forecasts" / "glofas_forecast.csv")

        cov_map = {
            "ELI": "cov_01_ELI.csv",
            "ONI": "cov_02_ONI.csv",
            "PPT": "cov_03_PPT.csv",
            "SOIL": "cov_04_SOIL.csv",
            "PCA": "cov_05_PCA.csv",
        }
        fit_covariates = fit_inputs.get("covariates") or []
        for item in fit_covariates:
            name = str(item.get("name", "")).upper()
            if name in cov_map:
                item["path"] = str(source_run_dir / "inputs" / "shared" / "covariates" / cov_map[name])

        post_inputs = inputs.setdefault("post", {})
        post_inputs["use_fit_outputs_from_run"] = True
        post_inputs["source_run_id"] = row["source_run_id"]
        post_inputs["source_run_root"] = row["source_run_root"]

        forecats = inputs.setdefault("forecats", {})
        forecats["existing_bundle_path"] = str(source_run_dir / "inputs" / "shared" / "forecats_bundle" / "meta.yaml")
        shared_inputs = inputs.setdefault("shared", {})
        shared_inputs["prefer_forecats_snapshot"] = True
        shared_inputs["exact_source_snapshot_root"] = str(snapshot_root / f"cutoff_date={row['cutoff_date']}")

        post_cfg = cfg.setdefault("post", {})
        post_cfg["smoke_fast"] = False
        post_cfg["figures"] = True
        post_cfg["export_tables"] = True
        post_cfg["table_formats"] = ["csv", "rds"]
        post_cfg["sort_keep_na"] = True
        post_cfg["force_isolation_smoke_fast"] = False

        cfg["debug_exalm_t1_post_replay"] = {
            "source_run_id": row["source_run_id"],
            "source_run_root": row["source_run_root"],
            "expected_mean_crps": float(row["expected_mean_crps"]),
            "compare_bundle": row["compare_bundle"],
            "section5_representative": str(row["section5_representative"]).lower() == "true",
            "manifest": str(manifest_path),
        }

        out_path = out_dir / f"{run_id}.yaml"
        with out_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(cfg, handle, sort_keys=False)
        print(out_path)


if __name__ == "__main__":
    main()

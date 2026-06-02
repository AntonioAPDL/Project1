#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from he2_exdqlm_keep_authoritative import (  # noqa: E402
    EXPECTED_CUTOFFS,
    EXPECTED_QUANTILE_LABELS,
    EXPECTED_QUANTILES,
    load_authoritative_spec,
)
from he2_publication_relaunch_lib import initialize_matrix_status  # noqa: E402


TARGET_FAMILY = "dqlm_multivar_al_keep"
TARGET_LABEL = "AL-M-T1"
TARGET_MODEL_ID = "dqlm_multivar_al_synth_keep"
TARGET_MODEL_KEY = "exdqlm_multivar"
SOURCE_FAMILY = "exdqlm_multivar_keep"
SOURCE_LABEL = "exAL-M-T1"
SOURCE_MODEL_ID = "exdqlm_multivar_synth_keep"
DEFAULT_ARTIFACT_ROOT = (
    ROOT.parent / "project1_ucsc_phd_runtime" / "multimodel_v8_he2_dqlm_multivar_al_keep_from_exal_winners_20260602"
)


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


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True)
    except Exception:
        return "unknown"
    return out.strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cutoff_dash(cutoff: str) -> str:
    cutoff = str(cutoff).zfill(8)
    return f"{cutoff[:4]}-{cutoff[4:6]}-{cutoff[6:8]}"


def target_run_id(cutoff: str, grid_spec_id: str) -> str:
    return f"multimodel_{str(cutoff).zfill(8)}_v8_he2grid_{grid_spec_id}_{TARGET_FAMILY}"


def _nested(payload: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _mutate_debug_blocks(
    cfg: dict[str, Any],
    *,
    winner: Any,
    source_config_path: Path,
    source_run_root: Path,
    target_config_path: Path,
    artifact_root: Path,
    manifest_path: Path,
    code_commit: str,
) -> None:
    if isinstance(cfg.get("debug_featurecov_cf1_eps_campaign"), dict):
        debug = cfg["debug_featurecov_cf1_eps_campaign"]
        debug["family_id"] = TARGET_FAMILY
        debug["model_id"] = TARGET_MODEL_ID
        debug["model_key"] = TARGET_MODEL_KEY
        debug["likelihood_mode"] = "al"
        debug["transfer_mode"] = "keep"
        debug["epsilon_label"] = winner.grid_spec_id
        debug["epsilon_value"] = float(winner.epsilon_value)
        debug["target_c_factor"] = float(winner.c_factor)
        debug["selected_source_run"] = winner.run_id
        debug["selected_source_type"] = "exdqlm_multivar_keep_authoritative_winner_clone"
        debug["selected_source_config"] = str(source_config_path)
        debug["selected_mean_crps"] = float(winner.mean_crps)

    if isinstance(cfg.get("debug_he2_publication_relaunch"), dict):
        debug = cfg["debug_he2_publication_relaunch"]
        debug["source_publication_run_id"] = winner.run_id
        debug["source_publication_run_root"] = str(source_run_root)
        debug["source_publication_resolved_config"] = str(source_config_path)
        debug["campaign_lineage"] = "exdqlm_multivar_keep_authoritative_winner_clone_20260602"
        debug["manuscript_label"] = TARGET_LABEL
        debug["family"] = TARGET_FAMILY
        debug["model_class"] = "quantile_multivariate"
        debug["implementation_mode"] = "legacy_bridge"
        debug["likelihood_mode"] = "al"
        debug["forecast_transfer_mode"] = "keep"
        debug["publication_crps_display4"] = ""
        debug["selected_spec_token"] = winner.grid_spec_id
        debug["model_config_key"] = TARGET_MODEL_KEY
        debug["config_patch_applied"] = True
        debug["config_patch_source"] = str(manifest_path)
        debug["grid_spec_id"] = winner.grid_spec_id

    cfg["debug_he2_dqlm_al_keep_from_exal_winners"] = {
        "status": "prepared_not_launched",
        "generated_at_utc": utc_now(),
        "builder": str(ROOT / "scripts" / "build_he2_dqlm_multivar_al_keep_from_exal_winners.py"),
        "code_commit": code_commit,
        "manifest_path": str(manifest_path),
        "source_family": SOURCE_FAMILY,
        "source_label": SOURCE_LABEL,
        "source_model_id": SOURCE_MODEL_ID,
        "source_likelihood_mode": "exal",
        "source_run_id": winner.run_id,
        "source_config_path": str(source_config_path),
        "target_family": TARGET_FAMILY,
        "target_label": TARGET_LABEL,
        "target_model_id": TARGET_MODEL_ID,
        "target_model_key": TARGET_MODEL_KEY,
        "target_likelihood_mode": "al",
        "target_config_path": str(target_config_path),
        "likelihood_switch": "exal_to_al",
        "forecast_transfer_mode": "keep",
        "preserved_grid_spec_id": winner.grid_spec_id,
        "discount_case_id": winner.discount_case_id,
        "epsilon_value": float(winner.epsilon_value),
        "c_factor": float(winner.c_factor),
        "active_quantiles": EXPECTED_QUANTILE_LABELS,
        "expected_quantile_submodels": len(EXPECTED_QUANTILES),
        "expected_gamma_contract": "DISC_W_LIKELIHOOD_MODE=al forces gamma draws and moments to zero in the active R workflow.",
        "expected_st_contract": "DISC_W_AL_MODE makes update_sts return zero E.sts/E.sts2; sampled sts are not a likelihood component because gamma is zero.",
        "input_and_state_contract": "Preserve source exAL-M-T1 winner inputs, dates, state_evolution, structure, epsilon, c_factor, and max_iter exactly.",
        "no_launch": True,
    }


def clone_config(
    source_cfg: dict[str, Any],
    *,
    winner: Any,
    source_config_path: Path,
    source_run_root: Path,
    target_config_path: Path,
    artifact_root: Path,
    manifest_path: Path,
    code_commit: str,
) -> dict[str, Any]:
    cfg = deepcopy(source_cfg)
    run_id = target_run_id(winner.cutoff, winner.grid_spec_id)
    run_root = artifact_root / "runs"

    cfg.setdefault("run", {})
    cfg["run"]["run_id"] = run_id
    cfg["run"]["run_root"] = str(run_root)
    cfg["run"]["resolved_run_root"] = str(run_root / run_id)
    cfg["run"]["resolved_config_path"] = str(target_config_path)
    cfg["run"]["overwrite"] = False
    cfg["run"]["auto_suffix_on_collision"] = False
    cfg["run"]["dry_run"] = False
    cfg["run"]["git_require_clean"] = False

    cfg.setdefault("models", {})
    cfg["models"]["run_exdqlm_multivar"] = True
    cfg["models"]["run_exdqlm_univar"] = False
    cfg["models"]["run_ndlm_main"] = False
    cfg["models"]["run_ndlm_univar"] = False
    cfg["models"].setdefault("exdqlm_multivar", {})
    cfg["models"]["exdqlm_multivar"]["likelihood_mode"] = "al"
    cfg["models"]["exdqlm_multivar"]["forecast_transfer_mode"] = "keep"

    _mutate_debug_blocks(
        cfg,
        winner=winner,
        source_config_path=source_config_path,
        source_run_root=source_run_root,
        target_config_path=target_config_path,
        artifact_root=artifact_root,
        manifest_path=manifest_path,
        code_commit=code_commit,
    )
    return cfg


def input_paths_for_row(cfg: dict[str, Any]) -> dict[str, str]:
    covariates = _nested(cfg, ["inputs", "fit", "covariates"], [])
    return {
        "parameters_path": str(_nested(cfg, ["inputs", "fit", "parameters_path"], "")),
        "retros_path": str(_nested(cfg, ["inputs", "fit", "retros_path"], "")),
        "nws_forecast_path": str(_nested(cfg, ["inputs", "fit", "nws_forecast_path"], "")),
        "glofas_forecast_path": str(_nested(cfg, ["inputs", "fit", "glofas_forecast_path"], "")),
        "forecats_existing_bundle_path": str(_nested(cfg, ["inputs", "forecats", "existing_bundle_path"], "")),
        "covariates_json": json.dumps(covariates, sort_keys=True),
    }


def build_package(manifest_path: Path, artifact_root: Path, *, reset_status: bool = True) -> dict[str, Any]:
    spec = load_authoritative_spec(manifest_path)
    artifact_root = artifact_root.resolve()
    matrix_dir = artifact_root / "control" / "publication_relaunch_matrix"
    config_output_dir = artifact_root / "control" / "generated_configs"
    matrix_dir.mkdir(parents=True, exist_ok=True)
    config_output_dir.mkdir(parents=True, exist_ok=True)

    code_commit = git_head()
    plan_rows: list[dict[str, Any]] = []
    frozen_rows: list[dict[str, Any]] = []
    clone_rows: list[dict[str, Any]] = []
    bundle_rows: list[dict[str, Any]] = []

    for order_index, winner in enumerate(spec.winners, 1):
        source_config_path = spec.generated_config_path(winner)
        if not source_config_path.exists():
            raise FileNotFoundError(f"missing authoritative source config: {source_config_path}")
        source_cfg = load_yaml(source_config_path)
        run_id = target_run_id(winner.cutoff, winner.grid_spec_id)
        target_config_path = config_output_dir / f"{run_id}.yaml"
        target_cfg = clone_config(
            source_cfg,
            winner=winner,
            source_config_path=source_config_path,
            source_run_root=spec.run_root(winner),
            target_config_path=target_config_path,
            artifact_root=artifact_root,
            manifest_path=manifest_path,
            code_commit=code_commit,
        )
        write_yaml(target_config_path, target_cfg)

        source_hash = sha256(source_config_path)
        target_hash = sha256(target_config_path)
        paths = input_paths_for_row(target_cfg)
        active_quantiles = _nested(target_cfg, ["fit", "quantiles"], [])
        row = {
            "order_index": order_index,
            "cutoff": winner.cutoff,
            "epsilon": winner.grid_spec_id,
            "epsilon_value": float(winner.epsilon_value),
            "grid_spec_id": winner.grid_spec_id,
            "discount_case_id": winner.discount_case_id,
            "lane": TARGET_FAMILY,
            "run_scope": "he2_dqlm_multivar_al_keep_from_exal_winners",
            "run_id": run_id,
            "config_path": str(target_config_path),
            "compare_outdir": "",
            "priority_group": 2 if winner.cutoff == "20221225" else 1,
            "max_concurrent_class": "heavy" if winner.cutoff == "20221225" else "ordinary",
            "family_id": TARGET_FAMILY,
            "model_id": TARGET_MODEL_ID,
            "model_key": TARGET_MODEL_KEY,
            "model_class": "quantile_multivariate",
            "manuscript_label": TARGET_LABEL,
            "likelihood_mode": "al",
            "transfer_mode": "keep",
            "row_kind": "quantile_multivariate",
            "quantile_submodels": len(active_quantiles),
            "active_quantiles": "|".join(f"{int(round(float(q) * 100)):02d}" for q in active_quantiles),
            "profile_name": "al_keep_from_exal_winners_20260602",
            "selected_source_run": winner.run_id,
            "selected_source_type": "exdqlm_multivar_keep_authoritative_winner_clone",
            "selected_source_config": str(source_config_path),
            "selected_mean_crps": float(winner.mean_crps),
            "source_family_id": SOURCE_FAMILY,
            "source_model_id": SOURCE_MODEL_ID,
            "source_likelihood_mode": "exal",
            "df_t": float(winner.df_t),
            "df_s1": float(winner.df_s1),
            "df_s2": float(winner.df_s2),
            "df_s67": float(winner.df_s67),
            "df_discrep": float(winner.df_discrep),
            "lambda": float(winner.lambda_value),
            "df_trans": float(winner.df_trans),
            "df_covs": float(winner.df_covs),
            "c_factor": float(winner.c_factor),
            "forecast_cov_epsilon": float(winner.epsilon_value),
            "max_iter": int(_nested(target_cfg, ["fit", "exdqlm_multivar", "gamma_sigma", "max_iter"], 0)),
            "data_start": str(_nested(target_cfg, ["dates", "data_start"], "")),
            "cutoff_date": str(_nested(target_cfg, ["dates", "cutoff_date"], cutoff_dash(winner.cutoff))),
            "artifact_root": str(artifact_root),
            "run_root": str(artifact_root / "runs" / run_id),
            "matrix_dir": str(matrix_dir),
            "source_config_sha256": source_hash,
            "target_config_sha256": target_hash,
            **paths,
        }
        plan_rows.append(row)
        frozen_rows.append(dict(row))
        clone_rows.append(
            {
                "cutoff": winner.cutoff,
                "grid_spec_id": winner.grid_spec_id,
                "source_run_id": winner.run_id,
                "source_config_path": str(source_config_path),
                "source_config_sha256": source_hash,
                "target_run_id": run_id,
                "target_config_path": str(target_config_path),
                "target_config_sha256": target_hash,
                "only_intended_scientific_change": "likelihood_mode exal -> al",
            }
        )
        bundle_rows.append(
            {
                "cutoff": winner.cutoff,
                "cutoff_date": cutoff_dash(winner.cutoff),
                "run_id": run_id,
                "bundle_meta": paths["forecats_existing_bundle_path"],
                "parameters_path": paths["parameters_path"],
                "retros_path": paths["retros_path"],
                "nws_forecast_path": paths["nws_forecast_path"],
                "glofas_forecast_path": paths["glofas_forecast_path"],
                "covariates_json": paths["covariates_json"],
            }
        )

    write_csv(matrix_dir / "matrix_plan.csv", plan_rows)
    write_csv(matrix_dir / "frozen_spec_manifest.csv", frozen_rows)
    write_csv(matrix_dir / "source_clone_manifest.csv", clone_rows)
    write_csv(matrix_dir / "cutoff_bundle_audit.csv", bundle_rows)
    write_csv(
        matrix_dir / "al_keep_run_registry.csv",
        [
            {
                key: row[key]
                for key in [
                    "cutoff",
                    "grid_spec_id",
                    "run_id",
                    "config_path",
                    "forecast_cov_epsilon",
                    "c_factor",
                    "df_t",
                    "df_s1",
                    "df_s2",
                    "df_s67",
                    "df_discrep",
                    "lambda",
                    "df_trans",
                    "df_covs",
                    "max_iter",
                ]
            }
            for row in plan_rows
        ],
    )

    queue = {
        "ordinary_max_concurrent": 5,
        "pause_free_gb": 25.0,
        "launch_free_gb": 35.0,
        "heavy_free_gb": 35.0,
        "pause_mem_gb": 0.0,
        "launch_mem_gb": 0.0,
        "heavy_mem_gb": 0.0,
        "heavy_cutoff_max_concurrent": 5,
        "heavy_cutoff_blocks_ordinary": False,
        "poll_seconds": 30,
    }
    resources = {
        "fit_parallel_workers": 7,
        "mc_cores": 7,
    }
    metadata = {
        "generated_at_utc": utc_now(),
        "status": "prepared_not_launched",
        "campaign_id": "he2_dqlm_multivar_al_keep_from_exal_winners_20260602",
        "source_manifest": str(spec.manifest_path),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "source_family": SOURCE_FAMILY,
        "source_label": SOURCE_LABEL,
        "source_model_id": SOURCE_MODEL_ID,
        "target_family": TARGET_FAMILY,
        "target_label": TARGET_LABEL,
        "target_model_id": TARGET_MODEL_ID,
        "target_model_key": TARGET_MODEL_KEY,
        "likelihood_switch": "exal_to_al",
        "forecast_transfer_mode": "keep",
        "bundle_artifact_root": spec.metadata.get("bundle_artifact_root", ""),
        "bundle_run_id": spec.metadata.get("bundle_run_id", ""),
        "data_start": spec.metadata.get("data_start", ""),
        "active_quantiles": EXPECTED_QUANTILE_LABELS,
        "n_cutoffs": len(EXPECTED_CUTOFFS),
        "n_run_rows": len(plan_rows),
        "n_quantile_fits": len(plan_rows) * len(EXPECTED_QUANTILES),
        "queue": queue,
        "resources": resources,
        "cleanup_rdata_after_post": True,
        "skip_compare_bundles": True,
        "continue_on_fail": True,
        "code_commit": code_commit,
    }
    write_yaml(matrix_dir / "matrix_metadata.yaml", metadata)
    if reset_status:
        initialize_matrix_status(matrix_dir / "matrix_status.csv")
    else:
        (matrix_dir / "matrix_status.csv").touch()
    (matrix_dir / "queue.log").touch()

    launch_cmd = [
        "python3",
        "scripts/run_multimodel_v8_queue.py",
        "--matrix-dir",
        str(matrix_dir),
        "--artifact-root",
        str(artifact_root),
        "--ordinary-max-concurrent",
        str(queue["ordinary_max_concurrent"]),
        "--pause-free-gb",
        str(queue["pause_free_gb"]),
        "--launch-free-gb",
        str(queue["launch_free_gb"]),
        "--heavy-free-gb",
        str(queue["heavy_free_gb"]),
        "--pause-mem-gb",
        str(queue["pause_mem_gb"]),
        "--launch-mem-gb",
        str(queue["launch_mem_gb"]),
        "--heavy-mem-gb",
        str(queue["heavy_mem_gb"]),
        "--heavy-cutoff-max-concurrent",
        str(queue["heavy_cutoff_max_concurrent"]),
        "--poll-seconds",
        str(queue["poll_seconds"]),
        "--continue-on-fail",
        "--skip-compares",
        "--no-heavy-cutoff-blocks-ordinary",
    ]
    launch_env = "\n".join(
        [
            f"ARTIFACT_ROOT={artifact_root}",
            f"MATRIX_DIR={matrix_dir}",
            f"ORDINARY_MAX_CONCURRENT={queue['ordinary_max_concurrent']}",
            f"PAUSE_FREE_GB={queue['pause_free_gb']}",
            f"LAUNCH_FREE_GB={queue['launch_free_gb']}",
            f"HEAVY_FREE_GB={queue['heavy_free_gb']}",
            f"PAUSE_MEM_GB={queue['pause_mem_gb']}",
            f"LAUNCH_MEM_GB={queue['launch_mem_gb']}",
            f"HEAVY_MEM_GB={queue['heavy_mem_gb']}",
            f"HEAVY_CUTOFF_MAX_CONCURRENT={queue['heavy_cutoff_max_concurrent']}",
            f"HEAVY_CUTOFF_BLOCKS_ORDINARY={1 if queue['heavy_cutoff_blocks_ordinary'] else 0}",
            f"POLL_SECONDS={queue['poll_seconds']}",
            "CONTINUE_ON_FAIL=1",
            "SKIP_COMPARES=1",
            "",
        ]
    )
    (matrix_dir / "launch_settings.env").write_text(launch_env, encoding="utf-8")

    scope_lines = [
        "# HE2 AL-M-T1 From exAL-M-T1 Winner Clone Scope",
        "",
        "- status: `prepared_not_launched`",
        f"- source family: `{SOURCE_LABEL}` / `{SOURCE_FAMILY}`",
        f"- target family: `{TARGET_LABEL}` / `{TARGET_FAMILY}`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- generated configs: `{config_output_dir}`",
        f"- run rows: `{len(plan_rows)}`",
        f"- quantile fits: `{len(plan_rows) * len(EXPECTED_QUANTILES)}`",
        "- intended scientific change: `likelihood_mode: exal -> al`",
        "- preserved: source input bundle paths, cutoff dates, data start, harmonics, transfer covariates, discount factors, epsilon, c_factor, and max_iter.",
        "- cleanup after post: `true`",
        "",
        "## Launch Command",
        "",
        "Do not run until explicit launch approval is given.",
        "",
        "```bash",
        " ".join(launch_cmd),
        "```",
        "",
        "## Key Files",
        "",
        "- `matrix_plan.csv`",
        "- `frozen_spec_manifest.csv`",
        "- `source_clone_manifest.csv`",
        "- `cutoff_bundle_audit.csv`",
        "- `al_keep_run_registry.csv`",
        "- `matrix_metadata.yaml`",
    ]
    (matrix_dir / "AL_KEEP_FROM_EXAL_WINNERS_SCOPE.md").write_text("\n".join(scope_lines) + "\n", encoding="utf-8")

    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare, without launching, AL-M-T1 configs cloned from the authoritative exAL-M-T1 winners."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "docs" / "exdqlm_multivar_keep_authoritative_specs_20260601.yaml",
    )
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--no-reset-status", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = build_package(
        args.manifest.resolve(),
        args.artifact_root.resolve(),
        reset_status=not args.no_reset_status,
    )
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

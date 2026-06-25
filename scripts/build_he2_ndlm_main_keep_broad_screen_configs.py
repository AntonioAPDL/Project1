#!/usr/bin/env python3
"""Build the HE2 N-M-T1 broad discount/epsilon screen matrix.

This is intentionally a Gaussian NDLM-main-keep screen.  It does not create
quantile lanes and it does not reuse the exDQLM seven-quantile grid launcher.
Each matrix row is one one-core `ndlm_main_keep` run for one cutoff/spec.
"""

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

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from multimodel_v8_lib import HEAVY_CUTOFF, artifact_disk_free_gb, ensure_dir, runs_dir, write_yaml  # noqa: E402

DEFAULT_AUTHORITY_ROWS = ROOT / "reports" / "nmt1_static_parity_audit_20260625" / "authority_rows.csv"
DEFAULT_ARTIFACT_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_ndlm_main_keep_broad_screen_20260625"
)
DEFAULT_MATRIX_DIR = DEFAULT_ARTIFACT_ROOT / "control" / "ndlm_main_keep_broad_screen"
DEFAULT_CONFIG_OUTPUT_DIR = DEFAULT_ARTIFACT_ROOT / "control" / "generated_configs"
EXPECTED_CUTOFFS = ["20210123", "20211112", "20211221", "20220511", "20221225"]
TARGET_LANE = "ndlm_main_keep"
TARGET_MODEL_ID = "ndlm_main_synth_keep"
TARGET_MODEL_VARIANT = "ndlm_main_keep"
TARGET_SCORE_SCALE = "log_cms_plus1"
TARGET_HARMONICS = [1.0, 2.0, 1.0 / 6.8068493]
GRID_EPSILONS = [1.0, 30.0, 60.0, 90.0, 180.0, 365.0]
GRID_AXES = {
    "df_t": [0.99999, 0.9999999],
    "df_s1": [0.99999, 0.9999],
    "df_s2": [0.99999, 0.9999],
    "df_s67": [0.99999],
    "df_discrep": [0.999, 0.9999, 0.99995],
    "lambda": [0.97],
    "df_trans": [0.9999999, 0.99999],
    "df_covs": [0.99999999],
    "c_factor": [1.0],
}
HASH_CACHE: dict[str, str] = {}
INPUT_SNAPSHOT_MAP = {
    "parameters": ("inputs", "fit", "parameters_path", "inputs/shared/parameters/parameters.txt"),
    "retros": ("inputs", "fit", "retros_path", "inputs/shared/retros/retros.csv"),
    "nws_forecast": ("inputs", "fit", "nws_forecast_path", "inputs/shared/forecasts/nws_forecast.csv"),
    "glofas_forecast": ("inputs", "fit", "glofas_forecast_path", "inputs/shared/forecasts/glofas_forecast.csv"),
}
USGS_SOURCE_SNAPSHOT_REL = "inputs/shared/usgs/usgs_daily.csv"
COVARIATE_SNAPSHOT_MAP = [
    ("PPT", "inputs/shared/covariates/cov_01_PPT.csv"),
    ("SOIL", "inputs/shared/covariates/cov_02_SOIL.csv"),
    ("PCA", "inputs/shared/covariates/cov_03_PCA.csv"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root is not a mapping: {path}")
    return data


def set_nested(cfg: dict[str, Any], path: list[str], value: Any) -> None:
    cur = cfg
    for key in path[:-1]:
        child = cur.get(key)
        if not isinstance(child, dict):
            child = {}
            cur[key] = child
        cur = child
    cur[path[-1]] = value


def nested(cfg: dict[str, Any], path: list[str], default: Any = None) -> Any:
    cur: Any = cfg
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def sha256_file(path: Path) -> str:
    key = str(path)
    if key in HASH_CACHE:
        return HASH_CACHE[key]
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    HASH_CACHE[key] = h.hexdigest()
    return HASH_CACHE[key]


def eps_label(epsilon: float) -> str:
    return f"eps{int(round(float(epsilon))):03d}"


def run_id_for(cutoff: str, grid_spec_id: str) -> str:
    return f"multimodel_{cutoff}_v8_nmt1screen_{grid_spec_id}_ndlm_main_keep"


def build_discount_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    idx = 0
    for df_t in GRID_AXES["df_t"]:
        for df_s1 in GRID_AXES["df_s1"]:
            for df_s2 in GRID_AXES["df_s2"]:
                for df_s67 in GRID_AXES["df_s67"]:
                    for df_discrep in GRID_AXES["df_discrep"]:
                        for lam in GRID_AXES["lambda"]:
                            for df_trans in GRID_AXES["df_trans"]:
                                for df_covs in GRID_AXES["df_covs"]:
                                    for c_factor in GRID_AXES["c_factor"]:
                                        idx += 1
                                        cases.append(
                                            {
                                                "discount_case_id": f"c{idx:03d}",
                                                "df_t": df_t,
                                                "df_s1": df_s1,
                                                "df_s2": df_s2,
                                                "df_s67": df_s67,
                                                "df_discrep": df_discrep,
                                                "lambda": lam,
                                                "df_trans": df_trans,
                                                "df_covs": df_covs,
                                                "c_factor": c_factor,
                                            }
                                        )
    return cases


def build_grid_specs() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for case in build_discount_cases():
        for epsilon in GRID_EPSILONS:
            row = dict(case)
            row["epsilon"] = float(epsilon)
            row["epsilon_label"] = eps_label(epsilon)
            row["grid_spec_id"] = f"{case['discount_case_id']}_{row['epsilon_label']}"
            row["max_iter"] = 100
            rows.append(row)
    return pd.DataFrame(rows)


def load_authority_rows(authority_rows: Path) -> pd.DataFrame:
    df = pd.read_csv(authority_rows, dtype=str)
    required = {"authority_class", "cutoff", "row_label", "source_class", "resolved_config", "run_root", "run_id"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"authority_rows missing required columns: {sorted(missing)}")
    subset = df.loc[
        (df["authority_class"] == "article_crps_table")
        & (df["row_label"] == "N-M-T1")
        & (df["source_class"] == TARGET_MODEL_VARIANT)
    ].copy()
    if set(subset["cutoff"].astype(str)) != set(EXPECTED_CUTOFFS):
        raise ValueError(
            "authority_rows must contain exactly one N-M-T1 article row for each cutoff; "
            f"observed={sorted(subset['cutoff'].astype(str).tolist())}"
        )
    if subset["cutoff"].duplicated().any():
        raise ValueError("authority_rows contains duplicated N-M-T1 cutoff rows")
    return subset.set_index("cutoff", drop=False).loc[EXPECTED_CUTOFFS].reset_index(drop=True)


def rewrite_inputs_to_source_snapshots(
    cfg: dict[str, Any],
    source_run_root: Path,
    *,
    source_cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for artifact, path_key1, path_key2, path_key3, rel in [
        (name, key1, key2, key3, rel)
        for name, (key1, key2, key3, rel) in INPUT_SNAPSHOT_MAP.items()
    ]:
        source_path = source_run_root / rel
        if not source_path.exists():
            raise FileNotFoundError(f"Missing source input snapshot for {artifact}: {source_path}")
        set_nested(cfg, [path_key1, path_key2, path_key3], str(source_path))
        rows.append(
            {
                "artifact": artifact,
                "path": str(source_path),
                "relative_path": rel,
                "sha256": sha256_file(source_path),
                "size_bytes": source_path.stat().st_size,
            }
        )

    source_usgs_snapshot = source_run_root / USGS_SOURCE_SNAPSHOT_REL
    if source_usgs_snapshot.exists():
        rows.append(
            {
                "artifact": "usgs_daily_source_cutoff_snapshot_audit_only",
                "path": str(source_usgs_snapshot),
                "relative_path": USGS_SOURCE_SNAPSHOT_REL,
                "sha256": sha256_file(source_usgs_snapshot),
                "size_bytes": source_usgs_snapshot.stat().st_size,
                "role": "audit_only_not_post_truth",
            }
        )

    full_usgs_cache_raw = nested(source_cfg, ["inputs", "fit", "usgs_cache_path"], "")
    full_usgs_cache = Path(str(full_usgs_cache_raw)).expanduser()
    if not full_usgs_cache.exists():
        raise FileNotFoundError(
            "Missing full USGS cache from source resolved config. "
            f"inputs.fit.usgs_cache_path={full_usgs_cache_raw!r}"
        )
    set_nested(cfg, ["inputs", "fit", "usgs_cache_path"], str(full_usgs_cache))
    rows.append(
        {
            "artifact": "usgs_daily_full_truth_cache",
            "path": str(full_usgs_cache),
            "relative_path": "",
            "sha256": sha256_file(full_usgs_cache),
            "size_bytes": full_usgs_cache.stat().st_size,
            "role": "post_truth_and_shared_usgs_cache",
        }
    )

    covariates: list[dict[str, str]] = []
    for name, rel in COVARIATE_SNAPSHOT_MAP:
        source_path = source_run_root / rel
        if not source_path.exists():
            raise FileNotFoundError(f"Missing source covariate snapshot for {name}: {source_path}")
        covariates.append({"name": name, "path": str(source_path)})
        rows.append(
            {
                "artifact": f"covariate_{name}",
                "path": str(source_path),
                "relative_path": rel,
                "sha256": sha256_file(source_path),
                "size_bytes": source_path.stat().st_size,
            }
        )
    set_nested(cfg, ["inputs", "fit", "covariates"], covariates)

    forecats_meta = source_run_root / "inputs/shared/forecats_bundle/meta.yaml"
    if forecats_meta.exists():
        set_nested(cfg, ["inputs", "forecats", "existing_bundle_path"], str(forecats_meta))
        rows.append(
            {
                "artifact": "forecats_bundle_meta",
                "path": str(forecats_meta),
                "relative_path": "inputs/shared/forecats_bundle/meta.yaml",
                "sha256": sha256_file(forecats_meta),
                "size_bytes": forecats_meta.stat().st_size,
            }
        )
    set_nested(cfg, ["inputs", "shared", "prefer_forecats_snapshot"], False)
    return rows


def mutate_config(
    source_cfg: dict[str, Any],
    *,
    source_row: pd.Series,
    spec: pd.Series,
    artifact_root: Path,
    matrix_dir: Path,
    config_path: Path,
    code_commit: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cfg = deepcopy(source_cfg)
    cutoff = str(source_row["cutoff"])
    grid_spec_id = str(spec["grid_spec_id"])
    run_id = run_id_for(cutoff, grid_spec_id)
    source_run_root = Path(str(source_row["run_root"]))

    set_nested(cfg, ["run", "run_id"], run_id)
    set_nested(cfg, ["run", "run_root"], str(runs_dir(artifact_root)))
    set_nested(cfg, ["run", "resolved_run_root"], str(runs_dir(artifact_root) / run_id))
    set_nested(cfg, ["run", "resolved_config_path"], str(config_path))
    set_nested(cfg, ["run", "overwrite"], False)
    set_nested(cfg, ["run", "auto_suffix_on_collision"], False)
    set_nested(cfg, ["run", "dry_run"], False)
    set_nested(cfg, ["run", "git_require_clean"], False)
    for key in ["omp", "openblas", "mkl", "veclib", "numexpr", "mc_cores"]:
        set_nested(cfg, ["run", "threads", key], 1)

    set_nested(cfg, ["stages", "forecats"], False)
    for stage in ["data_prep_shared", "fit", "post", "validate", "report"]:
        set_nested(cfg, ["stages", stage], True)

    set_nested(cfg, ["models", "run_exdqlm_multivar"], False)
    set_nested(cfg, ["models", "run_exdqlm_univar"], False)
    set_nested(cfg, ["models", "run_ndlm_main"], True)
    set_nested(cfg, ["models", "run_ndlm_univar"], False)
    set_nested(cfg, ["models", "ndlm_main", "forecast_transfer_mode"], "keep")
    set_nested(cfg, ["models", "ndlm_main", "implementation_mode"], "theory_aligned")
    set_nested(cfg, ["models", "ndlm_main", "kalman_backend"], "cpp")
    set_nested(cfg, ["models", "ndlm_main", "seasonality", "harmonics"], TARGET_HARMONICS)

    for field in ["df_t", "df_s1", "df_s2", "df_s67", "df_discrep", "lambda", "df_trans", "df_covs"]:
        set_nested(cfg, ["models", "ndlm_main", "state_evolution", field], float(spec[field]))
    set_nested(cfg, ["models", "ndlm_main", "prior", "forecast_cov", "c_factor"], float(spec["c_factor"]))
    set_nested(cfg, ["models", "ndlm_main", "prior", "forecast_cov", "epsilon"], float(spec["epsilon"]))
    set_nested(cfg, ["models", "ndlm_main", "prior", "forecast_cov", "dof_offset"], int(nested(cfg, ["models", "ndlm_main", "prior", "forecast_cov", "dof_offset"], 4)))
    set_nested(cfg, ["models", "ndlm_main", "prior", "forecast_cov", "scale_mult"], float(nested(cfg, ["models", "ndlm_main", "prior", "forecast_cov", "scale_mult"], 1.0)))
    set_nested(cfg, ["models", "ndlm_main", "prior", "forecast_cov", "jitter"], float(nested(cfg, ["models", "ndlm_main", "prior", "forecast_cov", "jitter"], 1e-8)))

    set_nested(cfg, ["fit", "parallel", "mode"], "global_models")
    set_nested(cfg, ["fit", "parallel", "workers"], 1)
    set_nested(cfg, ["fit", "ndlm_main", "gamma_sigma", "max_iter"], 100)
    if nested(cfg, ["fit", "ndlm_main", "gamma_sigma", "min_total_iters"]) is None:
        set_nested(cfg, ["fit", "ndlm_main", "gamma_sigma", "min_total_iters"], 20)
    set_nested(cfg, ["post", "figures"], True)
    set_nested(cfg, ["post", "export_tables"], True)
    set_nested(cfg, ["post", "smoke_fast"], True)
    set_nested(cfg, ["post", "force_isolation_smoke_fast"], True)

    input_rows = rewrite_inputs_to_source_snapshots(cfg, source_run_root, source_cfg=source_cfg)
    cfg["debug_he2_ndlm_main_keep_broad_screen"] = {
        "campaign_id": "he2_ndlm_main_keep_broad_screen_20260625",
        "grid_spec_id": grid_spec_id,
        "discount_case_id": str(spec["discount_case_id"]),
        "epsilon": float(spec["epsilon"]),
        "epsilon_label": str(spec["epsilon_label"]),
        "source_run_id": str(source_row["run_id"]),
        "source_run_root": str(source_run_root),
        "source_config": str(source_row["resolved_config"]),
        "matrix_dir": str(matrix_dir),
        "code_commit": code_commit,
        "cleanup_rdata_after_post": True,
        "one_core_per_run": True,
    }
    return cfg, input_rows


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    ensure_dir(path.parent)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def build_matrix(authority_rows: Path, artifact_root: Path, matrix_dir: Path, config_output_dir: Path, *, reset_status: bool) -> dict[str, Any]:
    ensure_dir(artifact_root)
    ensure_dir(matrix_dir)
    ensure_dir(config_output_dir)
    ensure_dir(runs_dir(artifact_root))
    authority = load_authority_rows(authority_rows)
    specs = build_grid_specs()
    code_commit = git_head()

    plan_rows: list[dict[str, Any]] = []
    source_input_rows: list[dict[str, Any]] = []
    frozen_rows: list[dict[str, Any]] = []
    order_index = 0

    for _, spec in specs.iterrows():
        for _, source_row in authority.iterrows():
            cutoff = str(source_row["cutoff"])
            grid_spec_id = str(spec["grid_spec_id"])
            run_id = run_id_for(cutoff, grid_spec_id)
            config_path = config_output_dir / f"{run_id}.yaml"
            source_config = Path(str(source_row["resolved_config"]))
            if not source_config.exists():
                raise FileNotFoundError(f"Missing source resolved config for cutoff={cutoff}: {source_config}")
            cfg, input_rows = mutate_config(
                load_yaml(source_config),
                source_row=source_row,
                spec=spec,
                artifact_root=artifact_root,
                matrix_dir=matrix_dir,
                config_path=config_path,
                code_commit=code_commit,
            )
            write_yaml(config_path, cfg)
            for input_row in input_rows:
                row = dict(input_row)
                row.update(
                    {
                        "cutoff": cutoff,
                        "source_run_id": str(source_row["run_id"]),
                        "source_run_root": str(source_row["run_root"]),
                    }
                )
                source_input_rows.append(row)

            order_index += 1
            is_heavy = cutoff == HEAVY_CUTOFF
            plan_row = {
                "order_index": order_index,
                "cutoff": cutoff,
                "epsilon": grid_spec_id,
                "epsilon_value": float(spec["epsilon"]),
                "epsilon_label": str(spec["epsilon_label"]),
                "grid_spec_id": grid_spec_id,
                "discount_case_id": str(spec["discount_case_id"]),
                "lane": TARGET_LANE,
                "run_scope": "he2_ndlm_main_keep_broad_screen",
                "run_id": run_id,
                "config_path": str(config_path),
                "compare_outdir": str(artifact_root / "reports" / f"{run_id}_compare_not_used"),
                "priority_group": 2 if is_heavy else 1,
                "max_concurrent_class": "heavy" if is_heavy else "ordinary",
                "family_id": TARGET_LANE,
                "model_id": TARGET_MODEL_ID,
                "model_key": "ndlm_main",
                "model_class": "ndlm",
                "model_variant": TARGET_MODEL_VARIANT,
                "transfer_mode": "keep",
                "quantile_submodels": 1,
                "active_quantiles": "",
                "selected_source_run": str(source_row["run_id"]),
                "selected_source_config": str(source_row["resolved_config"]),
                "selected_source_run_root": str(source_row["run_root"]),
                "selected_mean_crps": str(source_row.get("mean_crps", "")),
                "df_t": float(spec["df_t"]),
                "df_s1": float(spec["df_s1"]),
                "df_s2": float(spec["df_s2"]),
                "df_s67": float(spec["df_s67"]),
                "df_discrep": float(spec["df_discrep"]),
                "lambda": float(spec["lambda"]),
                "df_trans": float(spec["df_trans"]),
                "df_covs": float(spec["df_covs"]),
                "c_factor": float(spec["c_factor"]),
                "forecast_cov_epsilon": float(spec["epsilon"]),
                "max_iter": 100,
            }
            plan_rows.append(plan_row)
            frozen_rows.append(dict(plan_row))

    plan = pd.DataFrame(plan_rows)
    plan.to_csv(matrix_dir / "matrix_plan.csv", index=False)
    specs.to_csv(matrix_dir / "grid_spec_manifest_resolved.csv", index=False)
    pd.DataFrame(frozen_rows).to_csv(matrix_dir / "frozen_spec_manifest.csv", index=False)
    pd.DataFrame(plan_rows).loc[
        :,
        [
            "grid_spec_id",
            "discount_case_id",
            "cutoff",
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
        ],
    ].to_csv(matrix_dir / "grid_run_registry.csv", index=False)
    pd.DataFrame(source_input_rows).drop_duplicates().to_csv(matrix_dir / "source_input_manifest.csv", index=False)

    status_path = matrix_dir / "matrix_status.csv"
    if reset_status or not status_path.exists():
        write_csv(
            [],
            status_path,
        )
        status_path.write_text(
            "cutoff,epsilon,lane,run_id,phase,status,started_at,finished_at,manifest_path,latest_log_mtime,disk_free_gb,note\n",
            encoding="utf-8",
        )

    queue = {
        "ordinary_max_concurrent": 3,
        "pause_free_gb": 25.0,
        "launch_free_gb": 35.0,
        "heavy_free_gb": 35.0,
        "pause_mem_gb": 0.0,
        "launch_mem_gb": 0.0,
        "heavy_mem_gb": 0.0,
        "heavy_cutoff_max_concurrent": 1,
        "heavy_cutoff_blocks_ordinary": False,
        "poll_seconds": 60,
        "continue_on_fail": True,
        "skip_compares": True,
        "cleanup_rdata_after_post": True,
    }
    metadata = {
        "campaign_id": "he2_ndlm_main_keep_broad_screen_20260625",
        "created_at_utc": utc_now(),
        "authority_rows": str(authority_rows),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "target_lane": TARGET_LANE,
        "target_model_id": TARGET_MODEL_ID,
        "target_score_scale": TARGET_SCORE_SCALE,
        "queue": queue,
        "code_commit": code_commit,
        "n_discount_cases": int(len(build_discount_cases())),
        "n_specs": int(len(specs)),
        "n_cutoffs": int(len(EXPECTED_CUTOFFS)),
        "n_run_rows": int(len(plan_rows)),
        "expected_run_rows": 1440,
        "one_core_per_run": True,
        "cleanup_rdata_after_post": True,
        "launch_status": "prepared_not_launched",
    }
    write_yaml(matrix_dir / "matrix_metadata.yaml", metadata)
    write_yaml(matrix_dir / "campaign_snapshot.yaml", {"metadata": metadata, "grid_axes": GRID_AXES, "epsilons": GRID_EPSILONS})

    launch_cmd = [
        "python3",
        "scripts/run_multimodel_v8_queue.py",
        "--matrix-dir",
        str(matrix_dir),
        "--artifact-root",
        str(artifact_root),
        "--ordinary-max-concurrent",
        "3",
        "--pause-free-gb",
        "25",
        "--launch-free-gb",
        "35",
        "--heavy-free-gb",
        "35",
        "--heavy-cutoff-max-concurrent",
        "1",
        "--poll-seconds",
        "60",
        "--continue-on-fail",
        "--skip-compares",
        "--no-heavy-cutoff-blocks-ordinary",
    ]
    (matrix_dir / "launch_settings.env").write_text(
        "\n".join(
            [
                f"ARTIFACT_ROOT={artifact_root}",
                f"MATRIX_DIR={matrix_dir}",
                "ORDINARY_MAX_CONCURRENT=3",
                "HEAVY_CUTOFF_MAX_CONCURRENT=1",
                "HEAVY_CUTOFF_BLOCKS_ORDINARY=0",
                "CONTINUE_ON_FAIL=1",
                "SKIP_COMPARES=1",
                "CLEANUP_RDATA_AFTER_POST=1",
                "POLL_SECONDS=60",
                "",
            ]
        ),
        encoding="utf-8",
    )
    detached = (
        "setsid bash -lc 'cd "
        f"{ROOT} && exec {' '.join(launch_cmd)}' > "
        f"{matrix_dir / 'queue_stdout.log'} 2>&1 & echo $! > {matrix_dir / 'queue.pid'}"
    )
    lines = [
        "# HE2 N-M-T1 Broad Screen Launch Readiness",
        "",
        f"- status: `prepared_not_launched`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- config_output_dir: `{config_output_dir}`",
        f"- authority_rows: `{authority_rows}`",
        f"- specs: `{len(specs)}`",
        f"- cutoffs: `{len(EXPECTED_CUTOFFS)}`",
        f"- run rows: `{len(plan_rows)}`",
        f"- concurrency cap: `3` one-core NDLM runs",
        f"- heavy cutoff cap: `1` active `20221225` run",
        f"- cleanup after post: `true`",
        f"- continue on fail: `true`",
        f"- skip compare bundles during queue: `true`",
        f"- disk free GB at preparation: `{artifact_disk_free_gb(artifact_root)}`",
        "",
        "## Launch Command",
        "",
        "Do not run this command until explicit launch approval.",
        "",
        "```bash",
        detached,
        "```",
        "",
        "## Validation",
        "",
        "```bash",
        f"python3 scripts/validate_he2_ndlm_main_keep_broad_screen_prelaunch.py --artifact-root {artifact_root} --matrix-dir {matrix_dir}",
        "```",
    ]
    (matrix_dir / "LAUNCH_READY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (matrix_dir / "queue.log").touch()
    return metadata


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Prepare the HE2 N-M-T1 broad NDLM keep screen matrix.")
    ap.add_argument("--authority-rows", default=str(DEFAULT_AUTHORITY_ROWS))
    ap.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    ap.add_argument("--matrix-dir", default=str(DEFAULT_MATRIX_DIR))
    ap.add_argument("--config-output-dir", default=str(DEFAULT_CONFIG_OUTPUT_DIR))
    ap.add_argument("--reset-status", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    metadata = build_matrix(
        Path(args.authority_rows).expanduser().resolve(),
        Path(args.artifact_root).expanduser().resolve(),
        Path(args.matrix_dir).expanduser().resolve(),
        Path(args.config_output_dir).expanduser().resolve(),
        reset_status=bool(args.reset_status),
    )
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_he2_bayesian_publication_relaunch_configs import (  # noqa: E402
    MODEL_ID_BY_FAMILY,
    MODEL_KEY_BY_FAMILY,
    _build_cutoff_bundle_audit_rows,
    _build_run_config,
    _deep_merge_dict,
    _extract_spec_row,
    _resolve_row_config_patch,
)
from he2_publication_relaunch_lib import (  # noqa: E402
    DEFAULT_BUNDLE_ARTIFACT_ROOT,
    DEFAULT_BUNDLE_RUN_ID,
    DEFAULT_DATA_START,
    DEFAULT_QUANTILES,
    EXPECTED_CUTOFFS,
    canonical_shared_paths,
    ensure_dir,
    load_publication_manifest_rows,
    load_structured_file,
    load_yaml,
    model_class,
    render_quantile_label,
    row_kind,
    write_yaml,
)
from multimodel_v8_lib import HEAVY_CUTOFF, artifact_disk_free_gb, control_dir, reports_dir, runs_dir  # noqa: E402

DEFAULT_CONFIG = ROOT / "config" / "he2_bayesian_publication_relaunch_exdqlm_multivar_keep_epsilon_discount_grid_20260524.template.yaml"
REQUIRED_SPEC_COLUMNS = [
    "grid_spec_id",
    "discount_case_id",
    "epsilon",
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
    "min_update_iters",
]
FLOAT_COLUMNS = [
    "epsilon",
    "c_factor",
    "df_t",
    "df_s1",
    "df_s2",
    "df_s67",
    "df_discrep",
    "lambda",
    "df_trans",
    "df_covs",
]
INT_COLUMNS = ["max_iter", "min_update_iters"]


def resolve_path(raw: str | Path, *, base: Path = ROOT) -> Path:
    path = Path(str(raw)).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def safe_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value).strip())
    if not token:
        raise ValueError("empty grid token")
    return token


def grid_run_id(cutoff: str, grid_spec_id: str, family: str = "exdqlm_multivar_keep") -> str:
    return f"multimodel_{str(cutoff).zfill(8)}_v8_he2grid_{safe_token(grid_spec_id)}_{family}"


def load_grid_specs(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"grid_spec_id": str, "discount_case_id": str})
    missing = [col for col in REQUIRED_SPEC_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"grid spec manifest missing required columns: {missing}")
    if df["grid_spec_id"].duplicated().any():
        dupes = sorted(df.loc[df["grid_spec_id"].duplicated(), "grid_spec_id"].astype(str).unique())
        raise ValueError(f"grid_spec_id values must be unique; duplicates: {dupes}")
    for col in FLOAT_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="raise")
    for col in INT_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="raise").astype(int)
    for col in ["df_t", "df_s1", "df_s2", "df_s67", "df_discrep", "lambda", "df_trans", "df_covs"]:
        bad = df.loc[(df[col] <= 0) | (df[col] > 1), ["grid_spec_id", col]]
        if not bad.empty:
            raise ValueError(f"{col} must be in (0, 1]; bad rows: {bad.to_dict(orient='records')}")
    if (df["epsilon"] <= 0).any():
        raise ValueError("epsilon must be positive for every grid spec")
    if (df["c_factor"] <= 0).any():
        raise ValueError("c_factor must be positive for every grid spec")
    if (df["max_iter"] < df["min_update_iters"]).any():
        raise ValueError("max_iter must be >= min_update_iters for every grid spec")
    return df


def build_spec_patch(spec: pd.Series, component_cfg: dict[str, Any]) -> dict[str, Any]:
    component_enabled = bool(component_cfg.get("enabled", True))
    component_quantile = float(component_cfg.get("quantile", 0.50))
    component_pre_days = int(component_cfg.get("pre_days", 30))
    component_fail_fast = bool(component_cfg.get("fail_fast", True))
    return {
        "models": {
            "exdqlm_multivar": {
                "forecast_transfer_mode": "keep",
                "state_evolution": {
                    "df_t": float(spec["df_t"]),
                    "df_s1": float(spec["df_s1"]),
                    "df_s2": float(spec["df_s2"]),
                    "df_s67": float(spec["df_s67"]),
                    "df_discrep": float(spec["df_discrep"]),
                    "lambda": float(spec["lambda"]),
                    "df_trans": float(spec["df_trans"]),
                    "df_covs": float(spec["df_covs"]),
                },
            },
        },
        "fit": {
            "quantiles": list(DEFAULT_QUANTILES),
            "exdqlm_multivar": {
                "gamma_sigma": {
                    "max_iter": int(spec["max_iter"]),
                    "min_update_iters": int(spec["min_update_iters"]),
                    "min_total_iters": int(spec["min_update_iters"]),
                    "coherence_guard": {
                        "enabled": True,
                        "rollback_on_guard": True,
                        "min_uts_psi": 1e-8,
                        "nonnegative_tol": 1e-10,
                    },
                    "terminal_sampling_guard": {
                        "mode": "fail_fast",
                        "min_guard_count": 1,
                        "max_guard_lag_iters": 20,
                        "require_frozen": True,
                    },
                },
                "pseudodata_guard": {
                    "enabled": True,
                    "mode": "fail",
                },
                "legacy": {
                    "forecast_cov": {
                        "c_factor": float(spec["c_factor"]),
                        "epsilon": float(spec["epsilon"]),
                    },
                },
            },
        },
        "post": {
            "figures": True,
            "export_tables": True,
            "smoke_fast": True,
            "force_isolation_smoke_fast": True,
            "multivar_component_diagnostics": {
                "enabled": component_enabled,
                "quantile": component_quantile,
                "pre_days": component_pre_days,
                "fail_fast": component_fail_fast,
            },
        },
    }


def source_rows_by_cutoff(manifest_path: Path, cutoffs: list[str], family: str, manuscript_label: str) -> dict[str, dict[str, str]]:
    rows = load_publication_manifest_rows(manifest_path)
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        if row["family"] == family and row["manuscript_label"] == manuscript_label and row["cutoff"] in cutoffs:
            out[row["cutoff"]] = row
    missing = [cutoff for cutoff in cutoffs if cutoff not in out]
    if missing:
        raise ValueError(f"publication manifest missing source rows for cutoffs={missing}, family={family}, label={manuscript_label}")
    return out


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build the HE2 exDQLM multivar keep epsilon/discount grid matrix.")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--spec-manifest")
    ap.add_argument("--base-batch-file")
    ap.add_argument("--artifact-root")
    ap.add_argument("--matrix-dir")
    ap.add_argument("--config-output-dir")
    ap.add_argument("--reset-status", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    config_path = resolve_path(args.config)
    campaign = load_yaml(config_path)
    campaign_cfg = campaign.get("campaign", {}) if isinstance(campaign.get("campaign"), dict) else {}
    source_cfg = campaign.get("source", {}) if isinstance(campaign.get("source"), dict) else {}
    bundles_cfg = campaign.get("bundles", {}) if isinstance(campaign.get("bundles"), dict) else {}
    grid_cfg = campaign.get("grid", {}) if isinstance(campaign.get("grid"), dict) else {}
    queue_cfg = campaign.get("queue", {}) if isinstance(campaign.get("queue"), dict) else {}
    resources_cfg = campaign.get("resources", {}) if isinstance(campaign.get("resources"), dict) else {}

    spec_manifest_path = resolve_path(args.spec_manifest or grid_cfg.get("spec_manifest", ""))
    base_batch_path = resolve_path(args.base_batch_file or grid_cfg.get("base_batch_file", ""))
    manifest_path = resolve_path(source_cfg.get("publication_manifest", "reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv"))
    artifact_root = resolve_path(args.artifact_root or campaign_cfg.get("artifact_root", ""))
    matrix_dir = ensure_dir(resolve_path(args.matrix_dir or campaign_cfg.get("matrix_dir", artifact_root / "control" / "publication_relaunch_matrix")))
    config_output_dir = ensure_dir(resolve_path(args.config_output_dir or campaign_cfg.get("config_output_dir", artifact_root / "control" / "generated_configs")))
    ensure_dir(runs_dir(artifact_root))
    ensure_dir(reports_dir(artifact_root))
    ensure_dir(control_dir(artifact_root))

    cutoffs = [str(c).zfill(8) for c in campaign_cfg.get("cutoffs", EXPECTED_CUTOFFS)]
    family = str(grid_cfg.get("model_family", "exdqlm_multivar_keep"))
    manuscript_label = str(grid_cfg.get("manuscript_label", "exAL-M-T1"))
    bundle_artifact_root = resolve_path(bundles_cfg.get("artifact_root", DEFAULT_BUNDLE_ARTIFACT_ROOT))
    bundle_run_id = str(bundles_cfg.get("bundle_run_id", DEFAULT_BUNDLE_RUN_ID))
    data_start = str(bundles_cfg.get("data_start", DEFAULT_DATA_START))
    resources = {
        "fit_parallel_workers": int(resources_cfg.get("fit_parallel_workers", 7)),
        "mc_cores": int(resources_cfg.get("mc_cores", 7)),
    }
    component_cfg = grid_cfg.get("component_diagnostics", {}) if isinstance(grid_cfg.get("component_diagnostics"), dict) else {}

    specs = load_grid_specs(spec_manifest_path)
    source_rows = source_rows_by_cutoff(manifest_path, cutoffs, family, manuscript_label)
    base_batch = load_structured_file(base_batch_path)
    head = git_head()

    plan_rows: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    frozen_spec_rows: list[dict[str, Any]] = []
    generated_configs: list[Path] = []
    order_index = 0

    for _, spec in specs.iterrows():
        grid_spec_id = str(spec["grid_spec_id"])
        for cutoff in cutoffs:
            source_row = source_rows[cutoff]
            source_cfg_path = Path(source_row["resolved_config_path"])
            if not source_cfg_path.exists():
                raise FileNotFoundError(f"missing source resolved config: {source_cfg_path}")
            shared = canonical_shared_paths(bundle_artifact_root, cutoff, bundle_run_id)
            missing_shared = [str(path) for path in shared.values() if isinstance(path, Path) and not path.exists()]
            if missing_shared:
                raise FileNotFoundError(f"canonical shared bundle incomplete for cutoff={cutoff}: {missing_shared[:5]}")

            base_patch = _resolve_row_config_patch(base_batch, source_row)
            row_patch = _deep_merge_dict(base_patch, build_spec_patch(spec, component_cfg))
            run_id = grid_run_id(cutoff, grid_spec_id, family)
            config_file = config_output_dir / f"{run_id}.yaml"
            cfg = _build_run_config(
                load_yaml(source_cfg_path),
                run_id=run_id,
                artifact_root=artifact_root,
                cutoff=cutoff,
                bundle_artifact_root=bundle_artifact_root,
                bundle_run_id=bundle_run_id,
                source_row=source_row,
                resources=resources,
                selected_quantiles=list(DEFAULT_QUANTILES),
                profile_name="epsilon_discount_grid_20260524",
                row_config_patch=row_patch,
                row_config_patch_source=str(spec_manifest_path),
            )
            cfg.setdefault("run", {})
            cfg["run"]["resolved_run_root"] = str(runs_dir(artifact_root) / run_id)
            cfg["run"]["resolved_config_path"] = str(config_file)
            if isinstance(cfg.get("debug_he2_publication_relaunch"), dict):
                cfg["debug_he2_publication_relaunch"]["campaign_spec_id"] = str(
                    campaign_cfg.get("campaign_spec_id", "he2grid")
                )
                cfg["debug_he2_publication_relaunch"]["grid_spec_id"] = grid_spec_id
            cfg["debug_he2_exdqlm_keep_grid"] = {
                "grid_spec_id": grid_spec_id,
                "discount_case_id": str(spec["discount_case_id"]),
                "epsilon": float(spec["epsilon"]),
                "c_factor": float(spec["c_factor"]),
                "spec_manifest": str(spec_manifest_path),
                "base_batch_file": str(base_batch_path),
                "code_commit": head,
                "allow_run_failures": bool(grid_cfg.get("allow_run_failures", True)),
                "skip_compare_bundles": bool(grid_cfg.get("skip_compare_bundles", True)),
                "cleanup_rdata_after_post": bool(grid_cfg.get("cleanup_rdata_after_post", True)),
            }
            write_yaml(config_file, cfg)
            generated_configs.append(config_file)

            order_index += 1
            active_quantiles = ((cfg.get("fit") or {}).get("quantiles") or [])
            compare_outdir = reports_dir(artifact_root) / f"grid_{grid_spec_id}_{cutoff}_compare_not_used"
            plan_row = {
                "order_index": order_index,
                "cutoff": cutoff,
                "epsilon": grid_spec_id,
                "epsilon_value": float(spec["epsilon"]),
                "grid_spec_id": grid_spec_id,
                "discount_case_id": str(spec["discount_case_id"]),
                "lane": family,
                "run_scope": "he2_exdqlm_multivar_keep_epsilon_discount_grid",
                "run_id": run_id,
                "config_path": str(config_file),
                "compare_outdir": str(compare_outdir),
                "priority_group": 2 if cutoff == HEAVY_CUTOFF else 1,
                "max_concurrent_class": "heavy" if cutoff == HEAVY_CUTOFF else "ordinary",
                "family_id": family,
                "model_id": MODEL_ID_BY_FAMILY[family],
                "model_key": MODEL_KEY_BY_FAMILY[family],
                "model_class": model_class(family),
                "likelihood_mode": source_row.get("likelihood_mode", ""),
                "transfer_mode": "keep",
                "authoritative_compare_dir": "",
                "selected_compare_dir": "",
                "selected_source_run": source_row["run_id"],
                "selected_source_type": source_row["campaign_lineage"],
                "selected_source_config": source_row["resolved_config_path"],
                "selected_mean_crps": source_row.get("crps_exact", ""),
                "selected_c_factor": float(spec["c_factor"]),
                "selected_epsilon": grid_spec_id,
                "manuscript_label": manuscript_label,
                "row_kind": row_kind(family),
                "quantile_submodels": len(active_quantiles),
                "publication_crps_display4": source_row.get("crps_display4", ""),
                "active_quantiles": "|".join(render_quantile_label(float(q)) for q in active_quantiles),
                "profile_name": "epsilon_discount_grid_20260524",
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
            }
            plan_rows.append(plan_row)
            selection_rows.append(dict(plan_row))

            frozen = _extract_spec_row(plan_row, source_row, cfg)
            frozen.update({
                "grid_spec_id": grid_spec_id,
                "discount_case_id": str(spec["discount_case_id"]),
                "grid_epsilon": float(spec["epsilon"]),
                "grid_c_factor": float(spec["c_factor"]),
                "grid_code_commit": head,
                "grid_spec_manifest": str(spec_manifest_path),
                "grid_template": str(config_path),
                "allow_run_failures": bool(grid_cfg.get("allow_run_failures", True)),
                "skip_compare_bundles": bool(grid_cfg.get("skip_compare_bundles", True)),
                "cleanup_rdata_after_post": bool(grid_cfg.get("cleanup_rdata_after_post", True)),
            })
            frozen_spec_rows.append(frozen)

    plan_df = pd.DataFrame(plan_rows)
    plan_df.to_csv(matrix_dir / "matrix_plan.csv", index=False)
    pd.DataFrame(selection_rows).to_csv(matrix_dir / "selection_summary.csv", index=False)
    frozen_df = pd.DataFrame(frozen_spec_rows)
    frozen_df.to_csv(matrix_dir / "frozen_spec_manifest.csv", index=False)
    (matrix_dir / "frozen_spec_manifest.json").write_text(frozen_df.to_json(orient="records", indent=2) + "\n", encoding="utf-8")
    specs.assign(code_commit=head).to_csv(matrix_dir / "grid_spec_manifest_resolved.csv", index=False)
    pd.DataFrame(plan_rows).loc[:, [
        "grid_spec_id", "discount_case_id", "cutoff", "run_id", "config_path", "forecast_cov_epsilon",
        "c_factor", "df_t", "df_s1", "df_s2", "df_s67", "df_discrep", "lambda", "df_trans", "df_covs",
    ]].to_csv(matrix_dir / "grid_run_registry.csv", index=False)

    cutoff_audit_df = pd.DataFrame(_build_cutoff_bundle_audit_rows(plan_rows, bundle_artifact_root, bundle_run_id))
    cutoff_audit_df.to_csv(matrix_dir / "cutoff_bundle_audit.csv", index=False)
    (matrix_dir / "cutoff_bundle_audit.json").write_text(cutoff_audit_df.to_json(orient="records", indent=2) + "\n", encoding="utf-8")

    status_path = matrix_dir / "matrix_status.csv"
    if args.reset_status or not status_path.exists():
        from he2_publication_relaunch_lib import initialize_matrix_status

        initialize_matrix_status(status_path)
    (matrix_dir / "queue.log").touch()

    queue = {
        "ordinary_max_concurrent": int(queue_cfg.get("ordinary_max_concurrent", 8)),
        "pause_free_gb": float(queue_cfg.get("pause_free_gb", 25)),
        "launch_free_gb": float(queue_cfg.get("launch_free_gb", 35)),
        "heavy_free_gb": float(queue_cfg.get("heavy_free_gb", 35)),
        "pause_mem_gb": float(queue_cfg.get("pause_mem_gb", 0)),
        "launch_mem_gb": float(queue_cfg.get("launch_mem_gb", 0)),
        "heavy_mem_gb": float(queue_cfg.get("heavy_mem_gb", queue_cfg.get("launch_mem_gb", 0))),
        "heavy_cutoff_max_concurrent": int(queue_cfg.get("heavy_cutoff_max_concurrent", 8)),
        "heavy_cutoff_blocks_ordinary": bool(queue_cfg.get("heavy_cutoff_blocks_ordinary", False)),
        "poll_seconds": int(queue_cfg.get("poll_seconds", 30)),
    }
    metadata = {
        "campaign_id": campaign_cfg.get("campaign_id", "he2_exdqlm_keep_grid"),
        "campaign_config": str(config_path),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "publication_manifest": str(manifest_path),
        "bundle_artifact_root": str(bundle_artifact_root),
        "bundle_run_id": bundle_run_id,
        "data_start": data_start,
        "spec_manifest": str(spec_manifest_path),
        "base_batch_file": str(base_batch_path),
        "compare_builder": "",
        "skip_compare_bundles": bool(grid_cfg.get("skip_compare_bundles", True)),
        "allow_run_failures": bool(grid_cfg.get("allow_run_failures", True)),
        "queue": queue,
        "resources": resources,
        "code_commit": head,
        "n_specs": int(len(specs)),
        "n_cutoffs": int(len(cutoffs)),
        "n_run_rows": int(len(plan_rows)),
        "n_quantile_fits": int(len(plan_rows) * len(DEFAULT_QUANTILES)),
    }
    write_yaml(matrix_dir / "matrix_metadata.yaml", metadata)
    write_yaml(matrix_dir / "campaign_snapshot.yaml", {"campaign": campaign, "campaign_path": str(config_path), "grid_metadata": metadata})

    launch_cmd = [
        "python3", "scripts/run_multimodel_v8_queue.py",
        "--matrix-dir", str(matrix_dir),
        "--artifact-root", str(artifact_root),
        "--ordinary-max-concurrent", str(queue["ordinary_max_concurrent"]),
        "--pause-free-gb", str(queue["pause_free_gb"]),
        "--launch-free-gb", str(queue["launch_free_gb"]),
        "--heavy-free-gb", str(queue["heavy_free_gb"]),
        "--pause-mem-gb", str(queue["pause_mem_gb"]),
        "--launch-mem-gb", str(queue["launch_mem_gb"]),
        "--heavy-mem-gb", str(queue["heavy_mem_gb"]),
        "--heavy-cutoff-max-concurrent", str(queue["heavy_cutoff_max_concurrent"]),
        "--poll-seconds", str(queue["poll_seconds"]),
        "--continue-on-fail",
        "--skip-compares",
    ]
    if not queue["heavy_cutoff_blocks_ordinary"]:
        launch_cmd.append("--no-heavy-cutoff-blocks-ordinary")

    launch_env = "\n".join([
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
    ])
    (matrix_dir / "launch_settings.env").write_text(launch_env, encoding="utf-8")

    lines = [
        "# HE2 exDQLM Multivar Keep Epsilon/Discount Grid Scope",
        "",
        f"- status: `prepared_not_launched`",
        f"- campaign_config: `{config_path}`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- config_output_dir: `{config_output_dir}`",
        f"- spec_manifest: `{spec_manifest_path}`",
        f"- base_batch_file: `{base_batch_path}`",
        f"- code_commit: `{head}`",
        f"- specs: `{len(specs)}`",
        f"- cutoffs: `{len(cutoffs)}`",
        f"- run rows: `{len(plan_rows)}`",
        f"- quantile fits: `{len(plan_rows) * len(DEFAULT_QUANTILES)}`",
        f"- queue rows at once: `{queue['ordinary_max_concurrent']}`",
        f"- max active quantile workers: `{queue['ordinary_max_concurrent'] * resources['fit_parallel_workers']}`",
        f"- queue pause memory GB: `{queue['pause_mem_gb']}`",
        f"- queue launch memory GB: `{queue['launch_mem_gb']}`",
        f"- queue heavy memory GB: `{queue['heavy_mem_gb']}`",
        f"- allow run failures: `{bool(grid_cfg.get('allow_run_failures', True))}`",
        f"- skip compare bundles: `{bool(grid_cfg.get('skip_compare_bundles', True))}`",
        f"- cleanup after post: `{bool(grid_cfg.get('cleanup_rdata_after_post', True))}`",
        f"- artifact disk free GB: `{artifact_disk_free_gb(artifact_root)}`",
        "",
        "## Launch Command",
        "",
        "Do not run until smoke/prelaunch approval is explicit.",
        "",
        "```bash",
        " ".join(launch_cmd),
        "```",
        "",
        "## Key Files",
        "",
        "- `matrix_plan.csv`",
        "- `grid_spec_manifest_resolved.csv`",
        "- `grid_run_registry.csv`",
        "- `frozen_spec_manifest.csv`",
        "- `cutoff_bundle_audit.csv`",
    ]
    (matrix_dir / "GRID_SCOPE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"artifact_root={artifact_root}")
    print(f"matrix_dir={matrix_dir}")
    print(f"config_output_dir={config_output_dir}")
    print(f"specs={len(specs)}")
    print(f"run_rows={len(plan_rows)}")
    print(f"quantile_fits={len(plan_rows) * len(DEFAULT_QUANTILES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_he2_exdqlm_multivar_keep_grid_smoke_matrix import (  # noqa: E402
    rewrite_config,
    resolve_path,
    safe_token,
)
from he2_exdqlm_keep_authoritative import load_authoritative_spec  # noqa: E402
from he2_publication_relaunch_lib import ensure_dir, initialize_matrix_status, write_yaml  # noqa: E402
from multimodel_v8_lib import artifact_disk_free_gb, control_dir, reports_dir, runs_dir  # noqa: E402


DEFAULT_MANIFEST = ROOT / "docs" / "exdqlm_multivar_keep_authoritative_specs_20260601.yaml"
DEFAULT_ARTIFACT_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_multivar_keep_authoritative_rdata_retention_20260610"
)


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return ""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build an exact five-row no-cleanup matrix for the authoritative HE2 exDQLM multivar keep winners."
    )
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--source-matrix-dir", default=None)
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument("--tag", default="authoritative_rdata_retained_20260610")
    parser.add_argument("--ordinary-max-concurrent", type=int, default=5)
    parser.add_argument("--pause-free-gb", type=float, default=180.0)
    parser.add_argument("--launch-free-gb", type=float, default=300.0)
    parser.add_argument("--heavy-free-gb", type=float, default=320.0)
    parser.add_argument("--pause-mem-gb", type=float, default=120.0)
    parser.add_argument("--launch-mem-gb", type=float, default=160.0)
    parser.add_argument("--heavy-mem-gb", type=float, default=180.0)
    parser.add_argument("--heavy-cutoff-max-concurrent", type=int, default=1)
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--gamma-sigma-max-iter", type=int, default=None)
    parser.add_argument("--gamma-sigma-min-update-iters", type=int, default=None)
    parser.add_argument("--state-guard-start-iter", type=int, default=None)
    parser.add_argument("--reset-status", action="store_true")
    return parser.parse_args(argv)


def _source_matrix_dir(spec, override: str | None) -> Path:
    if override:
        return resolve_path(override)
    return spec.runtime_root / "control" / "publication_relaunch_matrix"


def _copy_filtered_sidecars(source_matrix_dir: Path, matrix_dir: Path, selected_cutoffs: set[str], selected_specs: set[str]) -> None:
    csv_filters = {
        "grid_spec_manifest_resolved.csv": lambda df: df.loc[df["grid_spec_id"].astype(str).isin(selected_specs)]
        if "grid_spec_id" in df.columns
        else df,
        "frozen_spec_manifest.csv": lambda df: df.loc[
            df["cutoff"].astype(str).str.zfill(8).isin(selected_cutoffs)
            & df["grid_spec_id"].astype(str).isin(selected_specs)
        ]
        if {"cutoff", "grid_spec_id"}.issubset(df.columns)
        else df,
        "cutoff_bundle_audit.csv": lambda df: df.loc[df["cutoff"].astype(str).str.zfill(8).isin(selected_cutoffs)]
        if "cutoff" in df.columns
        else df,
    }
    for name, filter_fn in csv_filters.items():
        source = source_matrix_dir / name
        if not source.exists():
            continue
        df = pd.read_csv(source, dtype=str)
        filter_fn(df).to_csv(matrix_dir / name, index=False)
    for name in ["frozen_spec_manifest.json", "cutoff_bundle_audit.json"]:
        source = source_matrix_dir / name
        if source.exists():
            (matrix_dir / name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def build_matrix(
    *,
    manifest_path: Path,
    source_matrix_dir: Path | None,
    artifact_root: Path,
    tag: str,
    ordinary_max_concurrent: int,
    pause_free_gb: float,
    launch_free_gb: float,
    heavy_free_gb: float,
    pause_mem_gb: float,
    launch_mem_gb: float,
    heavy_mem_gb: float,
    heavy_cutoff_max_concurrent: int,
    poll_seconds: int,
    gamma_sigma_max_iter: int | None,
    gamma_sigma_min_update_iters: int | None,
    state_guard_start_iter: int | None,
    reset_status: bool,
) -> dict[str, Any]:
    spec = load_authoritative_spec(manifest_path)
    source_matrix_dir = _source_matrix_dir(spec, str(source_matrix_dir) if source_matrix_dir else None)
    source_plan = pd.read_csv(source_matrix_dir / "matrix_plan.csv", dtype=str)
    winners = spec.winners
    selected_rows: list[pd.Series] = []
    for winner in winners:
        matches = source_plan.loc[source_plan["run_id"].astype(str) == winner.run_id]
        if len(matches) != 1:
            raise SystemExit(f"Expected exactly one source row for {winner.run_id}; observed={len(matches)}")
        selected_rows.append(matches.iloc[0])

    matrix_dir = ensure_dir(control_dir(artifact_root) / "publication_relaunch_matrix")
    config_output_dir = ensure_dir(control_dir(artifact_root) / "generated_configs")
    ensure_dir(runs_dir(artifact_root))
    ensure_dir(reports_dir(artifact_root))
    ensure_dir(control_dir(artifact_root))
    head = git_head()

    plan_rows: list[dict[str, Any]] = []
    if len(winners) != len(selected_rows):
        raise SystemExit(f"winner/source row length mismatch: winners={len(winners)} selected_rows={len(selected_rows)}")
    for order_index, (winner, row) in enumerate(zip(winners, selected_rows), start=1):
        source_run_id = str(row["run_id"])
        run_id = f"{source_run_id}_{tag}"
        config_path = config_output_dir / f"{run_id}.yaml"
        source_config = Path(str(row["config_path"]))
        cfg = rewrite_config(
            source_config,
            artifact_root=artifact_root,
            run_id=run_id,
            config_path=config_path,
            tag=tag,
            source_run_id=source_run_id,
            source_grid_spec_id=winner.grid_spec_id,
            gamma_sigma_max_iter=gamma_sigma_max_iter,
            gamma_sigma_min_update_iters=gamma_sigma_min_update_iters,
            state_guard_start_iter=state_guard_start_iter,
        )
        cfg["debug_he2_exdqlm_keep_authoritative_retained"] = {
            "tag": tag,
            "source_runtime_root": str(spec.runtime_root),
            "source_run_id": source_run_id,
            "source_config": str(source_config),
            "source_matrix_dir": str(source_matrix_dir),
            "authoritative_manifest": str(manifest_path),
            "grid_spec_id": winner.grid_spec_id,
            "cutoff": winner.cutoff,
            "retain_rdata_intent": True,
            "expected_launch_flag": "--no-cleanup",
            "code_commit": head,
        }
        write_yaml(config_path, cfg)

        out = row.to_dict()
        out.update(
            {
                "order_index": order_index,
                "run_id": run_id,
                "source_grid_run_id": source_run_id,
                "source_grid_config_path": str(source_config),
                "config_path": str(config_path),
                "compare_outdir": str(reports_dir(artifact_root) / f"{run_id}_compare_not_used"),
                "run_scope": "he2_exdqlm_multivar_keep_authoritative_rdata_retention",
                "profile_name": tag,
                "authoritative_mean_crps": winner.mean_crps,
                "authoritative_median_crps": winner.median_crps,
                "authoritative_max_crps": winner.max_crps,
                "authoritative_runner_up_grid_spec_id": winner.runner_up_grid_spec_id,
                "authoritative_runner_up_mean_crps": winner.runner_up_mean_crps,
                "cleanup_rdata_after_post": False,
            }
        )
        plan_rows.append(out)

    plan_df = pd.DataFrame(plan_rows)
    plan_df.to_csv(matrix_dir / "matrix_plan.csv", index=False)
    plan_df.to_csv(matrix_dir / "selection_summary.csv", index=False)
    plan_df.to_csv(matrix_dir / "grid_run_registry.csv", index=False)
    _copy_filtered_sidecars(
        source_matrix_dir,
        matrix_dir,
        {winner.cutoff for winner in winners},
        {winner.grid_spec_id for winner in winners},
    )

    if reset_status or not (matrix_dir / "matrix_status.csv").exists():
        initialize_matrix_status(matrix_dir / "matrix_status.csv")
    (matrix_dir / "queue.log").touch()

    queue = {
        "ordinary_max_concurrent": int(ordinary_max_concurrent),
        "pause_free_gb": float(pause_free_gb),
        "launch_free_gb": float(launch_free_gb),
        "heavy_free_gb": float(heavy_free_gb),
        "pause_mem_gb": float(pause_mem_gb),
        "launch_mem_gb": float(launch_mem_gb),
        "heavy_mem_gb": float(heavy_mem_gb),
        "heavy_cutoff_max_concurrent": int(heavy_cutoff_max_concurrent),
        "heavy_cutoff_blocks_ordinary": False,
        "poll_seconds": int(poll_seconds),
    }
    metadata = {
        "campaign_id": f"he2_exdqlm_multivar_keep_authoritative_rdata_retention_{tag}",
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "source_runtime_root": str(spec.runtime_root),
        "source_matrix_dir": str(source_matrix_dir),
        "authoritative_manifest": str(manifest_path),
        "tag": tag,
        "cutoffs": [winner.cutoff for winner in winners],
        "grid_spec_ids": [winner.grid_spec_id for winner in winners],
        "exact_winner_run_ids": [winner.run_id for winner in winners],
        "cleanup_rdata_after_post": False,
        "retained_rdata_expected_after_post": True,
        "skip_compare_bundles": True,
        "allow_run_failures": True,
        "queue": queue,
        "resources": {"fit_parallel_workers": 7, "mc_cores": 7},
        "overrides": {
            "gamma_sigma_max_iter": gamma_sigma_max_iter,
            "gamma_sigma_min_update_iters": gamma_sigma_min_update_iters,
            "state_guard_start_iter": state_guard_start_iter,
        },
        "code_commit": head,
        "n_cutoffs": len(winners),
        "n_run_rows": len(plan_rows),
        "n_quantile_fits": len(plan_rows) * 7,
    }
    write_yaml(matrix_dir / "matrix_metadata.yaml", metadata)
    write_yaml(matrix_dir / "campaign_snapshot.yaml", {"authoritative_retained_metadata": metadata})

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
        "--no-cleanup",
    ]
    (matrix_dir / "launch_settings.env").write_text(
        "\n".join(
            [
                f"ARTIFACT_ROOT={artifact_root}",
                f"MATRIX_DIR={matrix_dir}",
                f"TAG={tag}",
                f"ORDINARY_MAX_CONCURRENT={queue['ordinary_max_concurrent']}",
                f"PAUSE_FREE_GB={queue['pause_free_gb']}",
                f"LAUNCH_FREE_GB={queue['launch_free_gb']}",
                f"HEAVY_FREE_GB={queue['heavy_free_gb']}",
                f"PAUSE_MEM_GB={queue['pause_mem_gb']}",
                f"LAUNCH_MEM_GB={queue['launch_mem_gb']}",
                f"HEAVY_MEM_GB={queue['heavy_mem_gb']}",
                f"HEAVY_CUTOFF_MAX_CONCURRENT={queue['heavy_cutoff_max_concurrent']}",
                f"POLL_SECONDS={queue['poll_seconds']}",
                "CONTINUE_ON_FAIL=1",
                "SKIP_COMPARES=1",
                "NO_CLEANUP=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    lines = [
        "# HE2 exDQLM Multivar Keep Authoritative Retained-RData Scope",
        "",
        "- status: `prepared_not_launched`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- source_runtime_root: `{spec.runtime_root}`",
        f"- authoritative_manifest: `{manifest_path}`",
        f"- exact winner rows: `{len(plan_df)}`",
        f"- quantile fits: `{len(plan_df) * 7}`",
        f"- cleanup after post: `false`",
        f"- retained `.RData` expected after post: `true`",
        f"- queue rows at once: `{queue['ordinary_max_concurrent']}`",
        f"- max active quantile workers: `{queue['ordinary_max_concurrent'] * 7}`",
        f"- artifact disk free GB at prepare time: `{artifact_disk_free_gb(artifact_root)}`",
        "",
        "## Launch Command",
        "",
        "```bash",
        " ".join(launch_cmd),
        "```",
        "",
        "## Winner Rows",
        "",
        "| Cutoff | Source Run | Retained Run | Spec |",
        "|---|---|---|---|",
    ]
    for winner, row in zip(winners, plan_rows):
        lines.append(f"| `{winner.cutoff}` | `{winner.run_id}` | `{row['run_id']}` | `{winner.grid_spec_id}` |")
    (matrix_dir / "RETAINED_RDATA_SCOPE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return metadata


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    metadata = build_matrix(
        manifest_path=resolve_path(args.manifest),
        source_matrix_dir=resolve_path(args.source_matrix_dir) if args.source_matrix_dir else None,
        artifact_root=resolve_path(args.artifact_root),
        tag=safe_token(args.tag),
        ordinary_max_concurrent=args.ordinary_max_concurrent,
        pause_free_gb=args.pause_free_gb,
        launch_free_gb=args.launch_free_gb,
        heavy_free_gb=args.heavy_free_gb,
        pause_mem_gb=args.pause_mem_gb,
        launch_mem_gb=args.launch_mem_gb,
        heavy_mem_gb=args.heavy_mem_gb,
        heavy_cutoff_max_concurrent=args.heavy_cutoff_max_concurrent,
        poll_seconds=args.poll_seconds,
        gamma_sigma_max_iter=args.gamma_sigma_max_iter,
        gamma_sigma_min_update_iters=args.gamma_sigma_min_update_iters,
        state_guard_start_iter=args.state_guard_start_iter,
        reset_status=args.reset_status,
    )
    print(f"artifact_root={metadata['artifact_root']}")
    print(f"matrix_dir={metadata['matrix_dir']}")
    print(f"config_output_dir={metadata['config_output_dir']}")
    print(f"run_rows={metadata['n_run_rows']}")
    print(f"quantile_fits={metadata['n_quantile_fits']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

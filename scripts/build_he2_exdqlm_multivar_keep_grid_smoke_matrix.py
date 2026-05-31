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

from he2_publication_relaunch_lib import ensure_dir, initialize_matrix_status, load_yaml, write_yaml  # noqa: E402
from multimodel_v8_lib import artifact_disk_free_gb, control_dir, reports_dir, runs_dir  # noqa: E402

DEFAULT_SOURCE_ARTIFACT_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524"
)
DEFAULT_SOURCE_MATRIX_DIR = DEFAULT_SOURCE_ARTIFACT_ROOT / "control" / "publication_relaunch_matrix"
DEFAULT_SMOKE_ARTIFACT_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_smoke_nocleanup_20260524"
)
DEFAULT_CUTOFFS = ["20211112"]
DEFAULT_GRID_SPEC_IDS = ["c01_eps365", "c05_eps030", "c06_eps030"]


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
        raise ValueError("empty token")
    return token


def split_csv_tokens(raw: str | list[str] | None, default: list[str]) -> list[str]:
    if raw is None:
        return list(default)
    if isinstance(raw, list):
        pieces: list[str] = []
        for item in raw:
            pieces.extend(str(item).split(","))
    else:
        pieces = str(raw).split(",")
    out = [piece.strip() for piece in pieces if piece.strip()]
    return out or list(default)


def set_nested(data: dict[str, Any], keys: list[str], value: Any) -> None:
    cur = data
    for key in keys[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[keys[-1]] = value


def rewrite_config(
    source_config: Path,
    *,
    artifact_root: Path,
    run_id: str,
    config_path: Path,
    tag: str,
    source_run_id: str,
    source_grid_spec_id: str,
    gamma_sigma_max_iter: int | None = None,
    gamma_sigma_min_update_iters: int | None = None,
    state_guard_start_iter: int | None = None,
) -> dict[str, Any]:
    cfg = load_yaml(source_config)
    cfg.setdefault("run", {})
    cfg["run"]["run_id"] = run_id
    cfg["run"]["run_root"] = str(runs_dir(artifact_root))
    cfg["run"]["overwrite"] = False
    cfg["run"]["auto_suffix_on_collision"] = False
    cfg["run"]["resolved_run_root"] = str(runs_dir(artifact_root) / run_id)
    cfg["run"]["resolved_config_path"] = str(config_path)
    if gamma_sigma_max_iter is not None:
        set_nested(cfg, ["fit", "exdqlm_multivar", "gamma_sigma", "max_iter"], int(gamma_sigma_max_iter))
    if gamma_sigma_min_update_iters is not None:
        set_nested(
            cfg,
            ["fit", "exdqlm_multivar", "gamma_sigma", "min_update_iters"],
            int(gamma_sigma_min_update_iters),
        )
        set_nested(
            cfg,
            ["fit", "exdqlm_multivar", "gamma_sigma", "min_total_iters"],
            int(gamma_sigma_min_update_iters),
        )
    if state_guard_start_iter is not None:
        set_nested(
            cfg,
            ["fit", "exdqlm_multivar", "gamma_sigma", "stabilization", "state_guard_start_iter"],
            int(state_guard_start_iter),
        )
    cfg.setdefault("debug_he2_exdqlm_keep_grid_smoke", {})
    cfg["debug_he2_exdqlm_keep_grid_smoke"] = {
        "tag": tag,
        "source_run_id": source_run_id,
        "source_config": str(source_config),
        "source_grid_spec_id": source_grid_spec_id,
        "gamma_sigma_max_iter_override": gamma_sigma_max_iter,
        "gamma_sigma_min_update_iters_override": gamma_sigma_min_update_iters,
        "state_guard_start_iter_override": state_guard_start_iter,
        "code_commit": git_head(),
    }
    return cfg


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Prepare a small smoke matrix from the HE2 exDQLM keep epsilon/discount grid.")
    ap.add_argument("--source-matrix-dir", default=str(DEFAULT_SOURCE_MATRIX_DIR))
    ap.add_argument("--artifact-root", default=str(DEFAULT_SMOKE_ARTIFACT_ROOT))
    ap.add_argument("--tag", default="smoke_nocleanup_20260524")
    ap.add_argument("--cutoffs", nargs="*", default=None, help="Comma-separated and/or repeated cutoff ids.")
    ap.add_argument("--grid-spec-ids", nargs="*", default=None, help="Comma-separated and/or repeated grid spec ids.")
    ap.add_argument("--ordinary-max-concurrent", type=int, default=1)
    ap.add_argument("--pause-free-gb", type=float, default=25.0)
    ap.add_argument("--launch-free-gb", type=float, default=35.0)
    ap.add_argument("--heavy-free-gb", type=float, default=35.0)
    ap.add_argument("--pause-mem-gb", type=float, default=80.0)
    ap.add_argument("--launch-mem-gb", type=float, default=120.0)
    ap.add_argument("--heavy-mem-gb", type=float, default=120.0)
    ap.add_argument("--heavy-cutoff-max-concurrent", type=int, default=1)
    ap.add_argument("--poll-seconds", type=int, default=30)
    ap.add_argument("--gamma-sigma-max-iter", type=int, default=None)
    ap.add_argument("--gamma-sigma-min-update-iters", type=int, default=None)
    ap.add_argument("--state-guard-start-iter", type=int, default=None)
    ap.add_argument("--reset-status", action="store_true")
    return ap.parse_args(argv)


def main() -> int:
    args = parse_args()
    source_matrix_dir = resolve_path(args.source_matrix_dir)
    artifact_root = resolve_path(args.artifact_root)
    tag = safe_token(args.tag)
    cutoffs = [str(x).zfill(8) for x in split_csv_tokens(args.cutoffs, DEFAULT_CUTOFFS)]
    grid_spec_ids = split_csv_tokens(args.grid_spec_ids, DEFAULT_GRID_SPEC_IDS)
    if args.gamma_sigma_max_iter is not None and int(args.gamma_sigma_max_iter) < 1:
        raise SystemExit("--gamma-sigma-max-iter must be >= 1")
    if args.gamma_sigma_min_update_iters is not None and int(args.gamma_sigma_min_update_iters) < 1:
        raise SystemExit("--gamma-sigma-min-update-iters must be >= 1")
    if args.state_guard_start_iter is not None and int(args.state_guard_start_iter) < 1:
        raise SystemExit("--state-guard-start-iter must be >= 1")
    if (
        args.gamma_sigma_max_iter is not None
        and args.gamma_sigma_min_update_iters is not None
        and int(args.gamma_sigma_max_iter) < int(args.gamma_sigma_min_update_iters)
    ):
        raise SystemExit("--gamma-sigma-max-iter must be >= --gamma-sigma-min-update-iters")

    source_plan = pd.read_csv(source_matrix_dir / "matrix_plan.csv", dtype=str)
    selected = source_plan.loc[
        source_plan["cutoff"].astype(str).str.zfill(8).isin(cutoffs)
        & source_plan["grid_spec_id"].astype(str).isin(grid_spec_ids)
    ].copy()
    if selected.empty:
        raise SystemExit(f"No rows selected for cutoffs={cutoffs} grid_spec_ids={grid_spec_ids}")
    missing_specs = sorted(set(grid_spec_ids) - set(selected["grid_spec_id"].astype(str)))
    missing_cutoffs = sorted(set(cutoffs) - set(selected["cutoff"].astype(str).str.zfill(8)))
    if missing_specs:
        raise SystemExit(f"Missing selected specs in source matrix: {missing_specs}")
    if missing_cutoffs:
        raise SystemExit(f"Missing selected cutoffs in source matrix: {missing_cutoffs}")

    matrix_dir = ensure_dir(control_dir(artifact_root) / "publication_relaunch_matrix")
    config_output_dir = ensure_dir(control_dir(artifact_root) / "generated_configs")
    ensure_dir(runs_dir(artifact_root))
    ensure_dir(reports_dir(artifact_root))

    plan_rows: list[dict[str, Any]] = []
    for order_index, (_, row) in enumerate(selected.sort_values(["order_index"]).iterrows(), start=1):
        source_run_id = str(row["run_id"])
        run_id = f"{source_run_id}_{tag}"
        config_path = config_output_dir / f"{run_id}.yaml"
        cfg = rewrite_config(
            Path(str(row["config_path"])),
            artifact_root=artifact_root,
            run_id=run_id,
            config_path=config_path,
            tag=tag,
            source_run_id=source_run_id,
            source_grid_spec_id=str(row["grid_spec_id"]),
            gamma_sigma_max_iter=args.gamma_sigma_max_iter,
            gamma_sigma_min_update_iters=args.gamma_sigma_min_update_iters,
            state_guard_start_iter=args.state_guard_start_iter,
        )
        write_yaml(config_path, cfg)

        out = row.to_dict()
        out["order_index"] = order_index
        out["run_id"] = run_id
        out["source_grid_run_id"] = source_run_id
        out["source_grid_config_path"] = str(row["config_path"])
        out["config_path"] = str(config_path)
        out["compare_outdir"] = str(reports_dir(artifact_root) / f"{run_id}_compare_not_used")
        out["run_scope"] = f"he2_exdqlm_multivar_keep_epsilon_discount_grid_smoke_{tag}"
        out["profile_name"] = tag
        out["gamma_sigma_max_iter_override"] = "" if args.gamma_sigma_max_iter is None else int(args.gamma_sigma_max_iter)
        out["gamma_sigma_min_update_iters_override"] = (
            "" if args.gamma_sigma_min_update_iters is None else int(args.gamma_sigma_min_update_iters)
        )
        out["state_guard_start_iter_override"] = "" if args.state_guard_start_iter is None else int(args.state_guard_start_iter)
        plan_rows.append(out)

    plan_df = pd.DataFrame(plan_rows)
    plan_df.to_csv(matrix_dir / "matrix_plan.csv", index=False)
    plan_df.to_csv(matrix_dir / "selection_summary.csv", index=False)
    plan_df.to_csv(matrix_dir / "grid_run_registry.csv", index=False)

    for name in ["grid_spec_manifest_resolved.csv", "frozen_spec_manifest.csv", "frozen_spec_manifest.json", "cutoff_bundle_audit.csv", "cutoff_bundle_audit.json"]:
        source_path = source_matrix_dir / name
        if source_path.exists():
            if name.endswith(".csv"):
                if name in {"grid_spec_manifest_resolved.csv"}:
                    df = pd.read_csv(source_path, dtype=str)
                    if "grid_spec_id" in df.columns:
                        df = df.loc[df["grid_spec_id"].astype(str).isin(grid_spec_ids)].copy()
                    df.to_csv(matrix_dir / name, index=False)
                elif name == "frozen_spec_manifest.csv":
                    df = pd.read_csv(source_path, dtype=str)
                    if "grid_spec_id" in df.columns and "cutoff" in df.columns:
                        df = df.loc[
                            df["grid_spec_id"].astype(str).isin(grid_spec_ids)
                            & df["cutoff"].astype(str).str.zfill(8).isin(cutoffs)
                        ].copy()
                    df.to_csv(matrix_dir / name, index=False)
                else:
                    df = pd.read_csv(source_path, dtype=str)
                    if "cutoff" in df.columns:
                        df = df.loc[df["cutoff"].astype(str).str.zfill(8).isin(cutoffs)].copy()
                    df.to_csv(matrix_dir / name, index=False)
            else:
                (matrix_dir / name).write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    if args.reset_status or not (matrix_dir / "matrix_status.csv").exists():
        initialize_matrix_status(matrix_dir / "matrix_status.csv")
    (matrix_dir / "queue.log").touch()

    queue = {
        "ordinary_max_concurrent": int(args.ordinary_max_concurrent),
        "pause_free_gb": float(args.pause_free_gb),
        "launch_free_gb": float(args.launch_free_gb),
        "heavy_free_gb": float(args.heavy_free_gb),
        "pause_mem_gb": float(args.pause_mem_gb),
        "launch_mem_gb": float(args.launch_mem_gb),
        "heavy_mem_gb": float(args.heavy_mem_gb),
        "heavy_cutoff_max_concurrent": int(args.heavy_cutoff_max_concurrent),
        "heavy_cutoff_blocks_ordinary": False,
        "poll_seconds": int(args.poll_seconds),
    }
    metadata = {
        "campaign_id": f"he2_exdqlm_multivar_keep_grid_smoke_{tag}",
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "source_matrix_dir": str(source_matrix_dir),
        "tag": tag,
        "cutoffs": cutoffs,
        "grid_spec_ids": grid_spec_ids,
        "skip_compare_bundles": True,
        "allow_run_failures": True,
        "queue": queue,
        "resources": {"fit_parallel_workers": 7, "mc_cores": 7},
        "overrides": {
            "gamma_sigma_max_iter": args.gamma_sigma_max_iter,
            "gamma_sigma_min_update_iters": args.gamma_sigma_min_update_iters,
            "state_guard_start_iter": args.state_guard_start_iter,
        },
        "code_commit": git_head(),
        "n_specs": len(set(plan_df["grid_spec_id"])),
        "n_cutoffs": len(set(plan_df["cutoff"])),
        "n_run_rows": int(len(plan_df)),
        "n_quantile_fits": int(len(plan_df) * 7),
    }
    write_yaml(matrix_dir / "matrix_metadata.yaml", metadata)
    write_yaml(matrix_dir / "campaign_snapshot.yaml", {"smoke_metadata": metadata})

    base_cmd = [
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
        "--no-heavy-cutoff-blocks-ordinary",
    ]
    no_cleanup_cmd = base_cmd + ["--no-cleanup"]
    cleanup_cmd = list(base_cmd)

    (matrix_dir / "launch_settings.env").write_text(
        "\n".join([
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
            f"HEAVY_CUTOFF_BLOCKS_ORDINARY={1 if queue['heavy_cutoff_blocks_ordinary'] else 0}",
            f"POLL_SECONDS={queue['poll_seconds']}",
            f"GAMMA_SIGMA_MAX_ITER_OVERRIDE={args.gamma_sigma_max_iter or ''}",
            f"GAMMA_SIGMA_MIN_UPDATE_ITERS_OVERRIDE={args.gamma_sigma_min_update_iters or ''}",
            f"STATE_GUARD_START_ITER_OVERRIDE={args.state_guard_start_iter or ''}",
            "CONTINUE_ON_FAIL=1",
            "SKIP_COMPARES=1",
            "",
        ]),
        encoding="utf-8",
    )
    lines = [
        "# HE2 exDQLM Multivar Keep Grid Smoke Scope",
        "",
        f"- status: `prepared_not_launched`",
        f"- tag: `{tag}`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- source_matrix_dir: `{source_matrix_dir}`",
        f"- cutoffs: `{', '.join(cutoffs)}`",
        f"- grid_spec_ids: `{', '.join(grid_spec_ids)}`",
        f"- run rows: `{len(plan_df)}`",
        f"- quantile fits: `{len(plan_df) * 7}`",
        f"- concurrent rows: `{queue['ordinary_max_concurrent']}`",
        f"- pause memory GB: `{queue['pause_mem_gb']}`",
        f"- launch memory GB: `{queue['launch_mem_gb']}`",
        f"- heavy memory GB: `{queue['heavy_mem_gb']}`",
        f"- artifact disk free GB: `{artifact_disk_free_gb(artifact_root)}`",
        f"- gamma/sigma max_iter override: `{args.gamma_sigma_max_iter}`",
        f"- gamma/sigma min_update_iters override: `{args.gamma_sigma_min_update_iters}`",
        f"- state guard start iter override: `{args.state_guard_start_iter}`",
        "",
        "## No-Cleanup Smoke Launch",
        "",
        "Use this first if retained `.RData` inspection is needed after post.",
        "",
        "```bash",
        " ".join(no_cleanup_cmd),
        "```",
        "",
        "## Cleanup-Enabled Smoke Launch",
        "",
        "Use this only when this matrix/root is intended to be the cleanup-enabled smoke from scratch.",
        "After a no-cleanup smoke passes, build/use a separate cleanup smoke root so completed no-cleanup rows are not reused.",
        "",
        "```bash",
        " ".join(cleanup_cmd),
        "```",
    ]
    (matrix_dir / "SMOKE_SCOPE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"artifact_root={artifact_root}")
    print(f"matrix_dir={matrix_dir}")
    print(f"config_output_dir={config_output_dir}")
    print(f"run_rows={len(plan_df)}")
    print(f"quantile_fits={len(plan_df) * 7}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

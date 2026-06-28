#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from build_he2_bayesian_publication_relaunch_configs import (  # noqa: E402
    _build_cutoff_bundle_audit_rows,
    _build_run_config,
    _dependency_rows,
    _extract_spec_row,
)
from he2_publication_relaunch_lib import (  # noqa: E402
    DEFAULT_BUNDLE_RUN_ID,
    DEFAULT_DATA_START,
    DEFAULT_QUANTILES,
    EXPECTED_CUTOFFS,
    canonical_shared_paths,
    ensure_dir,
    initialize_matrix_status,
    load_publication_manifest_rows,
    load_yaml,
    render_quantile_label,
    write_yaml,
)
from multimodel_v8_lib import control_dir, reports_dir, resolve_artifact_root, runs_dir  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/he2_bayesian_publication_relaunch_exdqlm_univar_discount_screen_20260628.template.yaml"
STATE_FIELDS = ["df_t", "df_s1", "df_s2", "df_s67", "lambda", "df_trans", "df_covs"]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"template root is not a mapping: {path}")
    return data


def selected_manifest_rows(manifest_path: Path, cutoffs: list[str]) -> list[dict[str, str]]:
    rows = [
        row for row in load_publication_manifest_rows(manifest_path)
        if row.get("family") == "exdqlm_univar"
        and row.get("manuscript_label") == "exAL-U-T1"
        and row.get("cutoff") in set(cutoffs)
    ]
    rows.sort(key=lambda row: EXPECTED_CUTOFFS.index(row["cutoff"]))
    observed = {row["cutoff"] for row in rows}
    missing = [cutoff for cutoff in cutoffs if cutoff not in observed]
    if missing:
        raise RuntimeError(f"missing exdqlm_univar publication rows for cutoffs: {missing}")
    return rows


def run_id_for(cutoff: str, spec_short: str, campaign_spec_id: str) -> str:
    return f"multimodel_{cutoff}_v8_{campaign_spec_id}_{spec_short}_exdqlm_univar"


def spec_patch(spec: dict[str, Any], template: dict[str, Any], seed: int) -> dict[str, Any]:
    gamma_sigma = ((template.get("fit") or {}).get("gamma_sigma") or {})
    return {
        "run": {
            "seed": int(seed),
            "threads": {
                "omp": 1,
                "openblas": 1,
                "mkl": 1,
                "veclib": 1,
                "numexpr": 1,
            },
        },
        "models": {
            "run_ndlm_univar": False,
            "run_ndlm_main": False,
            "run_exdqlm_multivar": False,
            "run_exdqlm_univar": True,
            "exdqlm_univar": {
                "implementation_mode": "legacy_bridge",
                "likelihood_mode": "exal",
                "state_evolution": {field: float(spec[field]) for field in STATE_FIELDS},
            },
        },
        "fit": {
            "exdqlm_univar": {
                "gamma_sigma": {
                    "warmup_freeze_iters": int(gamma_sigma.get("warmup_freeze_iters", 5)),
                    "min_update_iters": int(gamma_sigma.get("min_update_iters", 50)),
                    "min_total_iters": int(gamma_sigma.get("min_total_iters", 50)),
                    "max_iter": int(gamma_sigma.get("max_iter", 100)),
                }
            }
        },
    }


def write_launch_script(matrix_dir: Path, artifact_root: Path, queue: dict[str, Any]) -> Path:
    script = matrix_dir / "launch_univar_discount_screen.sh"
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        f"cd {ROOT}",
        "python3 scripts/run_multimodel_v8_queue.py \\",
        f"  --matrix-dir {matrix_dir} \\",
        f"  --artifact-root {artifact_root} \\",
        f"  --ordinary-max-concurrent {int(queue.get('ordinary_max_concurrent', 4))} \\",
        f"  --pause-free-gb {float(queue.get('pause_free_gb', 25))} \\",
        f"  --launch-free-gb {float(queue.get('launch_free_gb', 35))} \\",
        f"  --heavy-free-gb {float(queue.get('heavy_free_gb', 35))} \\",
        f"  --heavy-cutoff-max-concurrent {int(queue.get('heavy_cutoff_max_concurrent', 4))} \\",
        f"  --poll-seconds {int(queue.get('poll_seconds', 60))} \\",
        "  --continue-on-fail \\",
        "  --skip-compares \\",
        "  --no-heavy-cutoff-blocks-ordinary",
    ]
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    script.chmod(0o755)
    return script


def build(config_path: Path) -> dict[str, Any]:
    template = read_config(config_path)
    campaign = template.get("campaign") or {}
    source = template.get("source") or {}
    bundles = template.get("bundles") or {}
    resources = template.get("resources") or {}
    queue = template.get("queue") or {}
    cleanup = template.get("cleanup") or {}
    specs = template.get("screen_specs") or []
    if not specs:
        raise RuntimeError("template has no screen_specs")

    cutoffs = [str(x) for x in campaign.get("cutoffs", EXPECTED_CUTOFFS)]
    campaign_spec_id = str(campaign.get("campaign_spec_id", "he2univscr20260628"))
    artifact_root = Path(resolve_artifact_root(campaign.get("artifact_root"))).resolve()
    matrix_dir = ensure_dir(Path(campaign.get("matrix_dir", artifact_root / "control/univar_discount_screen")).resolve())
    config_output_dir = ensure_dir(Path(campaign.get("config_output_dir", artifact_root / "control/generated_configs")).resolve())
    ensure_dir(runs_dir(artifact_root))
    ensure_dir(reports_dir(artifact_root))
    ensure_dir(control_dir(artifact_root))

    manifest_path = Path(str(source.get("publication_manifest", "reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv")))
    if not manifest_path.is_absolute():
        manifest_path = (ROOT / manifest_path).resolve()
    bundle_artifact_root = Path(str(bundles.get("artifact_root"))).resolve()
    bundle_run_id = str(bundles.get("bundle_run_id") or DEFAULT_BUNDLE_RUN_ID)

    rows = selected_manifest_rows(manifest_path, cutoffs)
    row_by_cutoff = {row["cutoff"]: row for row in rows}
    active_quantiles = [float(q) for q in DEFAULT_QUANTILES]

    plan_rows: list[dict[str, Any]] = []
    registry_rows: list[dict[str, Any]] = []
    frozen_rows: list[dict[str, Any]] = []
    dependency_rows: list[dict[str, Any]] = []
    generated_configs: list[Path] = []
    order_index = 0
    frozen_root = ensure_dir(matrix_dir / "source_config_freeze")

    for spec_index, spec in enumerate(specs, start=1):
        spec_short = str(spec.get("short_label") or f"u{spec_index:02d}")
        spec_id = str(spec["spec_id"])
        for cutoff in cutoffs:
            source_row = row_by_cutoff[cutoff]
            source_cfg_path = Path(source_row["resolved_config_path"])
            if not source_cfg_path.exists():
                raise FileNotFoundError(source_cfg_path)
            shared = canonical_shared_paths(bundle_artifact_root, cutoff, bundle_run_id)
            missing = [str(path) for path in shared.values() if isinstance(path, Path) and not path.exists()]
            if missing:
                raise FileNotFoundError(f"incomplete shared bundle for cutoff={cutoff}: {missing[:5]}")

            run_id = run_id_for(cutoff, spec_short, campaign_spec_id)
            config_path_out = config_output_dir / f"{run_id}.yaml"
            source_cfg = load_yaml(source_cfg_path)
            patch = spec_patch(spec, template, seed=int(cutoff))
            cfg = _build_run_config(
                source_cfg,
                run_id=run_id,
                artifact_root=artifact_root,
                cutoff=cutoff,
                bundle_artifact_root=bundle_artifact_root,
                bundle_run_id=bundle_run_id,
                source_row=source_row,
                resources={
                    "fit_parallel_workers": int(resources.get("fit_parallel_workers", 7)),
                    "mc_cores": int(resources.get("mc_cores", 7)),
                },
                selected_quantiles=active_quantiles,
                profile_name="univar_discount_screen",
                row_config_patch=patch,
                row_config_patch_source=str(config_path),
            )
            debug = cfg.setdefault("debug_he2_publication_relaunch", {})
            debug["campaign_spec_id"] = campaign_spec_id
            debug["univar_discount_screen"] = {
                "spec_id": spec_id,
                "short_label": spec_short,
                "state_evolution": {field: float(spec[field]) for field in STATE_FIELDS},
                "cleanup_rdata_after_post": bool(cleanup.get("cleanup_rdata_after_post", True)),
            }
            write_yaml(config_path_out, cfg)
            generated_configs.append(config_path_out)

            compare_dir = reports_dir(artifact_root) / f"{run_id}_compare"
            plan_row = {
                "order_index": order_index,
                "cutoff": cutoff,
                "epsilon": spec_short,
                "grid_spec_id": spec_id,
                "spec_short_label": spec_short,
                "lane": "exdqlm_univar",
                "family": "exdqlm_univar",
                "family_id": "exdqlm_univar",
                "manuscript_label": "exAL-U-T1",
                "run_id": run_id,
                "config_path": str(config_path_out),
                "compare_outdir": str(compare_dir),
                "quantile_submodels": len(active_quantiles),
                "active_quantiles": "|".join(render_quantile_label(q) for q in active_quantiles),
                "cleanup_rdata_after_post": bool(cleanup.get("cleanup_rdata_after_post", True)),
                **{field: float(spec[field]) for field in STATE_FIELDS},
            }
            plan_rows.append(plan_row)
            registry_rows.append(dict(plan_row))
            spec_row = _extract_spec_row(plan_row, source_row, cfg)
            spec_row.update({
                "grid_spec_id": spec_id,
                "spec_short_label": spec_short,
                "screen_df_t": float(spec["df_t"]),
                "screen_df_s1": float(spec["df_s1"]),
                "screen_df_s2": float(spec["df_s2"]),
                "screen_df_s67": float(spec["df_s67"]),
                "screen_lambda": float(spec["lambda"]),
                "screen_df_trans": float(spec["df_trans"]),
                "screen_df_covs": float(spec["df_covs"]),
            })
            frozen_rows.append(spec_row)
            dependency_rows.extend(_dependency_rows(config_path_out, cfg))
            order_index += 1

        frozen_cfg = frozen_root / f"{spec_short}_{spec_id}.yaml"
        frozen_cfg.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")

    write_csv(matrix_dir / "matrix_plan.csv", plan_rows)
    write_csv(matrix_dir / "grid_run_registry.csv", registry_rows)
    write_csv(matrix_dir / "grid_spec_manifest_resolved.csv", [
        {
            "spec_order": idx,
            "grid_spec_id": str(spec["spec_id"]),
            "spec_short_label": str(spec.get("short_label") or f"u{idx:02d}"),
            **{field: float(spec[field]) for field in STATE_FIELDS},
            "max_iter": int(((template.get("fit") or {}).get("gamma_sigma") or {}).get("max_iter", 100)),
        }
        for idx, spec in enumerate(specs, start=1)
    ])
    write_csv(matrix_dir / "frozen_spec_manifest.csv", frozen_rows)
    write_csv(matrix_dir / "dependency_manifest.csv", dependency_rows)
    write_csv(matrix_dir / "source_input_manifest.csv", _build_cutoff_bundle_audit_rows(plan_rows, bundle_artifact_root, bundle_run_id))
    initialize_matrix_status(matrix_dir / "matrix_status.csv")

    metadata = {
        "campaign_id": str(campaign.get("campaign_id", "he2_exdqlm_univar_discount_screen_20260628")),
        "campaign_spec_id": campaign_spec_id,
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "publication_manifest": str(manifest_path),
        "bundle_artifact_root": str(bundle_artifact_root),
        "bundle_run_id": bundle_run_id,
        "data_start": str(bundles.get("data_start", DEFAULT_DATA_START)),
        "family": "exdqlm_univar",
        "manuscript_label": "exAL-U-T1",
        "spec_count": len(specs),
        "run_rows": len(plan_rows),
        "quantile_fits": len(plan_rows) * len(active_quantiles),
        "queue": queue,
        "resources": resources,
        "cleanup_rdata_after_post": bool(cleanup.get("cleanup_rdata_after_post", True)),
        "cleanup_rdata_before_launch": bool(cleanup.get("cleanup_rdata_before_launch", True)),
        "skip_compare_bundles": True,
        "allow_run_failures": True,
    }
    (matrix_dir / "matrix_metadata.yaml").write_text(yaml.safe_dump(metadata, sort_keys=False), encoding="utf-8")
    (matrix_dir / "matrix_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    launch_env = "\n".join([
        f"ARTIFACT_ROOT={artifact_root}",
        f"MATRIX_DIR={matrix_dir}",
        f"CONFIG_OUTPUT_DIR={config_output_dir}",
        f"ORDINARY_MAX_CONCURRENT={int(queue.get('ordinary_max_concurrent', 4))}",
        f"PAUSE_FREE_GB={float(queue.get('pause_free_gb', 25))}",
        f"LAUNCH_FREE_GB={float(queue.get('launch_free_gb', 35))}",
        f"HEAVY_FREE_GB={float(queue.get('heavy_free_gb', 35))}",
        f"HEAVY_CUTOFF_MAX_CONCURRENT={int(queue.get('heavy_cutoff_max_concurrent', 4))}",
        f"POLL_SECONDS={int(queue.get('poll_seconds', 60))}",
        "CONTINUE_ON_FAIL=1",
        "SKIP_COMPARES=1",
        "CLEANUP_RDATA_AFTER_POST=1",
        "",
    ])
    (matrix_dir / "launch_settings.env").write_text(launch_env, encoding="utf-8")
    launch_script = write_launch_script(matrix_dir, artifact_root, queue)

    lines = [
        "# HE2 exDQLM Univariate Discount Screen",
        "",
        "- status: `prepared_not_launched`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- generated_configs: `{len(generated_configs)}`",
        f"- run rows: `{len(plan_rows)}`",
        f"- quantile fits: `{len(plan_rows) * len(active_quantiles)}`",
        f"- row concurrency: `{int(queue.get('ordinary_max_concurrent', 4))}`",
        f"- max quantile workers: `{int(queue.get('ordinary_max_concurrent', 4)) * int(resources.get('fit_parallel_workers', 7))}`",
        f"- cleanup after post: `{bool(cleanup.get('cleanup_rdata_after_post', True))}`",
        "",
        "## Launch",
        "",
        "```bash",
        str(launch_script),
        "```",
    ]
    (matrix_dir / "PRELAUNCH_RUNBOOK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "generated_configs": len(generated_configs),
        "plan_rows": len(plan_rows),
        "spec_rows": len(specs),
        "quantile_fits": len(plan_rows) * len(active_quantiles),
        "launch_script": str(launch_script),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build HE2 exDQLM univariate discount-screen configs.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build(args.config.resolve())
    for key, value in summary.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import pandas as pd

from build_multimodel_v8_all9_feature_matrix_configs import (
    _dependency_rows,
    _flatten_rows,
    _resolve_repo_path,
    _sorted_enabled,
)
from build_multimodel_v8_quantile_ndlm_discount_probe_matrix_configs import (
    _build_run_config,
    _cutoff_index,
    _load_selection_manifest,
)
from multimodel_v8_lib import (
    CUTOFFS,
    HEAVY_CUTOFF,
    artifact_disk_free_gb,
    ensure_dir,
    load_yaml,
    reports_dir,
    resolve_artifact_root,
    runs_dir,
    write_yaml,
)

FAMILY_ID = "exdqlm_multivar_keep"
MODEL_ORDER = [FAMILY_ID]
STATE_KEYS = [
    "df_t",
    "df_s1",
    "df_s2",
    "df_s67",
    "df_discrep",
    "lambda",
    "df_trans",
    "df_covs",
]


def _as_float(value: Any, *, profile_name: str, key: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"discount profile {profile_name!r} has non-numeric {key}: {value!r}") from exc


def _discount_profiles(campaign: dict[str, Any]) -> list[dict[str, Any]]:
    raw_profiles = campaign.get("discount_profiles", [])
    if not isinstance(raw_profiles, list) or not raw_profiles:
        raise ValueError("discount_profiles must be a non-empty list")

    profiles: list[dict[str, Any]] = []
    seen: set[str] = set()
    for idx, raw in enumerate(raw_profiles, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"discount profile #{idx} is not a mapping")
        name = str(raw.get("name") or f"set{idx:02d}").strip()
        if not name:
            raise ValueError(f"discount profile #{idx} has an empty name")
        if name in seen:
            raise ValueError(f"duplicate discount profile name: {name}")
        seen.add(name)
        state = raw.get("state_evolution", {})
        if not isinstance(state, dict):
            raise ValueError(f"discount profile {name!r} state_evolution must be a mapping")
        missing = [key for key in STATE_KEYS if key not in state]
        if missing:
            raise ValueError(f"discount profile {name!r} is missing state keys: {', '.join(missing)}")
        normalized = {key: _as_float(state[key], profile_name=name, key=key) for key in STATE_KEYS}
        profiles.append(
            {
                "name": name,
                "description": str(raw.get("description", "") or ""),
                "state_evolution": normalized,
                "index": idx,
            }
        )
    return profiles


def _profile_model_overrides(profile: dict[str, Any]) -> dict[str, Any]:
    return {"exdqlm_multivar": {"state_evolution": dict(profile["state_evolution"])}}


def _source_parallel_contract(template_cfg: dict[str, Any], family_cfg: dict[str, Any], fit_parallel_cfg: dict[str, Any]) -> tuple[str, int]:
    source_fit = template_cfg.get("fit", {}) if isinstance(template_cfg.get("fit"), dict) else {}
    source_parallel = source_fit.get("parallel", {}) if isinstance(source_fit.get("parallel"), dict) else {}
    mode = str(
        source_parallel.get("mode")
        or family_cfg.get("fit_parallel_mode")
        or fit_parallel_cfg.get("mode")
        or "global_models"
    )
    workers = int(
        source_parallel.get("workers")
        or family_cfg.get("fit_parallel_workers")
        or fit_parallel_cfg.get("default_workers")
        or 1
    )
    return mode, workers


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Build the exAL-M-T1 discount-factor grid configs from the corrected HE2 best-epsilon sources."
    )
    ap.add_argument("--config", required=True)
    ap.add_argument("--artifact-root")
    ap.add_argument("--matrix-dir")
    ap.add_argument("--config-output-dir")
    ap.add_argument("--cutoffs", nargs="*")
    ap.add_argument("--discount-profiles", nargs="*")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    campaign_path = _resolve_repo_path(args.config)
    if campaign_path is None:
        raise SystemExit("Missing --config")
    campaign = load_yaml(campaign_path)

    campaign_cfg = campaign.get("campaign", {}) if isinstance(campaign.get("campaign"), dict) else {}
    queue_cfg = campaign.get("queue", {}) if isinstance(campaign.get("queue"), dict) else {}
    fit_parallel_cfg = campaign.get("fit_parallel", {}) if isinstance(campaign.get("fit_parallel"), dict) else {}
    cutoffs_cfg = campaign.get("cutoffs", {}) if isinstance(campaign.get("cutoffs"), dict) else {}
    families_cfg = campaign.get("families", {}) if isinstance(campaign.get("families"), dict) else {}
    compare_cfg = campaign.get("compare", {}) if isinstance(campaign.get("compare"), dict) else {}
    inputs_cfg = campaign.get("inputs", {}) if isinstance(campaign.get("inputs"), dict) else {}
    selection_cfg = campaign.get("selection", {}) if isinstance(campaign.get("selection"), dict) else {}

    artifact_root = resolve_artifact_root(args.artifact_root or campaign_cfg.get("artifact_root"))
    matrix_dir = ensure_dir(
        _resolve_repo_path(args.matrix_dir or campaign_cfg.get("matrix_dir"))
        or (artifact_root / "control" / "exalm_t1_discount_grid")
    )
    config_output_dir = ensure_dir(
        _resolve_repo_path(args.config_output_dir or campaign_cfg.get("config_output_dir"))
        or (artifact_root / "control" / "generated_configs")
    )
    ensure_dir(runs_dir(artifact_root))
    ensure_dir(reports_dir(artifact_root))

    campaign_spec_id = str(
        campaign_cfg.get("spec_id", campaign_cfg.get("campaign_id", "exalm_t1_discount_grid_v1"))
    ).strip() or "exalm_t1_discount_grid_v1"
    supported_cutoffs = {cutoff for cutoff, _ in CUTOFFS}
    selected_cutoffs = set(str(c) for c in args.cutoffs) if args.cutoffs else None
    selected_profiles = set(str(p) for p in args.discount_profiles) if args.discount_profiles else None

    enabled_cutoffs = []
    for cutoff, cutoff_cfg in _sorted_enabled(cutoffs_cfg, preferred_order=[c for c, _cfg in CUTOFFS]):
        cutoff = str(cutoff).zfill(8)
        if cutoff not in supported_cutoffs:
            raise SystemExit(f"Unsupported cutoff in campaign config: {cutoff}")
        if selected_cutoffs and cutoff not in selected_cutoffs:
            continue
        enabled_cutoffs.append((cutoff, cutoff_cfg))

    enabled_families = _sorted_enabled(families_cfg, preferred_order=MODEL_ORDER)
    enabled_family_ids = [family_id for family_id, _cfg in enabled_families]
    if enabled_family_ids != [FAMILY_ID]:
        raise SystemExit(
            "This grid is intentionally narrow; enable only "
            f"{FAMILY_ID!r}. Observed enabled families: {enabled_family_ids}"
        )

    profiles = _discount_profiles(campaign)
    if selected_profiles:
        profiles = [profile for profile in profiles if str(profile["name"]) in selected_profiles]
    if not enabled_cutoffs:
        raise SystemExit("No enabled cutoffs selected for exAL-M-T1 discount-grid build.")
    if not profiles:
        raise SystemExit("No discount profiles selected for exAL-M-T1 discount-grid build.")

    parity_matrix_path = _resolve_repo_path(selection_cfg.get("parity_matrix_path"))
    if parity_matrix_path is None or not parity_matrix_path.exists():
        raise SystemExit(f"Missing selection.parity_matrix_path: {parity_matrix_path}")

    selections = _load_selection_manifest(
        parity_matrix_path,
        enabled_cutoffs=enabled_cutoffs,
        enabled_families=enabled_families,
        selection_cfg=selection_cfg,
    )

    family_id, family_cfg = enabled_families[0]
    cutoff_rank = _cutoff_index()
    selection_rows: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []
    dependency_rows: list[dict[str, Any]] = []
    generated_configs: list[Path] = []
    order_index = 0

    for profile in profiles:
        profile_name = str(profile["name"])
        model_overrides = _profile_model_overrides(profile)
        for cutoff, cutoff_cfg in enabled_cutoffs:
            authoritative_compare_dir = _resolve_repo_path(cutoff_cfg.get("authoritative_compare_dir"))
            if authoritative_compare_dir is None:
                raise SystemExit(f"Missing authoritative_compare_dir for cutoff {cutoff}")

            selection = selections[(cutoff, family_id)]
            source_epsilon_label = str(selection["selected_epsilon_label"])
            matrix_epsilon = f"{profile_name}_{source_epsilon_label}"
            template_cfg = load_yaml(Path(selection["source_config"]))
            run_suffix = str(family_cfg.get("run_suffix", family_id)).strip() or family_id
            run_id = f"multimodel_{cutoff}_v8_{campaign_spec_id}_{profile_name}_{run_suffix}"
            config_path = config_output_dir / f"{run_id}.yaml"
            fit_parallel_mode, fit_parallel_workers = _source_parallel_contract(
                template_cfg,
                family_cfg,
                fit_parallel_cfg,
            )

            cfg = _build_run_config(
                template_cfg=template_cfg,
                run_id=run_id,
                artifact_root=artifact_root,
                family_id=family_id,
                family_cfg=family_cfg,
                campaign_spec_id=campaign_spec_id,
                fit_parallel_mode=fit_parallel_mode,
                fit_parallel_workers=fit_parallel_workers,
                inputs_overrides=inputs_cfg,
                model_overrides=model_overrides,
                selection=selection,
            )
            source_shared_root = str(Path(selection["source_config"]).parent / "inputs" / "shared")
            cfg.setdefault("inputs", {}).setdefault("shared", {})["exact_source_snapshot_root"] = source_shared_root
            cfg["debug_exalm_t1_discount_grid"] = {
                "campaign_spec_id": campaign_spec_id,
                "discount_set": profile_name,
                "discount_set_index": int(profile["index"]),
                "source_epsilon_label": source_epsilon_label,
                "matrix_epsilon": matrix_epsilon,
                "state_evolution": dict(profile["state_evolution"]),
                "exact_source_snapshot_root": source_shared_root,
                "source_fit_parallel_mode": fit_parallel_mode,
                "source_fit_parallel_workers": fit_parallel_workers,
            }
            cfg.setdefault("debug_quantile_ndlm_discount_probe", {})["discount_set"] = profile_name
            cfg["debug_quantile_ndlm_discount_probe"]["source_epsilon_label"] = source_epsilon_label
            cfg["debug_quantile_ndlm_discount_probe"]["matrix_epsilon"] = matrix_epsilon
            cfg["debug_quantile_ndlm_discount_probe"]["exact_source_snapshot_root"] = source_shared_root
            write_yaml(config_path, cfg)
            generated_configs.append(config_path)
            dependency_rows.extend(_dependency_rows(config_path, cfg))

            order_index += 1
            is_heavy = cutoff == HEAVY_CUTOFF
            state = profile["state_evolution"]
            plan_row = {
                "order_index": order_index,
                "cutoff": cutoff,
                "epsilon": matrix_epsilon,
                "epsilon_value": selection["selected_epsilon"],
                "source_epsilon": source_epsilon_label,
                "discount_set": profile_name,
                "discount_set_index": int(profile["index"]),
                "lane": family_id,
                "run_scope": "exalm_t1_discount_grid",
                "run_id": run_id,
                "config_path": str(config_path),
                "compare_outdir": str(reports_dir(artifact_root) / f"multimodel_{cutoff}_v8_{matrix_epsilon}_compare"),
                "priority_group": 2 if is_heavy else 1,
                "max_concurrent_class": "heavy" if is_heavy else "ordinary",
                "family_id": family_id,
                "model_id": str(family_cfg["model_id"]),
                "model_key": str(family_cfg["model_key"]),
                "likelihood_mode": str(family_cfg.get("likelihood_mode", "")),
                "transfer_mode": str(family_cfg.get("transfer_mode", "")),
                "authoritative_compare_dir": str(authoritative_compare_dir),
                "selected_compare_dir": selection["compare_dir"],
                "selected_source_run": selection["source_run"],
                "selected_source_type": selection["source_type"],
                "selected_source_config": selection["source_config"],
                "selected_mean_crps": selection["mean_crps"],
                "selected_source_lineage": selection["source_lineage"],
                "selected_discount_df_t": selection["state_df_t"],
                "selected_discount_df_s1": selection["state_df_s1"],
                "selected_discount_df_s2": selection["state_df_s2"],
                "selected_discount_df_s67": selection["state_df_s67"],
                "selected_discount_df_discrep": selection["state_df_discrep"],
                "selected_discount_lambda": selection["state_lambda"],
                "selected_discount_df_trans": selection["state_df_trans"],
                "selected_discount_df_covs": selection["state_df_covs"],
                "grid_df_t": state["df_t"],
                "grid_df_s1": state["df_s1"],
                "grid_df_s2": state["df_s2"],
                "grid_df_s67": state["df_s67"],
                "grid_df_discrep": state["df_discrep"],
                "grid_lambda": state["lambda"],
                "grid_df_trans": state["df_trans"],
                "grid_df_covs": state["df_covs"],
                "cutoff_rank": cutoff_rank[cutoff],
            }
            plan_rows.append(plan_row)
            selection_rows.append(dict(plan_row))

    plan_df = pd.DataFrame(plan_rows).sort_values(["order_index"]).drop(columns=["cutoff_rank"])
    plan_df.to_csv(matrix_dir / "matrix_plan.csv", index=False)

    dep_df = pd.DataFrame(dependency_rows).sort_values(["consumer_config", "dependency_type"]).reset_index(drop=True)
    dep_df.to_csv(matrix_dir / "dependency_preservation.csv", index=False)

    selection_df = pd.DataFrame(selection_rows).sort_values(["discount_set_index", "cutoff", "family_id"]).reset_index(drop=True)
    selection_df.drop(columns=["cutoff_rank"]).to_csv(matrix_dir / "selection_summary.csv", index=False)

    spec_rows: list[dict[str, Any]] = []
    _flatten_rows("selection", selection_cfg, spec_rows, {"campaign_spec_id": campaign_spec_id, "section": "selection"})
    _flatten_rows("inputs", inputs_cfg, spec_rows, {"campaign_spec_id": campaign_spec_id, "section": "inputs"})
    for profile in profiles:
        _flatten_rows(
            f"discount_profiles.{profile['name']}.state_evolution",
            profile["state_evolution"],
            spec_rows,
            {
                "campaign_spec_id": campaign_spec_id,
                "section": "discount_profiles",
                "discount_set": profile["name"],
            },
        )
    _flatten_rows(
        "families." + family_id,
        family_cfg,
        spec_rows,
        {"campaign_spec_id": campaign_spec_id, "section": "families"},
    )
    pd.DataFrame(spec_rows).sort_values(["section", "parameter"]).reset_index(drop=True).to_csv(
        matrix_dir / "spec_parameter_table.csv", index=False
    )

    status_path = matrix_dir / "matrix_status.csv"
    if not status_path.exists():
        with status_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "cutoff",
                    "epsilon",
                    "lane",
                    "run_id",
                    "phase",
                    "status",
                    "started_at",
                    "finished_at",
                    "manifest_path",
                    "latest_log_mtime",
                    "disk_free_gb",
                    "note",
                ]
            )

    metadata = {
        "campaign_id": str(campaign_cfg.get("campaign_id", "multimodel_v8_exalm_t1_discount_grid")),
        "campaign_spec_id": campaign_spec_id,
        "campaign_config": str(campaign_path),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "compare_builder": str(compare_cfg.get("builder", "scripts/build_multimodel_v8_all9_feature_compare_bundle.py")),
        "queue": {
            "ordinary_max_concurrent": int(queue_cfg.get("ordinary_max_concurrent", 4)),
            "pause_free_gb": float(queue_cfg.get("pause_free_gb", 180)),
            "launch_free_gb": float(queue_cfg.get("launch_free_gb", 220)),
            "heavy_free_gb": float(queue_cfg.get("heavy_free_gb", 240)),
            "heavy_cutoff_max_concurrent": int(queue_cfg.get("heavy_cutoff_max_concurrent", 4)),
            "heavy_cutoff_blocks_ordinary": bool(queue_cfg.get("heavy_cutoff_blocks_ordinary", False)),
            "poll_seconds": int(queue_cfg.get("poll_seconds", 15)),
        },
    }
    write_yaml(matrix_dir / "matrix_metadata.yaml", metadata)
    write_yaml(
        matrix_dir / "campaign_snapshot.yaml",
        {
            "config_path": str(campaign_path),
            "artifact_root": str(artifact_root),
            "matrix_dir": str(matrix_dir),
            "config_output_dir": str(config_output_dir),
            "campaign": campaign,
        },
    )

    launch_env = "\n".join(
        [
            f"ARTIFACT_ROOT={artifact_root}",
            f"MATRIX_DIR={matrix_dir}",
            f"ORDINARY_MAX_CONCURRENT={metadata['queue']['ordinary_max_concurrent']}",
            f"PAUSE_FREE_GB={metadata['queue']['pause_free_gb']}",
            f"LAUNCH_FREE_GB={metadata['queue']['launch_free_gb']}",
            f"HEAVY_FREE_GB={metadata['queue']['heavy_free_gb']}",
            f"HEAVY_CUTOFF_MAX_CONCURRENT={metadata['queue']['heavy_cutoff_max_concurrent']}",
            f"HEAVY_CUTOFF_BLOCKS_ORDINARY={'1' if metadata['queue']['heavy_cutoff_blocks_ordinary'] else '0'}",
            f"POLL_SECONDS={metadata['queue']['poll_seconds']}",
            "",
        ]
    )
    (matrix_dir / "launch_settings.env").write_text(launch_env, encoding="utf-8")
    (matrix_dir / "queue.log").touch()

    scope_lines = [
        f"# {metadata['campaign_id']}",
        "",
        f"- campaign_config: `{campaign_path}`",
        f"- campaign_spec_id: `{campaign_spec_id}`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- config_output_dir: `{config_output_dir}`",
        f"- parity_matrix_path: `{parity_matrix_path}`",
        f"- generated_configs: `{len(generated_configs)}`",
        f"- enabled_cutoffs: `{', '.join(c for c, _cfg in enabled_cutoffs)}`",
        f"- enabled_family: `{FAMILY_ID}`",
        f"- discount_sets: `{', '.join(str(p['name']) for p in profiles)}`",
        "",
        "## Source Contract",
        "- every row is `exAL-M-T1`: `exdqlm_multivar_keep`, `likelihood_mode=exal`, `forecast_transfer_mode=keep`.",
        "- cutoff-specific best epsilon is inherited from the corrected HE2 parity matrix and the actual executed `featurecov_cf1_eps_sweep` source run.",
        "- generated configs preserve the exact selected-source `inputs/shared` snapshot before fit, so raw forecasts, PPT/SOIL/GDPC-compatibility covariates, deterministic-climate futures, and `covariate_features.csv` remain identical to the HE-table source run.",
        "- the only intended scientific difference across rows is the `models.exdqlm_multivar.state_evolution` discount-factor block.",
        "",
        "## Parallelism Contract",
        "- fit parallelism is inherited from the selected source config for each cutoff.",
        f"- ordinary_max_concurrent: `{metadata['queue']['ordinary_max_concurrent']}`",
        f"- heavy_cutoff_max_concurrent: `{metadata['queue']['heavy_cutoff_max_concurrent']}`",
        f"- heavy_cutoff_blocks_ordinary: `{metadata['queue']['heavy_cutoff_blocks_ordinary']}`",
        "- peak fit-core usage therefore follows the inherited source-worker mix rather than forcing a new global worker count.",
        "",
        "## Numerical Watch",
        "- run-level pass is not treated as proof of score stability; CRPS/input-health bundles must be inspected after post for huge finite values or infinite draw standard deviations.",
        "",
        "## Current disk headroom",
        f"- artifact disk free GB: `{artifact_disk_free_gb(artifact_root)}`",
    ]
    (matrix_dir / "exalm_t1_discount_grid_scope.md").write_text("\n".join(scope_lines) + "\n", encoding="utf-8")

    print(f"artifact_root={artifact_root}")
    print(f"matrix_dir={matrix_dir}")
    print(f"config_output_dir={config_output_dir}")
    print(f"generated_configs={len(generated_configs)}")
    print(f"plan_rows={len(plan_df)}")
    print(f"selection_rows={len(selection_df)}")
    print(f"spec_rows={len(spec_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

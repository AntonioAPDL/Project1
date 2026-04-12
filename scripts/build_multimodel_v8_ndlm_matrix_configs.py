#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import pandas as pd

from multimodel_v8_lib import (
    CUTOFFS,
    HEAVY_CUTOFF,
    ROOT,
    artifact_disk_free_gb,
    deep_copy_dict,
    ensure_dir,
    load_yaml,
    reports_dir,
    resolve_artifact_root,
    runs_dir,
    write_yaml,
)

NDLM_MODEL_ORDER = [
    "ndlm_main_keep",
    "ndlm_main_drop",
    "ndlm_univar_keep",
]
NDLM_MODEL_ID_BY_FAMILY = {
    "ndlm_main_keep": "ndlm_main_synth_keep",
    "ndlm_main_drop": "ndlm_main_synth_drop",
    "ndlm_univar_keep": "ndlm_univar_synth_keep",
}


def _set_nested(cfg: dict[str, Any], path: list[str], value: Any) -> None:
    cur = cfg
    for key in path[:-1]:
        nxt = cur.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[key] = nxt
        cur = nxt
    cur[path[-1]] = value


def _deep_update(dst: dict[str, Any], src: dict[str, Any]) -> dict[str, Any]:
    for key, value in src.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            _deep_update(dst[key], value)
        else:
            dst[key] = value
    return dst


def _resolve_repo_path(raw: str | Path | None) -> Path | None:
    if raw is None:
        return None
    path = Path(str(raw)).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _cutoff_index() -> dict[str, int]:
    return {cutoff: idx for idx, (cutoff, _date) in enumerate(CUTOFFS, start=1)}


def _sorted_enabled(mapping: dict[str, Any], preferred_order: list[str] | None = None) -> list[tuple[str, dict[str, Any]]]:
    preferred_order = preferred_order or []
    preferred_rank = {key: idx for idx, key in enumerate(preferred_order, start=1)}
    rows: list[tuple[str, dict[str, Any]]] = []
    for key, value in mapping.items():
        if not isinstance(value, dict):
            continue
        if value.get("enabled", True) is False:
            continue
        rows.append((str(key), value))
    rows.sort(key=lambda item: (preferred_rank.get(item[0], 10_000), item[0]))
    return rows


def _flatten_spec_rows(spec_id: str, spec_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def walk(prefix: str, value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                next_prefix = f"{prefix}.{key}" if prefix else str(key)
                walk(next_prefix, child)
            return
        if isinstance(value, list):
            rendered = ",".join(str(x) for x in value)
        else:
            rendered = value
        rows.append({"spec_id": spec_id, "parameter": prefix, "value": rendered})

    walk("", spec_cfg)
    return rows


def _dependency_rows(config_path: Path, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    dep_specs = [
        ("forecats_existing_bundle", cfg.get("inputs", {}).get("forecats", {}).get("existing_bundle_path", "")),
        ("fit_parameters", cfg.get("inputs", {}).get("fit", {}).get("parameters_path", "")),
        ("fit_retros", cfg.get("inputs", {}).get("fit", {}).get("retros_path", "")),
        ("fit_nws_forecast", cfg.get("inputs", {}).get("fit", {}).get("nws_forecast_path", "")),
        ("fit_glofas_forecast", cfg.get("inputs", {}).get("fit", {}).get("glofas_forecast_path", "")),
    ]
    for cov in cfg.get("inputs", {}).get("fit", {}).get("covariates", []) or []:
        if isinstance(cov, dict):
            dep_specs.append((f"covariate:{cov.get('name', '')}", cov.get("path", "")))
    for dep_type, dep_path in dep_specs:
        rows.append(
            {
                "consumer_config": str(config_path),
                "dependency_type": dep_type,
                "dependency_path": str(dep_path or ""),
            }
        )
    return rows


def _template_run_root(template_config: str, authoritative_compare_dir: str) -> Path:
    template_run_id = Path(template_config).stem
    compare_dir = Path(authoritative_compare_dir)
    artifact_root = compare_dir.parent.parent
    run_root = artifact_root / "runs" / template_run_id
    if not run_root.exists():
        raise FileNotFoundError(
            f"Could not resolve template run root for {template_run_id} from authoritative_compare_dir={authoritative_compare_dir}"
        )
    return run_root


def _rewrite_inputs_from_template_snapshot(
    cfg: dict[str, Any],
    *,
    template_config: str,
    authoritative_compare_dir: str,
) -> None:
    run_root = _template_run_root(template_config, authoritative_compare_dir)
    shared_root = run_root / "inputs" / "shared"

    snapshot_map = {
        ("inputs", "fit", "parameters_path"): shared_root / "parameters" / "parameters.txt",
        ("inputs", "fit", "retros_path"): shared_root / "retros" / "retros.csv",
        ("inputs", "fit", "nws_forecast_path"): shared_root / "forecasts" / "nws_forecast.csv",
        ("inputs", "fit", "glofas_forecast_path"): shared_root / "forecasts" / "glofas_forecast.csv",
        ("inputs", "forecats", "existing_bundle_path"): shared_root / "forecats_bundle" / "meta.yaml",
    }
    for path_keys, source_path in snapshot_map.items():
        if source_path.exists():
            _set_nested(cfg, list(path_keys), str(source_path))

    cov_dir = shared_root / "covariates"
    covariates = cfg.get("inputs", {}).get("fit", {}).get("covariates", []) or []
    if cov_dir.exists():
        for idx, cov in enumerate(covariates):
            if not isinstance(cov, dict):
                continue
            cov_name = str(cov.get("name", "")).strip()
            if not cov_name:
                continue
            matches = sorted(cov_dir.glob(f"cov_*_{cov_name}.csv"))
            if matches:
                cov["path"] = str(matches[0])
                covariates[idx] = cov


def _build_run_config(
    template_cfg: dict[str, Any],
    run_id: str,
    artifact_root: Path,
    family_id: str,
    family_cfg: dict[str, Any],
    spec_id: str,
    spec_cfg: dict[str, Any],
    fit_parallel_mode: str,
    fit_parallel_workers: int,
    authoritative_compare_dir: str,
    template_config: str,
) -> dict[str, Any]:
    cfg = deep_copy_dict(template_cfg)
    _set_nested(cfg, ["run", "run_id"], run_id)
    _set_nested(cfg, ["run", "run_root"], str(runs_dir(artifact_root)))
    _set_nested(cfg, ["run", "overwrite"], False)
    _set_nested(cfg, ["run", "dry_run"], False)
    _set_nested(cfg, ["run", "git_require_clean"], False)
    _set_nested(cfg, ["run", "auto_suffix_on_collision"], False)
    _set_nested(cfg, ["run", "threads", "mc_cores"], int(max(fit_parallel_workers, 1)))

    for stage in ["forecats", "data_prep_shared", "fit", "post", "validate", "report"]:
        _set_nested(cfg, ["stages", stage], True)
    _set_nested(cfg, ["post", "figures"], True)
    _set_nested(cfg, ["post", "smoke_fast"], True)
    _set_nested(cfg, ["post", "force_isolation_smoke_fast"], True)
    _set_nested(cfg, ["post", "export_tables"], True)

    _set_nested(cfg, ["fit", "parallel", "mode"], str(fit_parallel_mode))
    _set_nested(cfg, ["fit", "parallel", "workers"], int(max(fit_parallel_workers, 1)))

    _set_nested(cfg, ["models", "run_exdqlm_multivar"], False)
    _set_nested(cfg, ["models", "run_exdqlm_univar"], False)
    _set_nested(cfg, ["models", "run_ndlm_main"], False)
    _set_nested(cfg, ["models", "run_ndlm_univar"], False)

    model_key = str(family_cfg["model_key"])
    transfer_mode = str(family_cfg.get("transfer_mode", "")).strip()
    if model_key == "ndlm_main":
        _set_nested(cfg, ["models", "run_ndlm_main"], True)
        _set_nested(cfg, ["models", "ndlm_main", "forecast_transfer_mode"], transfer_mode)
        _deep_update(cfg.setdefault("models", {}).setdefault("ndlm_main", {}), deep_copy_dict(spec_cfg.get("ndlm_main", {})))
    elif model_key == "ndlm_univar":
        _set_nested(cfg, ["models", "run_ndlm_univar"], True)
        _set_nested(cfg, ["models", "ndlm_univar", "forecast_transfer_mode"], transfer_mode)
        _deep_update(cfg.setdefault("models", {}).setdefault("ndlm_univar", {}), deep_copy_dict(spec_cfg.get("ndlm_univar", {})))
    else:
        raise ValueError(f"Unsupported NDLM model_key: {model_key}")

    fit_overrides = deep_copy_dict(spec_cfg.get("fit", {}))
    if fit_overrides:
        _deep_update(cfg.setdefault("fit", {}), fit_overrides)

    _rewrite_inputs_from_template_snapshot(
        cfg,
        template_config=template_config,
        authoritative_compare_dir=authoritative_compare_dir,
    )

    cfg["debug_ndlm_campaign"] = {
        "spec_id": spec_id,
        "family_id": family_id,
        "model_id": str(family_cfg["model_id"]),
        "model_key": model_key,
        "transfer_mode": transfer_mode,
        "template_config": template_config,
        "authoritative_compare_dir": authoritative_compare_dir,
        "fit_parallel_mode": fit_parallel_mode,
        "fit_parallel_workers": fit_parallel_workers,
    }
    return cfg


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build NDLM-only multimodel v8 matrix configs from a central campaign YAML.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--artifact-root")
    ap.add_argument("--matrix-dir")
    ap.add_argument("--config-output-dir")
    ap.add_argument("--cutoffs", nargs="*")
    ap.add_argument("--specs", nargs="*")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    campaign_path = _resolve_repo_path(args.config)
    assert campaign_path is not None
    campaign = load_yaml(campaign_path)

    campaign_cfg = campaign.get("campaign", {}) if isinstance(campaign.get("campaign"), dict) else {}
    queue_cfg = campaign.get("queue", {}) if isinstance(campaign.get("queue"), dict) else {}
    fit_parallel_cfg = campaign.get("fit_parallel", {}) if isinstance(campaign.get("fit_parallel"), dict) else {}
    cutoffs_cfg = campaign.get("cutoffs", {}) if isinstance(campaign.get("cutoffs"), dict) else {}
    families_cfg = campaign.get("families", {}) if isinstance(campaign.get("families"), dict) else {}
    specs_cfg = campaign.get("specs", {}) if isinstance(campaign.get("specs"), dict) else {}

    artifact_root = resolve_artifact_root(args.artifact_root or campaign_cfg.get("artifact_root"))
    matrix_dir = ensure_dir(_resolve_repo_path(args.matrix_dir or campaign_cfg.get("matrix_dir")) or (artifact_root / "control" / "ndlm_matrix"))
    config_output_dir = ensure_dir(_resolve_repo_path(args.config_output_dir or campaign_cfg.get("config_output_dir")) or (artifact_root / "control" / "generated_configs"))
    ensure_dir(runs_dir(artifact_root))
    ensure_dir(reports_dir(artifact_root))

    supported_cutoffs = {cutoff for cutoff, _ in CUTOFFS}
    selected_cutoffs = set(str(c) for c in args.cutoffs) if args.cutoffs else None
    selected_specs = set(str(s) for s in args.specs) if args.specs else None

    enabled_cutoffs = []
    for cutoff, cutoff_cfg in _sorted_enabled(cutoffs_cfg, preferred_order=[c for c, _ in CUTOFFS]):
        if cutoff not in supported_cutoffs:
            raise SystemExit(f"Unsupported cutoff in campaign config: {cutoff}")
        if selected_cutoffs and cutoff not in selected_cutoffs:
            continue
        enabled_cutoffs.append((cutoff, cutoff_cfg))

    enabled_specs = []
    for spec_id, spec_cfg in _sorted_enabled(specs_cfg):
        if selected_specs and spec_id not in selected_specs:
            continue
        enabled_specs.append((spec_id, spec_cfg))

    enabled_families = _sorted_enabled(families_cfg, preferred_order=NDLM_MODEL_ORDER)
    if not enabled_cutoffs:
        raise SystemExit("No enabled cutoffs selected for NDLM campaign build.")
    if not enabled_specs:
        raise SystemExit("No enabled specs selected for NDLM campaign build.")
    if not enabled_families:
        raise SystemExit("No enabled NDLM families selected for NDLM campaign build.")

    plan_rows: list[dict[str, Any]] = []
    dependency_rows: list[dict[str, Any]] = []
    generated_configs: list[Path] = []
    spec_rows: list[dict[str, Any]] = []
    cutoff_rank = _cutoff_index()

    for spec_id, spec_cfg in enabled_specs:
        spec_rows.extend(_flatten_spec_rows(spec_id, spec_cfg))

    order_index = 0
    for cutoff, cutoff_cfg in enabled_cutoffs:
        template_l1 = _resolve_repo_path(cutoff_cfg.get("template_l1_config"))
        template_l2 = _resolve_repo_path(cutoff_cfg.get("template_l2_config"))
        authoritative_compare_dir = _resolve_repo_path(cutoff_cfg.get("authoritative_compare_dir"))
        if template_l1 is None or not template_l1.exists():
            raise SystemExit(f"Missing template_l1_config for cutoff {cutoff}: {template_l1}")
        if template_l2 is None or not template_l2.exists():
            raise SystemExit(f"Missing template_l2_config for cutoff {cutoff}: {template_l2}")
        if authoritative_compare_dir is None:
            raise SystemExit(f"Missing authoritative_compare_dir for cutoff {cutoff}")

        for spec_id, spec_cfg in enabled_specs:
            for family_id, family_cfg in enabled_families:
                template_lane = str(family_cfg.get("template_lane", "")).strip()
                template_path = template_l1 if template_lane == "l1" else template_l2 if template_lane == "l2" else None
                if template_path is None:
                    raise SystemExit(f"Unsupported template_lane for family {family_id}: {template_lane}")
                template_cfg = load_yaml(template_path)
                run_suffix = str(family_cfg.get("run_suffix", family_id)).strip() or family_id
                run_id = f"multimodel_{cutoff}_v8_{spec_id}_{run_suffix}"
                config_path = config_output_dir / f"{run_id}.yaml"

                fit_parallel_mode = str(family_cfg.get("fit_parallel_mode") or fit_parallel_cfg.get("mode") or "global_models")
                fit_parallel_workers = int(family_cfg.get("fit_parallel_workers") or fit_parallel_cfg.get("default_workers") or 1)

                cfg = _build_run_config(
                    template_cfg=template_cfg,
                    run_id=run_id,
                    artifact_root=artifact_root,
                    family_id=family_id,
                    family_cfg=family_cfg,
                    spec_id=spec_id,
                    spec_cfg=spec_cfg,
                    fit_parallel_mode=fit_parallel_mode,
                    fit_parallel_workers=fit_parallel_workers,
                    authoritative_compare_dir=str(authoritative_compare_dir),
                    template_config=str(template_path),
                )
                write_yaml(config_path, cfg)
                generated_configs.append(config_path)
                dependency_rows.extend(_dependency_rows(config_path, cfg))

                order_index += 1
                is_heavy = cutoff == HEAVY_CUTOFF
                plan_rows.append(
                    {
                        "order_index": order_index,
                        "cutoff": cutoff,
                        "epsilon": spec_id,
                        "epsilon_value": spec_id,
                        "lane": family_id,
                        "run_scope": "ndlm_only",
                        "run_id": run_id,
                        "config_path": str(config_path),
                        "compare_outdir": str(reports_dir(artifact_root) / f"multimodel_{cutoff}_v8_{spec_id}_compare"),
                        "priority_group": 2 if is_heavy else 1,
                        "max_concurrent_class": "heavy" if is_heavy else "ordinary",
                        "spec_id": spec_id,
                        "family_id": family_id,
                        "model_id": str(family_cfg["model_id"]),
                        "model_key": str(family_cfg["model_key"]),
                        "transfer_mode": str(family_cfg.get("transfer_mode", "")),
                        "template_config": str(template_path),
                        "authoritative_compare_dir": str(authoritative_compare_dir),
                        "cutoff_rank": cutoff_rank[cutoff],
                    }
                )

    plan_df = pd.DataFrame(plan_rows).sort_values(["cutoff_rank", "spec_id", "order_index"]).drop(columns=["cutoff_rank"])
    plan_df.to_csv(matrix_dir / "matrix_plan.csv", index=False)

    dep_df = pd.DataFrame(dependency_rows).sort_values(["consumer_config", "dependency_type"]).reset_index(drop=True)
    dep_df.to_csv(matrix_dir / "dependency_preservation.csv", index=False)

    spec_df = pd.DataFrame(spec_rows).sort_values(["spec_id", "parameter"]).reset_index(drop=True)
    spec_df.to_csv(matrix_dir / "spec_parameter_table.csv", index=False)

    status_path = matrix_dir / "matrix_status.csv"
    if not status_path.exists():
        with status_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow([
                "cutoff", "epsilon", "lane", "run_id", "phase", "status", "started_at", "finished_at",
                "manifest_path", "latest_log_mtime", "disk_free_gb", "note",
            ])

    metadata = {
        "campaign_id": str(campaign_cfg.get("campaign_id", "multimodel_v8_ndlm_campaign")),
        "campaign_config": str(campaign_path),
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "compare_builder": str(campaign.get("compare", {}).get("builder", "scripts/build_multimodel_v8_ndlm_compare_bundle.py")),
        "queue": {
            "ordinary_max_concurrent": int(queue_cfg.get("ordinary_max_concurrent", 3)),
            "pause_free_gb": float(queue_cfg.get("pause_free_gb", 180)),
            "launch_free_gb": float(queue_cfg.get("launch_free_gb", 220)),
            "heavy_free_gb": float(queue_cfg.get("heavy_free_gb", 240)),
            "poll_seconds": int(queue_cfg.get("poll_seconds", 60)),
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

    launch_env = "\n".join([
        f"ARTIFACT_ROOT={artifact_root}",
        f"MATRIX_DIR={matrix_dir}",
        f"ORDINARY_MAX_CONCURRENT={metadata['queue']['ordinary_max_concurrent']}",
        f"PAUSE_FREE_GB={metadata['queue']['pause_free_gb']}",
        f"LAUNCH_FREE_GB={metadata['queue']['launch_free_gb']}",
        f"HEAVY_FREE_GB={metadata['queue']['heavy_free_gb']}",
        f"POLL_SECONDS={metadata['queue']['poll_seconds']}",
        "",
    ])
    (matrix_dir / "launch_settings.env").write_text(launch_env, encoding="utf-8")
    (matrix_dir / "queue.log").touch()

    scope_lines = [
        f"# {metadata['campaign_id']}",
        "",
        f"- campaign_config: `{campaign_path}`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- config_output_dir: `{config_output_dir}`",
        f"- generated_configs: `{len(generated_configs)}`",
        f"- enabled_cutoffs: `{', '.join(c for c, _cfg in enabled_cutoffs)}`",
        f"- enabled_specs: `{', '.join(spec for spec, _cfg in enabled_specs)}`",
        f"- enabled_families: `{', '.join(fam for fam, _cfg in enabled_families)}`",
        "",
        "## Current queue defaults",
        f"- ordinary_max_concurrent: `{metadata['queue']['ordinary_max_concurrent']}`",
        f"- pause_free_gb: `{metadata['queue']['pause_free_gb']}`",
        f"- launch_free_gb: `{metadata['queue']['launch_free_gb']}`",
        f"- heavy_free_gb: `{metadata['queue']['heavy_free_gb']}`",
        f"- poll_seconds: `{metadata['queue']['poll_seconds']}`",
        "",
        "## Current disk headroom",
        f"- artifact disk free GB: `{artifact_disk_free_gb(artifact_root)}`",
    ]
    (matrix_dir / "ndlm_scope.md").write_text("\n".join(scope_lines) + "\n", encoding="utf-8")

    print(f"artifact_root={artifact_root}")
    print(f"matrix_dir={matrix_dir}")
    print(f"config_output_dir={config_output_dir}")
    print(f"generated_configs={len(generated_configs)}")
    print(f"plan_rows={len(plan_df)}")
    print(f"spec_rows={len(spec_df)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

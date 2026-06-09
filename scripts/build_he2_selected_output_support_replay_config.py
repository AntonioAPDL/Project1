#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUTHORITY = ROOT / "docs" / "authoritative_selected_outputs" / "he2_exal_m_t1_representative_20221225.yaml"
DEFAULT_REPLAY_ROOT = ROOT.parent / "project1_ucsc_phd_runtime" / "multimodel_v8_he2_selected_output_support_20260609"
DEFAULT_CONFIG_DIR = ROOT / "config" / "unified_runs_selected_output_support_20260609"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def build_config(authority_path: Path, replay_root: Path, config_dir: Path, tag: str) -> dict[str, Path]:
    authority_payload = load_yaml(authority_path)
    authority = authority_payload.get("authority", {})
    if not isinstance(authority, dict):
        raise ValueError(f"authority must be a mapping: {authority_path}")

    source_config = (
        Path(str(authority["runtime_root"]))
        / "control"
        / "generated_configs"
        / f"{authority['run_id']}.yaml"
    )
    cfg = load_yaml(source_config)

    run_id = f"{authority['run_id']}_{tag}"
    runs_root = replay_root / "runs"
    resolved_run_root = runs_root / run_id
    config_path = config_dir / f"{run_id}.yaml"

    cfg["run"]["run_id"] = run_id
    cfg["run"]["run_root"] = str(runs_root)
    cfg["run"]["resolved_run_root"] = str(resolved_run_root)
    cfg["run"]["resolved_config_path"] = str(config_path)
    cfg["run"]["overwrite"] = False
    cfg["run"]["auto_suffix_on_collision"] = False
    cfg["run"].setdefault("threads", {})
    cfg["run"]["threads"]["mc_cores"] = 7

    cfg.setdefault("post", {})
    cfg["post"]["figures"] = True
    cfg["post"]["export_tables"] = True
    cfg["post"]["force_isolation_smoke_fast"] = True
    cfg["post"].setdefault("multivar_component_diagnostics", {})
    cfg["post"]["multivar_component_diagnostics"]["enabled"] = True
    cfg["post"]["multivar_component_diagnostics"]["quantile"] = 0.5
    cfg["post"]["multivar_component_diagnostics"]["pre_days"] = 30
    cfg["post"]["multivar_component_diagnostics"]["fail_fast"] = True
    cfg["post"]["authoritative_selected_model_support"] = {
        "enabled": True,
        "fail_fast": True,
    }

    cfg.setdefault("debug_selected_output_support_replay", {})
    cfg["debug_selected_output_support_replay"] = {
        "authority_manifest": str(authority_path),
        "source_run_id": authority["run_id"],
        "source_runtime_output_root": authority["runtime_output_root"],
        "purpose": "Regenerate compact q05/q50/q95 selected-output support before .RData cleanup.",
        "cleanup_expected_after_post": True,
    }

    write_yaml(config_path, cfg)
    replay_root.mkdir(parents=True, exist_ok=True)
    manifest_path = replay_root / "control" / "selected_output_support_replay_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "authority_manifest": str(authority_path),
        "source_config": str(source_config),
        "replay_config": str(config_path),
        "replay_root": str(replay_root),
        "run_id": run_id,
        "resolved_run_root": str(resolved_run_root),
        "runtime_output_root": str(resolved_run_root / "post" / "outputs" / run_id),
        "cleanup_wrapper": "scripts/run_unified_with_cleanup.sh",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"config": config_path, "manifest": manifest_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the isolated HE2 selected-output support replay config.")
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--replay-root", type=Path, default=DEFAULT_REPLAY_ROOT)
    parser.add_argument("--config-dir", type=Path, default=DEFAULT_CONFIG_DIR)
    parser.add_argument("--tag", default="authoritative_support_20260609")
    args = parser.parse_args()

    out = build_config(
        authority_path=args.authority.resolve(),
        replay_root=args.replay_root.resolve(),
        config_dir=args.config_dir.resolve(),
        tag=args.tag,
    )
    print(out["config"])
    print(out["manifest"])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def q_label(q: float) -> str:
    return f"{int(round(float(q) * 100)):02d}"


def prepare_config(
    source_config: Path,
    artifact_root: Path,
    *,
    quantile: float,
    run_id_suffix: str,
    fit_only: bool,
) -> dict[str, Any]:
    cfg = load_yaml(source_config)
    artifact_root = artifact_root.resolve()
    source_config = source_config.resolve()
    run = cfg.setdefault("run", {})
    source_run_id = str(run.get("run_id", source_config.stem))
    run_id = f"{source_run_id}_{run_id_suffix}"
    config_path = artifact_root / "control" / "single_quantile_fit_configs" / f"{run_id}.yaml"
    run_root = artifact_root / "runs"

    run["run_id"] = run_id
    run["run_root"] = str(run_root)
    run["resolved_run_root"] = str(run_root / run_id)
    run["resolved_config_path"] = str(config_path)
    run["overwrite"] = False
    run["auto_suffix_on_collision"] = False
    run["dry_run"] = False
    run.setdefault("threads", {})
    run["threads"]["mc_cores"] = 1

    cfg.setdefault("fit", {})
    cfg["fit"]["quantiles"] = [float(quantile)]
    cfg["fit"].setdefault("parallel", {})
    cfg["fit"]["parallel"]["mode"] = "global_models"
    cfg["fit"]["parallel"]["workers"] = 1

    cfg.setdefault("stages", {})
    cfg["stages"]["forecats"] = False
    cfg["stages"]["data_prep_shared"] = True
    cfg["stages"]["fit"] = True
    if fit_only:
        cfg["stages"]["post"] = False
        cfg["stages"]["validate"] = False
        cfg["stages"]["report"] = False

    cfg["debug_he2_single_quantile_fit_diagnostic"] = {
        "generated_at_utc": utc_now(),
        "source_config": str(source_config),
        "source_run_id": source_run_id,
        "artifact_root": str(artifact_root),
        "run_id": run_id,
        "config_path": str(config_path),
        "quantile": float(quantile),
        "q_label": q_label(quantile),
        "fit_only": bool(fit_only),
        "purpose": "isolated one-quantile diagnostic using an already generated publication/smoke config as source of truth",
    }
    write_yaml(config_path, cfg)
    launch_cmd = [
        "Rscript",
        "--vanilla",
        "scripts/unified_run.R",
        "--config",
        str(config_path),
    ]
    launch_path = config_path.with_suffix(".launch.sh")
    launch_path.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\ncd " + str(Path(__file__).resolve().parents[1]) + "\n"
        + " ".join(launch_cmd) + "\n",
        encoding="utf-8",
    )
    return {
        "source_config": str(source_config),
        "artifact_root": str(artifact_root),
        "run_id": run_id,
        "run_root": str(run_root / run_id),
        "config_path": str(config_path),
        "launch_script": str(launch_path),
        "quantile": float(quantile),
        "q_label": q_label(quantile),
        "fit_only": bool(fit_only),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a one-quantile HE2 fit-only diagnostic config.")
    parser.add_argument("--source-config", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--quantile", type=float, required=True)
    parser.add_argument("--run-id-suffix", required=True)
    parser.add_argument("--full-pipeline", action="store_true", help="Keep source post/validate/report stages enabled.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = prepare_config(
        args.source_config.resolve(),
        args.artifact_root.resolve(),
        quantile=args.quantile,
        run_id_suffix=args.run_id_suffix,
        fit_only=not args.full_pipeline,
    )
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

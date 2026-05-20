#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False, indent=2),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Prepare an isolated reduced default-VB temporal-start bundle."
    )
    ap.add_argument("--source-config", type=Path, required=True)
    ap.add_argument("--target-runtime-root", type=Path, required=True)
    ap.add_argument("--spec-label", required=True)
    ap.add_argument("--data-start", required=True)
    ap.add_argument("--report-dir", type=Path, required=True)
    return ap.parse_args()


def build_run_id(spec_label: str) -> str:
    return f"multimodel_20221225_v8_he2pubgdpc1r1_{spec_label}_exdqlm_multivar_keep"


def main() -> int:
    args = parse_args()
    cfg = load_yaml(args.source_config)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    run_id = build_run_id(args.spec_label)
    prefit_id = f"{run_id}_prefitcheck"

    cfg["run"]["run_id"] = run_id
    cfg["run"]["run_root"] = str(args.target_runtime_root / "runs")
    cfg["run"]["overwrite"] = False
    cfg["run"]["auto_suffix_on_collision"] = True
    cfg["run"]["dry_run"] = False
    cfg["dates"]["data_start"] = str(args.data_start)
    cfg.setdefault("fit", {}).setdefault("warm_start", {})
    cfg["fit"]["warm_start"]["enabled"] = False
    cfg["fit"]["warm_start"]["source_run_id"] = None
    cfg["fit"]["warm_start"]["source_run_root"] = None

    debug = cfg.setdefault("debug_discount_refresh", {})
    debug["prepared_at"] = ts
    debug["note"] = (
        f"Temporary reducedspec relaunch using data_start={args.data_start} "
        "with default VB and isolated runtime root"
    )
    debug["warm_start_seed_root"] = None

    launch_cfg = json.loads(json.dumps(cfg))
    prefit_cfg = json.loads(json.dumps(cfg))
    prefit_cfg["run"]["run_id"] = prefit_id
    prefit_cfg["stages"]["fit"] = False
    prefit_cfg["stages"]["post"] = False
    prefit_cfg["stages"]["validate"] = False
    prefit_cfg["stages"]["report"] = False

    control = args.target_runtime_root / "control"
    generated = control / "generated_configs"
    generated.mkdir(parents=True, exist_ok=True)
    (args.target_runtime_root / "runs").mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)

    launch_cfg_path = generated / f"{run_id}.yaml"
    prefit_cfg_path = generated / f"{prefit_id}.yaml"
    write_yaml(launch_cfg_path, launch_cfg)
    write_yaml(prefit_cfg_path, prefit_cfg)

    launch_script = control / f"launch_{run_id}_without_cleanup.sh"
    launch_script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'REPO_ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd"',
                f'CONFIG="{launch_cfg_path}"',
                'cd "$REPO_ROOT"',
                'exec "$REPO_ROOT/scripts/run_unified_without_cleanup.sh" --config "$CONFIG"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    launch_script.chmod(0o755)

    prefit_script = control / f"launch_{prefit_id}.sh"
    prefit_script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'REPO_ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd"',
                f'CONFIG="{prefit_cfg_path}"',
                'cd "$REPO_ROOT"',
                'exec Rscript --vanilla scripts/unified_run.R --config "$CONFIG"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    prefit_script.chmod(0o755)

    summary = {
        "prepared_at": ts,
        "source_config": str(args.source_config),
        "target_runtime_root": str(args.target_runtime_root),
        "spec_label": args.spec_label,
        "data_start": args.data_start,
        "launch_config": str(launch_cfg_path),
        "prefit_config": str(prefit_cfg_path),
        "launch_script": str(launch_script),
        "prefit_script": str(prefit_script),
    }
    (args.report_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

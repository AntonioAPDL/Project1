#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from he2_publication_relaunch_lib import EXPECTED_CUTOFFS, initialize_matrix_status  # noqa: E402
from he2_exdqlm_multivar_drop_q50_policy import (  # noqa: E402
    Q50_REPAIR_STABILIZATION,
    Q50_REPAIR_TERMINAL_SAMPLING_GUARD,
    build_q50_repair_patch,
)


TARGET_FAMILY = "exdqlm_multivar_drop"
TARGET_LABEL = "exAL-M-T0"
TARGET_MODEL_ID = "exdqlm_multivar_synth_drop"
TARGET_MODEL_KEY = "exdqlm_multivar"
RUN_ROWS_AT_ONCE = 2
QUANTILE_WORKERS_PER_RUN = 7
MAX_ACTIVE_QUANTILE_WORKERS = RUN_ROWS_AT_ONCE * QUANTILE_WORKERS_PER_RUN
DEFAULT_ARTIFACT_ROOT = (
    ROOT.parent
    / "project1_ucsc_phd_runtime"
    / "multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602"
)
TEMPLATE = ROOT / "config" / "he2_bayesian_publication_relaunch_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.template.yaml"
SOURCE_BATCH = ROOT / "config" / "he2_relaunch_batches" / "exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.yaml"


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


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def find_family_patch(batch: dict[str, Any]) -> dict[str, Any]:
    overrides = batch.setdefault("overrides", {})
    patches = overrides.setdefault("row_config_patches", [])
    for item in patches:
        if not isinstance(item, dict):
            continue
        if item.get("family") == TARGET_FAMILY and not item.get("cutoff"):
            return item
    item = {"family": TARGET_FAMILY, "manuscript_label": TARGET_LABEL, "config_patch": {}}
    patches.insert(0, item)
    return item


def current_batch_payload(source_batch: Path) -> dict[str, Any]:
    batch = load_yaml(source_batch)
    batch["selection"] = {
        "cutoffs": EXPECTED_CUTOFFS,
        "families": [TARGET_FAMILY],
        "model_classes": ["quantile_multivariate"],
    }
    batch["resources"] = {
        "fit_parallel_workers": QUANTILE_WORKERS_PER_RUN,
        "mc_cores": QUANTILE_WORKERS_PER_RUN,
    }
    batch["queue"] = {
        "ordinary_max_concurrent": RUN_ROWS_AT_ONCE,
        "heavy_cutoff_max_concurrent": RUN_ROWS_AT_ONCE,
        "heavy_cutoff_blocks_ordinary": False,
        "pause_free_gb": 25,
        "launch_free_gb": 35,
        "heavy_free_gb": 35,
        "poll_seconds": 30,
    }

    family_patch = find_family_patch(batch)
    family_patch["family"] = TARGET_FAMILY
    family_patch["manuscript_label"] = TARGET_LABEL
    family_patch["config_patch"] = deep_merge(
        family_patch.get("config_patch", {}) if isinstance(family_patch.get("config_patch"), dict) else {},
        {
            "models": {
                TARGET_MODEL_KEY: {
                    "likelihood_mode": "exal",
                    "forecast_transfer_mode": "drop",
                    "structure": {
                        "include_trend": True,
                        "enabled_harmonic_indices": [1, 2, 3],
                    },
                }
            },
            "fit": {
                TARGET_MODEL_KEY: {
                    "gamma_sigma": {
                        "max_iter": 100,
                    }
                }
            },
            "scale_contract": {
                "transform_policy": "log1p_only",
            },
        },
    )
    family_patch["config_patch"] = deep_merge(family_patch["config_patch"], build_q50_repair_patch(TARGET_MODEL_KEY))
    return batch


def git_head() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True)
    except Exception:
        return "unknown"
    return out.strip()


def build_package(
    artifact_root: Path,
    *,
    template: Path = TEMPLATE,
    source_batch: Path = SOURCE_BATCH,
    reset_status: bool = True,
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    matrix_dir = artifact_root / "control" / "publication_relaunch_matrix"
    config_output_dir = artifact_root / "control" / "generated_configs"
    generated_batch_dir = artifact_root / "control" / "generated_batches"
    generated_batch = generated_batch_dir / "exdqlm_multivar_drop_current_relaunch_q50repair_20260602.yaml"
    write_yaml(generated_batch, current_batch_payload(source_batch))

    if reset_status:
        status_path = matrix_dir / "matrix_status.csv"
        if status_path.exists():
            status_path.unlink()

    cmd = [
        "python3",
        "scripts/build_he2_bayesian_publication_relaunch_configs.py",
        "--config",
        str(template),
        "--artifact-root",
        str(artifact_root),
        "--matrix-dir",
        str(matrix_dir),
        "--config-output-dir",
        str(config_output_dir),
        "--batch-file",
        str(generated_batch),
        "--cutoffs",
        *EXPECTED_CUTOFFS,
        "--families",
        TARGET_FAMILY,
        "--model-classes",
        "quantile_multivariate",
        "--fit-parallel-workers",
        str(QUANTILE_WORKERS_PER_RUN),
        "--mc-cores",
        str(QUANTILE_WORKERS_PER_RUN),
    ]
    completed = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise RuntimeError(f"relaunch config builder failed with returncode={completed.returncode}")

    if reset_status:
        initialize_matrix_status(matrix_dir / "matrix_status.csv")

    metadata_path = matrix_dir / "matrix_metadata.yaml"
    metadata = load_yaml(metadata_path)
    metadata.update(
        {
            "generated_at_utc": utc_now(),
            "status": "prepared_not_launched",
            "target_family": TARGET_FAMILY,
            "target_label": TARGET_LABEL,
            "target_model_id": TARGET_MODEL_ID,
            "target_model_key": TARGET_MODEL_KEY,
            "source_template": str(template),
            "source_batch": str(source_batch),
            "generated_batch": str(generated_batch),
            "run_rows_at_once": RUN_ROWS_AT_ONCE,
            "quantile_workers_per_run": QUANTILE_WORKERS_PER_RUN,
            "max_active_quantile_workers": MAX_ACTIVE_QUANTILE_WORKERS,
            "cleanup_rdata_after_post": True,
            "skip_compare_bundles": True,
            "continue_on_fail": True,
            "q50_repair_promoted": True,
            "q50_repair_terminal_sampling_guard": Q50_REPAIR_TERMINAL_SAMPLING_GUARD,
            "q50_repair_stabilization": Q50_REPAIR_STABILIZATION,
            "q50_repair_source_doc": "docs/he2_exdqlm_multivar_drop_20211112_q50_repair_20260602.md",
            "code_commit": git_head(),
            "current_relaunch_note": (
                "Fresh current-code exAL-M-T0 package with the promoted 20211112 q50 terminal-guard/stabilization "
                "repair. Do not promote older completed roots as final because the pre-repair q50 row could pass "
                "finite checks while producing pathological synthesis magnitudes."
            ),
        }
    )
    write_yaml(metadata_path, metadata)

    launch_cmd = [
        "python3",
        "scripts/run_multimodel_v8_queue.py",
        "--matrix-dir",
        str(matrix_dir),
        "--artifact-root",
        str(artifact_root),
        "--ordinary-max-concurrent",
        str(RUN_ROWS_AT_ONCE),
        "--pause-free-gb",
        "25.0",
        "--launch-free-gb",
        "35.0",
        "--heavy-free-gb",
        "35.0",
        "--pause-mem-gb",
        "0.0",
        "--launch-mem-gb",
        "0.0",
        "--heavy-mem-gb",
        "0.0",
        "--heavy-cutoff-max-concurrent",
        str(RUN_ROWS_AT_ONCE),
        "--poll-seconds",
        "30",
        "--continue-on-fail",
        "--skip-compares",
        "--no-heavy-cutoff-blocks-ordinary",
    ]
    (matrix_dir / "launch_current_drop.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\ncd " + str(ROOT) + "\n" + " ".join(launch_cmd) + "\n",
        encoding="utf-8",
    )

    scope = [
        "# HE2 exAL-M-T0 Current-Code Relaunch Scope",
        "",
        "- status: `prepared_not_launched`",
        f"- family: `{TARGET_LABEL}` / `{TARGET_FAMILY}`",
        f"- artifact_root: `{artifact_root}`",
        f"- matrix_dir: `{matrix_dir}`",
        f"- generated configs: `{config_output_dir}`",
        f"- generated batch: `{generated_batch}`",
        f"- run rows: `{len(EXPECTED_CUTOFFS)}`",
        f"- quantile fits: `{len(EXPECTED_CUTOFFS) * QUANTILE_WORKERS_PER_RUN}`",
        f"- run rows at once: `{RUN_ROWS_AT_ONCE}`",
        f"- quantile workers per run: `{QUANTILE_WORKERS_PER_RUN}`",
        f"- max active quantile workers: `{MAX_ACTIVE_QUANTILE_WORKERS}`",
        "- likelihood/transfer: `exal` / `drop`",
        "- explicit harmonics: `1,2,3` with trend included",
        "- canonical bundle: `20260510_publication_shared_r01`",
        "- promoted q50 repair: terminal guard `fail_fast`, freeze target `states`, hold-after-guard `10`, "
        "state/cov blend `1.0`, gamma step cap `0.075`, log-sigma step cap `0.15`",
        "- cleanup after post: `true` via the queue wrapper",
        "",
        "## Launch Command",
        "",
        "```bash",
        " ".join(launch_cmd),
        "```",
    ]
    (matrix_dir / "EXDQLM_MULTIVAR_DROP_CURRENT_SCOPE.md").write_text("\n".join(scope) + "\n", encoding="utf-8")

    return {
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "config_output_dir": str(config_output_dir),
        "generated_batch": str(generated_batch),
        "run_rows": len(EXPECTED_CUTOFFS),
        "quantile_fits": len(EXPECTED_CUTOFFS) * QUANTILE_WORKERS_PER_RUN,
        "run_rows_at_once": RUN_ROWS_AT_ONCE,
        "max_active_quantile_workers": MAX_ACTIVE_QUANTILE_WORKERS,
        "launch_command": launch_cmd,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare current-code exAL-M-T0 relaunch configs.")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--source-batch", type=Path, default=SOURCE_BATCH)
    parser.add_argument("--no-reset-status", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_package(
        args.artifact_root,
        template=args.template,
        source_batch=args.source_batch,
        reset_status=not args.no_reset_status,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

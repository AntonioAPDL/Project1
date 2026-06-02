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

from build_he2_exdqlm_multivar_drop_current_relaunch import (  # noqa: E402
    QUANTILE_WORKERS_PER_RUN,
    SOURCE_BATCH,
    TARGET_FAMILY,
    TARGET_LABEL,
    TARGET_MODEL_ID,
    TARGET_MODEL_KEY,
    TEMPLATE,
    current_batch_payload,
    deep_merge,
    git_head,
)
from he2_publication_relaunch_lib import initialize_matrix_status  # noqa: E402
from he2_exdqlm_multivar_drop_q50_policy import build_q50_repair_patch  # noqa: E402


TARGET_CUTOFF = "20211112"
REPAIR_TAG = "q50repair_20260602"
DIAGNOSTIC_TAG = "q50repair_diag_20260602"
DEFAULT_ARTIFACT_ROOT = (
    ROOT.parent
    / "project1_ucsc_phd_runtime"
    / "multimodel_v8_he2_exdqlm_multivar_drop_20211112_q50repair_20260602"
)

Q50_REPAIR_PATCH: dict[str, Any] = build_q50_repair_patch(TARGET_MODEL_KEY)


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


def find_family_patch(batch: dict[str, Any]) -> dict[str, Any]:
    patches = batch.setdefault("overrides", {}).setdefault("row_config_patches", [])
    for item in patches:
        if isinstance(item, dict) and item.get("family") == TARGET_FAMILY and not item.get("cutoff"):
            return item
    item = {"family": TARGET_FAMILY, "manuscript_label": TARGET_LABEL, "config_patch": {}}
    patches.insert(0, item)
    return item


def repair_batch_payload(source_batch: Path = SOURCE_BATCH) -> dict[str, Any]:
    batch = current_batch_payload(source_batch)
    batch["selection"]["cutoffs"] = [TARGET_CUTOFF]
    batch["selection"]["families"] = [TARGET_FAMILY]
    batch["resources"] = {
        "fit_parallel_workers": QUANTILE_WORKERS_PER_RUN,
        "mc_cores": QUANTILE_WORKERS_PER_RUN,
    }
    batch["queue"] = {
        "ordinary_max_concurrent": 1,
        "heavy_cutoff_max_concurrent": 1,
        "heavy_cutoff_blocks_ordinary": False,
        "pause_free_gb": 25,
        "launch_free_gb": 35,
        "heavy_free_gb": 35,
        "poll_seconds": 30,
    }
    family_patch = find_family_patch(batch)
    base_patch = family_patch.get("config_patch", {})
    family_patch["config_patch"] = deep_merge(base_patch if isinstance(base_patch, dict) else {}, Q50_REPAIR_PATCH)
    return batch


def _base_generated_config_path(config_output_dir: Path) -> Path:
    return config_output_dir / f"multimodel_{TARGET_CUTOFF}_v8_he2pubgdpc1r1_exdqlm_multivar_drop.yaml"


def _with_run_identity(cfg: dict[str, Any], *, artifact_root: Path, run_tag: str) -> dict[str, Any]:
    out = deepcopy(cfg)
    base_run_id = f"multimodel_{TARGET_CUTOFF}_v8_he2pubgdpc1r1_exdqlm_multivar_drop"
    out.setdefault("run", {})["run_id"] = f"{base_run_id}_{run_tag}"
    out["run"]["run_root"] = str(artifact_root / "runs")
    out["run"]["overwrite"] = False
    out["run"]["auto_suffix_on_collision"] = False
    out["run"].setdefault("threads", {})["omp"] = 1
    out["run"]["threads"]["openblas"] = 1
    out["run"]["threads"]["mkl"] = 1
    out["run"]["threads"]["veclib"] = 1
    out["run"]["threads"]["numexpr"] = 1
    out.setdefault("relaunch_metadata", {})["q50_repair_tag"] = run_tag
    out["relaunch_metadata"]["q50_repair_generated_at_utc"] = utc_now()
    out["relaunch_metadata"]["q50_repair_code_commit"] = git_head()
    out["relaunch_metadata"]["q50_repair_scope"] = (
        "isolated 20211112 exdqlm_multivar_drop rerun with q50 terminal-guard/stabilization repair"
    )
    return out


def _diagnostic_config(base_cfg: dict[str, Any], *, artifact_root: Path) -> dict[str, Any]:
    cfg = _with_run_identity(base_cfg, artifact_root=artifact_root, run_tag=DIAGNOSTIC_TAG)
    cfg.setdefault("stages", {})
    cfg["stages"].update({"forecats": False, "data_prep_shared": True, "fit": True, "post": False, "validate": False, "report": False})
    cfg.setdefault("fit", {})["quantiles"] = [0.5]
    cfg["fit"]["active_quantiles"] = [0.5]
    cfg["fit"].setdefault("parallel", {})["workers"] = 1
    cfg["run"].setdefault("threads", {})["mc_cores"] = 1
    return cfg


def _final_config(base_cfg: dict[str, Any], *, artifact_root: Path) -> dict[str, Any]:
    cfg = _with_run_identity(base_cfg, artifact_root=artifact_root, run_tag=REPAIR_TAG)
    cfg.setdefault("stages", {})
    cfg["stages"].update({"forecats": False, "data_prep_shared": True, "fit": True, "post": True, "validate": True, "report": True})
    cfg.setdefault("fit", {}).setdefault("parallel", {})["workers"] = QUANTILE_WORKERS_PER_RUN
    cfg["run"].setdefault("threads", {})["mc_cores"] = QUANTILE_WORKERS_PER_RUN
    return cfg


def _write_launch_scripts(matrix_dir: Path, diagnostic_config: Path, final_config: Path) -> None:
    diag_log = matrix_dir / "q50_diagnostic.log"
    final_log = matrix_dir / "final_row.log"
    diag_script = matrix_dir / "launch_q50_diagnostic.sh"
    final_script = matrix_dir / "launch_final_row.sh"
    diag_script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"cd {ROOT}",
                f"scripts/run_unified_without_cleanup.sh --config {diagnostic_config} 2>&1 | tee {diag_log}",
                "diag_run=$(python3 - <<'PY'",
                "import yaml",
                f"cfg = yaml.safe_load(open('{diagnostic_config}', encoding='utf-8'))",
                "print(str(cfg['run']['run_root']).rstrip('/') + '/' + cfg['run']['run_id'])",
                "PY",
                ")",
                "find \"${diag_run}\" \\( -name '*.RData' -o -name '*.rda' \\) -delete 2>/dev/null || true",
                "find \"${diag_run}\" \\( -name '*.RData' -o -name '*.rda' \\) 2>/dev/null | wc -l > " + str(matrix_dir / "q50_diagnostic_rdata_remaining.txt"),
                "",
            ]
        ),
        encoding="utf-8",
    )
    final_script.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"cd {ROOT}",
                f"scripts/run_unified_with_cleanup.sh --config {final_config} 2>&1 | tee {final_log}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    diag_script.chmod(0o755)
    final_script.chmod(0o755)


def build_package(
    artifact_root: Path,
    *,
    template: Path = TEMPLATE,
    source_batch: Path = SOURCE_BATCH,
    reset_status: bool = True,
) -> dict[str, Any]:
    artifact_root = artifact_root.resolve()
    matrix_dir = artifact_root / "control" / "q50_repair"
    config_output_dir = artifact_root / "control" / "generated_configs"
    generated_batch = artifact_root / "control" / "generated_batches" / "exdqlm_multivar_drop_20211112_q50repair_20260602.yaml"
    write_yaml(generated_batch, repair_batch_payload(source_batch))

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
        TARGET_CUTOFF,
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
        raise RuntimeError(f"repair config builder failed with returncode={completed.returncode}")

    if reset_status:
        initialize_matrix_status(matrix_dir / "matrix_status.csv")

    base_config = _base_generated_config_path(config_output_dir)
    base_cfg = load_yaml(base_config)
    diagnostic_config = config_output_dir / f"multimodel_{TARGET_CUTOFF}_v8_he2pubgdpc1r1_exdqlm_multivar_drop_{DIAGNOSTIC_TAG}.yaml"
    final_config = config_output_dir / f"multimodel_{TARGET_CUTOFF}_v8_he2pubgdpc1r1_exdqlm_multivar_drop_{REPAIR_TAG}.yaml"
    write_yaml(diagnostic_config, _diagnostic_config(base_cfg, artifact_root=artifact_root))
    write_yaml(final_config, _final_config(base_cfg, artifact_root=artifact_root))
    _write_launch_scripts(matrix_dir, diagnostic_config, final_config)

    metadata_path = matrix_dir / "q50_repair_metadata.yaml"
    metadata = {
        "generated_at_utc": utc_now(),
        "status": "prepared_not_launched",
        "artifact_root": str(artifact_root),
        "target_cutoff": TARGET_CUTOFF,
        "target_family": TARGET_FAMILY,
        "target_label": TARGET_LABEL,
        "target_model_id": TARGET_MODEL_ID,
        "target_model_key": TARGET_MODEL_KEY,
        "source_template": str(template),
        "source_batch": str(source_batch),
        "generated_batch": str(generated_batch),
        "base_generated_config": str(base_config),
        "diagnostic_config": str(diagnostic_config),
        "final_config": str(final_config),
        "repair_patch": Q50_REPAIR_PATCH,
        "diagnostic_cleanup_rdata": True,
        "final_cleanup_rdata_after_post": True,
        "code_commit": git_head(),
    }
    write_yaml(metadata_path, metadata)

    scope = [
        "# HE2 exDQLM Multivar Drop 20211112 q50 Repair Scope",
        "",
        f"- status: `prepared_not_launched`",
        f"- artifact root: `{artifact_root}`",
        f"- failed baseline evidence: `reports/he2_exdqlm_multivar_drop_20211112_q50_failure_audit_20260602`",
        f"- diagnostic config: `{diagnostic_config}`",
        f"- final row config: `{final_config}`",
        f"- q50 stabilization patch: hold-after-guard `10`, state/cov blend `1.0`, gamma step cap `0.075`, log-sigma step cap `0.15`",
        "- scientific contract unchanged: same cutoff, same input bundle, same drop transfer mode, same exAL likelihood, same discount factors, same epsilon/c_factor, same max_iter=100",
        "- diagnostic cleanup: explicit `.RData/.rda` deletion after q50-only fit",
        "- final cleanup: `CLEANUP_RDATA_AFTER_POST=1` via `scripts/run_unified_with_cleanup.sh`",
        "",
        "## Commands",
        "",
        "```bash",
        f"{matrix_dir / 'launch_q50_diagnostic.sh'}",
        f"{matrix_dir / 'launch_final_row.sh'}",
        "```",
        "",
    ]
    (matrix_dir / "Q50_REPAIR_SCOPE.md").write_text("\n".join(scope), encoding="utf-8")

    return {
        "artifact_root": str(artifact_root),
        "matrix_dir": str(matrix_dir),
        "generated_batch": str(generated_batch),
        "base_generated_config": str(base_config),
        "diagnostic_config": str(diagnostic_config),
        "final_config": str(final_config),
        "diagnostic_launch_script": str(matrix_dir / "launch_q50_diagnostic.sh"),
        "final_launch_script": str(matrix_dir / "launch_final_row.sh"),
        "metadata": str(metadata_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare isolated 20211112 q50 repair configs for exdqlm_multivar_drop.")
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

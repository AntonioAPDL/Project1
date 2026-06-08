#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from he2_exdqlm_keep_authoritative import (  # noqa: E402
    EXPECTED_QUANTILE_LABELS,
    REQUIRED_OUTPUT_FILES,
    load_authoritative_spec,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, default_flow_style=False)


def default_matrix_dir(spec_runtime_root: Path) -> Path:
    return spec_runtime_root / "control" / "authoritative_winner_matrix"


def build_matrix(manifest_path: Path, matrix_dir: Path | None = None, *, freeze_configs: bool = True) -> dict[str, Any]:
    spec = load_authoritative_spec(manifest_path)
    matrix_dir = matrix_dir or default_matrix_dir(spec.runtime_root)
    matrix_dir.mkdir(parents=True, exist_ok=True)
    config_freeze_dir = matrix_dir / "source_config_freeze"
    if freeze_configs:
        config_freeze_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    config_rows: list[dict[str, Any]] = []
    output_rows: list[dict[str, Any]] = []
    for idx, winner in enumerate(spec.winners, 1):
        cfg_path = spec.generated_config_path(winner)
        frozen_config = ""
        config_sha = ""
        if freeze_configs:
            dst = config_freeze_dir / f"{winner.cutoff}_{winner.grid_spec_id}_{winner.run_id}.yaml"
            shutil.copy2(cfg_path, dst)
            frozen_config = str(dst)
            config_sha = sha256(dst)
        run_root = spec.run_root(winner)
        output_root = spec.output_root(winner)
        crps_path = spec.crps_summary_path(winner)
        row = {
            "order_index": idx,
            "cutoff": winner.cutoff,
            "cutoff_display": winner.as_row()["cutoff_display"],
            "manuscript_label": spec.manuscript_label,
            "family": spec.model_family,
            "model_id": spec.model_id,
            "grid_spec_id": winner.grid_spec_id,
            "discount_case_id": winner.discount_case_id,
            "epsilon_value": winner.epsilon_value,
            "c_factor": winner.c_factor,
            "df_t": winner.df_t,
            "df_s1": winner.df_s1,
            "df_s2": winner.df_s2,
            "df_s67": winner.df_s67,
            "df_discrep": winner.df_discrep,
            "lambda": winner.lambda_value,
            "df_trans": winner.df_trans,
            "df_covs": winner.df_covs,
            "max_iter": spec.metadata.get("max_iter", 100),
            "active_quantiles": spec.metadata.get("active_quantiles", EXPECTED_QUANTILE_LABELS),
            "input_bundle_contract": spec.metadata.get("input_bundle_contract", ""),
            "bundle_artifact_root": spec.metadata.get("bundle_artifact_root", ""),
            "bundle_run_id": spec.metadata.get("bundle_run_id", ""),
            "data_start": spec.metadata.get("data_start", ""),
            "score_scale": spec.score_scale,
            "figure_scale": spec.metadata.get("figure_scale", ""),
            "run_id": winner.run_id,
            "run_root": str(run_root),
            "output_root": str(output_root),
            "generated_config_path": str(cfg_path),
            "frozen_config_path": frozen_config,
            "frozen_config_sha256": config_sha,
            "crps_summary_path": str(crps_path),
            "mean_crps": winner.mean_crps,
            "median_crps": winner.median_crps,
            "max_crps": winner.max_crps,
            "runner_up_grid_spec_id": winner.runner_up_grid_spec_id,
            "runner_up_mean_crps": winner.runner_up_mean_crps,
            "winner_runner_abs_diff": winner.winner_runner_abs_diff,
        }
        rows.append(row)
        config_rows.append(
            {
                "cutoff": winner.cutoff,
                "run_id": winner.run_id,
                "generated_config_path": str(cfg_path),
                "generated_config_exists": cfg_path.exists(),
                "frozen_config_path": frozen_config,
                "frozen_config_sha256": config_sha,
            }
        )
        for rel in REQUIRED_OUTPUT_FILES:
            path = output_root / rel
            output_rows.append(
                {
                    "cutoff": winner.cutoff,
                    "run_id": winner.run_id,
                    "artifact": rel,
                    "path": str(path),
                    "exists": path.exists(),
                    "sha256": sha256(path) if path.exists() and path.is_file() else "",
                }
            )

    write_csv(matrix_dir / "matrix_plan.csv", rows)
    write_csv(matrix_dir / "authoritative_winner_manifest_resolved.csv", rows)
    write_csv(matrix_dir / "source_config_manifest.csv", config_rows)
    write_csv(matrix_dir / "post_output_manifest.csv", output_rows)
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest_path": str(spec.manifest_path),
        "runtime_root": str(spec.runtime_root),
        "matrix_dir": str(matrix_dir),
        "family": spec.model_family,
        "manuscript_label": spec.manuscript_label,
        "model_id": spec.model_id,
        "winner_rows": len(rows),
        "quantile_fits_represented": len(rows) * 7,
        "required_output_files_per_winner": len(REQUIRED_OUTPUT_FILES),
        "publication_transition_gate": spec.metadata.get("publication_transition_note", ""),
        "remaining_model_input_parity_required": True,
        "remaining_8_model_input_parity_required": False,
    }
    write_yaml(matrix_dir / "matrix_metadata.yaml", metadata)
    (matrix_dir / "README.md").write_text(
        "# HE2 exDQLM Multivariate Keep Authoritative Winner Matrix\n\n"
        "This matrix freezes the five CRPS-selected `exAL-M-T1` / `exdqlm_multivar_keep` canonical-grid winners.\n\n"
        "It is a source-of-truth and validation artifact only; it does not launch or modify model runs.\n\n"
        "Publication gate:\n"
        "- all nine HE2 Bayesian comparison families now resolve to canonical-bundle promoted roots after the "
        "2026-06-07 NDLM promotion.\n\n"
        "Generated files:\n"
        "- `matrix_plan.csv`\n"
        "- `authoritative_winner_manifest_resolved.csv`\n"
        "- `source_config_manifest.csv`\n"
        "- `post_output_manifest.csv`\n"
        "- `matrix_metadata.yaml`\n",
        encoding="utf-8",
    )
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the five-row authoritative exDQLM multivariate keep winner matrix.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "docs" / "exdqlm_multivar_keep_authoritative_specs_20260601.yaml")
    parser.add_argument("--matrix-dir", type=Path)
    parser.add_argument("--no-freeze-configs", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = build_matrix(args.manifest.resolve(), args.matrix_dir.resolve() if args.matrix_dir else None, freeze_configs=not args.no_freeze_configs)
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

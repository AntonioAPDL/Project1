#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from build_he2_dqlm_multivar_al_drop_diagnostic_plan import (
    DEFAULT_ARTIFACT_ROOT,
    SOURCE_ARTIFACT_ROOT,
    TARGET_FAMILY,
    TARGET_MODEL_KEY,
    build_package,
)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return payload


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def nested(payload: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def validate_package(artifact_root: Path, *, expected_lane_scope: str) -> dict[str, Any]:
    matrix_dir = artifact_root / "control" / "diagnostic_matrix"
    metadata_path = matrix_dir / "diagnostic_matrix_metadata.yaml"
    plan_path = matrix_dir / "diagnostic_matrix_plan.csv"
    queue_plan_path = matrix_dir / "matrix_plan.csv"
    manifest_path = matrix_dir / "diagnostic_config_manifest.csv"
    guard_path = matrix_dir / "NO_LAUNCH_GUARD.txt"
    assert_true(metadata_path.exists(), f"missing metadata: {metadata_path}")
    assert_true(plan_path.exists(), f"missing plan: {plan_path}")
    assert_true(queue_plan_path.exists(), f"missing queue-compatible matrix plan: {queue_plan_path}")
    assert_true(manifest_path.exists(), f"missing config manifest: {manifest_path}")
    assert_true(guard_path.exists(), f"missing no-launch guard: {guard_path}")
    assert_true(not (matrix_dir / "launch_al_drop_diagnostics.sh").exists(), "diagnostic package must not write launch shell")

    metadata = load_yaml(metadata_path)
    rows = read_csv(plan_path)
    queue_rows = read_csv(queue_plan_path)
    assert_true(metadata.get("status") == "prepared_not_launched", f"unexpected status: {metadata.get('status')}")
    assert_true(metadata.get("no_launch") is True, "metadata no_launch must be true")
    assert_true(metadata.get("launch_files_written") is False, "launch_files_written must be false")
    assert_true(metadata.get("lane_scope") == expected_lane_scope, "lane scope mismatch")
    assert_true(len(rows) == int(metadata["n_lanes"]), "row count metadata mismatch")
    assert_true(len(queue_rows) == len(rows), "queue row count mismatch")

    for row in rows:
        assert_true(row["family_id"] == TARGET_FAMILY, f"unexpected family: {row}")
        assert_true(row["likelihood_mode"] == "al", f"unexpected likelihood: {row}")
        assert_true(row["transfer_mode"] == "drop", f"unexpected transfer: {row}")
        assert_true(row["no_launch"] == "True", f"row is not no-launch: {row}")
        assert_true(row["fit_only"] == "True", f"row is not fit-only: {row}")
        cfg = load_yaml(Path(row["config_path"]))
        assert_true(nested(cfg, ["models", TARGET_MODEL_KEY, "likelihood_mode"]) == "al", row["config_path"])
        assert_true(nested(cfg, ["models", TARGET_MODEL_KEY, "forecast_transfer_mode"]) == "drop", row["config_path"])
        assert_true(nested(cfg, ["fit", "quantiles"]) == [int(row["q"]) / 100.0], row["config_path"])
        assert_true(nested(cfg, ["fit", "parallel", "workers"]) == 1, row["config_path"])
        assert_true(nested(cfg, ["run", "threads", "mc_cores"]) == 1, row["config_path"])
        assert_true(nested(cfg, ["stages", "fit"]) is True, row["config_path"])
        assert_true(nested(cfg, ["stages", "data_prep_shared"]) is True, row["config_path"])
        for stage in ["forecats", "post", "validate", "report"]:
            assert_true(nested(cfg, ["stages", stage]) is False, f"{row['config_path']} stage {stage} not disabled")
        debug = nested(cfg, ["debug_he2_al_m_t0_diagnostic"], {})
        assert_true(debug.get("no_launch") is True, row["config_path"])
        assert_true(debug.get("retain_rdata_if_launched") is True, row["config_path"])
    return {
        "metadata": metadata,
        "rows": len(rows),
        "queue_rows": len(queue_rows),
        "spec_id": metadata.get("discount_spec", {}).get("spec_id", ""),
        "requires_user_discount_decision": metadata.get("requires_user_discount_decision"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the no-launch AL-M-T0 diagnostic matrix.")
    parser.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)
    parser.add_argument("--source-artifact-root", type=Path, default=SOURCE_ARTIFACT_ROOT)
    parser.add_argument("--discount-spec-yaml", type=Path)
    parser.add_argument("--lane-scope", choices=["representative", "all_failed"], default="representative")
    parser.add_argument("--outdir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    artifact_root = args.artifact_root.resolve()
    build_package(
        artifact_root,
        source_artifact_root=args.source_artifact_root.resolve(),
        discount_spec_path=args.discount_spec_yaml,
        lane_scope=args.lane_scope,
    )
    summary = {
        "validated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "artifact_root": str(artifact_root),
        "source_artifact_root": str(args.source_artifact_root.resolve()),
        "lane_scope": args.lane_scope,
        "checks": validate_package(artifact_root, expected_lane_scope=args.lane_scope),
        "launch_performed": False,
    }
    outdir = args.outdir.resolve() if args.outdir else artifact_root / "control" / "diagnostic_validation"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "diagnostic_validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (outdir / "DIAGNOSTIC_VALIDATION_SUMMARY.md").write_text(
        "\n".join(
            [
                "# AL-M-T0 No-Launch Diagnostic Validation",
                "",
                f"- artifact_root: `{artifact_root}`",
                f"- lane_scope: `{args.lane_scope}`",
                "- launch_performed: `False`",
                f"- rows: `{summary['checks']['rows']}`",
                f"- queue_rows: `{summary['checks']['queue_rows']}`",
                f"- spec_id: `{summary['checks']['spec_id']}`",
                f"- requires_user_discount_decision: `{summary['checks']['requires_user_discount_decision']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary["checks"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

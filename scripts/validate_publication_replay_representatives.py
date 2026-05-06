#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config" / "publication_replay_representatives_20260506"
OUT_DIR = REPO_ROOT / "reports" / "publication_replay"
OUT_MD = OUT_DIR / "publication_representative_validation.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the isolated publication representative replay bundles.")
    parser.add_argument("--slugs", nargs="*", help="Subset of bundle slugs to validate.")
    return parser.parse_args()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_launch_settings(path: Path) -> dict[str, str]:
    settings: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        settings[key.strip()] = value.strip()
    return settings


def selected_epsilon_from_run_id(run_id: str) -> str | None:
    match = re.search(r"_v8_(eps[^_]+)_", run_id)
    return match.group(1) if match else None


def assert_true(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def validate_template(path: Path) -> dict[str, str]:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    debug = cfg.get("debug_publication_replay") or {}
    campaign = cfg.get("campaign") or {}
    slug = path.stem.replace(".template", "")
    matrix_dir = Path(str(campaign["matrix_dir"])).resolve()
    config_output_dir = Path(str(campaign["config_output_dir"])).resolve()
    artifact_root = Path(str(campaign["artifact_root"])).resolve()
    failures: list[str] = []

    assert_true(bool(debug.get("source_r_version")), "template missing source_r_version", failures)
    assert_true(bool(debug.get("source_runtime_profile")), "template missing source_runtime_profile", failures)

    matrix_plan = matrix_dir / "matrix_plan.csv"
    selection_summary = matrix_dir / "selection_summary.csv"
    launch_env = matrix_dir / "launch_settings.env"

    assert_true(matrix_plan.exists(), "missing matrix_plan.csv", failures)
    assert_true(selection_summary.exists(), "missing selection_summary.csv", failures)
    assert_true(launch_env.exists(), "missing launch_settings.env", failures)
    assert_true(config_output_dir.exists(), "missing config_output_dir", failures)
    assert_true(artifact_root.exists(), "missing artifact_root", failures)

    if failures:
        return {
            "slug": slug,
            "cutoff": str(debug.get("cutoff", "")),
            "manuscript_label": str(debug.get("manuscript_label", "")),
            "campaign_lineage": str(debug.get("campaign_lineage", "")),
            "status": "FAIL",
            "note": "; ".join(failures),
        }

    plan_rows = read_csv_rows(matrix_plan)
    selection_rows = read_csv_rows(selection_summary)
    generated_configs = sorted(config_output_dir.glob("*.yaml"))
    settings = read_launch_settings(launch_env)

    assert_true(len(plan_rows) == 1, f"expected 1 plan row, found {len(plan_rows)}", failures)
    assert_true(len(selection_rows) == 1, f"expected 1 selection row, found {len(selection_rows)}", failures)
    assert_true(len(generated_configs) == 1, f"expected 1 generated config, found {len(generated_configs)}", failures)
    assert_true(settings.get("ORDINARY_MAX_CONCURRENT") == "1", "ORDINARY_MAX_CONCURRENT should be 1", failures)
    if "HEAVY_CUTOFF_MAX_CONCURRENT" in settings:
        assert_true(settings.get("HEAVY_CUTOFF_MAX_CONCURRENT") == "1", "HEAVY_CUTOFF_MAX_CONCURRENT should be 1", failures)
    if generated_configs:
        generated_cfg = yaml.safe_load(generated_configs[0].read_text(encoding="utf-8")) or {}
        run_cfg = generated_cfg.get("run") or {}
        assert_true(run_cfg.get("overwrite") is True, "generated config must set run.overwrite=true", failures)
        assert_true(run_cfg.get("auto_suffix_on_collision") is False, "generated config must set auto_suffix_on_collision=false", failures)

    if plan_rows:
        row = plan_rows[0]
        assert_true(row.get("cutoff") == str(debug.get("cutoff", "")), "cutoff mismatch in matrix plan", failures)
        assert_true(row.get("model_id") in path.read_text(encoding="utf-8"), "model_id not reflected in generated template", failures)

        lineage = str(debug.get("campaign_lineage", ""))
        publication_run_id = str(debug.get("publication_run_id", ""))
        if lineage == "featurecov_cf1_eps_sweep_20260416":
            expected_eps = selected_epsilon_from_run_id(publication_run_id)
            assert_true(row.get("epsilon") == expected_eps, f"expected epsilon {expected_eps}, found {row.get('epsilon')}", failures)
        elif lineage.startswith("exalm_t1_discount_grid_exact_20260424"):
            discount_set = row.get("discount_set") or ""
            assert_true(discount_set == "set09", f"expected discount_set set09, found {discount_set}", failures)
        elif lineage == "ndlm_featurecov_rerun_postfix_20260421":
            assert_true(row.get("spec_id") == "ndlm_featurecov_v1_postfix", "unexpected NDLM spec_id", failures)
        elif lineage == "univar_featurecov_he2_rerun_20260422":
            assert_true(row.get("family_id") == "exdqlm_univar", "unexpected univar family_id", failures)

    return {
        "slug": slug,
        "cutoff": str(debug.get("cutoff", "")),
        "manuscript_label": str(debug.get("manuscript_label", "")),
        "campaign_lineage": str(debug.get("campaign_lineage", "")),
        "status": "PASS" if not failures else "FAIL",
        "note": "structural replay bundle validated" if not failures else "; ".join(failures),
    }


def write_markdown(rows: list[dict[str, str]]) -> None:
    lines = [
        "# Publication Representative Replay Validation",
        "",
        "| Slug | Cutoff | Label | Campaign lineage | Status | Note |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['slug']}` | {row['cutoff']} | `{row['manuscript_label']}` | "
            f"`{row['campaign_lineage']}` | {row['status']} | {row['note']} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    all_templates = sorted(CONFIG_DIR.glob("*.template.yaml"))
    templates = all_templates
    if args.slugs:
        selected = set(args.slugs)
        templates = [path for path in templates if path.stem.replace(".template", "") in selected]
    if not templates:
        raise SystemExit("No representative replay templates selected.")

    rows = [validate_template(path) for path in all_templates]
    write_markdown(rows)
    if args.slugs:
        selected = set(args.slugs)
        rows = [row for row in rows if row["slug"] in selected]
    for row in rows:
        print(f"{row['slug']}: {row['status']} - {row['note']}")
    if any(row["status"] != "PASS" for row in rows):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

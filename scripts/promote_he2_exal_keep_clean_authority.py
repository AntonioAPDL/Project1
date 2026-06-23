#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT.parent / "project1_ucsc_phd_runtime"
DEFAULT_BASELINE = ROOT / "docs" / "exdqlm_multivar_keep_authoritative_specs_20260601.yaml"
DEFAULT_OVERLAY = ROOT / "config" / "he2_publication_manifest_replacement_overlay_current_authority_20260623.yaml"
DEFAULT_CLEAN_ROOT = (
    RUNTIME_ROOT / "multimodel_v8_he2_exdqlm_multivar_keep_partial_authority_refresh_20260623"
)
DEFAULT_OUT_DIR = ROOT / "reports" / "he2_exal_keep_clean_authority_promotion_20260623"

TARGET_FAMILY = "exdqlm_multivar_keep"
TARGET_LABEL = "exAL-M-T1"
TARGET_MODEL_ID = "exdqlm_multivar_synth_keep"
TARGET_CUTOFFS = ("20211221", "20220511", "20221225")
CLEAN_LINEAGE = "exdqlm_multivar_keep_partial_authority_refresh_20260623:clean_replay"
REPLACEMENT_REASON = "clean_replay_crps_improvement_over_20260601_authority"
PUBLICATION_NOTE = (
    "Clean replay of the partial-screen selected exAL-M-T1 specification on the canonical "
    "20260510 publication input bundle. The rerun passed fit/post/validate/report gates, "
    "retains the improved forecast-window CRPS relative to the 2026-06-01 authority, and "
    "does not retain heavy RData objects."
)
RUN_ID_BY_CUTOFF = {
    cutoff: f"multimodel_{cutoff}_v8_he2partial20260623_exdqlm_multivar_keep"
    for cutoff in TARGET_CUTOFFS
}
REPLACED_SOURCE_BY_CUTOFF = {
    "20211221": "multimodel_20211221_v8_he2grid_c03_eps030_exdqlm_multivar_keep",
    "20220511": "multimodel_20220511_v8_he2grid_c02_eps060_exdqlm_multivar_keep",
    "20221225": "multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep",
}
REQUIRED_OUTPUTS = (
    "publication_figure_manifest.csv",
    "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png",
    "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png",
    "multivar_vb_usgs_location_quantiles_cutoff_window.png",
    "tables/crps_forecast_summary.csv",
    "tables/crps_forecast_per_time.csv",
    "tables/crps_input_health.csv",
    "tables/gamma_summary.csv",
    "tables/sigma_summary.csv",
    "tables/covariate_effects_summary.csv",
    "tables/posterior_table_exports_manifest.csv",
)


@dataclass
class Check:
    scope: str
    item: str
    status: str
    detail: str


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise RuntimeError(f"YAML root must be a mapping: {path}")
    return payload


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False, width=100), encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def add(checks: list[Check], scope: str, item: str, ok: bool, detail: str) -> None:
    checks.append(Check(scope, item, "pass" if ok else "fail", detail))


def baseline_by_cutoff(path: Path) -> dict[str, dict[str, Any]]:
    payload = load_yaml(path)
    return {str(row["cutoff"]).zfill(8): row for row in payload.get("winners", [])}


def stage_statuses(run_root: Path) -> dict[str, str]:
    manifest_path = run_root / "run_manifest.yaml"
    payload = load_yaml(manifest_path)
    stages = payload.get("stages") or {}
    return {
        stage: str((stages.get(stage) or {}).get("status", "")).strip().lower()
        for stage in ("fit", "post", "validate", "report")
    }


def mean_crps(run_root: Path) -> tuple[float, Path]:
    path = run_root / "post" / "outputs" / run_root.name / "tables" / "crps_forecast_summary.csv"
    rows = read_csv(path)
    for row in rows:
        if row.get("model_id") == TARGET_MODEL_ID or row.get("model_variant") in {TARGET_MODEL_ID, TARGET_FAMILY}:
            return float(row["mean_crps"]), path
    if rows and rows[0].get("mean_crps"):
        return float(rows[0]["mean_crps"]), path
    raise RuntimeError(f"Could not identify mean CRPS row in {path}")


def retained_rdata(run_root: Path) -> list[Path]:
    found: list[Path] = []
    for pattern in ("**/*.RData", "**/*.rdata", "**/*.rda", "**/*.Rda"):
        found.extend(path for path in run_root.glob(pattern) if path.is_file())
    return sorted(found)


def validate_clean_runs(clean_root: Path, baseline_path: Path) -> tuple[list[Check], list[dict[str, Any]]]:
    checks: list[Check] = []
    rows: list[dict[str, Any]] = []
    baseline = baseline_by_cutoff(baseline_path)
    add(checks, "clean_root", "exists", clean_root.exists(), str(clean_root))
    matrix_path = clean_root / "control" / "publication_relaunch_matrix" / "matrix_status.csv"
    add(checks, "matrix", "matrix_status_exists", matrix_path.exists(), str(matrix_path))
    matrix_by_cutoff: dict[str, dict[str, str]] = {}
    if matrix_path.exists():
        matrix_rows = read_csv(matrix_path)
        matrix_by_cutoff = {str(row.get("cutoff", "")).zfill(8): row for row in matrix_rows}
        add(checks, "matrix", "row_count", len(matrix_rows) == len(TARGET_CUTOFFS), str(len(matrix_rows)))
    for cutoff in TARGET_CUTOFFS:
        run_id = RUN_ID_BY_CUTOFF[cutoff]
        run_root = clean_root / "runs" / run_id
        scope = f"{cutoff}:{run_id}"
        add(checks, scope, "baseline_present", cutoff in baseline, str(baseline.get(cutoff, {}).get("run_id", "")))
        add(checks, scope, "run_root_exists", run_root.exists(), str(run_root))
        matrix_row = matrix_by_cutoff.get(cutoff)
        add(checks, scope, "matrix_row_present", matrix_row is not None, json.dumps(matrix_row or {}, sort_keys=True))
        if matrix_row:
            add(checks, scope, "matrix_status_pass", matrix_row.get("status") == "pass", str(matrix_row.get("status", "")))
            add(checks, scope, "matrix_phase_report", matrix_row.get("phase") == "report", str(matrix_row.get("phase", "")))
        if not run_root.exists() or cutoff not in baseline:
            continue
        statuses = stage_statuses(run_root)
        add(
            checks,
            scope,
            "stages_pass",
            all(statuses.get(stage) == "pass" for stage in ("fit", "post", "validate", "report")),
            json.dumps(statuses, sort_keys=True),
        )
        output_root = run_root / "post" / "outputs" / run_root.name
        missing = [rel for rel in REQUIRED_OUTPUTS if not (output_root / rel).exists()]
        add(checks, scope, "required_outputs_exist", not missing, "|".join(missing))
        heavy = retained_rdata(run_root)
        add(checks, scope, "heavy_rdata_absent", not heavy, "|".join(str(path) for path in heavy[:5]))
        crps_path = output_root / "tables" / "crps_forecast_summary.csv"
        add(checks, scope, "crps_summary_exists", crps_path.exists(), str(crps_path))
        if not crps_path.exists():
            continue
        new_crps, source = mean_crps(run_root)
        old = baseline[cutoff]
        old_crps = float(old["mean_crps"])
        add(checks, scope, "crps_improved_vs_20260601_authority", new_crps <= old_crps, f"{new_crps:.12g} <= {old_crps:.12g}")
        rows.append(
            {
                "cutoff": cutoff,
                "run_id": run_id,
                "run_root": str(run_root),
                "replaced_source_run_id": REPLACED_SOURCE_BY_CUTOFF[cutoff],
                "old_authority_run_id": old["run_id"],
                "old_authority_mean_crps": f"{old_crps:.15g}",
                "clean_replay_mean_crps": f"{new_crps:.15g}",
                "delta_vs_old_authority": f"{new_crps - old_crps:.15g}",
                "crps_source": str(source),
                "campaign_lineage": CLEAN_LINEAGE,
            }
        )
    return checks, rows


def update_overlay(overlay_path: Path, clean_rows: list[dict[str, Any]]) -> dict[str, Any]:
    payload = load_yaml(overlay_path)
    replacements = payload.get("replacements")
    if not isinstance(replacements, list):
        raise RuntimeError(f"Overlay replacements must be a list: {overlay_path}")
    row_by_cutoff = {row["cutoff"]: row for row in clean_rows}
    updated = 0
    for row in replacements:
        if row.get("family") != TARGET_FAMILY or row.get("manuscript_label") != TARGET_LABEL:
            continue
        cutoff = str(row.get("cutoff", "")).zfill(8)
        clean = row_by_cutoff.get(cutoff)
        if clean is None:
            continue
        row["run_id"] = clean["run_id"]
        row["run_root"] = clean["run_root"]
        row["campaign_lineage"] = CLEAN_LINEAGE
        row["replacement_reason"] = REPLACEMENT_REASON
        row["publication_note"] = PUBLICATION_NOTE
        row["replaced_source_run_id"] = clean["replaced_source_run_id"]
        updated += 1
    if updated != len(TARGET_CUTOFFS):
        raise RuntimeError(f"Expected to update {len(TARGET_CUTOFFS)} exAL-M-T1 rows, updated {updated}")
    payload["publication_note"] = (
        "Current HE2 publication replacement overlay. This overlay combines the previously promoted "
        "Table 1 targeted repairs with clean-replayed exAL-M-T1 replacements selected from the "
        "2026-06-19 epsilon/discount screening checkpoint. Rows are promoted selectively: a "
        "replacement supersedes the previous authoritative row only when its CRPS is lower or tied, "
        "fit/post/validate/report pass, required post outputs exist, canonical input bundle checks "
        "pass, and heavy RData cleanup is complete. Remaining incomplete screening rows stay "
        "exploratory until a later screening manifest is produced."
    )
    payload["replacement_reason"] = "targeted_rerun_or_clean_screen_replay_improvement_selected_by_crps_and_output_gates"
    return payload


def write_report(out_dir: Path, checks: list[Check], rows: list[dict[str, Any]], *, apply: bool) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "clean_authority_promotion_checks.csv", [check.__dict__ for check in checks])
    write_csv(out_dir / "clean_authority_promoted_rows.csv", rows)
    failed = [check for check in checks if check.status != "pass"]
    metadata = {
        "generated_at_utc": utc_now(),
        "apply": apply,
        "failed_checks": len(failed),
        "target_cutoffs": list(TARGET_CUTOFFS),
        "lineage": CLEAN_LINEAGE,
    }
    (out_dir / "clean_authority_promotion_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# HE2 exAL-M-T1 Clean Authority Promotion",
        "",
        f"- generated_at_utc: `{metadata['generated_at_utc']}`",
        f"- apply: `{apply}`",
        f"- failed_checks: `{len(failed)}`",
        f"- lineage: `{CLEAN_LINEAGE}`",
        "",
        "| Cutoff | Old Authority CRPS | Clean Replay CRPS | Delta | Clean Run |",
        "|---|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['cutoff']}` | {float(row['old_authority_mean_crps']):.5f} | "
            f"{float(row['clean_replay_mean_crps']):.5f} | "
            f"{float(row['delta_vs_old_authority']):+.5f} | `{row['run_id']}` |"
        )
    if failed:
        lines.extend(["", "## Failed Checks", ""])
        for check in failed:
            lines.append(f"- `{check.scope}` / `{check.item}`: {check.detail}")
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote clean-replayed HE2 exAL-M-T1 selected specs into the current overlay.")
    parser.add_argument("--clean-root", type=Path, default=DEFAULT_CLEAN_ROOT)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--overlay", type=Path, default=DEFAULT_OVERLAY)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--apply", action="store_true", help="Write the overlay after all checks pass.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    checks, rows = validate_clean_runs(args.clean_root, args.baseline)
    failed = [check for check in checks if check.status != "pass"]
    write_report(args.out_dir, checks, rows, apply=bool(args.apply))
    print(f"checks={len(checks)} failed={len(failed)}")
    print(f"report={args.out_dir}")
    if failed:
        return 1
    if args.apply:
        payload = update_overlay(args.overlay, rows)
        write_yaml(args.overlay, payload)
        print(f"updated_overlay={args.overlay}")
    else:
        print("dry_run=true; pass --apply to update overlay")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

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
DEFAULT_BASELINE = ROOT / "docs" / "exdqlm_multivar_keep_authoritative_specs_20260601.yaml"
DEFAULT_OVERLAY = ROOT / "config" / "he2_publication_manifest_replacement_overlay_current_authority_20260623.yaml"
DEFAULT_SCREEN_ROOT = (
    ROOT.parent / "project1_ucsc_phd_runtime" / "multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619"
)
PARTIAL_LINEAGE = "exdqlm_multivar_keep_partial_screen_20260623:best_so_far"
CLEAN_REPLAY_LINEAGE = "exdqlm_multivar_keep_partial_authority_refresh_20260623:clean_replay"
SELECTED_LINEAGE_PREFIXES = (
    "exdqlm_multivar_keep_partial_screen_20260623:",
    "exdqlm_multivar_keep_partial_authority_refresh_20260623:",
)
TARGET_FAMILY = "exdqlm_multivar_keep"
TARGET_LABEL = "exAL-M-T1"
TARGET_MODEL_ID = "exdqlm_multivar_synth_keep"
REQUIRED_OUTPUTS = [
    "publication_figure_manifest.csv",
    "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png",
    "exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png",
    "tables/crps_forecast_summary.csv",
    "tables/crps_forecast_per_time.csv",
    "tables/crps_input_health.csv",
    "tables/gamma_summary.csv",
    "tables/sigma_summary.csv",
    "tables/covariate_effects_summary.csv",
    "tables/posterior_table_exports_manifest.csv",
]


@dataclass
class Check:
    scope: str
    item: str
    status: str
    detail: str


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise RuntimeError(f"YAML root is not a mapping: {path}")
    return payload


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def add(checks: list[Check], scope: str, item: str, ok: bool, detail: str) -> None:
    checks.append(Check(scope, item, "pass" if ok else "fail", detail))


def baseline_by_cutoff(path: Path) -> dict[str, dict[str, Any]]:
    data = load_yaml(path)
    return {str(row["cutoff"]).zfill(8): row for row in data.get("winners", [])}


def score_row(run_root: Path) -> dict[str, str]:
    path = run_root / "post" / "outputs" / run_root.name / "tables" / "crps_forecast_summary.csv"
    for row in read_csv(path):
        if row.get("model_id") == TARGET_MODEL_ID or row.get("model_variant") == TARGET_FAMILY:
            return row
    raise RuntimeError(f"Missing {TARGET_MODEL_ID}/{TARGET_FAMILY} row in {path}")


def stage_statuses(run_root: Path) -> dict[str, str]:
    manifest_path = run_root / "run_manifest.yaml"
    data = load_yaml(manifest_path)
    stages = data.get("stages") or {}
    return {
        stage: str((stages.get(stage) or {}).get("status", "")).strip().lower()
        for stage in ["fit", "post", "validate", "report"]
    }


def retained_rdata(run_root: Path) -> list[Path]:
    out: list[Path] = []
    for pattern in ["**/*.RData", "**/*.rdata", "**/*.rda", "**/*.Rda"]:
        out.extend(path for path in run_root.glob(pattern) if path.is_file())
    return sorted(out)


def partial_replacements(overlay_path: Path) -> list[dict[str, Any]]:
    overlay = load_yaml(overlay_path)
    replacements = overlay.get("replacements") or []
    return [
        row
        for row in replacements
        if str(row.get("family", "")).strip() == TARGET_FAMILY
        and str(row.get("manuscript_label", "")).strip() == TARGET_LABEL
        and any(str(row.get("campaign_lineage", "")).startswith(prefix) for prefix in SELECTED_LINEAGE_PREFIXES)
    ]


def matrix_counts(screen_root: Path) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    status_path = screen_root / "control" / "publication_relaunch_matrix" / "matrix_status.csv"
    rows = read_csv(status_path)
    overall: dict[str, int] = {}
    by_case: dict[str, dict[str, int]] = {}
    for row in rows:
        status = row.get("status", "") or "missing"
        overall[status] = overall.get(status, 0) + 1
        spec = row.get("epsilon", "")
        case = spec[:3] if spec else "unknown"
        by_case.setdefault(case, {})
        by_case[case][status] = by_case[case].get(status, 0) + 1
    return overall, by_case


def validate(baseline_path: Path, overlay_path: Path, screen_root: Path) -> tuple[list[Check], list[dict[str, str]], dict[str, Any]]:
    checks: list[Check] = []
    rows: list[dict[str, str]] = []
    baseline = baseline_by_cutoff(baseline_path)
    replacements = partial_replacements(overlay_path)
    lineage_values = {str(row.get("campaign_lineage", "")) for row in replacements}
    clean_replay_mode = bool(lineage_values) and all(value == CLEAN_REPLAY_LINEAGE for value in lineage_values)
    replacement_campaign_roots = {
        Path(str(row.get("run_root", ""))).parent.parent
        for row in replacements
        if str(row.get("run_root", "")).strip()
    }
    declared_root = (
        next(iter(replacement_campaign_roots))
        if clean_replay_mode and len(replacement_campaign_roots) == 1
        else screen_root
    )
    add(checks, "overlay", "partial_replacement_count", len(replacements) == 3, f"{len(replacements)} rows")
    expected_cutoffs = {"20211221", "20220511", "20221225"}
    observed_cutoffs = {str(row.get("cutoff", "")).zfill(8) for row in replacements}
    add(checks, "overlay", "partial_replacement_cutoffs", observed_cutoffs == expected_cutoffs, "|".join(sorted(observed_cutoffs)))
    if clean_replay_mode:
        add(
            checks,
            "overlay",
            "clean_replay_single_campaign_root",
            len(replacement_campaign_roots) == 1,
            "|".join(str(path) for path in sorted(replacement_campaign_roots)),
        )

    for repl in replacements:
        cutoff = str(repl["cutoff"]).zfill(8)
        run_root = Path(str(repl.get("run_root", "")))
        base = baseline.get(cutoff)
        scope = f"{cutoff}:{repl.get('run_id', '')}"
        add(checks, scope, "baseline_present", base is not None, str(base.get("run_id", "")) if base else "missing")
        add(checks, scope, "run_root_exists", run_root.exists(), str(run_root))
        add(
            checks,
            scope,
            "run_under_declared_root",
            str(run_root).startswith(str(declared_root / "runs") + "/"),
            str(run_root),
        )
        if not run_root.exists() or base is None:
            continue
        statuses = stage_statuses(run_root)
        add(checks, scope, "stages_pass", all(statuses.get(stage) == "pass" for stage in ["fit", "post", "validate", "report"]), json.dumps(statuses, sort_keys=True))
        out_root = run_root / "post" / "outputs" / run_root.name
        missing = [rel for rel in REQUIRED_OUTPUTS if not (out_root / rel).exists()]
        add(checks, scope, "required_outputs_exist", not missing, "|".join(missing))
        heavy = retained_rdata(run_root)
        add(checks, scope, "heavy_rdata_absent", not heavy, "|".join(str(path) for path in heavy[:5]))
        score = score_row(run_root)
        new_crps = float(score["mean_crps"])
        old_crps = float(base["mean_crps"])
        add(checks, scope, "crps_improved", new_crps < old_crps, f"{new_crps:.12g} < {old_crps:.12g}")
        rows.append(
            {
                "cutoff": cutoff,
                "old_run_id": str(base["run_id"]),
                "new_run_id": str(repl["run_id"]),
                "old_mean_crps": f"{old_crps:.15g}",
                "new_mean_crps": f"{new_crps:.15g}",
                "delta": f"{new_crps - old_crps:.15g}",
                "pct_delta": f"{100 * (new_crps - old_crps) / old_crps:.6g}",
                "lineage": str(repl["campaign_lineage"]),
            }
        )

    overall, by_case = matrix_counts(declared_root)
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline_manifest": str(baseline_path),
        "overlay": str(overlay_path),
        "screen_root": str(declared_root),
        "requested_screen_root": str(screen_root),
        "screen_status_counts": overall,
        "screen_status_by_case": by_case,
        "validation_mode": "clean_replay" if clean_replay_mode else "partial_screen",
        "promotion_policy": (
            "clean replay of selected partial-screen winners; all promoted clean-replay rows must pass"
            if clean_replay_mode
            else "partial-screen best-so-far overlay; unfinished rows remain exploratory"
        ),
    }
    if clean_replay_mode:
        add(
            checks,
            "screen",
            "clean_replay_complete",
            overall == {"pass": len(replacements)},
            json.dumps(overall, sort_keys=True),
        )
    else:
        add(
            checks,
            "screen",
            "screen_not_final_full_grid",
            overall.get("not_started", 0) > 0 or overall.get("pending", 0) > 0,
            json.dumps(overall, sort_keys=True),
        )
    return checks, rows, metadata


def write_report(out_dir: Path, checks: list[Check], rows: list[dict[str, str]], metadata: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = ["scope", "item", "status", "detail"]
    write_csv(out_dir / "partial_screen_promotion_checks.csv", [c.__dict__ for c in checks], fields)
    write_csv(
        out_dir / "partial_screen_promoted_exal_keep_rows.csv",
        rows,
        ["cutoff", "old_run_id", "new_run_id", "old_mean_crps", "new_mean_crps", "delta", "pct_delta", "lineage"],
    )
    (out_dir / "partial_screen_promotion_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    failed = [c for c in checks if c.status != "pass"]
    lines = [
        "# HE2 exAL-M-T1 Partial-Screen Promotion Validation\n\n",
        f"- generated_at_utc: `{metadata['generated_at_utc']}`\n",
        f"- overlay: `{metadata['overlay']}`\n",
        f"- screening root: `{metadata['screen_root']}`\n",
        f"- failed checks: `{len(failed)}`\n",
        "\n## Promoted Rows\n\n",
        "| cutoff | old run | new run | old CRPS | new CRPS | delta | pct delta |\n",
        "|---|---|---|---:|---:|---:|---:|\n",
    ]
    for row in rows:
        lines.append(
            f"| {row['cutoff']} | `{row['old_run_id']}` | `{row['new_run_id']}` | "
            f"{float(row['old_mean_crps']):.6f} | {float(row['new_mean_crps']):.6f} | "
            f"{float(row['delta']):+.6f} | {float(row['pct_delta']):+.2f}% |\n"
        )
    lines.extend([
        "\n## Screening State\n\n",
        (
            "The promoted rows are clean replays of selected partial-screen winners; all clean-replay rows must pass before publication promotion.\n\n"
            if metadata.get("validation_mode") == "clean_replay"
            else "The promoted rows are best-so-far partial-screen selections. The remaining screening rows are intentionally not treated as final authority.\n\n"
        ),
        "```json\n",
        json.dumps(metadata["screen_status_counts"], indent=2, sort_keys=True),
        "\n```\n",
    ])
    if failed:
        lines.extend(["\n## Failed Checks\n\n"])
        for check in failed:
            lines.append(f"- `{check.scope}` / `{check.item}`: {check.detail}\n")
    (out_dir / "README.md").write_text("".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the 2026-06-23 partial-screen exAL-M-T1 promotion overlay.")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--overlay", type=Path, default=DEFAULT_OVERLAY)
    parser.add_argument("--screen-root", type=Path, default=DEFAULT_SCREEN_ROOT)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "reports" / "he2_exal_keep_partial_screen_promotion_20260623")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    checks, rows, metadata = validate(args.baseline, args.overlay, args.screen_root)
    write_report(args.out_dir, checks, rows, metadata)
    failed = [c for c in checks if c.status != "pass"]
    print(f"checks={len(checks)} failed={len(failed)}")
    print(f"report={args.out_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
RUNTIME_ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd_runtime")

CAMPAIGN_ROOT = RUNTIME_ROOT / "multimodel_v8_exalm_t1_discount_grid_exact_20260424"
CONTROL_DIR = CAMPAIGN_ROOT / "control" / "exalm_t1_discount_grid_exact_v1"
MATRIX_PLAN = CONTROL_DIR / "matrix_plan.csv"
OUTPUT_DIR = REPO_ROOT / "reports" / "quantile_discount_probe_analysis"
CSV_OUT = OUTPUT_DIR / "exalm_t1_discount_grid_exact_vs_he2.csv"
MD_OUT = OUTPUT_DIR / "exalm_t1_discount_grid_exact_vs_he2.md"

BASELINE_REQUIRED_FIELDS = ["data_prep_shared", "fit", "post", "validate", "report"]

CSV_FIELDS = [
    "cutoff",
    "discount_set",
    "run_id",
    "status",
    "apples_to_apples_contract",
    "exact_copy_mode",
    "shared_snapshot_matches_selected_source",
    "baseline_run_id",
    "baseline_crps",
    "probe_crps",
    "delta_vs_baseline",
    "is_better_than_baseline",
    "score_scale",
    "horizon_days",
    "n_valid",
    "df_t",
    "df_s1",
    "df_s2",
    "df_s67",
    "df_discrep",
    "lambda",
    "df_trans",
    "df_covs",
]


@dataclass(frozen=True)
class ScoreSummary:
    mean_crps: float
    score_scale: str
    horizon_days: str
    n_valid: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return yaml.safe_load(handle)


def format_float(value: float | None) -> str:
    if value is None:
        return ""
    if abs(value) >= 1e6:
        return f"{value:.6e}"
    return f"{value:.6f}"


def parse_bool(value: bool) -> str:
    return "True" if value else "False"


def stage_status(manifest: dict[str, Any]) -> str:
    stages = {k: (v or {}).get("status") for k, v in (manifest.get("stages") or {}).items()}
    if all(stages.get(field) == "pass" for field in BASELINE_REQUIRED_FIELDS):
        return "pass"
    if manifest.get("status") == "failed" or any(status == "failed" for status in stages.values()):
        return "failed"
    if any(status in {"pending", "running"} for status in stages.values()):
        return "running"
    return "not_started"


def score_table_path(run_root: Path, run_id: str) -> Path:
    return run_root / "post" / "outputs" / run_id / "tables" / "crps_forecast_summary.csv"


def load_score_summary(path: Path, *, model_variant: str) -> ScoreSummary:
    rows = read_csv(path)
    for row in rows:
        if row.get("model_variant") == model_variant:
            return ScoreSummary(
                mean_crps=float(row["mean_crps"]),
                score_scale=row["score_scale"],
                horizon_days=row["horizon_days"],
                n_valid=row["n_valid"],
            )
    raise ValueError(f"Missing model_variant={model_variant} in {path}")


def selected_source_root(selected_source_config: str) -> Path:
    return Path(selected_source_config).parent / "inputs" / "shared"


def baseline_score_from_plan_row(row: dict[str, str]) -> ScoreSummary:
    baseline_run_id = row["selected_source_run"]
    baseline_run_root = Path(row["selected_source_config"]).parent
    table = score_table_path(baseline_run_root, baseline_run_id)
    if table.exists():
        return load_score_summary(table, model_variant="exdqlm_multivar_keep")
    return ScoreSummary(
        mean_crps=float(row["selected_mean_crps"]),
        score_scale="",
        horizon_days="",
        n_valid="",
    )


def row_state_evolution(resolved_cfg: dict[str, Any]) -> dict[str, str]:
    state = ((resolved_cfg.get("debug_exalm_t1_discount_grid") or {}).get("state_evolution") or {})
    return {key: str(state.get(key, "")) for key in ("df_t", "df_s1", "df_s2", "df_s67", "df_discrep", "lambda", "df_trans", "df_covs")}


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for plan_row in read_csv(MATRIX_PLAN):
        run_id = plan_row["run_id"]
        run_root = CAMPAIGN_ROOT / "runs" / run_id
        manifest_path = run_root / "run_manifest.yaml"
        manifest = load_yaml(manifest_path) if manifest_path.exists() else {}
        status = stage_status(manifest) if manifest else "not_started"

        resolved_cfg_path = run_root / "resolved_config.yaml"
        resolved_cfg = load_yaml(resolved_cfg_path) if resolved_cfg_path.exists() else {}
        state = row_state_evolution(resolved_cfg)

        baseline = baseline_score_from_plan_row(plan_row)
        probe_score: ScoreSummary | None = None
        probe_table = score_table_path(run_root, run_id)
        if probe_table.exists():
            probe_score = load_score_summary(probe_table, model_variant="exdqlm_multivar_keep")

        shared_snapshot = manifest.get("shared_snapshot") or {}
        source_root = str(shared_snapshot.get("source_root") or "")
        expected_root = str(selected_source_root(plan_row["selected_source_config"]))
        exact_copy_mode = shared_snapshot.get("mode") == "exact_copy"
        source_match = source_root == expected_root if source_root else False
        apples_to_apples = exact_copy_mode and source_match

        delta = None
        better = ""
        if probe_score is not None:
            delta = probe_score.mean_crps - baseline.mean_crps
            better = parse_bool(probe_score.mean_crps < baseline.mean_crps)

        rows.append(
            {
                "cutoff": plan_row["cutoff"],
                "discount_set": plan_row["discount_set"],
                "run_id": run_id,
                "status": status,
                "apples_to_apples_contract": parse_bool(apples_to_apples),
                "exact_copy_mode": parse_bool(exact_copy_mode),
                "shared_snapshot_matches_selected_source": parse_bool(source_match),
                "baseline_run_id": plan_row["selected_source_run"],
                "baseline_crps": format_float(baseline.mean_crps),
                "probe_crps": format_float(probe_score.mean_crps if probe_score else None),
                "delta_vs_baseline": format_float(delta),
                "is_better_than_baseline": better,
                "score_scale": probe_score.score_scale if probe_score else baseline.score_scale,
                "horizon_days": probe_score.horizon_days if probe_score else baseline.horizon_days,
                "n_valid": probe_score.n_valid if probe_score else baseline.n_valid,
                **state,
            }
        )
    return rows


def write_csv(rows: list[dict[str, str]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    sep = "|---" * len(headers) + "|"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, sep, *body])


def build_markdown(rows: list[dict[str, str]]) -> str:
    counts = {"pass": 0, "running": 0, "failed": 0, "not_started": 0}
    for row in rows:
        counts[row["status"]] += 1

    started_rows = [row for row in rows if row["status"] != "not_started"]
    exact_contract_ok = sum(row["apples_to_apples_contract"] == "True" for row in started_rows)

    summary_rows = [
        [status, str(count), format_float((count / len(rows)) * 100.0)]
        for status, count in counts.items()
    ]

    cutoff_best_rows: list[list[str]] = []
    for cutoff in sorted({row["cutoff"] for row in rows}):
        cutoff_rows = [row for row in rows if row["cutoff"] == cutoff and row["probe_crps"]]
        if not cutoff_rows:
            cutoff_best_rows.append([cutoff, rows[0]["baseline_crps"], "", "", "No completed probe rows yet"])
            continue
        best_probe = min(cutoff_rows, key=lambda row: float(row["probe_crps"]))
        baseline_crps = next(row["baseline_crps"] for row in rows if row["cutoff"] == cutoff)
        better_flag = "Yes" if best_probe["is_better_than_baseline"] == "True" else "No"
        cutoff_best_rows.append(
            [
                cutoff,
                baseline_crps,
                best_probe["discount_set"],
                best_probe["probe_crps"],
                f"{best_probe['delta_vs_baseline']} ({better_flag})",
            ]
        )

    detail_rows = []
    for row in sorted(rows, key=lambda item: (item["cutoff"], item["discount_set"])):
        detail_rows.append(
            [
                row["cutoff"],
                row["discount_set"],
                row["status"],
                row["apples_to_apples_contract"],
                row["baseline_crps"],
                row["probe_crps"] or "",
                row["delta_vs_baseline"] or "",
                row["is_better_than_baseline"] or "",
                row["df_t"],
                row["df_discrep"],
                row["df_covs"],
            ]
        )

    return f"""# exAL-M-T1 Exact-Input Discount Grid Comparison

This report compares the current HE-table `exAL-M-T1` baseline against the **exact-input** discount-grid reruns under `multimodel_v8_exalm_t1_discount_grid_exact_20260424`.

Comparison contract:
- baseline rows are the current HE `exAL-M-T1` source runs selected in the completed featurecov cf1 epsilon sweep
- probe rows are read from the exact-input discount-grid reruns
- both sides use the same run-local `crps_forecast_summary.csv` metric for `model_variant=exdqlm_multivar_keep`
- the exact-input campaign is considered apples-to-apples when:
  - `shared_snapshot.mode == exact_copy`
  - the preserved `shared_snapshot.source_root` matches the selected HE source `inputs/shared` root

Contract check:
- rows in grid: **{len(rows)}**
- started rows already verified as exact-copy apples-to-apples: **{exact_contract_ok} / {len(started_rows)}**

Current campaign status:
{markdown_table(['Status', 'Rows', 'Percent'], summary_rows)}

Current best completed challenger by cutoff:
{markdown_table(['Cutoff', 'HE baseline CRPS', 'Best completed set', 'Best completed probe CRPS', 'Delta vs HE'], cutoff_best_rows)}

Detailed row-level comparison:
{markdown_table(['Cutoff', 'Set', 'Status', 'Exact-copy', 'HE baseline', 'Probe CRPS', 'Delta', 'Better than HE', 'df_t', 'df_discrep', 'df_covs'], detail_rows)}
"""


def main() -> int:
    rows = build_rows()
    write_csv(rows)
    MD_OUT.write_text(build_markdown(rows), encoding="utf-8")
    print(f"Wrote {CSV_OUT}")
    print(f"Wrote {MD_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_CSV = ROOT / "reports" / "he2_publication_manifest" / "he2_bayesian_publication_manifest.csv"
ALIGNMENT_CSV = ROOT / "reports" / "he2_publication_manifest" / "he2_bayesian_publication_alignment.csv"
HISTORICAL_AUDIT_CSV = (
    ROOT
    / "reports"
    / "he2_publication_manifest"
    / "historical_support_audit_20260507"
    / "historical_support_audit.csv"
)
OUT_CSV = ROOT / "reports" / "publication_replay" / "he2_bayesian_full_relaunch_matrix_20260510.csv"
OUT_JSON = ROOT / "reports" / "publication_replay" / "he2_bayesian_full_relaunch_matrix_20260510.json"
OUT_MD = ROOT / "repro" / "run" / "HE2_BAYESIAN_FULL_RELAUNCH_TRACKER_20260510.md"


@dataclass(frozen=True)
class RowAudit:
    cutoff: str
    manuscript_label: str
    family: str
    campaign_lineage: str
    run_id: str
    crps_display4: str
    effective_common_start: str
    full_history_from_1987: bool
    within_cutoff_shared_inputs_aligned: bool


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


def _load_historical_audit() -> dict[tuple[str, str], RowAudit]:
    rows = _read_csv(HISTORICAL_AUDIT_CSV)
    out: dict[tuple[str, str], RowAudit] = {}
    for row in rows:
        key = (row["cutoff"], row["manuscript_label"])
        out[key] = RowAudit(
            cutoff=row["cutoff"],
            manuscript_label=row["manuscript_label"],
            family=row["family"],
            campaign_lineage=row["campaign_lineage"],
            run_id=row["run_id"],
            crps_display4=row["crps_display4"],
            effective_common_start=row["effective_common_start"],
            full_history_from_1987=_bool(row["full_history_from_1987"]),
            within_cutoff_shared_inputs_aligned=_bool(row["within_cutoff_shared_inputs_aligned"]),
        )
    return out


def _load_alignment_by_cutoff() -> dict[str, dict[str, str]]:
    rows = _read_csv(ALIGNMENT_CSV)
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for row in rows:
        cutoff = row["cutoff"]
        artifact = row["artifact"]
        out[cutoff][artifact] = row["all_equal"]
    return out


def _row_kind(family: str) -> str:
    if family.startswith("ndlm_"):
        return "ndlm"
    if "univar" in family:
        return "quantile_univariate"
    return "quantile_multivariate"


def _quantile_submodels(family: str) -> int:
    return 1 if family.startswith("ndlm_") else 7


def _transfer_mode(label: str) -> str:
    if label.endswith("-T0"):
        return "drop"
    if label.endswith("-T1"):
        return "keep"
    return ""


def _likelihood_mode(label: str) -> str:
    if label.startswith("N-"):
        return "normal"
    if label.startswith("AL-"):
        return "al"
    if label.startswith("exAL-"):
        return "exal"
    return ""


def _spec_token(row: dict[str, str]) -> str:
    run_id = row["run_id"]
    campaign = row["campaign_lineage"]
    if campaign.startswith("featurecov_cf1_eps_sweep_20260416"):
        parts = run_id.split("_")
        for part in parts:
            if part.startswith("eps") and part.endswith("cf1"):
                return part
        return "featurecov_cf1_selected"
    if campaign.startswith("exalm_t1_discount_grid_exact_20260424"):
        if "_set" in run_id:
            return "set" + run_id.split("_set", 1)[1].split("_", 1)[0]
        return "set09"
    if campaign.startswith("univar_featurecov_he2_rerun_20260422"):
        return "univar_featurecov_he2_v1"
    if campaign.startswith("ndlm_featurecov_rerun_postfix_20260421"):
        return "ndlm_featurecov_v1_postfix"
    return campaign


def _current_bundle_status(full_history_from_1987: bool) -> str:
    return "full_history" if full_history_from_1987 else "short_history"


def _relaunch_reason(row: dict[str, str], audit: RowAudit) -> str:
    reasons = ["canonical_GDPC1_replacement"]
    if not audit.full_history_from_1987:
        reasons.append("restore_1987_full_history")
    reasons.append("within_cutoff_shared_bundle_refresh")
    if row["campaign_lineage"].startswith("exalm_t1_discount_grid_exact_20260424"):
        reasons.append("preserve_selected_discount_profile")
    return "|".join(reasons)


def _target_bundle_slug(cutoff: str) -> str:
    return f"cutoff_{cutoff}_canonical_shared_bundle"


def build_matrix() -> tuple[list[dict[str, str]], dict[str, object]]:
    manifest_rows = _read_csv(MANIFEST_CSV)
    hist_audit = _load_historical_audit()
    alignment = _load_alignment_by_cutoff()

    matrix_rows: list[dict[str, str]] = []
    for row in manifest_rows:
        key = (row["cutoff"], row["manuscript_label"])
        audit = hist_audit[key]
        family = row["family"]
        kind = _row_kind(family)
        matrix_rows.append(
            {
                "cutoff": row["cutoff"],
                "cutoff_display": row["cutoff_display"],
                "manuscript_label": row["manuscript_label"],
                "family": family,
                "row_kind": kind,
                "campaign_lineage": row["campaign_lineage"],
                "current_run_id": row["run_id"],
                "current_crps_display4": row["crps_display4"],
                "likelihood_mode": _likelihood_mode(row["manuscript_label"]),
                "transfer_mode": _transfer_mode(row["manuscript_label"]),
                "selected_spec_token": _spec_token(row),
                "fit_covariate_names_current": row["fit_covariate_names"],
                "fit_covariate_names_target": "PPT|SOIL|GDPC1(alias:PCA)",
                "effective_common_start_current": audit.effective_common_start,
                "full_history_from_1987_current": str(audit.full_history_from_1987),
                "within_cutoff_shared_inputs_aligned_current": str(audit.within_cutoff_shared_inputs_aligned),
                "current_bundle_status": _current_bundle_status(audit.full_history_from_1987),
                "target_bundle_slug": _target_bundle_slug(row["cutoff"]),
                "target_bundle_contract": "shared_across_all_9_rows_within_cutoff",
                "target_retros_window": f"1987-05-29_to_{row['cutoff']}",
                "target_forecast_window": "shared_within_cutoff",
                "quantile_submodels": str(_quantile_submodels(family)),
                "requires_rerun": "True",
                "relaunch_reason": _relaunch_reason(row, audit),
            }
        )

    matrix_rows.sort(key=lambda r: (r["cutoff"], r["manuscript_label"]))

    workload = {
        "row_launches": len(matrix_rows),
        "ndlm_rows": sum(1 for row in matrix_rows if row["row_kind"] == "ndlm"),
        "quantile_rows": sum(1 for row in matrix_rows if row["row_kind"] != "ndlm"),
        "quantile_submodels": sum(int(row["quantile_submodels"]) for row in matrix_rows if row["row_kind"] != "ndlm"),
        "ndlm_submodels": sum(int(row["quantile_submodels"]) for row in matrix_rows if row["row_kind"] == "ndlm"),
        "total_submodels": sum(int(row["quantile_submodels"]) for row in matrix_rows),
    }
    cutoff_summary: dict[str, dict[str, object]] = {}
    for cutoff in sorted({row["cutoff"] for row in matrix_rows}):
        cutoff_rows = [row for row in matrix_rows if row["cutoff"] == cutoff]
        cutoff_summary[cutoff] = {
            "rows": len(cutoff_rows),
            "families": [row["family"] for row in cutoff_rows],
            "full_history_current": all(row["full_history_from_1987_current"] == "True" for row in cutoff_rows),
            "artifacts_all_equal": alignment.get(cutoff, {}),
        }
    metadata = {
        "manifest_csv": str(MANIFEST_CSV),
        "alignment_csv": str(ALIGNMENT_CSV),
        "historical_audit_csv": str(HISTORICAL_AUDIT_CSV),
        "workload": workload,
        "cutoff_summary": cutoff_summary,
        "campaign_counts": Counter(row["campaign_lineage"] for row in matrix_rows),
    }
    return matrix_rows, metadata


def _write_csv(path: Path, rows: Iterable[dict[str, str]]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("No rows to write.")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _render_markdown(rows: list[dict[str, str]], meta: dict[str, object]) -> str:
    workload = meta["workload"]
    cutoff_summary = meta["cutoff_summary"]
    campaign_counts = meta["campaign_counts"]

    lines: list[str] = []
    lines.append("# HE2 Bayesian Full Relaunch Tracker")
    lines.append("")
    lines.append("Date: 2026-05-10")
    lines.append("")
    lines.append("## Purpose")
    lines.append("")
    lines.append("This tracker freezes the prelaunch contract for the **full 45-row HE2 Bayesian relaunch** after the canonical GDPC1 replacement.")
    lines.append("")
    lines.append("The goal is to preserve the current published row-level model specifications while replacing the shared-input lineage so that:")
    lines.append("")
    lines.append("- every row uses the canonical `GDPC1` covariate through the existing `PCA` alias path")
    lines.append("- every row within a cutoff shares the **same** observational and forecast-window bundle")
    lines.append("- retrospective support runs from `1987-05-29` through the cutoff for every row")
    lines.append("- prelaunch validation proves the cutoff bundle is hash-identical across the 9 rows")
    lines.append("")
    lines.append("## Source of truth")
    lines.append("")
    lines.append(f"- publication manifest: `{MANIFEST_CSV}`")
    lines.append(f"- within-cutoff alignment audit: `{ALIGNMENT_CSV}`")
    lines.append(f"- historical-support audit: `{HISTORICAL_AUDIT_CSV}`")
    lines.append("")
    lines.append("## Workload summary")
    lines.append("")
    lines.append(f"- row launches: `{workload['row_launches']}`")
    lines.append(f"- quantile row launches: `{workload['quantile_rows']}`")
    lines.append(f"- NDLM row launches: `{workload['ndlm_rows']}`")
    lines.append(f"- quantile submodels: `{workload['quantile_submodels']}`")
    lines.append(f"- NDLM submodels: `{workload['ndlm_submodels']}`")
    lines.append(f"- total fitted submodels: `{workload['total_submodels']}`")
    lines.append("")
    lines.append("## Current publication freeze by campaign lineage")
    lines.append("")
    lines.append("| Campaign lineage | Rows |")
    lines.append("|---|---:|")
    for campaign, count in sorted(campaign_counts.items()):
        lines.append(f"| `{campaign}` | `{count}` |")
    lines.append("")
    lines.append("## Why all 45 rows need relaunch")
    lines.append("")
    lines.append("1. The canonical climate factor is now `GDPC1`, replacing the old frozen PCA-like artifact.")
    lines.append("2. The current publication rows still point at four older campaign lineages whose builders rewrite inputs from older `resolved_config.yaml` snapshots.")
    lines.append("3. Three cutoffs (`20210123`, `20211112`, `20221225`) still use short-history effective retrospective support across all 9 rows within the cutoff.")
    lines.append("4. Even the two full-history cutoffs (`20211221`, `20220511`) still need reruns so that the fit covariate lineage is the canonical GDPC-backed one and the within-cutoff bundles are rebuilt under one explicit contract.")
    lines.append("")
    lines.append("## Cutoff-level bundle status")
    lines.append("")
    lines.append("| Cutoff | Rows | Full 1987 history currently? | Required action |")
    lines.append("|---|---:|---|---|")
    for cutoff, summary in cutoff_summary.items():
        full_history = "Yes" if summary["full_history_current"] else "No"
        action = "refresh_GDPC_only" if summary["full_history_current"] else "rebuild_full_history_and_refresh_GDPC"
        lines.append(f"| `{cutoff}` | `{summary['rows']}` | `{full_history}` | `{action}` |")
    lines.append("")
    lines.append("## Builder surfaces that must be rewired before launch")
    lines.append("")
    lines.append("- `scripts/build_multimodel_v8_featurecov_cf1_eps_matrix_configs.py`")
    lines.append("- `scripts/build_multimodel_v8_all9_feature_matrix_configs.py`")
    lines.append("- `scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py`")
    lines.append("")
    lines.append("These builders currently materialize each run by copying fit/forecast/covariate paths from an older `selected_source_config` / `resolved_config.yaml` snapshot.")
    lines.append("")
    lines.append("Relevant functions:")
    lines.append("")
    lines.append("- `_rewrite_inputs_from_source_snapshot(...)`")
    lines.append("- `_rewrite_fit_covariates_from_source_snapshot(...)`")
    lines.append("")
    lines.append("For the full relaunch, those rewrites should target a **new canonical per-cutoff shared bundle**, not the old source-run snapshots.")
    lines.append("")
    lines.append("## Required canonical shared-bundle contract per cutoff")
    lines.append("")
    lines.append("Every one of the 9 rows within a cutoff must point to the same versions of:")
    lines.append("")
    lines.append("- `parameters.txt`")
    lines.append("- `retros.csv`")
    lines.append("- `nws_forecast.csv`")
    lines.append("- `glofas_forecast.csv`")
    lines.append("- `usgs_daily.csv`")
    lines.append("- `cov_01_PPT.csv`")
    lines.append("- `cov_02_SOIL.csv`")
    lines.append("- `cov_03_PCA.csv` or `cov_05_PCA.csv` as the compatibility alias to canonical `GDPC1`")
    lines.append("- `covariate_features.csv`")
    lines.append("- deterministic climate future precip bundle")
    lines.append("- deterministic climate future soil bundle")
    lines.append("")
    lines.append("## Prelaunch validation gates")
    lines.append("")
    lines.append("1. Per cutoff, hash all shared-input artifacts above across the 9 row configs and require `all_equal = True`.")
    lines.append("2. Require `effective_common_start = 1987-05-29` in `inputs/shared/data_start_filter_summary.txt` for every row.")
    lines.append("3. Require fit covariates to resolve to `PPT|SOIL|PCA`, where `PCA` is now the canonical `GDPC1` compatibility alias.")
    lines.append("4. Require deterministic-climate and engineered-covariate feature flags to remain enabled exactly as in the publication freeze.")
    lines.append("5. Require one smoke run per family against the new shared bundle contract before launching the full matrix.")
    lines.append("")
    lines.append("## Row-level relaunch matrix")
    lines.append("")
    lines.append("| Cutoff | Label | Family | Campaign | Current CRPS | Current start | Full history? | Selected spec | Submodels |")
    lines.append("|---|---|---|---|---:|---|---|---|---:|")
    for row in rows:
        lines.append(
            f"| `{row['cutoff_display']}` | `{row['manuscript_label']}` | `{row['family']}` | `{row['campaign_lineage']}` | `{row['current_crps_display4']}` | `{row['effective_common_start_current']}` | `{row['full_history_from_1987_current']}` | `{row['selected_spec_token']}` | `{row['quantile_submodels']}` |"
        )
    lines.append("")
    lines.append("## Recommended next implementation order")
    lines.append("")
    lines.append("1. Build five canonical shared bundles, one per cutoff.")
    lines.append("2. Patch the three matrix builders so they consume those bundles instead of older source-run snapshots.")
    lines.append("3. Add a dedicated prelaunch validator for the full 45-row relaunch contract.")
    lines.append("4. Regenerate the 45-row matrix from the publication freeze and confirm hash-equality within each cutoff.")
    lines.append("5. Smoke-test one row per family against the new bundle contract.")
    lines.append("6. Only then launch the full 45-row rerun campaign.")
    lines.append("")
    lines.append("## Machine-readable outputs")
    lines.append("")
    lines.append(f"- CSV: `{OUT_CSV}`")
    lines.append(f"- JSON: `{OUT_JSON}`")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    rows, meta = build_matrix()
    _write_csv(OUT_CSV, rows)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"rows": rows, "metadata": meta}, indent=2), encoding="utf-8")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(_render_markdown(rows, meta), encoding="utf-8")
    print(f"wrote_csv={OUT_CSV}")
    print(f"wrote_json={OUT_JSON}")
    print(f"wrote_md={OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path("/data/muscat_data/jaguir26/project1_ucsc_phd")
OUT_ROOT = ROOT / "reports" / "he2_master_workflow_audit_20260517"
OUT_ROOT.mkdir(parents=True, exist_ok=True)

EXAL_KEEP_MATRIX = ROOT / "project1_ucsc_phd_runtime_placeholder"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def exists(path: Path) -> bool:
    return path.exists()


def load_matrix(path: Path) -> list[dict[str, str]]:
    return read_csv(path) if path.exists() else []


EXAL_KEEP_MATRIX = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/"
    "control/publication_relaunch_matrix/matrix_status.csv"
)
EXAL_DROP_MATRIX = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516/"
    "control/publication_relaunch_matrix/matrix_status.csv"
)
EXAL_UNIVAR_MATRIX = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516/"
    "control/publication_relaunch_matrix/matrix_status.csv"
)
AL_UNIVAR_MATRIX = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_dqlm_univar_al_all_cutoffs_sharedspec_20260517/"
    "control/publication_relaunch_matrix/matrix_status.csv"
)
EXAL_AUDIT_SUMMARY = ROOT / "reports/he2_exal_revised_doc_audit_20260517/summary.json"
CRPS_TABLE_READINESS = ROOT / "reports/he2_crps_table_readiness_20260517/crps_table_readiness.json"
NDLM_MATRIX = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/matrix_status.csv"
)
NDLM_RUNS_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_ndlm_featurecov_rerun_20260420/runs"
)
CURRENT_CANONICAL_SHARED_ROOT = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_publication_shared_inputs_20260510"
)

ARTICLE_LINEAGE_SUMMARY = ROOT / "Evironmetrics---REVISED-DOC-2/reports/article_figure_lineage_audit_20260516/summary.json"
ARTICLE_SUPPORT_BACKGROUND_STATUS = ROOT / "reports/current_model_output_support_contract_audit_20260517/background_refresh_status.json"
ARTICLE_SUPPORT_AUDIT = ROOT / "reports/current_model_output_support_contract_audit_20260517/current_model_output_support_contract_audit_20260517.json"
PUBLICATION_MANIFEST_MD = ROOT / "reports/he2_publication_manifest/he2_bayesian_publication_manifest.md"
NDLM_AUDIT_TRACKER = ROOT / "repro/TRACKER_NDLM_PARITY_AUDIT.md"
AL_KEEP_FAIL_LOG = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_dqlm_multivar_al_keep_20221225_q65_prodclone_diagnostic_20260517/"
    "control/prelaunch_validation_prodclone_20221225_q65_20260517/"
    "fit_smoke_dqlm_multivar_al_keep_20221225_qsubset.stderr.log"
)
AL_DROP_FAIL_LOG = Path(
    "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/"
    "multimodel_v8_he2_dqlm_multivar_al_drop_20221225_q65_prodclone_diagnostic_20260517/"
    "control/prelaunch_validation_prodclone_20221225_q65_20260517/"
    "fit_smoke_dqlm_multivar_al_drop_20221225_qsubset.stderr.log"
)


def matrix_summary(rows: list[dict[str, str]]) -> dict[str, object]:
    if not rows:
        return {"cutoffs_total": 0, "cutoffs_passed": 0, "active_rows": [], "all_passed": False}
    passed = [r for r in rows if r.get("status") == "pass"]
    active = [r for r in rows if r.get("note") == "in_progress" or r.get("status") == "pending"]
    return {
        "cutoffs_total": len(rows),
        "cutoffs_passed": len(passed),
        "active_rows": active,
        "all_passed": len(passed) == len(rows),
    }


def fail_log_status(path: Path) -> tuple[str, str]:
    if not path.exists():
        return ("not_run", "No prodclone failure log found.")
    text = path.read_text(encoding="utf-8", errors="replace")
    if "FIT_FORECAST_HEALTH_FAIL" in text:
        last = ""
        for line in text.splitlines():
            if "FIT_FORECAST_HEALTH_FAIL" in line:
                last = line.strip()
        return ("failed", last or "Forecast-health validator failure present.")
    return ("unknown", "Prodclone log exists but no failure token was found.")


def publication_manifest_state() -> str:
    text = PUBLICATION_MANIFEST_MD.read_text(encoding="utf-8")
    if "featurecov_cf1_eps_sweep_20260416" in text or "univar_featurecov_he2_rerun_20260422" in text:
        return "legacy_publication_manifest_still_points_to_pre-relaunch_sources"
    return "publication_manifest_already_switched"


def read_source_map(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    if not path.exists():
        return payload
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            payload[k] = v
    return payload


def build_ndlm_lineage_rows(ndlm_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in ndlm_rows:
        run_id = row["run_id"]
        sm = NDLM_RUNS_ROOT / run_id / "inputs/shared/source_map.txt"
        payload = read_source_map(sm)
        retros = payload.get("source.retros", "")
        nws = payload.get("source.nws", "")
        glofas = payload.get("source.glofas", "")
        rows.append(
            {
                "cutoff": row.get("cutoff", ""),
                "lane": row.get("lane", ""),
                "run_id": run_id,
                "retros_path": retros,
                "nws_path": nws,
                "glofas_path": glofas,
                "retros_root_group": str(Path(retros).parent.parent.parent.parent.parent) if retros else "",
                "aligned_to_20260510_canonical_shared_bundle": str(retros.startswith(str(CURRENT_CANONICAL_SHARED_ROOT))).lower(),
            }
        )
    return rows


def main() -> int:
    exal_keep = load_matrix(EXAL_KEEP_MATRIX)
    exal_drop = load_matrix(EXAL_DROP_MATRIX)
    exal_univar = load_matrix(EXAL_UNIVAR_MATRIX)
    al_univar = load_matrix(AL_UNIVAR_MATRIX)
    ndlm = load_matrix(NDLM_MATRIX)

    exal_keep_summary = matrix_summary(exal_keep)
    exal_drop_summary = matrix_summary(exal_drop)
    exal_univar_summary = matrix_summary(exal_univar)
    al_univar_summary = matrix_summary(al_univar)
    ndlm_summary = matrix_summary(ndlm)

    al_keep_status, al_keep_note = fail_log_status(AL_KEEP_FAIL_LOG)
    al_drop_status, al_drop_note = fail_log_status(AL_DROP_FAIL_LOG)
    ndlm_lineage_rows = build_ndlm_lineage_rows(ndlm)
    ndlm_bundle_aligned = all(row["aligned_to_20260510_canonical_shared_bundle"] == "true" for row in ndlm_lineage_rows)
    ndlm_unique_roots = sorted({row["retros_root_group"] for row in ndlm_lineage_rows if row["retros_root_group"]})

    article_lineage = read_json(ARTICLE_LINEAGE_SUMMARY) if exists(ARTICLE_LINEAGE_SUMMARY) else {}
    article_support_background = read_json(ARTICLE_SUPPORT_BACKGROUND_STATUS) if exists(ARTICLE_SUPPORT_BACKGROUND_STATUS) else {}
    article_support_audit = read_json(ARTICLE_SUPPORT_AUDIT) if exists(ARTICLE_SUPPORT_AUDIT) else {}
    exal_audit_summary = read_json(EXAL_AUDIT_SUMMARY) if exists(EXAL_AUDIT_SUMMARY) else {}
    crps_readiness = read_json(CRPS_TABLE_READINESS) if exists(CRPS_TABLE_READINESS) else {}

    family_rows = [
        {
            "label": "exAL-M-T1",
            "family": "exdqlm_multivar_keep",
            "mode": "exAL",
            "shape": "multivar_keep",
            "authoritative_state": "production_complete",
            "cutoffs_passed": f"{exal_keep_summary['cutoffs_passed']}/{exal_keep_summary['cutoffs_total']}",
            "quantile_contract": "q05,q20,q35,q50,q65,q80,q95",
            "current_status": "authoritative_complete",
            "blocker": "",
            "notes": "Corrected shared-spec rerun complete.",
        },
        {
            "label": "exAL-M-T0",
            "family": "exdqlm_multivar_drop",
            "mode": "exAL",
            "shape": "multivar_drop",
            "authoritative_state": "production_complete",
            "cutoffs_passed": f"{exal_drop_summary['cutoffs_passed']}/{exal_drop_summary['cutoffs_total']}",
            "quantile_contract": "q05,q20,q35,q50,q65,q80,q95",
            "current_status": "authoritative_complete",
            "blocker": "",
            "notes": "Corrected shared-spec rerun complete.",
        },
        {
            "label": "exAL-U-T1",
            "family": "exdqlm_univar",
            "mode": "exAL",
            "shape": "univar",
            "authoritative_state": "production_complete",
            "cutoffs_passed": f"{exal_univar_summary['cutoffs_passed']}/{exal_univar_summary['cutoffs_total']}",
            "quantile_contract": "q05,q20,q35,q50,q65,q80,q95",
            "current_status": "authoritative_complete",
            "blocker": "",
            "notes": "Corrected shared-spec rerun complete.",
        },
        {
            "label": "AL-M-T1",
            "family": "dqlm_multivar_al_keep",
            "mode": "AL",
            "shape": "multivar_keep",
            "authoritative_state": "not_launched",
            "cutoffs_passed": "0/5",
            "quantile_contract": "q05,q20,q35,q50,q65,q80,q95",
            "current_status": "diagnostic_failed",
            "blocker": "20221225 q65 prodclone failed forecast-health validation.",
            "notes": al_keep_note,
        },
        {
            "label": "AL-M-T0",
            "family": "dqlm_multivar_al_drop",
            "mode": "AL",
            "shape": "multivar_drop",
            "authoritative_state": "not_launched",
            "cutoffs_passed": "0/5",
            "quantile_contract": "q05,q20,q35,q50,q65,q80,q95",
            "current_status": "diagnostic_failed",
            "blocker": "20221225 q65 prodclone failed forecast-health validation.",
            "notes": al_drop_note,
        },
        {
            "label": "AL-U-T1",
            "family": "dqlm_univar_al",
            "mode": "AL",
            "shape": "univar",
            "authoritative_state": "production_complete",
            "cutoffs_passed": f"{al_univar_summary['cutoffs_passed']}/{al_univar_summary['cutoffs_total']}",
            "quantile_contract": "q05,q20,q35,q50,q65,q80,q95",
            "current_status": "authoritative_complete",
            "blocker": "",
            "notes": "Canonical AL univar shared-spec rerun complete across all five cutoffs.",
        },
        {
            "label": "N-M-T1",
            "family": "ndlm_main_keep",
            "mode": "normal",
            "shape": "ndlm_multivar_keep",
            "authoritative_state": "older_corrected_rerun_complete",
            "cutoffs_passed": "5/5",
            "quantile_contract": "single_model",
            "current_status": "completed_but_not_current_bundle_aligned",
            "blocker": "NDLM rerun does not yet use the current 20260510 canonical shared bundle lineage.",
            "notes": "Corrected NDLM featurecov rerun complete, but source_map still points to older input lineages.",
        },
        {
            "label": "N-M-T0",
            "family": "ndlm_main_drop",
            "mode": "normal",
            "shape": "ndlm_multivar_drop",
            "authoritative_state": "older_corrected_rerun_complete",
            "cutoffs_passed": "5/5",
            "quantile_contract": "single_model",
            "current_status": "completed_but_not_current_bundle_aligned",
            "blocker": "NDLM rerun does not yet use the current 20260510 canonical shared bundle lineage.",
            "notes": "Corrected NDLM featurecov rerun complete, but source_map still points to older input lineages.",
        },
        {
            "label": "N-U-T1",
            "family": "ndlm_univar_keep",
            "mode": "normal",
            "shape": "ndlm_univar",
            "authoritative_state": "older_corrected_rerun_complete",
            "cutoffs_passed": "5/5",
            "quantile_contract": "single_model",
            "current_status": "completed_but_not_current_bundle_aligned",
            "blocker": "NDLM rerun does not yet use the current 20260510 canonical shared bundle lineage.",
            "notes": "Corrected NDLM featurecov rerun complete, but source_map still points to older input lineages.",
        },
    ]

    cutoff_rows: list[dict[str, str]] = []
    for name, matrix_rows in [
        ("exdqlm_multivar_keep", exal_keep),
        ("exdqlm_multivar_drop", exal_drop),
        ("exdqlm_univar", exal_univar),
        ("dqlm_univar_al", al_univar),
        ("ndlm_featurecov", ndlm),
    ]:
        for row in matrix_rows:
            cutoff_rows.append(
                {
                    "family": name,
                    "cutoff": row.get("cutoff", ""),
                    "lane": row.get("lane", ""),
                    "phase": row.get("phase", ""),
                    "status": row.get("status", ""),
                    "note": row.get("note", ""),
                    "run_id": row.get("run_id", ""),
                }
            )

    summary = {
        "ultimate_goal": "Rebuild authoritative manuscript tables and figures from corrected run roots under one documented, reproducible workflow.",
        "canonical_contract": {
            "scale": "log1p",
            "retrospective_start": "1987-05-29",
            "forecast_alignment": "within-cutoff NWS and GloFAS versions must match the authoritative bundle audit",
            "covariates": ["PPT", "SOIL", "PCA(alias=GDPC1)"],
            "covariate_features": {
                "lags": [1, 2, 3],
                "include_squares": True,
                "include_interaction": True,
            },
            "deterministic_climate": "blended PPT/SOIL forecast contract where applicable",
            "debugging_policy": "warm-up and stabilization first; epsilon and c_factor only as last resort with explicit approval",
        },
        "publication_manifest_state": publication_manifest_state(),
        "al_q65_diag_processes_active": False,
        "ndlm_current_bundle_alignment": {
            "aligned_to_20260510_canonical_shared_bundle": ndlm_bundle_aligned,
            "unique_source_roots": ndlm_unique_roots,
        },
        "article_state": {
            "lineage_status_counts": article_lineage.get("status_counts", {}),
            "historical_support_background": article_support_background,
            "historical_support_contract_status": article_support_audit.get("status", ""),
            "exal_revised_doc_audit": exal_audit_summary,
            "crps_table_readiness": crps_readiness,
        },
        "families": family_rows,
    }

    with (OUT_ROOT / "family_tracker.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(family_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(family_rows)

    with (OUT_ROOT / "cutoff_tracker.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(cutoff_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(cutoff_rows)

    with (OUT_ROOT / "ndlm_lineage_tracker.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ndlm_lineage_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(ndlm_lineage_rows)

    (OUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    md: list[str] = []
    md.append("# HE2 Master Workflow Audit And Tracker\n\n")
    md.append("Date: 2026-05-17\n\n")
    md.append("## Purpose\n\n")
    md.append(
        "This document centralizes the current HE2 manuscript-rebuild state so we can clearly distinguish "
        "authoritative reruns, validation-only work, diagnostic failures, and article-repair lanes.\n\n"
    )
    md.append("## Your Ultimate Goal\n\n")
    md.append("- Rebuild the full CRPS table from authoritative rerun outputs.\n")
    md.append("- Rebuild the other manuscript tables, including ablation-style comparisons, from the same authoritative run roots.\n")
    md.append("- Refresh every manuscript figure from authoritative outputs and corrected input bundles.\n")
    md.append("- Keep the whole workflow reproducible, centralized, documented, and flexible enough to tune individual quantiles without losing provenance.\n")
    md.append("- Clean heavy fit artifacts after post when they are no longer needed, while preserving the retained artifacts required for manuscript reproduction.\n\n")
    md.append("## Canonical Contract We Are Trying To Enforce\n\n")
    md.append("- Scale: `log(x+1)`.\n")
    md.append("- Shared retrospective history: `1987-05-29 -> cutoff`.\n")
    md.append("- Forecast alignment: NWS + GloFAS versions must match within cutoff.\n")
    md.append("- Covariates: `PPT`, `SOIL`, `PCA(alias=GDPC1)`.\n")
    md.append("- Engineered covariate features: lags `1,2,3`, squares on, interactions on.\n")
    md.append("- Deterministic climate: blended forecast contract where applicable.\n")
    md.append("- Quantile debugging policy: warm-up/stabilization first; only then consider `epsilon` / `c_factor`, and only with explicit approval.\n\n")
    md.append("## Current Authoritative Family State\n\n")
    md.append("| Label | Family | Mode | Current state | Notes |\n")
    md.append("|---|---|---|---|---|\n")
    for row in family_rows:
        md.append(
            f"| `{row['label']}` | `{row['family']}` | `{row['mode']}` | `{row['current_status']}` | {row['notes'] or row['blocker']} |\n"
        )
    md.append("\n")
    md.append("## What Is Done\n\n")
    md.append("- `exdqlm_multivar_keep`, `exdqlm_multivar_drop`, and `exdqlm_univar` corrected shared-spec reruns are complete across all `5` cutoffs.\n")
    md.append("- `ndlm_main_keep`, `ndlm_main_drop`, and `ndlm_univar_keep` corrected featurecov reruns are complete across all `5` cutoffs, but they are **not yet** on the current `20260510` canonical shared bundle lineage.\n")
    md.append("- `dqlm_univar_al` canonical shared-spec rerun is complete across all `5` cutoffs.\n\n")
    md.append("## What Is Not Done\n\n")
    md.append("- `dqlm_multivar_al_keep` has **not** been launched as a production family.\n")
    md.append("- `dqlm_multivar_al_drop` has **not** been launched as a production family.\n")
    md.append("- The current manuscript-facing publication manifest still points to older pre-relaunch AL/exAL lineage for many table rows and should not yet be treated as the rebuilt final table source.\n")
    md.append("- The keep-side historical-support/current-model revised-doc figures are repaired and promoted through the retained-support replay contract.\n")
    md.append("- The benchmark CRPS table should remain frozen until NDLM is canonical, AL multivariate keep/drop are complete, and the exAL benchmark rows are reconciled.\n\n")
    md.append("## What Failed\n\n")
    md.append("- The AL multivariate late-cutoff diagnostic lane failed specifically at `20221225 q65`.\n")
    md.append(f"- `AL-M-T1`: {al_keep_note}\n")
    md.append(f"- `AL-M-T0`: {al_drop_note}\n")
    md.append("- These were diagnostic failures, not completed production reruns.\n\n")
    md.append("## AL q65 Diagnostic State\n\n")
    md.append("- There are no active AL q65 prodclone processes now.\n")
    md.append("- The keep/drop q65 lanes should be treated as stopped failed diagnostics, not as live work.\n\n")
    md.append("## NDLM Provenance Correction\n\n")
    md.append("- The NDLM rerun is **not** on the current `20260510` canonical shared-input bundle lineage.\n")
    md.append(f"- Unique NDLM retrospective source-root groups observed: `{', '.join(ndlm_unique_roots)}`.\n")
    md.append("- So NDLM should currently be classified as `completed older corrected rerun`, not `current canonical-bundle authoritative`.\n\n")
    md.append("## What Is Running Right Now\n\n")
    md.append("- No exAL/AL/NDLM q65 diagnostic processes are active now.\n")
    md.append("- No historical-support replay is still pending; that article-side repair is complete.\n\n")
    md.append("## Why The State Felt Messy\n\n")
    md.append("- Production reruns, no-launch validators, prodclone diagnostics, and article-repair replays ended up coexisting in the same time window.\n")
    md.append("- Some status reports are stale or validation-centric and do not distinguish clearly between `running`, `failed diagnostic`, and `authoritative production complete`.\n")
    md.append("- The publication manifest is a frozen manuscript-source report, not yet the final rebuilt authoritative-table tracker.\n")
    md.append("- The article figure tree is authoritative for the repaired exAL keep-side figures, but the benchmark table still depends on the frozen publication manifest.\n\n")
    md.append("## Policy Correction Going Forward\n\n")
    md.append("- Do **not** change `epsilon` / `c_factor` in active remediation without explicit approval.\n")
    md.append("- Treat warm-up / stabilization / initialization as the first-line quantile remediation path.\n")
    md.append("- Keep one central tracker for each family with four separate states: `authoritative production`, `validation-only`, `diagnostic`, `article integration`.\n")
    md.append("- Do not treat older publication-manifest rows as final once a corrected rerun exists.\n\n")
    md.append("## Article Integration State\n\n")
    md.append(f"- Figure lineage summary currently reports: `{article_lineage.get('status_counts', {})}`.\n")
    md.append("- Setup/support/context and synthesis families are already updated from corrected runtimes.\n")
    md.append(f"- Historical-support repair status: `{article_support_audit.get('status', 'unknown')}`.\n")
    md.append(f"- exAL benchmark reconciliation status: `{exal_audit_summary.get('final_certification', 'unknown')}`.\n")
    md.append(f"- CRPS benchmark-table readiness decision: `{crps_readiness.get('decision', 'unknown')}`.\n\n")
    md.append("## Immediate Next Actions\n\n")
    md.append("1. Keep the benchmark CRPS table frozen until the NDLM family set is relaunched on the canonical shared bundle.\n")
    md.append("2. Re-open the AL multivariate lane as an explicit warm-up/stabilization investigation, not as a silent epsilon retuning exercise.\n")
    md.append("3. Freeze this tracker as the central status spine instead of relying on the older publication manifest or chat memory.\n")
    md.append("4. Build the final authoritative CRPS/table export layer only after NDLM is canonical, AL multivariate keep/drop are complete, and the exAL benchmark reconciliation policy is explicit.\n")
    md.append("5. Add explicit heavy-artifact retention/cleanup policy by stage so the post-required objects are preserved and the rest can be deleted safely.\n")
    md.append("\n")
    md.append("## Outputs\n\n")
    md.append(f"- [family_tracker.csv]({OUT_ROOT / 'family_tracker.csv'})\n")
    md.append(f"- [cutoff_tracker.csv]({OUT_ROOT / 'cutoff_tracker.csv'})\n")
    md.append(f"- [ndlm_lineage_tracker.csv]({OUT_ROOT / 'ndlm_lineage_tracker.csv'})\n")
    md.append(f"- [summary.json]({OUT_ROOT / 'summary.json'})\n")

    (OUT_ROOT / "HE2_MASTER_WORKFLOW_AUDIT_AND_TRACKER_20260517.md").write_text("".join(md), encoding="utf-8")
    print(OUT_ROOT / "HE2_MASTER_WORKFLOW_AUDIT_AND_TRACKER_20260517.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

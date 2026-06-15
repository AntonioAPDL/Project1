#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from multimodel_v8_lib import ROOT, load_yaml
from forecast_design_contract import (
    ARTICLE_FORECAST_DESIGN_DOC_REL,
    FORBIDDEN_FORECAST_DESIGN_CLAIMS,
    FORECAST_DESIGN_CONTRACT_REL,
    FORECAST_DESIGN_MANIFEST_REL,
    REQUIRED_FORECAST_DESIGN_ARTICLE_CLAIMS,
    REQUIRED_FORECAST_DESIGN_CORRECTIONS_CLAIMS,
    check_forecast_design_manifest,
)
from latest_forecast_issue_contract import (
    ARTICLE_LATEST_FORECAST_ISSUE_DOC_REL,
    FORBIDDEN_LATEST_FORECAST_ARTICLE_CLAIMS,
    LATEST_FORECAST_ISSUE_CONTRACT_REL,
    LATEST_FORECAST_ISSUE_MANIFEST_REL,
    REQUIRED_LATEST_FORECAST_ARTICLE_CLAIMS,
    REQUIRED_LATEST_FORECAST_CORRECTIONS_CLAIMS,
    check_latest_forecast_issue_manifest,
)
from runtime_feasibility_contract import (
    ARTICLE_RUNTIME_DOC_REL,
    FORBIDDEN_RUNTIME_DECOMPOSITION_CLAIMS,
    REQUIRED_RUNTIME_ARTICLE_CLAIMS,
    REQUIRED_RUNTIME_CORRECTIONS_CLAIMS,
    RUNTIME_CONTRACT_REL,
    RUNTIME_MANIFEST_REL,
    check_runtime_manifest,
)
from software_availability_contract import (
    ARTICLE_SOFTWARE_DOC_REL,
    CRAN_EXDQLM_DOI_URL,
    CRAN_EXDQLM_URL,
    PROJECT1_URL,
    SOFTWARE_CONTRACT_REL,
    SOFTWARE_MANIFEST_REL,
    WORKFLOW_ARCHIVE_READINESS_REL,
    WORKFLOW_CITATION_REL,
    WORKFLOW_README_REL,
    WORKFLOW_RELEASE_NOTES_REL,
    WORKFLOW_RELEASE_READINESS_RELS,
    check_archive_status,
)


CUTOFF_ORDER = ["20210123", "20211112", "20211221", "20220511", "20221225"]
CUTOFF_DISPLAY = {
    "20210123": "01/23/2021",
    "20211112": "11/12/2021",
    "20211221": "12/21/2021",
    "20220511": "05/11/2022",
    "20221225": "12/25/2022",
}
HE3_VARIANTS = ["full", "noTrend", "noTF", "noH1", "noH2", "noH3"]
HE3_LABEL_BY_VARIANT = {
    "full": "exAL-M-T1 (full)",
    "noTrend": "exAL-M-T1-noTrend",
    "noTF": "exAL-M-noTF",
    "noH1": "exAL-M-T1-noH1",
    "noH2": "exAL-M-T1-noH2",
    "noH3": "exAL-M-T1-noH3",
}
TARGETED_REPAIR_LINEAGE = "he2_table1_targeted_repair_20260612:canonical_bundle_targeted_repair"
AUTHORITATIVE_KEEP_LINEAGE = "exdqlm_multivar_keep_canonical_grid_20260524:authoritative_winner"
DISPLAY_DIGITS = 5
DISPLAY_TOL = 0.5 * 10 ** (-DISPLAY_DIGITS)

NON_PROMOTED_WORSE_REPAIRS = {
    ("20210123", "exAL-U-T1"): 1.593758839350553,
    ("20210123", "N-M-T1"): 3.2149023502665646,
    ("20211112", "exAL-U-T1"): 1.3720641646044698,
    ("20211221", "exAL-U-T1"): 2.5629546886058745,
    ("20220511", "exAL-U-T1"): 1.2667703182160184,
    ("20221225", "exAL-M-T0"): 1.2113191493945392,
    ("20221225", "exAL-U-T1"): 3.595277539023264,
    ("20221225", "N-M-T1"): 3.8886290887278108,
}

SELECTED_MODEL_FIGURES = {
    "fig:dry_quantile",
    "fig:rainy_quantile",
    "fig:synth1",
    "fig:80_components",
}

@dataclass
class Check:
    family: str
    item: str
    status: str
    detail: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git_value(repo: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
    except Exception as exc:
        return f"ERROR: {exc}"


def add(checks: list[Check], family: str, item: str, ok: bool, detail: str) -> None:
    checks.append(Check(family, item, "pass" if ok else "fail", detail))


def as_float(value: object) -> float:
    return float(str(value).strip())


def same_display(expected: float, observed: float) -> bool:
    return abs(round(expected, DISPLAY_DIGITS) - observed) <= DISPLAY_TOL


def strip_tex(cell: str) -> str:
    text = cell.strip()
    previous = None
    while previous != text:
        previous = text
        text = re.sub(r"\\textbf\{([^{}]+)\}", r"\1", text)
        text = re.sub(r"\\textit\{([^{}]+)\}", r"\1", text)
        text = re.sub(r"\\texttt\{([^{}]+)\}", r"\1", text)
    return text.replace("$", "").replace("\\", "").strip()


def parse_numeric(cell: str) -> float:
    match = re.search(r"-?\d+(?:\.\d+)?", strip_tex(cell))
    if not match:
        raise ValueError(f"Could not parse numeric cell: {cell!r}")
    return float(match.group(0))


def parse_flat_tex(path: Path, expected_numeric_cells: int = 5) -> dict[str, list[float]]:
    rows: dict[str, list[float]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if "&" not in line or line.startswith("\\") or "\\multicolumn" in line:
            continue
        parts = [part.strip() for part in line.rstrip("\\").split("&")]
        if len(parts) != expected_numeric_cells + 1:
            continue
        label = strip_tex(parts[0])
        if label in {"Ablation model", "Model", "Model label"}:
            continue
        try:
            rows[label] = [parse_numeric(cell) for cell in parts[1:]]
        except ValueError:
            continue
    return rows


def mean_crps_for_leads(path: Path, *, model_id: str, horizon_days: int) -> float:
    rows = [
        row for row in read_csv(path)
        if row.get("model_id") == model_id and 1 <= int(row["lead_day"]) <= horizon_days
    ]
    leads = sorted(int(row["lead_day"]) for row in rows)
    expected = list(range(1, horizon_days + 1))
    if leads != expected:
        raise ValueError(f"Expected leads {expected} for model_id={model_id} in {path}; got {leads}")
    return sum(as_float(row["crps"]) for row in rows) / len(rows)


def keyed(rows: list[dict[str, str]], *cols: str) -> dict[tuple[str, ...], dict[str, str]]:
    out: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        out[tuple(str(row[col]).strip() for col in cols)] = row
    return out


def check_he2_selective_manifest(
    *,
    workflow_root: Path,
    article_root: Path,
    checks: list[Check],
) -> None:
    overlay = load_yaml(workflow_root / "config/he2_publication_manifest_replacement_overlay_table1_targeted_repair_20260612.yaml")
    replacements = overlay.get("replacements", [])
    overlay_keys = {(str(r["cutoff"]), str(r["manuscript_label"])) for r in replacements}
    add(checks, "he2_selective", "overlay_active", bool(overlay.get("active")), "overlay active flag")
    add(checks, "he2_selective", "overlay_replacement_count", len(replacements) == 16, f"{len(replacements)} replacements")
    add(
        checks,
        "he2_selective",
        "overlay_mentions_selective_policy",
        "promoted selectively" in str(overlay.get("publication_note", "")),
        "publication_note records selective policy",
    )

    manifest_path = article_root / "artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv"
    rows = read_csv(manifest_path)
    by_key = keyed(rows, "cutoff", "manuscript_label")
    targeted = {
        (r["cutoff"], r["manuscript_label"])
        for r in rows
        if r.get("campaign_lineage") == TARGETED_REPAIR_LINEAGE
    }
    add(checks, "he2_selective", "manifest_row_count", len(rows) == 45, f"{len(rows)} rows")
    add(checks, "he2_selective", "targeted_repair_count", len(targeted) == 16, f"{len(targeted)} targeted rows")
    add(
        checks,
        "he2_selective",
        "targeted_rows_match_overlay",
        targeted == overlay_keys,
        f"manifest={len(targeted)} overlay={len(overlay_keys)}",
    )

    for key, expected_crps in sorted(NON_PROMOTED_WORSE_REPAIRS.items()):
        row = by_key.get(key)
        label = f"{key[0]}:{key[1]}"
        add(checks, "he2_selective", f"{label}:present", row is not None, "fallback row present")
        if row is None:
            continue
        add(
            checks,
            "he2_selective",
            f"{label}:not_targeted_repair",
            row.get("campaign_lineage") != TARGETED_REPAIR_LINEAGE,
            row.get("campaign_lineage", ""),
        )
        add(
            checks,
            "he2_selective",
            f"{label}:fallback_crps",
            abs(as_float(row["crps_exact"]) - expected_crps) <= 1e-10,
            f"{as_float(row['crps_exact']):.12f}",
        )


def check_he3_authoritative(
    *,
    workflow_root: Path,
    article_root: Path,
    corrections_root: Path,
    he3_runtime_root: Path,
    checks: list[Check],
) -> None:
    winners = load_yaml(workflow_root / "docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml")["winners"]
    winner_by_cutoff = {str(row["cutoff"]): row for row in winners}
    add(checks, "he3_authority", "winner_cutoff_set", list(winner_by_cutoff) == CUTOFF_ORDER, ",".join(winner_by_cutoff))

    matrix_dir = he3_runtime_root / "control/he3_exdqlm_ablation_authoritative_winners_v1"
    status_rows = read_csv(matrix_dir / "matrix_status.csv")
    selection_rows = read_csv(matrix_dir / "selection_manifest.csv")
    status_counts: dict[str, int] = {}
    variant_counts: dict[str, int] = {}
    for row in status_rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
        variant_counts[row["variant"]] = variant_counts.get(row["variant"], 0) + 1
    add(checks, "he3_authority", "matrix_row_count", len(status_rows) == 30, f"{len(status_rows)} rows")
    add(checks, "he3_authority", "matrix_all_pass", status_counts == {"pass": 30}, json.dumps(status_counts, sort_keys=True))
    add(
        checks,
        "he3_authority",
        "variant_balance",
        variant_counts == {variant: 5 for variant in HE3_VARIANTS},
        json.dumps(variant_counts, sort_keys=True),
    )

    selection_by_key = keyed(selection_rows, "cutoff", "variant")
    wide_runtime = read_csv(he3_runtime_root / "reports/he3_exdqlm_ablation/he3_ablation_wide.csv")
    wide_article = read_csv(article_root / "artifacts/he3_exdqlm_ablation_authoritative/he3_ablation_wide.csv")
    runtime_key = keyed(wide_runtime, "cutoff", "variant")
    article_key = keyed(wide_article, "cutoff", "variant")
    add(checks, "he3_authority", "runtime_wide_row_count", len(wide_runtime) == 30, f"{len(wide_runtime)} rows")
    add(checks, "he3_authority", "article_wide_row_count", len(wide_article) == 30, f"{len(wide_article)} rows")

    for cutoff in CUTOFF_ORDER:
        winner = winner_by_cutoff[cutoff]
        full_sel = selection_by_key.get((cutoff, "full"))
        full_row = runtime_key.get((cutoff, "full"))
        label = CUTOFF_DISPLAY[cutoff]
        add(
            checks,
            "he3_authority",
            f"{cutoff}:full_source_run",
            full_sel is not None and full_sel.get("source_run_id") == winner["run_id"],
            full_sel.get("source_run_id", "missing") if full_sel else "missing",
        )
        add(
            checks,
            "he3_authority",
            f"{cutoff}:full_grid_spec",
            full_sel is not None and full_sel.get("best_epsilon_label") == winner["grid_spec_id"],
            full_sel.get("best_epsilon_label", "missing") if full_sel else "missing",
        )
        add(
            checks,
            "he3_authority",
            f"{cutoff}:full_crps_matches_winner",
            full_row is not None and abs(as_float(full_row["mean_crps"]) - as_float(winner["mean_crps"])) <= 1e-12,
            f"{label} full={as_float(full_row['mean_crps']):.12f}" if full_row else "missing",
        )
        meta_path = article_root / f"artifacts/five_cutoff_main_model_synthesis/{cutoff}_exal_m_t1/source_metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        add(checks, "he3_authority", f"{cutoff}:synthesis_run_id", meta.get("multivar_run_id") == winner["run_id"], meta.get("multivar_run_id", ""))
        add(checks, "he3_authority", f"{cutoff}:synthesis_grid", meta.get("grid_spec_id") == winner["grid_spec_id"], meta.get("grid_spec_id", ""))
        add(checks, "he3_authority", f"{cutoff}:synthesis_lineage", meta.get("source_lineage") == AUTHORITATIVE_KEEP_LINEAGE, meta.get("source_lineage", ""))

    for key, runtime_row in runtime_key.items():
        article_row = article_key.get(key)
        add(
            checks,
            "he3_authority",
            f"{key[0]}:{key[1]}:article_artifact_matches_runtime",
            article_row is not None and abs(as_float(article_row["mean_crps"]) - as_float(runtime_row["mean_crps"])) <= 1e-12,
            f"runtime={runtime_row.get('mean_crps')} article={article_row.get('mean_crps') if article_row else 'missing'}",
        )

    article_table = parse_flat_tex(article_root / "tables/generated_tex/he3_ablation_crps_main_table.tex")
    corrections_table = parse_flat_tex(corrections_root / "tables/generated_tex/he3_ablation_crps_response_table.tex")
    article_nws_table = parse_flat_tex(article_root / "tables/generated_tex/he3_ablation_crps_nws_horizon_table.tex")
    corrections_nws_table = parse_flat_tex(corrections_root / "tables/generated_tex/he3_ablation_crps_nws_horizon_response_table.tex")
    add(checks, "he3_authority", "article_table_excludes_nws_28day", "RAW-NWS" not in article_table, "NWS omitted from 28-day HE3 table")
    add(checks, "he3_authority", "corrections_table_excludes_nws_28day", "RAW-NWS" not in corrections_table, "NWS omitted from 28-day HE3 response table")
    add(checks, "he3_authority", "article_nws_horizon_includes_nws", "RAW-NWS" in article_nws_table, "NWS included in eight-day HE3 table")
    add(checks, "he3_authority", "corrections_nws_horizon_includes_nws", "RAW-NWS" in corrections_nws_table, "NWS included in eight-day HE3 response table")
    for variant in HE3_VARIANTS:
        label = HE3_LABEL_BY_VARIANT[variant]
        expected = [as_float(runtime_key[(cutoff, variant)]["mean_crps"]) for cutoff in CUTOFF_ORDER]
        observed = article_table.get(label)
        add(
            checks,
            "he3_authority",
            f"article_table:{label}",
            observed is not None and all(same_display(e, o) for e, o in zip(expected, observed)),
            "five-decimal rendered values",
        )
        corrections_observed = corrections_table.get(label)
        add(
            checks,
            "he3_authority",
            f"corrections_table:{label}",
            corrections_observed is not None and all(same_display(e, o) for e, o in zip(expected, corrections_observed)),
            "five-decimal rendered values",
        )
        expected_nws_horizon = []
        for cutoff in CUTOFF_ORDER:
            row = runtime_key[(cutoff, variant)]
            per_time_path = (
                Path(row["resolved_run_dir"])
                / "post"
                / "outputs"
                / row["resolved_run_id"]
                / "tables"
                / "crps_forecast_per_time.csv"
            )
            expected_nws_horizon.append(mean_crps_for_leads(per_time_path, model_id=row["target_model_id"], horizon_days=8))
        observed_nws = article_nws_table.get(label)
        add(
            checks,
            "he3_authority",
            f"article_nws_horizon_table:{label}",
            observed_nws is not None and all(same_display(e, o) for e, o in zip(expected_nws_horizon, observed_nws)),
            "eight-day rendered values",
        )
        corrections_observed_nws = corrections_nws_table.get(label)
        add(
            checks,
            "he3_authority",
            f"corrections_nws_horizon_table:{label}",
            corrections_observed_nws is not None and all(same_display(e, o) for e, o in zip(expected_nws_horizon, corrections_observed_nws)),
            "eight-day rendered values",
        )


def check_he4_sync(article_root: Path, corrections_root: Path, checks: list[Check]) -> None:
    audit_rows = read_csv(article_root / "artifacts/he4_quantile_check_loss_current_publication/he4_selection_audit.csv")
    source_modes = sorted({row.get("source_mode", "") for row in audit_rows})
    max_crps_diff = max(as_float(row.get("crps_abs_diff", "0")) for row in audit_rows)
    add(checks, "he4_sync", "selection_row_count", len(audit_rows) == 20, f"{len(audit_rows)} rows")
    add(checks, "he4_sync", "selection_source_mode", source_modes == ["he2-publication-manifest"], ",".join(source_modes))
    add(checks, "he4_sync", "selection_crps_crosscheck", max_crps_diff <= 1e-6, f"max={max_crps_diff:.3g}")
    article_rows = (article_root / "tables/generated_tex/he4_quantile_check_loss_rows.tex").read_text(encoding="utf-8").strip()
    corrections = (corrections_root / "tables/generated_tex/he4_quantile_check_loss_response_table.tex").read_text(encoding="utf-8")
    add(checks, "he4_sync", "corrections_contains_article_rows", article_rows in corrections, "HE4 rows synced into corrections wrapper")


def check_selected_figures(article_root: Path, checks: list[Check]) -> None:
    manifest = json.loads((article_root / "MANUSCRIPT_ASSET_MANIFEST.json").read_text(encoding="utf-8"))
    figures = {row["label"]: row for row in manifest.get("figures", [])}
    for label in SELECTED_MODEL_FIGURES:
        row = figures.get(label)
        add(checks, "figure_lineage", f"{label}:manifest_entry", row is not None, "manifest entry")
        if row is None:
            continue
        add(checks, "figure_lineage", f"{label}:current_model_flag", bool(row.get("current_model_output_wired")), str(row.get("current_model_output_wired")))
        add(checks, "figure_lineage", f"{label}:source_exists", (article_root / row["source_path"]).exists(), row["source_path"])
        add(checks, "figure_lineage", f"{label}:manuscript_exists", (article_root / row["manuscript_path"]).exists(), row["manuscript_path"])
        add(
            checks,
            "figure_lineage",
            f"{label}:selected_authority_note",
            "selected" in str(row.get("note", "")).lower() or "authoritative" in str(row.get("note", "")).lower(),
            str(row.get("note", "")),
        )
    bundle = json.loads((article_root / "artifacts/representative_selected_model_2022_12_25/bundle_metadata.json").read_text(encoding="utf-8"))
    add(
        checks,
        "figure_lineage",
        "representative_bundle_run",
        bundle.get("run_id") == "multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep",
        str(bundle.get("run_id", "")),
    )
    support_readme = (article_root / "artifacts/representative_selected_model_2022_12_25/authoritative_support/README.md").read_text(encoding="utf-8")
    add(
        checks,
        "figure_lineage",
        "support_readme_same_authority",
        "same selected-output authority as the synthesis figure" in support_readme,
        "authoritative support README",
    )


def check_prose(article_root: Path, corrections_root: Path, checks: list[Check]) -> None:
    generated_tables = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((article_root / "tables" / "generated_tex").glob("*.tex"))
    )
    article = (article_root / "wileyNJD-APA.tex").read_text(encoding="utf-8") + "\n" + generated_tables
    corrections = (corrections_root / "main.tex").read_text(encoding="utf-8")
    required_article = [
        "AL-M-T1 is the best corrected Bayesian row at 12/25/2022",
        "A separate eight-day NWS-horizon table preserves the direct operational comparison to NWS",
        r"Appendix~\ref{app:he3ablation} reports a targeted component ablation",
        r"noH3} refers to the retained noninteger frequency \(1/6.8068493\)",
        "same 2022-12-25 selected exAL-M-T1 output authority used for the synthesis illustration",
        "conceptual or physically based models",
        "Conceptual formulations remain especially practical for prediction",
        "easier to specify, calibrate, and deploy operationally",
        "The empirical focus is forecasting performance and uncertainty quantification",
        r"Section~\ref{sec:forecastvalidation} reports the out-of-sample forecast validation results",
        r"\section{FORECAST VALIDATION RESULTS}",
        r"\section{INTERPRETATION OF THE SELECTED SPECIFICATION}",
        "five-cutoff rolling-origin forecast comparison",
        "not as a second forecast-validation exercise",
        "not as additional rolling-origin evidence",
        "five rolling-origin cutoff dates that span contrasting hydrological conditions",
        "relatively low-flow windows as well as winter high-flow episodes",
        "not a continuous daily hindcast over the full post-2022 period",
        "Post-cutoff USGS observations are reserved strictly for verification",
        "time-ordered analogue of cross-validation",
        "each fold fixes a forecast origin",
        "scores the resulting predictive distribution against future USGS observations",
        "feasible folds are constrained by version-consistent forecast archives",
        "heavily overlapping forecast windows would overrepresent the same hydrological episode",
        "These two uncertainty sources are related but distinct",
        "Hydrological uncertainty arises from model structure, parameters, states, and observations",
        "meteorological uncertainty enters through imperfect precipitation and related atmospheric forcing fields",
        "local hydrometeorological covariates",
        "reanalysis-based model inputs",
        "rather than direct observations or uncertainty-free measurements",
        "ERA5/ERA5-Land variables may include short forecast components",
        "not verification observations",
        r"\section{APPLICATION DATA AND FORECASTING DESIGN}",
        r"\subsection{Study Setting and Observations}",
        "Our target series is",
        "USGS target series",
        "three additional information sources",
        "Each source plays a different role",
        "retrospective products are used to learn source-specific discrepancies",
        "relative to the USGS target series",
        "Precipitation is not modeled through a separate censoring",
        "zero-inflation, or occurrence/intensity layer",
        "dry days are retained in the supplied covariate path",
        "deterministic engineered terms",
        r"\subsection{Extended Asymmetric Laplace Likelihood}",
        r"The benchmark variants reported in Section~\ref{sec:forecastvalidation} are tied to this formulation",
        r"the observation likelihood gives the \(N\), AL, and exAL rows",
        r"the active source set gives the \(U\) and \(M\) rows",
        r"the forecast-window treatment of the transfer block gives the \(T0\) and \(T1\) rows",
        "nine Bayesian variants of the common state-space framework",
        "Because exAL-M-T1 is the selected extended-likelihood multivariate specification",
        "Selected Posterior Means and 95\\% Credible Intervals for Transfer-Function Covariates",
        "Posterior Medians and 95\\% Credible Intervals for the Source-Specific Weight Coefficients",
        "Posterior Medians and 95\\% Credible Intervals for the Source-Specific Scale Parameters",
        "probability integral transform (PIT) diagnostics",
        "For reproducibility, implementation pseudocode for the VB algorithm is provided",
        "Its role is illustrative",
        "comparative forecast evaluation remains the main empirical evidence",
        "uncertainty around fitted quantile-location curves",
        "rather than the full forecast distribution at a single origin",
        "full synthesized posterior predictive distribution",
        "posterior predictive envelope can vary across the forecast window",
        "increased the risk of quantile crossing in the discrepancy states",
    ]
    required_corrections = [
        "best corrected Bayesian row at 12/25/2022",
        "separate eight-day NWS-horizon comparison",
        "Because this is a sensitivity analysis of the selected specification rather than a primary benchmark table",
        r"noH3} refers to the retained noninteger frequency \(1/6.8068493\)",
        "Within this fixed ablation matrix",
        "same 2022-12-25 selected-model posterior-output authority",
        "centering the forecasting analysis on multiple rolling-origin cutoffs",
        "supported by rolling-origin forecast evaluation and selected-model interpretation",
        "rather than treating dynamic discrepancy correction alone as the central novelty",
        "forecasting evaluation is expanded to five rolling-origin out-of-sample cutoffs",
        "evidence is no longer tied to a single moderate-flood episode",
        "not presented as a continuous 2023-present hindcast",
        "representative illustration of the selected model at one forecast origin",
        "not counted as additional forecast-validation evidence",
        "organized around forecast origins rather than a conventional random split",
        "time-ordered analogue of cross-validation",
        "post-cutoff USGS observations are used only for verification",
        "heavily overlapping forecast windows overrepresent the same hydrological regime",
        "The revised introduction now broadens this statement",
        "uses both conceptual and physically based models",
        "simpler to specify, calibrate, and deploy in forecasting applications",
        "typographical error rather than intended terminology",
        "The revised manuscript no longer uses this term",
        "reanalysis-based model products rather than direct observations or uncertainty-free measurements",
        "ERA5/ERA5-Land variables may include short forecast components",
        "precipitation is from PRISM and ERA5-Land enters as the soil-moisture covariate",
        "external covariates rather than verification observations",
        "now separates the general methodology from the application data and forecasting design",
        "USGS daily flow series as the observed target",
        "distinguishes forecast covariates, retrospective products, and operational forecast products",
        "external historical inputs used to learn source-specific discrepancies relative to the USGS target",
        "now states explicitly that precipitation is not handled through censoring",
        "zero-inflation, or a separate occurrence/intensity model",
        "zero-precipitation days are retained in the supplied covariate path",
        "precipitation intermittency enters through the transfer component",
        "no longer uses the vague ``General Results'' organization",
        "separates the material by inferential role",
        "Forecast Validation Results",
        "Interpretation of the Selected Specification",
        "rather than as a second forecast-validation exercise",
        "representative transfer-function covariate table reports posterior means",
        "tables report posterior medians with 95\\% credible intervals",
        "table-specific export contract",
        "The revised introduction now separates these concepts before introducing the Bayesian framework",
        "hydrological uncertainty with river-system structure, parameters, states, and observations",
        "meteorological uncertainty with precipitation and atmospheric forcing fields",
        "using available forecast and retrospective products to produce calibrated predictive distributions",
        "no longer uses the staged A/B/C presentation as the organizing device",
        "one common state-space formulation",
        r"forecast-validation section maps the reported benchmark rows through the \(L\)-\(S\)-\(T\) labels",
        "likelihood family, source set, and forecast-window transfer treatment",
        r"selected \texttt{exAL-M-T1} specification",
        "PIT-centered development has been removed from the main text",
        "final forecast comparison uses CRPS as the primary full-distribution score",
        "targeted quantile check loss as the quantile-level diagnostic",
        "Posterior predictive synthesis is retained only as a concise selected-origin illustration",
        "posterior uncertainty around fitted quantile-location or component summaries",
        "full forecast predictive distribution at each date",
        "representative single-cutoff posterior predictive distribution",
        "forecast-window inputs change",
        "Quantile crossing is no longer developed as a separate procedure in the main text",
        "MCMC and VB pseudocode remains in the appendices for reproducibility",
    ]
    forbidden = [
        "best-performing model in all five cutoffs",
        "lowest forecast-window CRPS in every case",
        "do uniformly dominate the operational baseline",
        "raw NWS forecast product has the lowest CRPS overall",
        "raw NWS forecast product has the lowest CRPS in the table",
        "the full model remains best across all five ablation comparisons",
        "full model remains the best ablation configuration",
        "the main contribution will be presented",
        "does not currently distinguish meteorological and hydrological uncertainty",
        "we will reorganize the introduction",
        "we will broaden it",
        "we will correct it",
        "we will replace the deterministic language",
        "we will state earlier and more explicitly",
        "we will reorganize the application material",
        "We will make this explicit in the revised manuscript",
        "We agree that the current organization of Section 3 is not clear enough",
        "we will replace vague headings",
        "This will separate setup, historical behavior, and forecasting evidence more clearly",
        "The original labeling of Tables 1 and 2 was inconsistent: the entries reported there are posterior medians",
        "Posterior Means and 95\\% Credible Intervals for the Source-Specific",
        "local hydrological covariates",
        "current A/B/C presentation does not make the connection",
        "we will present the final forecasting specification",
        "We will also revise the opening of the results section",
        "we will simplify the presentation substantially",
        "we will remove the detailed PIT development",
        "we will reduce intermediate derivational detail",
        "will be mentioned briefly as a robustness device",
        "random K-fold cross-validation",
    ]
    for claim in required_article:
        add(checks, "prose", f"article_required:{claim}", claim in article, claim)
    for claim in required_corrections:
        add(checks, "prose", f"corrections_required:{claim}", claim in corrections, claim)
    for claim in forbidden:
        add(checks, "prose", f"article_forbidden:{claim}", claim not in article, claim)
        add(checks, "prose", f"corrections_forbidden:{claim}", claim not in corrections, claim)
    add(checks, "prose", "article_forbidden:flexile", "flexile" not in article.lower(), "flexile")


def check_software_availability(workflow_root: Path, article_root: Path, corrections_root: Path, checks: list[Check]) -> None:
    manifest_path = article_root / SOFTWARE_MANIFEST_REL
    add(checks, "software_availability", "manifest_exists", manifest_path.exists(), SOFTWARE_MANIFEST_REL)
    if not manifest_path.exists():
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    package = manifest.get("public_estimation_package", {})
    workflow = manifest.get("study_workflow_repository", {})
    article_repo = manifest.get("revised_article_repository", {})
    corrections_repo = manifest.get("corrections_repository", {})
    archive = manifest.get("archive_status", {})
    validation_policy = manifest.get("validation_policy", {})
    release_readiness_files = workflow.get("release_readiness_files", {})

    add(
        checks,
        "software_availability",
        "schema_version",
        manifest.get("schema_version") == "revision_software_availability_v1",
        str(manifest.get("schema_version", "")),
    )
    add(checks, "software_availability", "cran_package_url", package.get("cran_package_url") == CRAN_EXDQLM_URL, str(package.get("cran_package_url", "")))
    add(checks, "software_availability", "cran_package_doi", package.get("package_doi") == CRAN_EXDQLM_DOI_URL, str(package.get("package_doi", "")))
    add(checks, "software_availability", "cran_version_recorded", package.get("cran_version_verified_for_contract") == "1.0.0", str(package.get("cran_version_verified_for_contract", "")))
    add(checks, "software_availability", "workflow_url", workflow.get("public_url") == PROJECT1_URL, str(workflow.get("public_url", "")))
    expected_release_files = {
        "readme": WORKFLOW_README_REL,
        "citation": WORKFLOW_CITATION_REL,
        "pending_release_notes": WORKFLOW_RELEASE_NOTES_REL,
        "archive_readiness_checklist": WORKFLOW_ARCHIVE_READINESS_REL,
    }
    add(
        checks,
        "software_availability",
        "workflow_release_readiness_manifest",
        release_readiness_files == expected_release_files,
        json.dumps(release_readiness_files, sort_keys=True),
    )
    add(
        checks,
        "software_availability",
        "workflow_contract_doc",
        (workflow_root / SOFTWARE_CONTRACT_REL).exists(),
        SOFTWARE_CONTRACT_REL,
    )
    add(
        checks,
        "software_availability",
        "article_contract_doc",
        (article_root / ARTICLE_SOFTWARE_DOC_REL).exists(),
        ARTICLE_SOFTWARE_DOC_REL,
    )
    add(
        checks,
        "software_availability",
        "article_repo_url",
        "Evironmetrics---REVISED-DOC-Corrected-2" in str(article_repo.get("public_url", "")),
        str(article_repo.get("public_url", "")),
    )
    add(
        checks,
        "software_availability",
        "corrections_repo_url",
        "Corrections---Project-1" in str(corrections_repo.get("public_url", "")),
        str(corrections_repo.get("public_url", "")),
    )
    archive_check = check_archive_status(archive)
    add(checks, "software_availability", "archive_status_coherent", archive_check.ok, archive_check.detail)
    add(
        checks,
        "software_availability",
        "static_commit_policy",
        "reason_static_commits_are_not_recorded" in validation_policy,
        str(validation_policy.get("reason_static_commits_are_not_recorded", "")),
    )
    for rel in WORKFLOW_RELEASE_READINESS_RELS:
        add(checks, "software_availability", f"workflow_release_readiness_exists:{rel}", (workflow_root / rel).exists(), rel)
    remote_url = git_value(workflow_root, "remote", "get-url", "origin")
    add(checks, "software_availability", "workflow_remote_matches_project1", "AntonioAPDL/Project1" in remote_url, remote_url)

    readme_path = workflow_root / WORKFLOW_README_REL
    citation_path = workflow_root / WORKFLOW_CITATION_REL
    release_notes_path = workflow_root / WORKFLOW_RELEASE_NOTES_REL
    checklist_path = workflow_root / WORKFLOW_ARCHIVE_READINESS_REL
    if readme_path.exists():
        readme_text = readme_path.read_text(encoding="utf-8")
        add(checks, "software_availability", "readme_names_project1", PROJECT1_URL in readme_text, WORKFLOW_README_REL)
        add(checks, "software_availability", "readme_names_cran_package", CRAN_EXDQLM_URL in readme_text, WORKFLOW_README_REL)
        add(checks, "software_availability", "readme_names_contract", SOFTWARE_CONTRACT_REL in readme_text, WORKFLOW_README_REL)
        add(checks, "software_availability", "readme_archive_pending", "pending final revision freeze" in readme_text, WORKFLOW_README_REL)
    if citation_path.exists():
        citation_text = citation_path.read_text(encoding="utf-8")
        add(checks, "software_availability", "citation_pending_version", 'version: "pending-final-archive"' in citation_text, WORKFLOW_CITATION_REL)
        add(checks, "software_availability", "citation_no_workflow_doi_field", "\ndoi:" not in citation_text, WORKFLOW_CITATION_REL)
        add(checks, "software_availability", "citation_names_project1", PROJECT1_URL in citation_text, WORKFLOW_CITATION_REL)
    if release_notes_path.exists():
        release_notes_text = release_notes_path.read_text(encoding="utf-8")
        add(checks, "software_availability", "release_notes_archive_pending", "pending final revision freeze" in release_notes_text, WORKFLOW_RELEASE_NOTES_REL)
    if checklist_path.exists():
        checklist_text = checklist_path.read_text(encoding="utf-8")
        add(checks, "software_availability", "archive_checklist_license_gate", "Workflow repository license is confirmed by the authors" in checklist_text, WORKFLOW_ARCHIVE_READINESS_REL)
        add(checks, "software_availability", "archive_checklist_final_doi_gate", "Final workflow release is archived with a permanent DOI" in checklist_text, WORKFLOW_ARCHIVE_READINESS_REL)

    article_text = (article_root / "wileyNJD-APA.tex").read_text(encoding="utf-8")
    corrections_text = (corrections_root / "main.tex").read_text(encoding="utf-8")
    required_article = [
        r"CRAN R package \texttt{exdqlm}",
        CRAN_EXDQLM_URL,
        CRAN_EXDQLM_DOI_URL,
        PROJECT1_URL,
        "compact provenance manifests",
    ]
    required_corrections = [
        r"CRAN R package \texttt{exdqlm}",
        CRAN_EXDQLM_URL,
        CRAN_EXDQLM_DOI_URL,
        PROJECT1_URL,
        "compact provenance manifests",
    ]
    if archive_check.is_pending:
        required_article.append("permanent archival release of the workflow repository will be created")
        required_corrections.append("Before final resubmission")
    elif archive_check.is_final:
        required_article.append(archive_check.doi)
        required_corrections.append(archive_check.doi)
    for claim in required_article:
        add(checks, "software_availability", f"article_required:{claim}", claim in article_text, claim)
    for claim in required_corrections:
        add(checks, "software_availability", f"corrections_required:{claim}", claim in corrections_text, claim)
    if archive_check.is_pending:
        premature_archive_claims = [
            "workflow repository has been archived",
            "workflow has been archived",
            "archived workflow DOI",
        ]
        for claim in premature_archive_claims:
            add(checks, "software_availability", f"article_no_premature_archive_claim:{claim}", claim not in article_text, claim)
            add(checks, "software_availability", f"corrections_no_premature_archive_claim:{claim}", claim not in corrections_text, claim)
            for rel in WORKFLOW_RELEASE_READINESS_RELS:
                readiness_path = workflow_root / rel
                if readiness_path.exists():
                    readiness_text = readiness_path.read_text(encoding="utf-8")
                    add(checks, "software_availability", f"workflow_no_premature_archive_claim:{rel}:{claim}", claim not in readiness_text, claim)
    elif archive_check.is_final:
        stale_pending_claims = [
            "permanent archival release of the workflow repository will be created",
            "Before final resubmission, we will archive",
            "workflow archive DOI: pending",
        ]
        for claim in stale_pending_claims:
            add(checks, "software_availability", f"article_no_stale_pending_claim:{claim}", claim not in article_text, claim)
            add(checks, "software_availability", f"corrections_no_stale_pending_claim:{claim}", claim not in corrections_text, claim)


def check_runtime_feasibility(workflow_root: Path, article_root: Path, corrections_root: Path, checks: list[Check]) -> None:
    manifest_path = article_root / RUNTIME_MANIFEST_REL
    add(checks, "runtime_feasibility", "manifest_exists", manifest_path.exists(), RUNTIME_MANIFEST_REL)
    if not manifest_path.exists():
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in check_runtime_manifest(manifest):
        add(checks, "runtime_feasibility", row.item, row.ok, row.detail)

    workflow_doc = workflow_root / RUNTIME_CONTRACT_REL
    article_doc = article_root / ARTICLE_RUNTIME_DOC_REL
    add(checks, "runtime_feasibility", "workflow_contract_doc", workflow_doc.exists(), RUNTIME_CONTRACT_REL)
    add(checks, "runtime_feasibility", "article_contract_doc", article_doc.exists(), ARTICLE_RUNTIME_DOC_REL)

    article_text = (article_root / "wileyNJD-APA.tex").read_text(encoding="utf-8")
    corrections_text = (corrections_root / "main.tex").read_text(encoding="utf-8")
    for claim in REQUIRED_RUNTIME_ARTICLE_CLAIMS:
        add(checks, "runtime_feasibility", f"article_required:{claim}", claim in article_text, claim)
    for claim in REQUIRED_RUNTIME_CORRECTIONS_CLAIMS:
        add(checks, "runtime_feasibility", f"corrections_required:{claim}", claim in corrections_text, claim)
    for claim in FORBIDDEN_RUNTIME_DECOMPOSITION_CLAIMS:
        add(checks, "runtime_feasibility", f"article_forbidden:{claim}", claim not in article_text, claim)
        add(checks, "runtime_feasibility", f"corrections_forbidden:{claim}", claim not in corrections_text, claim)


def check_forecast_design(workflow_root: Path, article_root: Path, corrections_root: Path, checks: list[Check]) -> None:
    manifest_path = article_root / FORECAST_DESIGN_MANIFEST_REL
    add(checks, "forecast_design", "manifest_exists", manifest_path.exists(), FORECAST_DESIGN_MANIFEST_REL)
    if not manifest_path.exists():
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in check_forecast_design_manifest(manifest):
        add(checks, "forecast_design", row.item, row.ok, row.detail)

    workflow_doc = workflow_root / FORECAST_DESIGN_CONTRACT_REL
    article_doc = article_root / ARTICLE_FORECAST_DESIGN_DOC_REL
    add(checks, "forecast_design", "workflow_contract_doc", workflow_doc.exists(), FORECAST_DESIGN_CONTRACT_REL)
    add(checks, "forecast_design", "article_contract_doc", article_doc.exists(), ARTICLE_FORECAST_DESIGN_DOC_REL)

    article_text = (article_root / "wileyNJD-APA.tex").read_text(encoding="utf-8")
    corrections_text = (corrections_root / "main.tex").read_text(encoding="utf-8")
    for claim in REQUIRED_FORECAST_DESIGN_ARTICLE_CLAIMS:
        add(checks, "forecast_design", f"article_required:{claim}", claim in article_text, claim)
    for claim in REQUIRED_FORECAST_DESIGN_CORRECTIONS_CLAIMS:
        add(checks, "forecast_design", f"corrections_required:{claim}", claim in corrections_text, claim)
    for claim in FORBIDDEN_FORECAST_DESIGN_CLAIMS:
        add(checks, "forecast_design", f"article_forbidden:{claim}", claim not in article_text, claim)
        add(checks, "forecast_design", f"corrections_forbidden:{claim}", claim not in corrections_text, claim)


def check_latest_forecast_issue(workflow_root: Path, article_root: Path, corrections_root: Path, checks: list[Check]) -> None:
    manifest_path = article_root / LATEST_FORECAST_ISSUE_MANIFEST_REL
    add(checks, "latest_forecast_issue", "manifest_exists", manifest_path.exists(), LATEST_FORECAST_ISSUE_MANIFEST_REL)
    if not manifest_path.exists():
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in check_latest_forecast_issue_manifest(manifest, workflow_root=workflow_root):
        add(checks, "latest_forecast_issue", row.item, row.ok, row.detail)

    workflow_doc = workflow_root / LATEST_FORECAST_ISSUE_CONTRACT_REL
    article_doc = article_root / ARTICLE_LATEST_FORECAST_ISSUE_DOC_REL
    add(checks, "latest_forecast_issue", "workflow_contract_doc", workflow_doc.exists(), LATEST_FORECAST_ISSUE_CONTRACT_REL)
    add(checks, "latest_forecast_issue", "article_contract_doc", article_doc.exists(), ARTICLE_LATEST_FORECAST_ISSUE_DOC_REL)

    article_text = (article_root / "wileyNJD-APA.tex").read_text(encoding="utf-8")
    corrections_text = (corrections_root / "main.tex").read_text(encoding="utf-8")
    for claim in REQUIRED_LATEST_FORECAST_ARTICLE_CLAIMS:
        add(checks, "latest_forecast_issue", f"article_required:{claim}", claim in article_text, claim)
    for claim in REQUIRED_LATEST_FORECAST_CORRECTIONS_CLAIMS:
        add(checks, "latest_forecast_issue", f"corrections_required:{claim}", claim in corrections_text, claim)
    for claim in FORBIDDEN_LATEST_FORECAST_ARTICLE_CLAIMS:
        add(checks, "latest_forecast_issue", f"article_forbidden:{claim}", claim not in article_text, claim)


def repo_metadata(repo: Path) -> dict[str, str]:
    return {
        "path": str(repo),
        "branch": git_value(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "head": git_value(repo, "rev-parse", "--short", "HEAD"),
        "status_short": git_value(repo, "status", "--short"),
    }


def render_summary(checks: list[Check], metadata: dict[str, object]) -> str:
    failed = [check for check in checks if check.status != "pass"]
    counts: dict[str, dict[str, int]] = {}
    for check in checks:
        counts.setdefault(check.family, {"pass": 0, "fail": 0})
        counts[check.family]["pass" if check.status == "pass" else "fail"] += 1
    lines = [
        "# Publication Freeze Validation",
        "",
        f"- Timestamp UTC: `{metadata['timestamp_utc']}`",
        f"- Overall status: `{'pass' if not failed else 'fail'}`",
        f"- Failed checks: `{len(failed)}`",
        "",
        "## Repositories",
        "",
        "| repo | branch | head | dirty |",
        "|---|---|---|---|",
    ]
    for name, meta in metadata["repos"].items():
        dirty = "yes" if str(meta["status_short"]).strip() else "no"
        lines.append(f"| {name} | `{meta['branch']}` | `{meta['head']}` | {dirty} |")
    lines.extend(["", "## Check Families", "", "| family | pass | fail |", "|---|---:|---:|"])
    for family in sorted(counts):
        row = counts[family]
        lines.append(f"| {family} | {row['pass']} | {row['fail']} |")
    if failed:
        lines.extend(["", "## Failures", "", "| family | item | detail |", "|---|---|---|"])
        for check in failed:
            lines.append(f"| {check.family} | `{check.item}` | {check.detail} |")
    return "\n".join(lines) + "\n"


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Validate the current cross-repo publication freeze.")
    ap.add_argument("--workflow-root", type=Path, default=ROOT)
    ap.add_argument("--article-root", type=Path, default=ROOT / "Evironmetrics---REVISED-DOC-Corrected-2")
    ap.add_argument("--corrections-root", type=Path, default=Path("/data/muscat_data/jaguir26/Corrections---Project-1"))
    ap.add_argument(
        "--he3-runtime-root",
        type=Path,
        default=ROOT.parent / "project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608",
    )
    ap.add_argument("--report-dir", type=Path, default=ROOT / "reports/publication_freeze_validation_20260614")
    ap.add_argument("--require-clean", action="store_true")
    return ap.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    workflow_root = args.workflow_root.resolve()
    article_root = args.article_root.resolve()
    corrections_root = args.corrections_root.resolve()
    he3_runtime_root = args.he3_runtime_root.resolve()
    report_dir = args.report_dir.resolve()
    report_dir.mkdir(parents=True, exist_ok=True)

    checks: list[Check] = []
    metadata: dict[str, object] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "argv": list(argv or sys.argv[1:]),
        "repos": {
            "workflow": repo_metadata(workflow_root),
            "article": repo_metadata(article_root),
            "corrections": repo_metadata(corrections_root),
        },
        "he3_runtime_root": str(he3_runtime_root),
    }
    if args.require_clean:
        for name, meta in metadata["repos"].items():
            add(checks, "repo_clean", name, not str(meta["status_short"]).strip(), str(meta["status_short"]))

    check_he2_selective_manifest(workflow_root=workflow_root, article_root=article_root, checks=checks)
    check_he3_authoritative(
        workflow_root=workflow_root,
        article_root=article_root,
        corrections_root=corrections_root,
        he3_runtime_root=he3_runtime_root,
        checks=checks,
    )
    check_he4_sync(article_root, corrections_root, checks)
    check_selected_figures(article_root, checks)
    check_prose(article_root, corrections_root, checks)
    check_forecast_design(workflow_root, article_root, corrections_root, checks)
    check_latest_forecast_issue(workflow_root, article_root, corrections_root, checks)
    check_runtime_feasibility(workflow_root, article_root, corrections_root, checks)
    check_software_availability(workflow_root, article_root, corrections_root, checks)

    rows = [{"family": c.family, "item": c.item, "status": c.status, "detail": c.detail} for c in checks]
    write_csv(report_dir / "publication_freeze_validation_checks.csv", rows, ["family", "item", "status", "detail"])
    payload = {
        "metadata": metadata,
        "total_checks": len(checks),
        "failed_checks": sum(1 for c in checks if c.status != "pass"),
        "status": "pass" if all(c.status == "pass" for c in checks) else "fail",
    }
    (report_dir / "publication_freeze_validation_summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (report_dir / "PUBLICATION_FREEZE_VALIDATION.md").write_text(render_summary(checks, metadata), encoding="utf-8")

    if payload["status"] != "pass":
        print(f"Publication freeze validation failed: {report_dir}")
        return 1
    print(f"Publication freeze validation passed: {report_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

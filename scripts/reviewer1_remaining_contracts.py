#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass

from current_article_contract import active_tex, scientific_checks, structure_checks


R1_REMAINING_CONTRACT_REL = "docs/reviewer1_remaining_contracts_20260615.md"
ARTICLE_R1_REMAINING_DOC_REL = "docs/reviewer1_remaining_contracts.md"


@dataclass(frozen=True)
class Reviewer1RemainingSpec:
    item_id: str
    required_corrections: tuple[str, ...]
    forbidden_article: tuple[str, ...] = ()
    forbidden_corrections_stale: tuple[str, ...] = ()


@dataclass(frozen=True)
class Reviewer1RemainingCheck:
    item: str
    ok: bool
    detail: str


REVIEWER1_REMAINING_SPECS: tuple[Reviewer1RemainingSpec, ...] = (
    Reviewer1RemainingSpec(
        item_id="R1-M2",
        required_corrections=(
            "no longer organizes the methodology around models A, B, and C",
            "presents a common state-space formulation",
            r"Section 4 identifies the models in terms of \(L\)-\(S\)-\(T\) labels",
            "likelihood family, source set, and forecast-window transfer treatment",
            r"selected \texttt{exAL-M-T1} specification",
        ),
        forbidden_article=("Model A", "Model B", "Model C", "General Results"),
        forbidden_corrections_stale=(
            "we will present the final forecasting specification",
            "We will also revise the opening of the results section",
        ),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-M3",
        required_corrections=(
            "PIT-centered development has been removed from the main text",
            "final forecast comparison uses CRPS as the primary full-distribution score",
            "targeted quantile check loss as the quantile-level diagnostic",
            "retained a compact posterior predictive synthesis subsection",
            "Quantile crossing is no longer developed as a separate procedure in the main text",
            "Details about the MCMC and VB algorithms are provided in the Appendix",
        ),
        forbidden_article=(
            "PITs are described in detail",
            "two-step method",
            "resolve quantile crossing",
            "Posterior Predictive Synthesis part",
        ),
        forbidden_corrections_stale=(
            "we will simplify the presentation substantially",
            "we will remove the detailed PIT development",
            "we will reduce intermediate derivational detail",
        ),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-M4",
        required_corrections=(
            "forecasting evaluation is expanded to five rolling-origin out-of-sample cutoffs",
            "evidence is no longer tied to a single moderate-flood episode",
            "not presented as a continuous 2023-present hindcast",
            "representative selected-model illustration at one forecast origin",
            "validation evidence is the multi-cutoff CRPS and check-loss tables",
            "selected-model diagnostics",
        ),
        forbidden_article=("only one short forecast has been evaluated",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-M5",
        required_corrections=(
            "organized around forecast origins rather than a conventional random split",
            "five cutoff-specific forecast-window evaluations",
            "post-cutoff USGS observations are used only for verification",
            "archive reconstruction step before any model can be fit",
            "rather than a dense set of overlapping windows that would repeatedly score the same hydrological episode",
            "pre-cutoff observational window",
            "fixed calibrated specification",
        ),
        forbidden_article=("random K-fold cross-validation",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m1",
        required_corrections=(
            "uses both conceptual and physically based models",
            "simpler to specify, calibrate, and deploy in forecasting applications",
        ),
        forbidden_article=("Hydrological predictions are often produced using physical models",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m2",
        required_corrections=(
            "typographical error rather than intended terminology",
            "The revised manuscript no longer uses this term",
        ),
        forbidden_article=("flexile",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m3",
        required_corrections=(
            "reanalysis-based model products rather than direct observations or uncertainty-free measurements",
            "ERA5/ERA5-Land variables may include short forecast components",
            "precipitation is from PRISM and ERA5-Land enters as the soil-moisture covariate",
            "external covariates rather than verification observations",
        ),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m4",
        required_corrections=(
            "now separates the general methodology from the application data and forecasting design",
            "USGS daily flow series as the observed target",
            "distinguishes forecast covariates, retrospective products, and operational forecast products",
            "external historical inputs used to learn source-specific discrepancies relative to the USGS target",
        ),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m5",
        required_corrections=(
            "now states explicitly that precipitation is not handled through censoring",
            "zero-inflation, or a separate occurrence/intensity model",
            "zero-precipitation days are retained in the supplied covariate path",
            "precipitation intermittency enters through the transfer component",
        ),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m6",
        required_corrections=(
            "using forecasts issued at earlier times may reduce forecast performance",
            "use only the most recent forecast ensemble available",
            "latest-forecast-only protocol",
        ),
        forbidden_article=("weighted combination of prior forecasts",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m7",
        required_corrections=(
            "no longer uses the vague ``General Results'' organization",
            "separates the material by inferential role",
            "Forecast Validation Results",
            "Interpretation of the Selected Specification",
            "selected-model diagnostics are separated from the forecast-validation tables",
        ),
        forbidden_article=("General Results",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m8",
        required_corrections=(
            "representative transfer-function covariate table reports posterior means",
            "tables report posterior medians with 95\\% credible intervals",
            "table-specific export contract",
        ),
        forbidden_article=("Posterior Means and 95\\% Credible Intervals for the Source-Specific",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m9",
        required_corrections=(
            "comparatively stable bands reflect posterior uncertainty around fitted quantile-location or component summaries",
            "not a full forecast predictive distribution at each date",
            "representative single-cutoff posterior predictive distribution",
            "forecast-window inputs change",
            "expanded multi-cutoff CRPS and quantile-diagnostic tables remain the forecast-validation evidence",
        ),
    ),
)


def check_reviewer1_remaining_text(article_text: str, corrections_text: str) -> list[Reviewer1RemainingCheck]:
    checks: list[Reviewer1RemainingCheck] = []
    article_text = active_tex(article_text)
    article_lower = article_text.lower()
    checks.extend(Reviewer1RemainingCheck(item, ok, detail) for item, ok, detail in scientific_checks(article_text))
    checks.extend(Reviewer1RemainingCheck(item, ok, detail) for item, ok, detail in structure_checks(article_text))
    for spec in REVIEWER1_REMAINING_SPECS:
        for claim in spec.required_corrections:
            checks.append(
                Reviewer1RemainingCheck(
                    item=f"{spec.item_id}:corrections_required:{claim}",
                    ok=claim in corrections_text,
                    detail=claim,
                )
            )
        for claim in spec.forbidden_article:
            haystack = article_lower if claim == "flexile" else article_text
            needle = claim.lower() if claim == "flexile" else claim
            checks.append(
                Reviewer1RemainingCheck(
                    item=f"{spec.item_id}:article_forbidden:{claim}",
                    ok=needle not in haystack,
                    detail=claim,
                )
            )
        for claim in spec.forbidden_corrections_stale:
            checks.append(
                Reviewer1RemainingCheck(
                    item=f"{spec.item_id}:corrections_forbidden_stale:{claim}",
                    ok=claim not in corrections_text,
                    detail=claim,
                )
            )
    return checks

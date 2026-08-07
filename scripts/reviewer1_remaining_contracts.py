#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass


R1_REMAINING_CONTRACT_REL = "docs/reviewer1_remaining_contracts_20260615.md"
ARTICLE_R1_REMAINING_DOC_REL = "docs/reviewer1_remaining_contracts.md"


@dataclass(frozen=True)
class Reviewer1RemainingSpec:
    item_id: str
    required_article: tuple[str, ...]
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
        required_article=(
            "single state-space model",
            r"\(L\in\{\mathrm{N},\mathrm{AL},\mathrm{exAL}\}\) denotes a Gaussian, asymmetric Laplace, or extended asymmetric Laplace observation likelihood",
            r"\(S\in\{\mathrm{U},\mathrm{M}\}\) indicates whether the synthesis is univariate or multivariate",
            r"\(T\in\{\mathrm{T0},\mathrm{T1}\}\) indicates whether the transfer component is suppressed or retained during the forecast window",
            "nine Bayesian variants of the common state-space framework",
            "We focus on exAL-M-T1 because it has the lowest 28-day forecast-window CRPS",
        ),
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
        required_article=(
            "CRPS is negatively oriented",
            "For reproducibility, implementation pseudocode for the VB algorithm is provided",
            "Table~\\ref{tab:he4_quantile_check_loss} complements the CRPS comparisons with targeted quantile diagnostics",
            "quantile-specific posterior predictions into a single predictive distribution",
        ),
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
        required_article=(
            "five cutoff-specific, version-consistent staged datasets that span contrasting hydrological conditions",
            "relatively low-flow windows as well as winter high-flow episodes",
            "not a continuous daily hindcast over the full post-2022 period",
            "Post-cutoff USGS observations are reserved strictly for verification",
            "we use the Continuous Ranked Probability Score (CRPS)",
            "quantile check loss",
            "These figures are interpretation diagnostics",
            "The selected exAL-M-T1 specification attains the lowest 28-day forecast-window CRPS in all five cutoffs",
        ),
        required_corrections=(
            "forecasting evaluation is expanded to five rolling-origin out-of-sample cutoffs",
            "evidence is no longer tied to a single moderate-flood episode",
            "not presented as a continuous 2023-present hindcast",
            "representative selected-model illustration at one forecast origin",
            "not counted as additional forecast-validation evidence",
        ),
        forbidden_article=("only one short forecast has been evaluated",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-M5",
        required_article=(
            "five cutoff-specific, version-consistent staged datasets",
            "uses only information available at that origin to fit seven quantile-specific models",
            "scores that distribution against future USGS observations held out over the forecast window",
            "archive-feasible, version-consistent origins that span contrasting hydrological settings",
            "avoid dense overlaps that would overrepresent the same episode",
        ),
        required_corrections=(
            "organized around forecast origins rather than a conventional random split",
            "five cutoff-specific forecast-window evaluations",
            "post-cutoff USGS observations are used only for verification",
            "avoid dense overlapping windows that would repeatedly score the same hydrological regime",
            "pre-cutoff observational window",
            "fixed calibrated specification",
        ),
        forbidden_article=("random K-fold cross-validation",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m1",
        required_article=(
            "conceptual or physically based models",
            "Conceptual formulations remain especially practical for prediction",
            "easier to specify, calibrate, and deploy operationally",
        ),
        required_corrections=(
            "uses both conceptual and physically based models",
            "simpler to specify, calibrate, and deploy in forecasting applications",
        ),
        forbidden_article=("Hydrological predictions are often produced using physical models",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m2",
        required_article=(r"\subsection{Extended Asymmetric Laplace Likelihood}",),
        required_corrections=(
            "typographical error rather than intended terminology",
            "The revised manuscript no longer uses this term",
        ),
        forbidden_article=("flexile",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m3",
        required_article=(
            "local soil moisture from ECMWF ERA5-Land",
            "historical gridded covariates extracted at the Big Trees location",
            "forecast-window precipitation and soil-moisture covariates from the same staged origin bundle",
            "The GDPC factor is treated as a climate-index covariate, not as an operational forecast product or verification target",
        ),
        required_corrections=(
            "reanalysis-based model products rather than direct observations or uncertainty-free measurements",
            "ERA5/ERA5-Land variables may include short forecast components",
            "precipitation is from PRISM and ERA5-Land enters as the soil-moisture covariate",
            "external covariates rather than verification observations",
        ),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m4",
        required_article=(
            r"\section{APPLICATION DATA AND FORECASTING DESIGN}",
            r"\subsection{Study Setting and Observations}",
            "Our target series is",
            "USGS target series",
            "three additional information sources",
            "Each source plays a different role",
            "retrospective products are used to learn source-specific discrepancies",
            "relative to the USGS target series",
        ),
        required_corrections=(
            "now separates the general methodology from the application data and forecasting design",
            "USGS daily flow series as the observed target",
            "distinguishes forecast covariates, retrospective products, and operational forecast products",
            "external historical inputs used to learn source-specific discrepancies relative to the USGS target",
        ),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m5",
        required_article=(
            "The transfer component takes three inputs",
            "local precipitation from the PRISM Climate Group",
            "local soil moisture from ECMWF ERA5-Land",
            "These local hydrometeorological covariates enter as deterministic summaries in the present implementation",
        ),
        required_corrections=(
            "now states explicitly that precipitation is not handled through censoring",
            "zero-inflation, or a separate occurrence/intensity model",
            "zero-precipitation days are retained in the supplied covariate path",
            "precipitation intermittency enters through the transfer component",
        ),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m6",
        required_article=(
            "using the latest forecast products issued at or before",
            "aggregates the latest available forecast issuances to daily member-specific forecast matrices",
            "Post-cutoff USGS observations are reserved strictly for verification",
        ),
        required_corrections=(
            "using forecasts issued at earlier times may reduce forecast performance",
            "use only the most recent forecast ensemble available",
            "latest-forecast-only protocol",
        ),
        forbidden_article=("weighted combination of prior forecasts",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m7",
        required_article=(
            r"\section{FORECAST VALIDATION RESULTS}",
            r"\section{INTERPRETATION OF THE SELECTED SPECIFICATION}",
            "These figures are interpretation diagnostics",
            "decomposes fitted historical quantile behavior across contrasting regimes",
        ),
        required_corrections=(
            "no longer uses the vague ``General Results'' organization",
            "separates the material by inferential role",
            "Forecast Validation Results",
            "Interpretation of the Selected Specification",
            "rather than as a second forecast-validation exercise",
        ),
        forbidden_article=("General Results",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m8",
        required_article=(
            "Selected Posterior Means and 95\\% Credible Intervals for Transfer-Function Covariates",
            "Posterior Medians and 95\\% Credible Intervals for the Source-Specific Skewness Parameters",
            "Posterior Medians and 95\\% Credible Intervals for the Source-Specific Scale Parameters",
        ),
        required_corrections=(
            "representative transfer-function covariate table reports posterior means",
            "tables report posterior medians with 95\\% credible intervals",
            "table-specific export contract",
        ),
        forbidden_article=("Posterior Means and 95\\% Credible Intervals for the Source-Specific",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-m9",
        required_article=(
            "uncertainty around fitted quantile-location curves",
            "synthesized posterior predictive distribution",
            "fitted quantile-specific forecasts combine into one predictive distribution",
            "posterior predictive envelope can vary across the forecast window",
        ),
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
    article_lower = article_text.lower()
    for spec in REVIEWER1_REMAINING_SPECS:
        for claim in spec.required_article:
            haystack = article_lower if claim == "flexile" else article_text
            needle = claim.lower() if claim == "flexile" else claim
            checks.append(
                Reviewer1RemainingCheck(
                    item=f"{spec.item_id}:article_required:{claim}",
                    ok=needle in haystack,
                    detail=claim,
                )
            )
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

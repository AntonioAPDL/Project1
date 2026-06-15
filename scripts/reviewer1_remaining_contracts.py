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
            r"The benchmark variants reported in Section~\ref{sec:forecastvalidation} are tied to this formulation",
            r"the observation likelihood gives the \(N\), AL, and exAL rows",
            r"the active source set gives the \(U\) and \(M\) rows",
            r"the forecast-window treatment of the transfer block gives the \(T0\) and \(T1\) rows",
            "nine Bayesian variants of the common state-space framework",
            "Because exAL-M-T1 is the selected extended-likelihood multivariate specification",
        ),
        required_corrections=(
            "no longer uses the staged A/B/C presentation as the organizing device",
            "one common state-space formulation",
            r"forecast-validation section maps the reported benchmark rows through the \(L\)-\(S\)-\(T\) labels",
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
            "probability integral transform (PIT) diagnostics",
            "For reproducibility, implementation pseudocode for the VB algorithm is provided",
            "Its role is illustrative",
            "risk of quantile crossing",
        ),
        required_corrections=(
            "PIT-centered development has been removed from the main text",
            "final forecast comparison uses CRPS as the primary full-distribution score",
            "targeted quantile check loss as the quantile-level diagnostic",
            "Posterior predictive synthesis is retained only as a concise selected-origin illustration",
            "Quantile crossing is no longer developed as a separate procedure in the main text",
            "MCMC and VB pseudocode remains in the appendices for reproducibility",
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
            "five rolling-origin cutoff dates that span contrasting hydrological conditions",
            "relatively low-flow windows as well as winter high-flow episodes",
            "not a continuous daily hindcast over the full post-2022 period",
            "Post-cutoff USGS observations are reserved strictly for verification",
            "Forecast skill is evaluated from the resulting posterior predictive distributions by the mean continuous ranked probability score",
            "targeted quantile diagnostics",
            "Its role is illustrative",
            "comparative forecast evaluation remains the main empirical evidence",
        ),
        required_corrections=(
            "forecasting evaluation is expanded to five rolling-origin out-of-sample cutoffs",
            "evidence is no longer tied to a single moderate-flood episode",
            "not presented as a continuous 2023-present hindcast",
            "representative illustration of the selected model at one forecast origin",
            "not counted as additional forecast-validation evidence",
        ),
        forbidden_article=("only one short forecast has been evaluated",),
    ),
    Reviewer1RemainingSpec(
        item_id="R1-M5",
        required_article=(
            "time-ordered analogue of cross-validation",
            "each fold fixes a forecast origin",
            "uses only information available at that origin",
            "scores the resulting predictive distribution against future USGS observations",
            "feasible folds are constrained by version-consistent forecast archives",
            "heavily overlapping forecast windows would overrepresent the same hydrological episode",
        ),
        required_corrections=(
            "organized around forecast origins rather than a conventional random split",
            "time-ordered analogue of cross-validation",
            "post-cutoff USGS observations are used only for verification",
            "heavily overlapping forecast windows overrepresent the same hydrological regime",
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
            "reanalysis-based model inputs",
            "rather than direct observations or uncertainty-free measurements",
            "ERA5/ERA5-Land variables may include short forecast components",
            "not verification observations",
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
            "Precipitation is not modeled through a separate censoring",
            "zero-inflation, or occurrence/intensity layer",
            "dry days are retained in the supplied covariate path",
            "deterministic engineered terms",
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
            "older forecast issuances are not averaged into the publication forecast matrices",
            "compatibility aliases only",
        ),
        required_corrections=(
            "we no longer combine older forecast issuances for the target time",
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
            "not as a second forecast-validation exercise",
            "not as additional rolling-origin evidence",
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
            "Posterior Medians and 95\\% Credible Intervals for the Source-Specific Weight Coefficients",
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
            "rather than the full forecast distribution at a single origin",
            "full synthesized posterior predictive distribution",
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

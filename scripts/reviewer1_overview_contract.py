#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass


R1_OVERVIEW_CONTRACT_REL = "docs/r1_overview_forecasting_emphasis_contract_20260615.md"
ARTICLE_R1_OVERVIEW_DOC_REL = "docs/reviewer1_overview_forecasting_emphasis_contract.md"

REQUIRED_R1_OVERVIEW_ARTICLE_CLAIMS = [
    "The empirical focus is forecasting performance and uncertainty quantification",
    "rather than only historical fit or methodological development in isolation",
    r"Section~\ref{sec:forecastvalidation} reports the out-of-sample forecast validation results",
    r"\section{FORECAST VALIDATION RESULTS}",
    r"\section{INTERPRETATION OF THE SELECTED SPECIFICATION}",
    "comparative forecast evaluation remains the main empirical evidence",
    "five-cutoff rolling-origin forecast comparison",
    "supporting interpretation for the selected specification",
]

REQUIRED_R1_OVERVIEW_CORRECTIONS_CLAIMS = [
    "centering the forecasting analysis on multiple rolling-origin cutoffs",
    "comparing the proposed method against simpler Bayesian alternatives and raw forecast products",
    "reporting both CRPS and targeted quantile diagnostics",
    "supported by rolling-origin forecast evaluation and selected-model interpretation",
    "rather than treating dynamic discrepancy correction alone as the central novelty",
]

FORBIDDEN_R1_OVERVIEW_ARTICLE_CLAIMS = [
    "General Results",
    "Model A",
    "Model B",
    "Model C",
    "current A/B/C presentation",
    "forecasting component is limited",
    "robust forecast evaluation is absent",
]

FORBIDDEN_R1_OVERVIEW_CORRECTIONS_STALE_CLAIMS = [
    "we will center the forecasting analysis",
    "we will revise how the contribution is stated",
    "we will present the contribution",
    "will add forecast validation",
]


@dataclass(frozen=True)
class R1OverviewCheck:
    item: str
    ok: bool
    detail: str


def check_r1_overview_text(article_text: str, corrections_text: str) -> list[R1OverviewCheck]:
    checks: list[R1OverviewCheck] = []
    for claim in REQUIRED_R1_OVERVIEW_ARTICLE_CLAIMS:
        checks.append(
            R1OverviewCheck(
                item=f"article_required:{claim}",
                ok=claim in article_text,
                detail=claim,
            )
        )
    for claim in REQUIRED_R1_OVERVIEW_CORRECTIONS_CLAIMS:
        checks.append(
            R1OverviewCheck(
                item=f"corrections_required:{claim}",
                ok=claim in corrections_text,
                detail=claim,
            )
        )
    for claim in FORBIDDEN_R1_OVERVIEW_ARTICLE_CLAIMS:
        checks.append(
            R1OverviewCheck(
                item=f"article_forbidden:{claim}",
                ok=claim not in article_text,
                detail=claim,
            )
        )
    for claim in FORBIDDEN_R1_OVERVIEW_CORRECTIONS_STALE_CLAIMS:
        checks.append(
            R1OverviewCheck(
                item=f"corrections_forbidden_stale:{claim}",
                ok=claim not in corrections_text,
                detail=claim,
            )
        )
    return checks

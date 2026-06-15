#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass


R1_UNCERTAINTY_CONTRACT_REL = "docs/r1_m1_uncertainty_framing_contract_20260615.md"
ARTICLE_R1_UNCERTAINTY_DOC_REL = "docs/reviewer1_uncertainty_framing_contract.md"

REQUIRED_R1_UNCERTAINTY_ARTICLE_CLAIMS = [
    "These two uncertainty sources are related but distinct",
    "Hydrological uncertainty arises from model structure, parameters, states, and observations",
    "meteorological uncertainty enters through imperfect precipitation and related atmospheric forcing fields",
    "A useful statistical forecasting framework should keep these roles clear",
    "local hydrometeorological covariates",
    "precipitation from the PRISM Climate Group",
    "soil moisture from ECMWF ERA5-Land",
]

REQUIRED_R1_UNCERTAINTY_CORRECTIONS_CLAIMS = [
    "The revised introduction now separates these concepts before introducing the Bayesian framework",
    "hydrological uncertainty with river-system structure, parameters, states, and observations",
    "meteorological uncertainty with precipitation and atmospheric forcing fields",
    "shortened the discussion of atmospheric ensemble-generation details",
    "using available forecast and retrospective products to produce calibrated predictive distributions",
]

FORBIDDEN_R1_UNCERTAINTY_ARTICLE_CLAIMS = [
    "does not currently distinguish meteorological and hydrological uncertainty",
    "Hydrological predictions are often produced using physical models",
    "local hydrological covariates",
    "meteorological and hydrological concepts are mixed",
    "under-dispersion in ensembles and perturbation methods",
]

FORBIDDEN_R1_UNCERTAINTY_CORRECTIONS_STALE_CLAIMS = [
    "we will reorganize the introduction",
    "we will separate meteorological",
    "we will distinguish meteorological",
    "we will shorten the discussion",
    "will introduce the Bayesian framework after separating",
]


@dataclass(frozen=True)
class R1UncertaintyCheck:
    item: str
    ok: bool
    detail: str


def check_r1_uncertainty_text(article_text: str, corrections_text: str) -> list[R1UncertaintyCheck]:
    checks: list[R1UncertaintyCheck] = []
    for claim in REQUIRED_R1_UNCERTAINTY_ARTICLE_CLAIMS:
        checks.append(
            R1UncertaintyCheck(
                item=f"article_required:{claim}",
                ok=claim in article_text,
                detail=claim,
            )
        )
    for claim in REQUIRED_R1_UNCERTAINTY_CORRECTIONS_CLAIMS:
        checks.append(
            R1UncertaintyCheck(
                item=f"corrections_required:{claim}",
                ok=claim in corrections_text,
                detail=claim,
            )
        )
    for claim in FORBIDDEN_R1_UNCERTAINTY_ARTICLE_CLAIMS:
        checks.append(
            R1UncertaintyCheck(
                item=f"article_forbidden:{claim}",
                ok=claim not in article_text,
                detail=claim,
            )
        )
    for claim in FORBIDDEN_R1_UNCERTAINTY_CORRECTIONS_STALE_CLAIMS:
        checks.append(
            R1UncertaintyCheck(
                item=f"corrections_forbidden_stale:{claim}",
                ok=claim not in corrections_text,
                detail=claim,
            )
        )
    return checks

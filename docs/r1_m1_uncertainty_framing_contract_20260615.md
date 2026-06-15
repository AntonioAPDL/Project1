# R1-M1 Uncertainty-Framing Contract

Status: active response/revised-article contract, June 15, 2026.

This document records the contract for Reviewer 1 major comment 1. The reviewer
argued that the original introduction mixed meteorological and hydrological
uncertainty before explaining how the Bayesian framework consolidated
uncertainty sources.

## Contract

The revised article and corrections response must preserve four points.

1. The introduction distinguishes hydrological uncertainty from
   meteorological/input uncertainty before introducing the Bayesian
   correction-and-synthesis framework.
2. Hydrological uncertainty is associated with river-system structure,
   parameters, latent states, and observations.
3. Meteorological/input uncertainty is associated with precipitation and related
   atmospheric forcing fields.
4. The transfer inputs are described as local hydrometeorological covariates,
   not as purely hydrological covariates.

## Scope

This contract does not require a full taxonomy of all hydrological-forecasting
uncertainty sources. The revised paper only needs the distinction required for
this application: available forecast products, retrospective products, and
observations carry different information and must be statistically corrected and
synthesized for probabilistic river-flow prediction.

## Validation

The contract is enforced by:

- `scripts/reviewer1_uncertainty_contract.py`;
- `tests/python/test_r1_m1_uncertainty_contract.py`;
- `scripts/validate_publication_freeze.py`;
- `scripts/validate_revision_cross_repo_wiring.py`;
- the revised-article test
  `tests/test_article_a1_and_table_contracts.py`.

The validators require the article to keep the hydrological-versus-
meteorological distinction and the `local hydrometeorological covariates`
wording. They also forbid stale main-article language that says the manuscript
does not distinguish those sources, reintroduces the old physical-model opening
sentence, or labels the precipitation-bearing covariates as only hydrological.

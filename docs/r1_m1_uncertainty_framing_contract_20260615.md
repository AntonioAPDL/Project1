# R1-M1 Uncertainty-Framing Contract

Status: active contract; current-article editorial checks updated November 7, 2026.
The earlier response remains a historical record.

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

The validators check the hydrological/meteorological uncertainty distinction and
the roles of observations, products and covariates in active LaTeX. They do not
require a particular connecting sentence or implementation label. The opening must
explain uncertainty before linking it to available information. Historical response
requirements remain unchanged. The shared current-article checks are implemented
in scripts/current_article_contract.py and the article's manuscript_text_contract.py.

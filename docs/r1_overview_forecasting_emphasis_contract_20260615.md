# R1-O Forecasting-Emphasis Contract

Status: active response/revised-article contract, June 15, 2026.

This document records the contract for Reviewer 1's overview comment. The
comment accepted the modeling contribution but argued that the original
manuscript was framed as a forecasting paper without enough forecast validation
or a clear statement of the forecasting contribution.

## Contract

The revised article and corrections response must preserve four points.

1. The manuscript is framed around forecast performance and uncertainty
   quantification, not only model development or historical fit.
2. The main empirical evidence is the five-cutoff rolling-origin forecast
   comparison with CRPS and targeted quantile diagnostics.
3. Selected-model dynamics, covariate effects, and the representative synthesis
   figure are supporting interpretation and illustration, not a second
   validation exercise.
4. The contribution is stated as a Bayesian quantile-based
   correction-and-synthesis framework supported by rolling-origin forecast
   evaluation and selected-model interpretation, rather than as dynamic
   discrepancy correction alone.

## Validation

The contract is enforced by:

- `scripts/reviewer1_overview_contract.py`;
- `tests/python/test_r1_overview_contract.py`;
- `scripts/validate_publication_freeze.py`;
- `scripts/validate_revision_cross_repo_wiring.py`;
- the revised-article test
  `tests/test_article_a1_and_table_contracts.py`.

The validators require the revised article to retain the `Forecast Validation
Results` and `Interpretation of the Selected Specification` section structure.
They also forbid stale main-article framing such as `General Results`, staged
`Model A/B/C` language, or language implying that forecast validation remains
absent.

## Non-Claims

This contract does not claim that the current five-origin evaluation is a dense
continuous hindcast. That limitation is handled by the rolling-origin forecast
design contract. This contract only protects the high-level response to the
reviewer's request to reframe, validate, and clarify the forecasting
contribution.

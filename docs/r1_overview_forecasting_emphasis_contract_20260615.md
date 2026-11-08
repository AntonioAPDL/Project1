# R1-O Forecasting-Emphasis Contract

Status: active contract; current-article editorial checks updated November 7, 2026.
The earlier response remains a historical record.

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

Current-article validators protect the six-section order through stable labels:
introduction, data, methodology, application/evaluation, results, discussion.
The predictive illustration precedes the supporting interpretation within Results.
Scientific concepts and active LaTeX are checked without locking a sentence or
obsolete section title. Staged `Model A/B/C` language and claims that the existing
forecast evidence is absent remain excluded. Historical response checks are unchanged.

## Non-Claims

This contract does not claim that the current five-origin evaluation is a dense
continuous hindcast. That limitation is handled by the rolling-origin forecast
design contract. This contract only protects the high-level response to the
reviewer's request to reframe, validate, and clarify the forecasting
contribution.

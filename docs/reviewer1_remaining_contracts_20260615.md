# Reviewer 1 Remaining-Item Contract

This document records the consolidated reproducibility contract for the
remaining Reviewer 1 major and minor items that are already substantively
implemented in the revised manuscript and response letter:

- R1-M2: model formulation linked to results.
- R1-M3: mathematical detail, PIT material, synthesis, and quantile crossing
  streamlined.
- R1-M4: forecast evidence expanded beyond the original single event.
- R1-M5: fair forecast assessment described as cutoff-specific rolling-origin
  forecast-window evaluation.
- R1-m1 to R1-m9: minor wording, data-role, forecast-protocol,
  figure-explanation, and table-caption corrections.

This contract does not change model outputs or manuscript results. Its purpose
is to make the already completed response items explicit, auditable, and
protected against future drift when the manuscript, response letter, generated
tables, or figure provenance are refreshed.

## Protected Contract

| Item | Protected publication behavior |
|---|---|
| R1-M2 | The main manuscript uses one common state-space framework and maps benchmark rows through likelihood, source-set, and transfer-treatment labels rather than the old staged A/B/C organization. |
| R1-M3 | The main text uses CRPS and targeted quantile check loss for validation, keeps posterior predictive synthesis illustrative, and leaves implementation-level MCMC/VB details in appendices. |
| R1-M4 | Forecast validation is based on five rolling-origin cutoffs with held-out USGS observations and is not represented as a continuous post-2022 hindcast. |
| R1-M5 | The evaluation is described as five cutoff-specific rolling-origin forecast-window evaluations: each cutoff defines a version-consistent staged dataset, uses only available information to fit seven quantile-specific models and synthesize the posterior predictive distribution, and verifies against held-out future USGS observations. |
| R1-m1 | The introduction acknowledges both conceptual and physically based hydrological models and motivates conceptual models as operationally practical. |
| R1-m2 | The old "flexile" typo is absent from the revised article. |
| R1-m3 | ERA5/ERA5-Land inputs are described as reanalysis-based model products, not uncertainty-free direct observations. |
| R1-m4 | The application section introduces the USGS target and separates observations, retrospective products, forecast covariates, and operational forecasts. |
| R1-m5 | Precipitation is not treated with a separate censoring, zero-inflation, or occurrence/intensity model; zero days are retained in the supplied covariate path. |
| R1-m6 | The latest-forecast-only protocol is used and older forecast issuances are not averaged into publication forecast matrices. |
| R1-m7 | Forecast validation and selected-model interpretation are separate sections; diagnostic figures are not additional validation evidence. |
| R1-m8 | Transfer-function covariate summaries report posterior means, while source-specific gamma and sigma tables report posterior medians. |
| R1-m9 | Diagnostic fitted-location/component bands are distinguished from full posterior predictive synthesis envelopes. |

## Validation Hooks

The machine-readable implementation lives in
`scripts/reviewer1_remaining_contracts.py`. It is exercised by:

- `tests/python/test_reviewer1_remaining_contracts.py`;
- `scripts/validate_publication_freeze.py`, which includes the checks in the
  publication-freeze summary;
- `scripts/validate_revision_cross_repo_wiring.py`, which writes
  `reviewer1_remaining_audit.csv` and includes the checked sources in the
  SHA-256 manifest.

The article-side companion note is
`Evironmetrics---REVISED-DOC-Corrected-2/docs/reviewer1_remaining_contracts.md`.

## Review Rule

If future calibration or manuscript editing changes any of the affected
sections, regenerate the relevant tables/figures first, then re-run the
publication-freeze and cross-repo validators before editing the corrections
response. This keeps the response letter, revised article, and workflow
provenance synchronized.

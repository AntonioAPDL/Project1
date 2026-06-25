# N-M-T1 Static Parity And Algorithm Audit Plan

Date: 2026-06-25

## Purpose

This plan defines a static, reproducible parity audit for the multivariate NDLM
keep model (`N-M-T1`, `ndlm_main_keep`) relative to the authoritative
multivariate exDQLM keep model (`exAL-M-T1`, `exdqlm_multivar_keep`).

The audit is limited to specifications, input bundles, model contracts,
algorithmic wiring, and article/table provenance. It does not include launches,
reruns, runtime monitoring, runtime health checks, tuning grids, or sensitivity
experiments.

## Scope Boundary

In scope:

1. Authoritative source resolution.
2. Frozen input-bundle parity.
3. Configuration/specification parity.
4. Covariate and forecast-product parity.
5. Harmonic and transfer-structure parity.
6. NDLM state-space and algorithm contract.
7. CRPS/table-source wiring and provenance checks.
8. Tests/validators that enforce the static contract.

Out of scope:

1. Relaunching any model.
2. Preparing launch matrices.
3. Runtime monitoring.
4. Runtime health analysis.
5. Discount-factor sensitivity experiments.
6. Hyperparameter probe runs.
7. Promotion of new model outputs.

## Current Evidence

Fresh evidence file:

- `reports/ndlm_multivar_keep_input_bundle_audit_20260625/README.md`

Main evidence so far:

1. `N-M-T1` and the current retained exDQLM figure/replay authority use the same
   substantive frozen input bundle for all five cutoffs.
2. The current article-table exDQLM source rows for `20210123` and `20211112`
   have a byte-level `retros.csv` mismatch relative to `N-M-T1`, but the
   mismatch is only decimal formatting at machine precision
   (`max_abs_numeric_diff` about `4.94e-17`).
3. `N-M-T1` is a normal/Gaussian multivariate dynamic linear model, not an exAL
   quantile model. It does not use `s_t`, `u_t`, exAL `gamma`, or the
   exAL sigma/gamma Laplace approximation.
4. The current `N-M-T1` and `exAL-M-T1` configurations differ in likelihood and
   discount/prior specification. These differences must be documented clearly;
   they should not be silently described as a likelihood-only comparison.

## Parity Classes

### Class A: Hard Equality Required

These fields/files must match exactly, except where a documented numeric
tolerance is used for decimal-format-only text differences.

1. Site identifier.
2. Cutoff date.
3. Historical start date and historical end date.
4. Forecast-window dates.
5. CRPS scoring horizon and date set.
6. Frozen run-local input files:
   - `inputs/shared/parameters/parameters.txt`
   - `inputs/shared/retros/retros.csv`
   - `inputs/shared/usgs/usgs_daily.csv`
   - `inputs/shared/forecasts/nws_forecast.csv`
   - `inputs/shared/forecasts/glofas_forecast.csv`
   - `inputs/shared/covariates/cov_01_PPT.csv`
   - `inputs/shared/covariates/cov_02_SOIL.csv`
   - `inputs/shared/covariates/cov_03_PCA.csv`
   - `inputs/shared/covariates/covariate_features.csv`
   - `inputs/shared/deterministic_climate/deterministic_precip_future.csv`
   - `inputs/shared/deterministic_climate/deterministic_soil_future.csv`
7. Transform contract:
   - retros on internal `log1p` scale
   - forecast adapters applying the same `log1p` convention
8. Forecast product contract:
   - same raw NWS forecast file
   - same raw GloFAS forecast file
   - same active lead profile
   - same member counts by active lead, where applicable
9. Engineered covariate table:
   - same rows/dates
   - same columns
   - same values

### Class B: Semantic Equality Required

These can be represented differently but must mean the same thing.

1. Transfer mode:
   - `N-M-T1` must be `keep`.
   - comparison target `exAL-M-T1` must be `keep`.
2. Harmonics:
   - NDLM may store actual harmonic values `1, 2, 1/6.8068493`.
   - exDQLM may store enabled harmonic indices `1,2,3` against the canonical
     vector `c(1, 2, 1/6.8068493)`.
   - The validator should normalize both to actual values before comparison.
3. Trend inclusion:
   - both model families should be checked for the intended trend block.
4. Covariate feature meaning:
   - PPT, SOIL, and GDPC/PCA roles must match.
   - lag orders, squares, and interactions must match.
5. Forecast raggedness:
   - the same NWS/GloFAS overlap and extension structure must be represented.

### Class C: Documented Specification Differences

These fields are not forced to be equal unless the manuscript explicitly claims
a strict specification-parity comparison. They must still be extracted,
reported, and cross-linked.

1. Likelihood family:
   - NDLM: normal/Gaussian
   - exDQLM: extended asymmetric Laplace
2. Quantile structure:
   - NDLM: one Gaussian model, not quantile-specific
   - exDQLM: quantile-indexed fits plus synthesis
3. Latent variables:
   - NDLM: no `s_t`/`u_t`
   - exDQLM: `s_t`/`u_t` latent layer
4. State-evolution discounts:
   - `df_t`
   - `df_s1`
   - `df_s2`
   - `df_s67`
   - `df_discrep`
   - `lambda`
   - `df_trans`
   - `df_covs`
5. Forecast covariance / Wishart prior fields:
   - NDLM `forecast_iw_epsilon0`
   - NDLM `forecast_iw_c_factor`
   - NDLM `forecast_iw_dof_offset`
   - NDLM `forecast_iw_scale_mult`
   - NDLM `forecast_iw_jitter`
   - exDQLM `epsilon`
   - exDQLM `c_factor`
6. Stabilization and convergence settings.
7. Posterior predictive draw counts and random seeds.

### Class D: Not Comparable

These must be explicitly marked not applicable for `N-M-T1`.

1. Quantile lanes (`q05`, `q20`, ..., `q95`).
2. exAL latent `s_t`.
3. exAL latent `u_t`.
4. exAL `gamma`.
5. sigma/gamma Laplace approximation.
6. Cross-quantile synthesis internals.

## Static Audit Workstreams

### 1. Authority Resolution Audit

Objective: identify exactly which `N-M-T1` and `exAL-M-T1` outputs are used by
the manuscript tables and figures.

Inputs:

- `Evironmetrics---REVISED-DOC-Corrected-2/tables/generated_tex/benchmark_crps_horizon_summary.csv`
- current exDQLM retained-current figure manifests
- current table/provenance manifests in the revised article repo

Outputs:

- `reports/nmt1_static_parity_audit_<DATE>/authority_rows.csv`
- `reports/nmt1_static_parity_audit_<DATE>/authority_resolution.md`

Checks:

1. Resolve each CRPS source path to a run root.
2. Resolve each retained-current exDQLM figure source to a run root.
3. Record source class: table authority, figure authority, diagnostic-only.
4. Record run id, cutoff, model label, model variant, source path, run root,
   output root, `resolved_config.yaml`, and `run_manifest.yaml`.
5. Flag any article table row whose source differs from the retained-current
   figure authority for the same cutoff/model label.

### 2. Frozen Input-Bundle Parity Audit

Objective: prove whether `N-M-T1` and `exAL-M-T1` used the same frozen inputs.

Outputs:

- `input_bundle_inventory.csv`
- `input_bundle_pairwise_comparison.csv`
- `input_bundle_parity_summary.json`
- `input_bundle_parity.md`

Checks:

1. Hash all Class A files.
2. Record rows, columns, header, size, and modification time.
3. For date-indexed CSVs, record min/max date and row count.
4. For hash mismatches, compute:
   - textual difference row count
   - max absolute numeric difference
   - max relative numeric difference where defined
5. Classify each mismatch:
   - exact mismatch
   - numeric-equivalent formatting mismatch
   - schema mismatch
   - missing file
   - substantive numeric mismatch

Hard failure conditions:

1. Missing required input.
2. Different row count.
3. Different date range.
4. Different column set.
5. Numeric mismatch above tolerance.

Recommended tolerance for formatting-only numeric mismatches:

- `max_abs_numeric_diff <= 1e-12`

### 3. Configuration And Specification Audit

Objective: extract all comparable and non-comparable specification fields into a
single machine-readable matrix.

Outputs:

- `spec_field_matrix.csv`
- `spec_pairwise_comparison.csv`
- `spec_noncomparable_fields.csv`
- `spec_summary.md`

Checks:

1. Extract model-family flags:
   - `models.run_ndlm_main`
   - `models.run_exdqlm_multivar`
   - implementation mode
   - likelihood mode
   - Kalman backend
2. Extract state-evolution fields:
   - discounts
   - `lambda`
3. Extract prior fields:
   - NDLM forecast IW fields
   - exDQLM forecast covariance fields
4. Extract convergence/stabilization fields.
5. Extract posterior draw/sample fields.
6. Mark every field as:
   - hard parity
   - semantic parity
   - documented difference
   - not applicable

Important interpretation rule:

- If discount factors differ, report the difference plainly. Do not label the
  comparison as likelihood-only unless the article text explicitly narrows the
  claim to the observed selected specifications.

### 4. Harmonic, Trend, And Transfer Structure Audit

Objective: verify that the same intended structural components are used.

Outputs:

- `harmonic_normalization.csv`
- `trend_transfer_structure.csv`
- `structure_parity.md`

Checks:

1. Normalize harmonic representation:
   - convert exDQLM enabled indices to actual harmonic values
   - compare against NDLM actual harmonic values
2. Confirm no literal third harmonic `3` is being interpreted as frequency
   `3`; it must mean the third element of `c(1,2,1/6.8068493)` for exDQLM.
3. Confirm trend inclusion.
4. Confirm retained transfer mode.
5. Confirm retrospective discrepancy blocks where model-family relevant.
6. Confirm the transfer covariate block uses the intended engineered features.

### 5. Covariate And Forecast-Product Audit

Objective: verify the static data construction used by both models.

Outputs:

- `covariate_feature_contract.csv`
- `forecast_product_contract.csv`
- `covariate_forecast_contract.md`

Checks:

1. Covariate feature table columns and roles.
2. PPT and SOIL forecast blending products.
3. GDPC/PCA file identity and column identity.
4. Lag orders.
5. Squares.
6. Interactions.
7. History-based scaling or normalization rule.
8. Forecast member counts and lead availability.
9. NWS/GloFAS horizon and ragged overlap.

### 6. N-M-T1 Algorithm Contract Audit

Objective: document and verify the active NDLM algorithm, without confusing it
with the exDQLM latent-variable algorithm.

Tracked doc output:

- `docs/ndlm_multivar_keep_algorithm_contract_20260625.md`

Report outputs:

- `ndlm_algorithm_source_map.csv`
- `ndlm_state_space_contract.csv`
- `ndlm_measurement_loading_contract.csv`

Required content:

1. Active entry point:
   - `R/unified/stages/stage_fit.R`
   - `scripts/run_ndlm_main.R`
2. Active family modules:
   - `R/unified/families/ndlm_main/00_constants.R`
   - `R/unified/families/ndlm_main/01_inputs.R`
   - `R/unified/families/ndlm_main/02_model_spec.R`
   - `R/unified/families/ndlm_main/05_fitloop.R`
   - `R/unified/families/ndlm_main/08_vb_cavi_exact.R`
   - `R/unified/families/ndlm_main/ndlm_kalman_backend.cpp`
3. Historical observation equations.
4. Forecast keep equations.
5. State block definitions.
6. Measurement-loading definitions by source and lead.
7. Forecast covariance prior construction.
8. Explicit statement that `s_t`, `u_t`, and exAL `gamma` are absent.

### 7. Article/Table Wiring Audit

Objective: prevent the revised article and corrections article from using stale
or mixed authority rows.

Outputs:

- `article_table_wiring_check.csv`
- `article_table_wiring_summary.md`

Checks:

1. `benchmark_crps_horizon_summary.csv` source paths match the selected
   authority rows.
2. The generated TeX tables reproduce the CSV values.
3. Article text does not overclaim a strict likelihood-only comparison if specs
   differ.
4. Corrections article references the same model labels and table values.
5. Any retained-current figure authority that differs from table authority is
   explicitly documented.

## Tests And Validators To Add

Recommended validator:

- `scripts/validate_nmt1_static_parity.py`

Recommended tests:

- `tests/python/test_nmt1_static_parity.py`

Test cases:

1. Exact input hash match passes.
2. Decimal-format-only mismatch passes under numeric tolerance.
3. Row-count mismatch fails.
4. Date-window mismatch fails.
5. Missing required input fails.
6. Harmonic index/value normalization passes.
7. Literal harmonic `3` as an actual frequency fails.
8. `s_t/u_t/gamma` parity requests for NDLM are marked not applicable.
9. Differing discounts are reported as documented spec differences, not hidden.
10. Table source path mismatch is flagged.

## Deliverables

Tracked docs:

1. `docs/ndlm_multivar_keep_deep_parity_plan_20260625.md`
2. `docs/ndlm_multivar_keep_algorithm_contract_20260625.md`

Tracked code/tests, if implemented:

1. `scripts/validate_nmt1_static_parity.py`
2. `tests/python/test_nmt1_static_parity.py`

Untracked report outputs:

1. `reports/nmt1_static_parity_audit_<DATE>/authority_rows.csv`
2. `reports/nmt1_static_parity_audit_<DATE>/input_bundle_parity.md`
3. `reports/nmt1_static_parity_audit_<DATE>/spec_summary.md`
4. `reports/nmt1_static_parity_audit_<DATE>/structure_parity.md`
5. `reports/nmt1_static_parity_audit_<DATE>/covariate_forecast_contract.md`
6. `reports/nmt1_static_parity_audit_<DATE>/article_table_wiring_summary.md`

## Main Takeaways

1. The next work should be a static parity validator and algorithm-contract
   audit, not a relaunch or tuning exercise.
2. `N-M-T1` should be checked against `exAL-M-T1` only on comparable objects:
   inputs, structure, covariates, forecasts, scoring, and documentation wiring.
3. exAL-specific latent-variable machinery is not part of the NDLM audit.
4. Differences in discount factors and priors are valid specification
   differences to report, not automatic bugs.
5. The article must not imply a strict likelihood-only comparison unless the
   static spec matrix supports that claim.


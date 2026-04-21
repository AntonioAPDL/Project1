# Phase 6 NDLM Transfer / Blend Contract Audit

Status: complete

## Audit Scope

- Audited `45` authoritative HE2 comparison rows against the intended all-9 featurecov contract.
- Reference contract documented in [MULTIMODEL_V8_ALL9_FEATURECOV_20260415.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/MULTIMODEL_V8_ALL9_FEATURECOV_20260415.md).
- This phase compares the current manuscript-facing rows against the intended shared featurecov design, not just against each other.

## Headline Findings

- End-to-end featurecov contract matches: `0 / 45`.
- Fit-covariate list matches: `0 / 45`.
- Engineered covariate-feature contract matches: `0 / 45`.
- Deterministic-climate / blend contract matches: `0 / 45`.
- Transfer-mode semantics still match: `45 / 45`.
- Legacy `use_covariates` semantics still match where exposed: `45 / 45`.
- Authoritative runtime rows carrying `covariate_features.csv`: `0 / 45`.
- Authoritative runtime rows carrying `deterministic_climate_summary.txt`: `0 / 45`.

## Contract Classification

Authoritative manuscript-facing rows:
- `legacy_base_covariates`: `45` rows

Reference all-9 featurecov rows:
- `featurecov_engineered_blended`: `45` rows

## Specific Interpretation

- The current authoritative HE2 rows are internally aligned to an older simpler covariate contract, not the newer featurecov contract.
- Authoritative fit covariates are `ELI|ONI|PPT|SOIL|PCA`.
- Intended featurecov fit covariates are `PPT|SOIL|PCA`.
- In the intended featurecov workflow, the reduced `PPT/SOIL/PCA` inputs are expanded through `covariate_features.csv` and deterministic-climate forecast substitution.
- The generated all-9 featurecov configs express that contract through reduced fit covariates, `inputs.covariate_features`, and `inputs.deterministic_climate`; they do not need a separate `transfer_function_covariates` key to enforce it.
- The authoritative manuscript-facing rows do not carry those runtime artifacts, so they are not using the lagged, squared, interaction-based feature matrix or the GEFS q85 blend contract now documented for the all-9 relaunch.
- This means the current NDLM-versus-quantile comparison is not yet a comparison under the newer shared featurecov specification.
- The main discrepancy in this phase is therefore not transfer-mode wiring. Keep/drop activation and `use_covariates` semantics remain aligned. The discrepancy is the broader covariate and forecast-blend contract.

## Bottom Line

- Phase 6 supports a narrower diagnosis: the poor NDLM CRPS values are not explained by mislabeled transfer modes, but the current manuscript-facing rows are still anchored in a pre-featurecov covariate regime.
- To claim a true likelihood-only comparison under the new article specification, later phases must either reproduce all families under the shared featurecov/blended-forecast contract or formally constrain the claims to the older contract.

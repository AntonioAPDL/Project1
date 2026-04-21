# NDLM Contract Remediation Report

Date: 2026-04-20  
Status: implemented, validated, and live-replayed

## Why Remediation Was Needed

Phases 1-6 showed that the manuscript-facing NDLM rows were not failing because of bad archived inputs. The real problem was contract drift:

- current NDLM manuscript rows were still on the older five-covariate regime
- deterministic-climate blending was not active in those rows
- the multivariate NDLM prior surface exposed `dof_offset` and `scale_mult`, but the active theory-aligned code path did not use them

## Remediations Implemented

### 1. Activated multivariate NDLM prior knobs

Patched:

- [08_vb_cavi_exact.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/08_vb_cavi_exact.R)

Changes:

- `nu0` now uses `dof_offset`
- `S0` now uses `scale_mult`
- both values are carried into saved diagnostics and forecast-prior outputs

### 2. Extended NDLM regression coverage

Patched:

- [test_ndlm_fitloop_contract.R](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/testthat/test_ndlm_fitloop_contract.R)
- [test_ndlm_save_state.R](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/testthat/test_ndlm_save_state.R)
- [test_ndlm_wishart_prior_audit.py](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/python/test_ndlm_wishart_prior_audit.py)

Coverage added:

- direct anchor-level use of `dof_offset`
- direct anchor-level use of `scale_mult`
- persistence of those fields in saved state and audit surfaces

### 3. Built a dedicated corrected rerun builder

Added:

- [build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py)

This builder:

- selects the best current source run per cutoff and NDLM family only as an input/provenance anchor
- rewrites the fit covariate base set to `PPT`, `SOIL`, `PCA`
- injects engineered feature generation and deterministic-climate blending
- overrides NDLM main and NDLM univariate settings from one frozen rerun spec

### 4. Added prelaunch validation and launch tooling

Added:

- [validate_ndlm_featurecov_rerun_prelaunch.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/validate_ndlm_featurecov_rerun_prelaunch.py)
- [launch_multimodel_v8_ndlm_featurecov_rerun.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/launch_multimodel_v8_ndlm_featurecov_rerun.py)
- [run_multimodel_v8_ndlm_featurecov_rerun.sh](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_multimodel_v8_ndlm_featurecov_rerun.sh)

These tools make the rerun:

- repeatable
- validated before launch
- easy to monitor through matrix/controller state

### 5. Fixed the NDLM-only post-stage contract leak

Patched:

- [stage_post.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/stages/stage_post.R)

Changes:

- `multivar_output_suffix` is now initialized unconditionally before any family-conditional branching
- NDLM-only post runs no longer depend on an exDQLM-multivar-only variable being defined
- this closes the shared post-stage contract leak that caused the first two live rerun rows to fail in `post`

## Validation Evidence

The remediation path passed:

- Python unit tests for the NDLM prior audit and rerun builder
- R regression tests for NDLM fit-loop contract and save-state contract
- `data_prep_shared` + `fit` + `post` smoke runs for all three NDLM families under the corrected featurecov contract
- clean end-to-end live replays of the formerly failing `20210123 ndlm_main_keep` and `20210123 ndlm_main_drop` rows

Evidence bundle:

- [prelaunch_validation_summary.json](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/prelaunch_validation_20260421T045415Z/prelaunch_validation_summary.json)

## Result

The active NDLM code path now matches the public prior surface more closely, and the rerun scaffolding no longer depends on mixed baseline configs to express the corrected featurecov contract.

# exDQLM Pre-Patch Verification

Date: 2026-05-20

## Baseline reference

- Branch: `feature/export_posterior_tables`
- Pre-patch checkpoint commit: `91d690e`
- Baseline tag: `exdqlm-prepatch-20260520`

This document records the baseline verification completed before starting the theory-aligned patch series.

## Theory reference set

The following documents are the locked reference set for the patch series:

- `docs/exdqlm_theory_source_map.md`
- `docs/exdqlm_sigma_gamma_equation_sheet.md`
- `docs/exdqlm_keep_drop_clarification.md`
- `docs/exdqlm_sigma_gamma_objective_audit.md`
- `docs/exdqlm_laplace_delta_audit.md`
- `docs/exdqlm_patching_strategy.md`

## Baseline tests run

The following baseline tests were re-run and passed before patching:

### Python

- `tests/python/test_prepare_reduced_defaultvb_temporal_bundle.py`

Result:
- `1 passed`

### R / testthat

- `tests/testthat/test_disc_w_state_blend.R`
- `tests/testthat/test_disc_w_state_refresh_schedule.R`
- `tests/testthat/test_disc_w_warm_start_io.R`
- `tests/testthat/test_unified_gamma_sigma_state_refresh_schedule_config.R`

Result:
- all passed

## Baseline operational notes

At patch start, runtime artifacts and live runs were intentionally kept outside the patch commit series.
The patch series is evaluated against theory docs, unit/regression tests, and controlled validation runs.

## Immediate patch priorities

1. Group A: near-zero `gamma` split optimization
2. Group B: exact pure-`u` sigma moments
3. Group C: covariance/fallback/namespace semantics
4. Group D: stale-path quarantine

## Fixture intent

The patch series should add focused fixtures covering:

1. clearly negative `gamma` modes,
2. clearly positive `gamma` modes,
3. near-zero `gamma` modes,
4. stabilized Hessian/ridge cases,
5. fallback cases where safe to test.

These fixture-backed checks are implemented as part of the patch groups rather than stored here as frozen runtime artifacts.

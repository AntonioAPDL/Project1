# exDQLM Parallel-Patch Repair Cycle

## Purpose
This note records the repair cycle that followed the first patched `2010` and `2017` parallel relaunches. The goal was to promote the Laplace/Delta patch only after we verified that the previously failing quantile lanes either:

1. stayed numerically valid, or
2. fell back safely instead of halting the worker.

This document is intentionally implementation-first. Older notes are not treated as authoritative unless they agree with both the canonical manuscript source and the active implementation.

## Failure mode that triggered this repair
The first patched relaunches no longer failed for the original `NULL` state-blend reason, but several quantile lanes still died with:

- `Var(theta_s) must be finite and >= 0`

The failure audit showed a deeper issue in the Laplace covariance path:

1. a finite matrix inverse could still be accepted as `Sigma.LD` even when it was not a valid covariance matrix,
2. the exact sigma-moment helper correctly rejected the invalid variance,
3. the uncaught exact-moment error then halted the worker.

A second issue appeared after the initial repair:

1. the worker no longer died,
2. but some guard-triggered split-gamma searches still selected boundary-saturated `gamma` values,
3. which propagated into `ELBO=NA` and effectively unusable updates.

## Repair bundles implemented in this cycle

### Bundle R1: covariance validity and sigma-moment fallback
Implemented in:
- `R/disc_w/10_gamsig_laplace.R`
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- `tests/testthat/test_disc_w_gamsig_laplace.R`

Changes:
- added strict covariance validation before accepting a Laplace covariance,
- required positive-semidefinite behavior rather than merely finite inversion,
- added guarded exact sigma-moment evaluation,
- routed exact-moment failure into sigma-only fallback or guard fallback instead of halting.

### Bundle R2: boundary-saturated split-gamma rejection and non-finite expectation fallback
Implemented in:
- `R/disc_w/10_gamsig_laplace.R`
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- `tests/testthat/test_disc_w_gamsig_laplace.R`

Changes:
- added support-margin checks for `gamma` itself, not just transformed-parameter interior checks,
- rejected split candidates that were technically interior in `theta_g` but effectively on the `gamma` support boundary,
- forced sigma-only fallback when no acceptable split candidate remained,
- wrapped Laplace expectation calculations so non-finite expected values trigger fallback instead of silently propagating `NA`.

## Verification strategy
We used three layers of verification.

### 1. Unit and contract tests
Focused tests were run after each repair bundle:
- `tests/testthat/test_disc_w_gamsig_laplace.R`
- `tests/testthat/test_stage_fit_preflight.R`
- `tests/testthat/test_disc_w_sampling_contracts.R`
- `tests/testthat/test_disc_w_state_refresh_schedule.R`
- `tests/testthat/test_unified_gamma_sigma_state_refresh_schedule_config.R`
- `tests/python/test_prepare_reduced_defaultvb_temporal_bundle.py`
- `tests/python/test_data_start_usgs_filter_contract.py`
- `tests/python/test_stage_fit_quantile_gamma_sigma_overrides.py`
- `tests/python/test_exdqlm_median_warmup_probes.py`

### 2. Synthetic local covariance reproduction
We reproduced the invalid-covariance case locally using an indefinite precision matrix and verified:
- the old path accepted it incorrectly,
- the repaired path rejects it or repairs it with ridge regularization,
- exact sigma moments no longer halt on that synthetic case.

### 3. Targeted live fix-verify runs
Instead of relaunching full campaigns immediately, we targeted the historically bad quantile lanes:
- `2010 q80`
- `2010 q95`
- `2017 q20`
- `2017 q50`
- `2017 q80`

Each was launched as a one-quantile, one-worker, `max_iter=250` diagnostic run under the same data window, discount factors, and state-refresh schedule as the failing patched campaigns.

## Current live interpretation
At the time of writing:
- the short-window failures (`2010 q80`, `2017 q20`, `2017 q50`, `2017 q80`) have been rechecked on clean diagnostic roots,
- the original hard worker-halting covariance failure has not reappeared,
- the second repair removed the previous `ELBO=NA` / saturated `gamma` behavior on the fast-failing lanes,
- `2010 q95` is still the long-horizon validation lane because its historical failure point occurred much later.

## Promotion rule
The patch is ready for full-run relaunch promotion only when:

1. `2010 q95` remains numerically healthy through its historical failure region, and
2. the older production runs remain untouched, and
3. the new full patched relaunches start cleanly and survive the first real `gamma/sigma` update region.

## Related runtime evidence
Operational evidence for this repair cycle lives outside git in:
- `reports/exdqlm_parallelpatch_failure_audit_20260520/`
- `reports/exdqlm_parallelpatch_fixverify_20260520/`

These report directories are intentionally left untracked.

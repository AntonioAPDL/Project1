# NDLM likelihood/update-path audit

Question:
- Is the apparent overfit caused by Gaussian-likelihood update defects, or by diagnostic use of smoothed state fit?

Findings:
1. Existing diagnostics were based on smoothed-state observation fit:
   - `R/unified/families/ndlm_main/02_model_spec.R` computes `fitted_mean` from smoothed state (`ms`).
   - `R/unified/ndlm_post_diagnostics.R` previously evaluated coverage against `exps[2,]` (smoothed path).
2. This can make in-sample fit appear unnaturally tight even when one-step fit is weaker.
3. No direct evidence of Gaussian-likelihood sign/scale bug was found in this audit pass.

Implemented changes (this execution):
- Kalman outputs now export all three observation-space fit modes:
  - one-step predicted,
  - filtered,
  - smoothed.
- NDLM post diagnostics now export side-by-side mode series/coverage.

Files changed:
- `R/unified/families/ndlm_main/02_model_spec.R`
- `R/unified/families/ndlm_main/ndlm_kalman_backend.cpp`
- `R/unified/families/ndlm_main/03_vb_updates.R`
- `R/unified/families/ndlm_main/06_save_state.R`
- `R/unified/ndlm_post_diagnostics.R`
- `tests/testthat/test_ndlm_kalman_backend.R`
- `tests/testthat/test_ndlm_save_state.R`

Current root-cause classification:
- Primary: diagnostics interpretation issue (smoothed fit viewed as primary fit diagnostic).
- Secondary (still open): calibration quality itself; requires reading new mode-separated outputs on next NDLM run.

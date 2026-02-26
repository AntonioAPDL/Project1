# NDLM vs multiv exDQLM parity audit (state-evolution path)

Scope:
- Compare discount/W_t mechanics and transition/covariance wiring (excluding likelihood differences).

Reference anchors:
- NDLM (unified):
  - `R/unified/families/ndlm_main/03_vb_updates.R`
  - `R/unified/families/ndlm_main/ndlm_kalman_backend.cpp`
- multiv exDQLM (reference):
  - `R/environmetrics/20_model_setup.R`
  - `DISC_kalman_synth.cpp`
  - `scripts/run_DISC_Optimal_Synth_Ranges_W.R`

Comparison summary:
1. Discount-factor parameter family is aligned conceptually (`df_t`, `df_s1`, `df_s2`, `df_s67`, discrepancy scaling, `lambda`, transition/covariance factors).
2. W_t construction uses element-wise scaling by discount matrices in both implementations.
3. multiv C++ path uses robust SVD-based inverses broadly (`robust_svd_inv`, `robust_svd_inv_sqrt`).
4. NDLM C++ path uses `inv_sympd` + regularized fallback (`safe_inv_sympd`) and explicit SPD repair at R layer.

Risk note:
- Numerical linear algebra strategy is not identical (SVD-heavy in multiv vs sympd-first in NDLM). This is not necessarily wrong, but should be tracked as a numerical-stability divergence.

Status:
- No blocking mismatch found in discount/W_t contract semantics.
- Numerical strategy divergence remains a watch item.

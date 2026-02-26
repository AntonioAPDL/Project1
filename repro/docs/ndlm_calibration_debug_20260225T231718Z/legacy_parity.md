# Modern NDLM vs legacy NDLM parity audit

Legacy anchors reviewed:
- `scripts/_notebook_linearized.R`
- `DISC_kalman_synth_NDLM.cpp`
- `kalman_synth_NDLM.cpp`

Drift classification table:

| Area | Classification | Note |
|---|---|---|
| Discount-factor family (`df_t`, `df_s1`, `df_s2`, `df_s67`, `df_discrep`, `lambda`) | intentional_theory_update | Preserved and made explicit in unified NDLM constants + logs. |
| Forecast covariance treatment | intentional_theory_update | Unified NDLM follows current model-spec direction (including forecast covariance handling), not strictly old notebook defaults. |
| Numerical stabilization path | legacy_technical_debt | Legacy and unified differ in matrix inversion/cholesky stabilization strategies. |
| Fit diagnostic metric definition (smoothed-only evaluation) | unexpected_mismatch | This was causing misleading overfit signal interpretation; fixed by exporting one-step/filtered/smoothed diagnostics side-by-side. |

Conclusion:
- Main actionable mismatch for this phase was diagnostic interpretation, not proven likelihood-sign bug.

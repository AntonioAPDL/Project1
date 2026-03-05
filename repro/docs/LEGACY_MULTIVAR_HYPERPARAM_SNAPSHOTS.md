# Legacy Multivar Hyperparameter Snapshots

This file records key legacy multivariate exDQLM hyperparameters used in unified runs.

## Baseline defaults (captured on 2026-02-27 before custom override run)

Source of truth before env/YAML override wiring:
- `DISC_Optimal_Synth_Ranges_W.r` (hardcoded defaults)

Values:
- `initial_delta = [df_t, df_s1, df_s2, df_s67, df_discrep, lambda] = [0.9999995, 0.9997, 0.9997, 0.9997, 0.999, 0.8995]`
- `df_trans = 0.99999999`
- `df_covs = 0.99999`
- `lam1 = 0.999999`
- `lam2 = 0.999999`
- `n_samp = 2000`
- `sims_enabled = TRUE`
- `use_covariates = TRUE`

## Custom test override request (2026-02-27)

Requested by user for isolated multivar q=0.50 run:
- `initial_delta = [0.99997, 0.99997, 0.99997, 0.99997, 0.99997, 0.8995]`
- `df_trans = 0.99999999`
- `df_covs = 0.99999999`

Run config path:
- `config/unified_runs/diag_multiv_only_legacy_bridge_q50_customdelta_20260227.yaml`


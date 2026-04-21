# NDLM Featurecov Rerun Specification Freeze

Date: 2026-04-20  
Status: frozen for launch

## Purpose

Freeze one corrected NDLM rerun contract for the manuscript-facing NDLM families so the relaunch no longer inherits mixed baseline settings from older source lineages.

## Rerun Scope

- Families:
  - `ndlm_main_keep`
  - `ndlm_main_drop`
  - `ndlm_univar_keep`
- Cutoffs:
  - `20210123`
  - `20211112`
  - `20211221`
  - `20220511`
  - `20221225`
- Total rows: `15`

## Authoritative Campaign Surface

- Template: [multimodel_v8_ndlm_featurecov_rerun.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_ndlm_featurecov_rerun.template.yaml)
- Builder: [build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py)
- Validator: [validate_ndlm_featurecov_rerun_prelaunch.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/validate_ndlm_featurecov_rerun_prelaunch.py)
- Launcher: [launch_multimodel_v8_ndlm_featurecov_rerun.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/launch_multimodel_v8_ndlm_featurecov_rerun.py)

## Frozen Input Contract

- Archived cutoff-consistent snapshots are still reused for:
  - parameters
  - retrospectives
  - NWS forecasts
  - GloFAS forecasts
  - shared base covariate CSVs
- The rerun no longer accepts the older five-covariate fit contract.
- The frozen fit covariates are exactly:
  - `PPT`
  - `SOIL`
  - `PCA`
- Engineered covariate features are always enabled:
  - lag orders `1, 2, 3`
  - squared terms enabled
  - `PPT x SOIL` interaction enabled
- Deterministic-climate blending is always enabled from the recovered GEFS/NWM handoff:
  - precipitation source `gefs_apcp`, reduction `q85`
  - soil source `gefs_soilw_0_0.1m`, reduction `q85`
  - noisy and observed blends preserved from the all-9 featurecov contract

## Frozen NDLM Main Contract

- Implementation mode: `theory_aligned`
- Kalman backend: `cpp`
- Transfer mode is family-specific only:
  - `ndlm_main_keep -> keep`
  - `ndlm_main_drop -> drop`
- Seasonality:
  - period `363.5854`
  - harmonics `[1, 2, 0.1469118904]`
- State evolution:
  - `df_t = 0.99999999`
  - `df_s1 = 0.99999999`
  - `df_s2 = 0.99999999`
  - `df_s67 = 0.99999999`
  - `df_discrep = 0.99999999`
  - `lambda = 0.97`
  - `df_trans = 0.9999999`
  - `df_covs = 0.99999999`
- Forecast covariance prior:
  - `c_factor = 1.0`
  - `epsilon = null` so runtime `epsilon0` still falls back to `T`
  - `dof_offset = 4`
  - `scale_mult = 1.0`
  - `jitter = 1e-8`
- Stabilization:
  - `cov_eig_floor = 1e-8`
  - `cov_eig_cap = 1e8`
  - `cov_diag_jitter = 1e-10`
  - `sigma_upper_cap = 1e12`
  - `sigma_update_damping = 1.0`
  - `latent_var_cap_mult = 1e4`
  - `latent_var_cap_abs = 1e8`
- Fit gamma-sigma loop:
  - `min_total_iters = 20`
  - `max_iter = 100`
  - `elbo_tol = 1e-6`
  - `elbo_rel_tol = 2.5e-4`

## Frozen NDLM Univariate Contract

- Implementation mode: `theory_aligned_closed_form`
- Kalman backend: `cpp`
- Transfer mode: `keep`
- Seasonality:
  - period `363.5854`
  - harmonics `[1, 2, 3]`
- `horizon_cap = 90`
- `posterior_draws = 64`
- Prior:
  - `n0 = 20`
  - `S0 = 1`
- State evolution:
  - `df_t = 0.99999999`
  - `df_s1 = 0.99999999`
  - `df_s2 = 0.99999999`
  - `df_s67 = 0.99999999`
  - `lambda = 0.97`
  - `df_trans = 0.9999999`
  - `df_covs = 0.99999999`

## What Is Intentionally Family-Specific

- NDLM keeps its own Normal-likelihood family implementation.
- NDLM main and NDLM univariate retain their own state and prior structures.
- `keep` versus `drop` remains a transfer-mode distinction, not a different input-data contract.

## What Is No Longer Allowed To Drift

- fit covariate base set
- engineered feature matrix activation
- deterministic-climate blending
- NDLM main prior knobs (`dof_offset`, `scale_mult`)
- NDLM main state-evolution defaults across cutoffs
- NDLM univariate state-evolution defaults across cutoffs

## Launch Evidence

The frozen contract is backed by the successful prelaunch validation at:

- [prelaunch_validation_summary.json](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/prelaunch_validation_20260421T045415Z/prelaunch_validation_summary.json)
- [prelaunch_validation_summary.md](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/prelaunch_validation_20260421T045415Z/prelaunch_validation_summary.md)

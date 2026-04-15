# Multimodel v8 All-9 Feature-Covariate Relaunch (2026-04-15)

## Scope

- Relaunch all 9 model families across 5 cutoffs using the best currently selected source run per `(cutoff, model type)`.
- Add a shared engineered covariate layer built from run-scoped `PPT`, `SOIL`, and `PCA`.
- Do not launch until `inputs.deterministic_climate.handoff_root` is set to a valid handoff cache root.

## Engineered Covariates

- Base covariates: `PPT`, `SOIL`, `PCA`
- Nonlinear terms: `PPT^2`, `SOIL^2`, `PPT * SOIL`
- Lag terms: `PPT_lag1..3`, `SOIL_lag1..3`
- Forecast-window rule:
  - use observed `PPT` and `SOIL` through cutoff `T`
  - use deterministic post-cutoff `PPT` and `SOIL` from the run-scoped climate substitution after `T`
  - keep `PCA` as passthrough
  - lags after cutoff are built from the stitched observed-plus-forecast `PPT`/`SOIL` series

## Current Build Status

- Builder output: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_all9_featurecov_20260415/control/featurecov_v1/`
- Generated configs: `45`
- Matrix rows: `45`
- Launch wrapper blocks real launch while `handoff_root` is unset.

## Selected Best Source Specs

### 20210123

| family_id | model_id | selected_epsilon | selected_c_factor | source_run | selected_mean_crps |
|---|---|---:|---:|---|---:|
| `dqlm_multivar_al_drop` | `dqlm_multivar_al_synth_drop` | `30.0` | `1.0` | `multimodel_20210123_v8_eps30cf1_l1_mv` | `0.325237` |
| `dqlm_multivar_al_keep` | `dqlm_multivar_al_synth_keep` | `180.0` | `1.0` | `multimodel_20210123_v8_eps180cf1_l1_mv` | `0.121244` |
| `dqlm_univar_al` | `dqlm_univar_al_synth` | `TT` | `NA` | `multimodel_20210123_v8_epsTT_l1` | `0.294603` |
| `exdqlm_multivar_drop` | `exdqlm_multivar_synth_drop` | `30.0` | `1.0` | `multimodel_20210123_v8_eps30cf1_l2_mv` | `0.331506` |
| `exdqlm_multivar_keep` | `exdqlm_multivar_synth_keep` | `180.0` | `1.0` | `multimodel_20210123_v8_eps180cf1_l2_mv` | `0.129499` |
| `exdqlm_univar` | `exdqlm_univar_synth` | `TT` | `NA` | `multimodel_20210123_v8_epsTT_l2` | `0.296919` |
| `ndlm_main_drop` | `ndlm_main_synth_drop` | `TT` | `1.0` | `multimodel_20210123_v8_epsTT_l2` | `0.359930` |
| `ndlm_main_keep` | `ndlm_main_synth_keep` | `TT` | `1.0` | `multimodel_20210123_v8_ndlm_tune_20260411_v1_ndlm_main_keep` | `2.406850` |
| `ndlm_univar_keep` | `ndlm_univar_synth_keep` | `TT` | `NA` | `multimodel_20210123_v8_ndlm_tune_20260411_v1_ndlm_univar_keep` | `0.495433` |

### 20211112

| family_id | model_id | selected_epsilon | selected_c_factor | source_run | selected_mean_crps |
|---|---|---:|---:|---|---:|
| `dqlm_multivar_al_drop` | `dqlm_multivar_al_synth_drop` | `30.0` | `100.0` | `multimodel_20211112_v8_eps30_l1_mv` | `0.254715` |
| `dqlm_multivar_al_keep` | `dqlm_multivar_al_synth_keep` | `TT` | `1.0` | `multimodel_20211112_v8_epsTTcf1_l1_mv` | `0.023663` |
| `dqlm_univar_al` | `dqlm_univar_al_synth` | `TT` | `NA` | `multimodel_20211112_v8_epsTT_l1` | `0.133267` |
| `exdqlm_multivar_drop` | `exdqlm_multivar_synth_drop` | `30.0` | `100.0` | `multimodel_20211112_v8_eps30_l2_mv` | `0.283645` |
| `exdqlm_multivar_keep` | `exdqlm_multivar_synth_keep` | `TT` | `1.0` | `multimodel_20211112_v8_epsTTcf1_l2_mv` | `0.020137` |
| `exdqlm_univar` | `exdqlm_univar_synth` | `TT` | `NA` | `multimodel_20211112_v8_epsTT_l2` | `0.135044` |
| `ndlm_main_drop` | `ndlm_main_synth_drop` | `TT` | `1.0` | `multimodel_20211112_v8_epsTT_l2` | `0.322562` |
| `ndlm_main_keep` | `ndlm_main_synth_keep` | `TT` | `1.0` | `multimodel_20211112_v8_epsTT_l1` | `0.355715` |
| `ndlm_univar_keep` | `ndlm_univar_synth_keep` | `TT` | `NA` | `multimodel_20211112_v8_ndlm_tune_20260411_v1_ndlm_univar_keep` | `0.817004` |

### 20211221

| family_id | model_id | selected_epsilon | selected_c_factor | source_run | selected_mean_crps |
|---|---|---:|---:|---|---:|
| `dqlm_multivar_al_drop` | `dqlm_multivar_al_synth_drop` | `TT` | `1.0` | `multimodel_20211221_v8_epsTTcf1_l1_mv` | `0.670785` |
| `dqlm_multivar_al_keep` | `dqlm_multivar_al_synth_keep` | `90.0` | `100.0` | `multimodel_20211221_v8_eps90_l1_mv` | `0.359512` |
| `dqlm_univar_al` | `dqlm_univar_al_synth` | `TT` | `NA` | `multimodel_20211221_v8_epsTT_l1` | `1.137704` |
| `exdqlm_multivar_drop` | `exdqlm_multivar_synth_drop` | `90.0` | `1.0` | `multimodel_20211221_v8_eps90cf1_l2_mv` | `0.574574` |
| `exdqlm_multivar_keep` | `exdqlm_multivar_synth_keep` | `90.0` | `100.0` | `multimodel_20211221_v8_eps90_l2_mv` | `0.283043` |
| `exdqlm_univar` | `exdqlm_univar_synth` | `TT` | `NA` | `multimodel_20211221_v8_epsTT_l2` | `1.204329` |
| `ndlm_main_drop` | `ndlm_main_synth_drop` | `TT` | `1.0` | `multimodel_20211221_v8_epsTT_l2` | `2.046148` |
| `ndlm_main_keep` | `ndlm_main_synth_keep` | `TT` | `1.0` | `multimodel_20211221_v8_epsTT_l1` | `1.878909` |
| `ndlm_univar_keep` | `ndlm_univar_synth_keep` | `TT` | `NA` | `multimodel_20211221_v8_ndlm_tune_20260411_v1_ndlm_univar_keep` | `0.589342` |

### 20220511

| family_id | model_id | selected_epsilon | selected_c_factor | source_run | selected_mean_crps |
|---|---|---:|---:|---|---:|
| `dqlm_multivar_al_drop` | `dqlm_multivar_al_synth_drop` | `30.0` | `1.0` | `multimodel_20220511_v8_eps30cf1_l1_mv` | `0.045959` |
| `dqlm_multivar_al_keep` | `dqlm_multivar_al_synth_keep` | `TT` | `100.0` | `multimodel_20220511_v8_epsTT_l1` | `0.015679` |
| `dqlm_univar_al` | `dqlm_univar_al_synth` | `TT` | `NA` | `multimodel_20220511_v8_epsTT_l1` | `0.046546` |
| `exdqlm_multivar_drop` | `exdqlm_multivar_synth_drop` | `TT` | `100.0` | `multimodel_20220511_v8_epsTT_l2` | `0.069475` |
| `exdqlm_multivar_keep` | `exdqlm_multivar_synth_keep` | `TT` | `100.0` | `multimodel_20220511_v8_epsTT_l2` | `0.016496` |
| `exdqlm_univar` | `exdqlm_univar_synth` | `TT` | `NA` | `multimodel_20220511_v8_epsTT_l2` | `0.046843` |
| `ndlm_main_drop` | `ndlm_main_synth_drop` | `TT` | `1.0` | `multimodel_20220511_v8_epsTT_l2` | `0.935611` |
| `ndlm_main_keep` | `ndlm_main_synth_keep` | `TT` | `1.0` | `multimodel_20220511_v8_epsTT_l1` | `1.325617` |
| `ndlm_univar_keep` | `ndlm_univar_synth_keep` | `TT` | `NA` | `multimodel_20220511_v8_ndlm_tune_20260411_v1_ndlm_univar_keep` | `0.728249` |

### 20221225

| family_id | model_id | selected_epsilon | selected_c_factor | source_run | selected_mean_crps |
|---|---|---:|---:|---|---:|
| `dqlm_multivar_al_drop` | `dqlm_multivar_al_synth_drop` | `1.0` | `1.0` | `multimodel_20221225_v8_eps1cf1_l1_mv` | `2.195549` |
| `dqlm_multivar_al_keep` | `dqlm_multivar_al_synth_keep` | `90.0` | `1.0` | `multimodel_20221225_v8_eps90cf1_l1_mv` | `0.663952` |
| `dqlm_univar_al` | `dqlm_univar_al_synth` | `TT` | `NA` | `multimodel_20221225_v8_epsTT_l1` | `1.029263` |
| `exdqlm_multivar_drop` | `exdqlm_multivar_synth_drop` | `1.0` | `1.0` | `multimodel_20221225_v8_eps1cf1_l2_mv` | `2.278513` |
| `exdqlm_multivar_keep` | `exdqlm_multivar_synth_keep` | `90.0` | `1.0` | `multimodel_20221225_v8_eps90cf1_l2_mv` | `0.599110` |
| `exdqlm_univar` | `exdqlm_univar_synth` | `TT` | `NA` | `multimodel_20221225_v8_epsTT_l2` | `0.932420` |
| `ndlm_main_drop` | `ndlm_main_synth_drop` | `TT` | `1.0` | `multimodel_20221225_v8_epsTT_l2` | `3.232163` |
| `ndlm_main_keep` | `ndlm_main_synth_keep` | `TT` | `1.0` | `multimodel_20221225_v8_epsTT_l1` | `2.878452` |
| `ndlm_univar_keep` | `ndlm_univar_synth_keep` | `TT` | `NA` | `multimodel_20221225_v8_epsTT_l1` | `1.161732` |

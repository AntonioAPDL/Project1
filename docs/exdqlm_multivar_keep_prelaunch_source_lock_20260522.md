# exDQLM Multivariate Keep Prelaunch Source Lock

Date: 2026-05-22

Scope: no-launch verification of the `2022-12-25` full-history HE2 `exdqlm_multivar_keep` prelaunch package after
retargeting discounts to the requested `df99999`/`eps365` profile.

## Sources Checked

Primary active package:

- template:
  `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20221225_fullhistory_promotion_20260522.template.yaml`
- batch:
  `config/he2_relaunch_batches/exdqlm_multivar_keep_20221225_fullhistory_promotion_20260522.yaml`

Legacy/source-lock references:

- May 18 generated config:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_discount_refresh_retained_20260518/control/generated_configs/multimodel_20221225_v8_he2pubgdpc1r1_df99999_eps365_sigp001v1e3_retainrdata_exdqlm_multivar_keep.yaml`
- May 18 resolved config:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_discount_refresh_retained_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_df99999_eps365_sigp001v1e3_retainrdata_exdqlm_multivar_keep/resolved_config.yaml`
- May 18 discount spec:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_discount_refresh_retained_20260518/control/multimodel_20221225_v8_he2pubgdpc1r1_df99999_eps365_sigp001v1e3_retainrdata_exdqlm_multivar_keep_discount_spec.yaml`
- selected set09 representative:
  `config/unified_runs_publication_replay_representatives_20260506/20221225_exal_m_t1/multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep.yaml`
- canonical shared bundle:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`

## Locked Prelaunch Contract

| field | active prelaunch value | verification |
| --- | --- | --- |
| cutoff | `2022-12-25` | template selects only `20221225` |
| family | `exdqlm_multivar_keep` | template/batch select only this family |
| data start | `1987-05-29` | template bundle and generated builder contract |
| quantiles | `0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95` | batch patch and builder test |
| transform | `log1p_cms`, `transform_policy: log1p_only` | batch patch and generated config test |
| covariates | `PPT`, `SOIL`, `PCA` | builder maps to canonical shared bundle covariates |
| engineered terms | `PPT_sq`, `SOIL_sq`, `PPT_x_SOIL`, `PPT_lag1:3`, `SOIL_lag1:3` | batch patch and generated config test |
| harmonic basis | indices `[1, 2, 3]` -> values `c(1, 2, 1/6.8068493)` | `tests/testthat/test_exdqlm_multivar_structure_contract.R` |
| `df_t` | `0.99999` | requested value and batch patch |
| `df_s1`, `df_s2`, `df_s67` | `0.9999` | requested value and batch patch |
| `df_discrep` | `0.9999` | requested value and batch patch |
| `lambda` | `0.97` | requested value and batch patch |
| `df_trans` | `0.9999999` | requested value and batch patch |
| `df_covs` | `0.9999999` | requested value and batch patch |
| Wishart forecast prior | `epsilon=365.0`, `c_factor=1.0` | requested value and batch patch |
| VB iterations | `max_iter=200` | requested prelaunch smoke setting |

## Legacy Comparison

The May 18 `df99999_eps365_sigp001v1e3` retained run confirms the intended old-run family of settings:

- full history from `1987-05-29`;
- all seven quantiles;
- `PPT`, `SOIL`, `PCA` fit covariates from the 20260510 shared bundle;
- full transfer-feature list;
- `df_t=0.99999`;
- `df_s1=df_s2=df_s67=df_discrep=0.9999`;
- `lambda=0.97`;
- `df_trans=0.9999999`;
- forecast `epsilon=365.0`, `c_factor=1.0`;
- `max_iter=200`.

The only intentional discount difference from that May 18 resolved config is `df_covs`: May 18 used `0.99999`; the
active prelaunch package uses the explicitly requested `0.9999999`.

The May 6 set09 representative is still useful as a publication lineage reference, but it is not the current
discount/Wishart target because it used `df_t=0.99999999`, `df_s1=df_s2=0.9998`, `df_discrep=0.998`, and
`epsilon=360.0`.

The generated relaunch metadata still carries `selected_spec_token: set09` because the builder records the source
publication manifest row. The active prelaunch values are therefore verified from the generated config and
`frozen_spec_manifest.csv` `config_patch_json`, not from the lineage token alone.

## Input Bundle Check

The active template points to:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`

with bundle run id `20260510_publication_shared_r01`. The checked bundle contains:

- `retros.csv` with columns `Date, USGS, GloFAS, NWS3.0`;
- `nws_forecast.csv` with seven forecast members;
- `glofas_forecast.csv` with fifty-one forecast members plus `member_00`;
- `cov_03_PPT.csv`;
- `cov_04_SOIL.csv`;
- `cov_05_PCA.csv`;
- support manifest mapping `PCA` to the canonical GDPC PCA alias source.

The bundle metadata records `bundle_kind: multimodel_v8_histfix_long_history`, `data_start: 1987-05-29`, and
`transforms.plot_scale: log1p_cms`.

## Guarding Caveat

The prelaunch package keeps the audited promotion-v2 guards. Because `max_iter=200` and
`state_guard_start_iter=1000`, a 200-iteration smoke does not exercise the delayed state-norm guard. It still verifies
static wiring, generated config content, latent cap export, pseudo-data guard export, input paths, and early fit
configuration. A later longer candidate is still required to test delayed state-guard behavior.

## No-Launch Boundary

No model relaunch was run during this source-lock pass. The checks are static, parser-level, and temporary
builder-output validations only.

## Validation Completed

The following no-launch checks passed after retargeting the package:

| check | result |
| --- | --- |
| `Rscript --vanilla -e "invisible(parse('R/unified/config.R')); invisible(parse('R/unified/stages/stage_fit.R'))"` | pass |
| `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_config_mode_resolution.R')"` | pass, 49 expectations |
| `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_structure_contract.R')"` | pass, 6 expectations |
| `python3 -m unittest tests.python.test_he2_publication_relaunch_template -v` | pass, 19 tests |
| `python3 -m unittest tests.python.test_he2_publication_relaunch_builder_selection.HE2PublicationRelaunchBuilderSelectionTests.test_exdqlm_fullhistory_promotion_batch_builds_guarded_20221225_config -v` | pass, 1 test |
| `python3 -m unittest tests.python.test_disc_sampling_diagnostics_source_contract -v` | pass, 6 tests |
| direct batch-value assertion for requested discounts/Wishart/max-iter/harmonic indices | pass |
| `git diff --check` | pass |

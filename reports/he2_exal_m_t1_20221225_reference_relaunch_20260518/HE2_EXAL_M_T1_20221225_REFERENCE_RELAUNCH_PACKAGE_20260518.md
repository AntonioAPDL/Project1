# exAL-M-T1 Representative Relaunch Package

This package prepares a **single-cutoff representative relaunch** for `exAL-M-T1` at cutoff `2022-12-25`. It is **prepared but not launched**.

## Decision Frame

- Goal: rerun one representative cutoff cleanly so we can inspect fit traces, retained fit-state `.RData`, posterior summaries, synthesis figures, and post tables before any family-wide relaunch.
- Policy: keep the corrected shared input bundle and the current shared-spec discount/epsilon contract unchanged for now; extend fit budget from `100` to `200` iterations and make the warm-up hold length common at `10` iterations across all quantiles.
- Heavy-state retention: this package must **not** use the queue cleanup wrapper. It must launch through the direct no-cleanup runner so fit-state `.RData` survives post.

## Prepared Artifacts

- template: [`links/template.yaml`](./links/template.yaml)
- batch: [`links/batch.yaml`](./links/batch.yaml)
- generated config: [`links/candidate_generated_config.yaml`](./links/candidate_generated_config.yaml)
- direct no-cleanup launcher: [`links/launch_no_cleanup.sh`](./links/launch_no_cleanup.sh)
- shared-bundle metadata: [`links/bundle_meta.yaml`](./links/bundle_meta.yaml)

## Candidate vs Current vs Publication Source

| Spec | df_s1 | df_s2 | df_s67 | df_discrep | lambda | epsilon | c_factor | max_iter | fit internal scale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `candidate_reference_relaunch` | `0.99999` | `0.99999` | `0.99999` | `0.99999` | `0.97` | `30.0` | `1.0` | `200` | `log1p_cms` |
| `current_sharedspec_run` | `0.99999` | `0.99999` | `0.99999` | `0.99999` | `0.97` | `30.0` | `1.0` | `100` | `log1p_cms` |
| `publication_exact_source` | `0.9998` | `0.9998` | `0.9999` | `0.998` | `0.97` | `360.0` | `1.0` | `100` | `log_log1p_cms` |

## What Changes In This Candidate

- `max_iter`: `100 -> 200` for `fit.exdqlm_multivar.gamma_sigma`
- `warmup_freeze_iters`: unified to `10` across all seven quantiles
- launch path: use `scripts/run_unified_without_cleanup.sh` so post does not delete fit-state `.RData`
- everything else stays on the corrected shared-spec baseline for now:
  - full-history repaired shared input bundle
  - `log1p_cms` fit/post internal scale
  - same quantile list
  - same q35/q50 state-freeze overrides and stabilization blocks
  - same `epsilon=30`, `c_factor=1` current shared-spec covariance-prior contract

## Quantile-by-Quantile Review

Review table: [`quantile_review_matrix.csv`](./quantile_review_matrix.csv)

| q | current freeze_target | current warmup | first update iter | updates at preflight | last sigma_exp | last gamma_exp | last state_norm_sq | nonfinite forecast exps | recommendation |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `q05` | `gamma_sigma` | `5` | `6` | `95` | `0.1505987` | `-0.0545162` | `17667119.0` | `48` | extend gamma/sigma freeze hold to 10 |
| `q20` | `gamma_sigma` | `5` | `6` | `95` | `0.01603074` | `-0.2826537` | `92543.37` | `48` | extend gamma/sigma freeze hold to 10 |
| `q35` | `states` | `8` | `1` | `100` | `0.03477374` | `-0.5940608` | `550040.5` | `48` | keep state-freeze path; extend common hold to 10 |
| `q50` | `states` | `5` | `1` | `100` | `0.008623681` | `1.056023` | `40245.6` | `48` | keep state-freeze path; extend common hold to 10 |
| `q65` | `gamma_sigma` | `5` | `6` | `95` | `0.01151543` | `0.5942656` | `62524.85` | `48` | extend gamma/sigma freeze hold to 10 |
| `q80` | `gamma_sigma` | `5` | `6` | `95` | `0.0164745` | `0.2834627` | `148796.0` | `48` | extend gamma/sigma freeze hold to 10 |
| `q95` | `gamma_sigma` | `5` | `6` | `95` | `0.1494973` | `0.05450874` | `17958348.0` | `48` | extend gamma/sigma freeze hold to 10 |

Warm-up decision rationale:

- all seven quantiles were still improving at `iter=100`; none had a terminal fit-side settle point before sampling
- `q05`, `q20`, `q65`, `q80`, and `q95` delay their first live gamma/sigma update until after the base warm-up ends, so a modest common hold extension is the least invasive warm-up-only lever
- `q35` and `q50` already use `freeze_target=states`; we preserve that path and only align their hold length to the same common `10`
- we do **not** change discount factors, `epsilon`, `c_factor`, or the special q35/q50 stabilization blocks in this candidate

## Config Section Review

Section review table: [`config_section_review.csv`](./config_section_review.csv)

| section | status | key points |
|---|---|---|
| `run` | `pass` | strict repro mode, fixed seed, thread caps at 1, mc_cores=7 |
| `stages` | `pass` | data_prep_shared+fit+post+validate+report enabled; forecats disabled |
| `inputs` | `pass` | shared 20260510 bundle, full history, deterministic climate, PPT/SOIL/PCA covariates |
| `fit_gamma_sigma` | `pass` | max_iter=200, common warmup=10, q35/q50 state freeze preserved |
| `fit_legacy` | `pass` | n_samp=2000, epsilon=30, c_factor=1, sampling diagnostics on |
| `post` | `pass` | figures+tables enabled, smoke_fast preserved, input-health checks on |
| `validation` | `pass` | production_proof profile, self-canonical validation |
| `scale_contract` | `pass` | fit/post internal scale locked to log1p_cms |
| `cleanup_policy` | `pass` | direct no-cleanup launcher prepared for retained .RData diagnostics |

## Launch Readiness Checklist

Checklist: [`launch_readiness_checklist.csv`](./launch_readiness_checklist.csv)

| check | status | note |
|---|---|---|
| `generated_config_exists` | `pass` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/control/generated_configs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep.yaml` |
| `launch_script_exists` | `pass` | `/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/launch_he2_exal_m_t1_20221225_reference_no_cleanup.sh` |
| `launch_script_shell_syntax` | `pass` | `bash -n launch script` |
| `no_cleanup_runner_exists` | `pass` | `/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_unified_without_cleanup.sh` |
| `no_cleanup_runner_shell_syntax` | `pass` | `bash -n no-cleanup runner` |
| `shared_input_paths_exist` | `pass` | `count=8` |
| `bundle_start_is_1987_05_29` | `pass` | `1987-05-29` |
| `fit_scale_is_log1p` | `pass` | `log1p_cms` |
| `post_scale_is_log1p` | `pass` | `log1p_cms` |
| `candidate_max_iter_200` | `pass` | `200` |
| `candidate_common_warmup_10` | `pass` | `10` |
| `q35_state_freeze_preserved` | `pass` | `q35 freeze_target` |
| `q50_state_freeze_preserved` | `pass` | `q50 freeze_target` |
| `epsilon_kept_at_30` | `pass` | `30.0` |
| `c_factor_kept_at_1` | `pass` | `1.0` |
| `post_enabled` | `pass` | `stages.post` |
| `validate_enabled` | `pass` | `stages.validate` |
| `report_enabled` | `pass` | `stages.report` |
| `artifact_retention_ready` | `pass` | `launch path keeps CLEANUP_RDATA_AFTER_POST=0` |
| `not_launched_yet` | `pass` | `package prepared only` |
| `current_run_reviewed_quantile_by_quantile` | `pass` | `quantile_review_rows=7` |

## Prior Summary

### State-evolution discounts

- candidate discounts: `df_t=0.99999999`, `df_s1=0.99999`, `df_s2=0.99999`, `df_s67=0.99999`, `df_discrep=0.99999`, `lambda=0.97`, `df_trans=0.9999999`, `df_covs=0.9999999`

### Gamma/sigma initialization and warm-up policy

- base init: `gamma=0.0`, `sigma_floor=0.001`, `sigma_scale=1.0`
- q20/q35/q50/q65/q80 override the init floor/scale as in the current shared-spec run; see [`quantile_policy.csv`](./quantile_policy.csv)
- q35 and q50 retain the state-focused freeze/stabilization logic from the current shared-spec run
- this candidate changes only the fit budget and the common warm-up hold length; it does not change the discount factors or covariance-prior knobs

### Legacy DLM variance prior

- the legacy bridge initializes the DLM variance prior as `s.priors = list(l0 = 1, S0 = mean(sig0))`
- anchor refs: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1794`, `R/environmetrics/20_model_setup.R:428`

### Wishart-like forecast covariance prior

- active config knobs: `forecast_cov.c_factor=1.0`, `forecast_cov.epsilon=30.0` in the candidate
- the legacy bridge computes `epsilon <- DISC_W_FORECAST_COV_EPSILON else TT`, then `nu <- dim_theta + 1 + epsilon`
- the forecast covariance blend is anchored as `new_cov = epsilon/(epsilon+1) * c_factor * prior_w + 1/(epsilon+1) * ww`
- anchor refs: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2896-2898`, `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3537`
- publication exact source context for this cutoff used `epsilon=360.0`; the current shared-spec run used `epsilon=30.0`; this candidate stays with `30.0` until we explicitly choose otherwise

## Input Bundle Summary

- bundle run id: `20260510_publication_shared_r01`
- bundle kind: `multimodel_v8_histfix_long_history`
- cutoff: `2022-12-25`
- data start: `1987-05-29`
- GloFAS source: `glofas_hist_v31_lisflood_cons` / `hist_v31_lisflood_cons`
- NWS policy: primary=`nws_retro_v21`, tail-fill=`nws_retro_v30`, tail-fill start=`2021-01-01`
- NWS selection rule: `use v2.1 through its natural coverage end; fill subsequent cutoff-era dates from v3.0 daily retrospective`
- USGS daily source: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=usgs_daily_flow/full_runs/source_native_tranche1_20260406T194500Z/outputs/usgs_daily_flow_11160500.csv`
- forecast-member NWS source: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/runs/multimodel_20221225_v8_epsTT_l1/inputs/shared/forecats_bundle/nws_forecast.csv`
- forecast-member GloFAS source: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/runs/multimodel_20221225_v8_epsTT_l1/inputs/shared/forecats_bundle/glofas_forecast.csv`
- plot/display flow scale: `log1p_cms` / `log1p_cms`

The candidate config uses the same corrected bundle paths for:

- retros: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-12-25/run_id=20260510_publication_shared_r01/retros.csv`
- NWS forecast: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-12-25/run_id=20260510_publication_shared_r01/nws_forecast.csv`
- GloFAS forecast: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/stable_inputs/site=11160500/cutoff_date=2022-12-25/run_id=20260510_publication_shared_r01/glofas_forecast.csv`
- PPT: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_03_PPT.csv`
- SOIL: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_04_SOIL.csv`
- PCA/GDPC: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv`

## Expected Review Outputs After Launch

The launch is designed so that, after it runs, we can inspect:

- retained fit-state `.RData` for all 7 quantiles
- per-quantile `fit.log` and `sampling_diagnostics.log`
- per-quantile `multivar_forecast_health.txt`
- aggregate ELBO figure `All_ELBOS_DISC.png`
- publication-facing synthesis figures and `publication_figure_manifest.csv`
- `crps_forecast_summary.csv`, `crps_forecast_per_time.csv`, `crps_input_health*.csv`
- `gamma_summary.csv`, `sigma_summary.csv`, `covariate_effects_summary.csv`
- `posterior_table_exports_manifest.csv`

## Launch Instructions When Approved

Do **not** use the queue wrapper for this representative relaunch. Use the dedicated no-cleanup launcher:

```bash
scripts/launch_he2_exal_m_t1_20221225_reference_no_cleanup.sh
```

Then build the review bundle from the resulting run root with:

```bash
python3 scripts/build_he2_exal_m_t1_cutoff_healthcheck.py \
  --runtime-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518 \
  --run-id multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep \
  --out-dir /data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_20221225_reference_relaunch_20260518/postlaunch_healthcheck
```

## Status

- package prepared: `yes`
- config generated: `yes`
- launched: `no`
- cleanup disabled for planned launch path: `yes`
- discount/epsilon changed from current shared-spec: `no`

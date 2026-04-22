# NDLM Post-Correction Reaudit: Forecast Scoring Audit

Date: 2026-04-21  
Status: complete

## Scope

This note audits the score-construction path for the corrected NDLM rerun, with emphasis on the multivariate rows whose forecast-window CRPS values remained implausibly poor after the earlier contract fixes.

## Runtime Evidence

- Corrected rerun root:
  [/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420)
- Anomaly digest:
  [ndlm_reaudit_anomaly_digest.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_reaudit_anomaly_digest.csv)
- Runtime inventory:
  [ndlm_reaudit_runtime_inventory.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_reaudit_runtime_inventory.csv)

## Scoring Path Confirmed

The current NDLM forecast-window CRPS is produced inside the post stage through the same scoring scaffold used by the synthesis families:

- NDLM predictive draws are built in [post_ndlm_predictive_draws](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:189)
- Those draws are saved to:
  - `post/cache/xbs_ndlm_log1p.rds`
  - `post/cache/y_reps_ndlm_log1p.rds`
- The saved matrix is then passed to `post_crps_model_tables(...)` in [40_figures_smoke_fast.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/40_figures_smoke_fast.R:1807)
- The resulting score tables are written to:
  - `post/outputs/<run>/tables/crps_forecast_per_time.csv`
  - `post/outputs/<run>/tables/crps_forecast_summary.csv`

The scoring metadata for the worst multivariate rows is internally consistent:

- `score_method = quantile_check_loss_sum`
- `tau_rule = k_over_m_plus_1`
- `score_scale = log_cms_plus1`
- `n_samples_eff = 48`

This was confirmed directly in:

- [20211221 ndlm_main_keep CRPS per-time table](</data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/runs/multimodel_20211221_v8_ndlm_featurecov_v1_ndlm_main_keep/post/outputs/multimodel_20211221_v8_ndlm_featurecov_v1_ndlm_main_keep/tables/crps_forecast_per_time.csv>)
- [20221225 ndlm_main_keep CRPS per-time table](</data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/runs/multimodel_20221225_v8_ndlm_featurecov_v1_ndlm_main_keep/post/outputs/multimodel_20221225_v8_ndlm_featurecov_v1_ndlm_main_keep/tables/crps_forecast_per_time.csv>)

## Main Finding

The scoring machinery itself is not the root issue.

The CRPS tables are faithfully scoring the predictive sample matrices they are given. The problem is upstream of the score calculation: the predictive sample matrices themselves are numerically contaminated in the multivariate NDLM path.

Evidence:

- The worst forecast-window CRPS values occur on a small number of forecast days:
  - `20211221 / ndlm_main_keep`: max daily CRPS `205.620105`
  - `20221225 / ndlm_main_keep`: max daily CRPS `104.556740`
- The forecast-window medians are much smaller than the maxima:
  - `20211221 / ndlm_main_keep`: median `2.875417`
  - `20221225 / ndlm_main_keep`: median `2.420286`

This pattern is consistent with a predictive-tail explosion, not with a broad bookkeeping error in the score summarization step.

## Conclusion

- The NDLM forecast-window CRPS tables are being computed on the intended transformed scale.
- The post-stage scoring contract is internally consistent.
- The implausible NDLM CRPS values are being driven by bad predictive draws, not by a separate CRPS aggregation bug.

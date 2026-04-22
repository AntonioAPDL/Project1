# NDLM Post-Correction Reaudit: Predictive Generation Audit

Date: 2026-04-21  
Status: complete

## Scope

This note audits the posterior predictive generation path for the corrected NDLM rerun, with emphasis on whether the multivariate NDLM rows are producing implausible forecast draws before scoring.

## Key Artifacts

- Predictive cache summaries:
  [ndlm_predictive_cache_summaries.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_predictive_cache_summaries.csv)
- Matched quantile-model predictive scale comparison:
  [ndlm_vs_quantile_predictive_scale.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_vs_quantile_predictive_scale.csv)
- Numeric replay:
  [ndlm_sigma_mixing_replay.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_sigma_mixing_replay.csv)
- Synthetic harness summary:
  [ndlm_synthetic_harness_report.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_synthetic_harness_report.md)

## Observed Pathology

The multivariate NDLM predictive caches are wildly larger than both:

- the matched raw forecast ensembles
- the matched exDQLM multivariate predictive cubes

Examples from the corrected rerun:

| Run | NDLM max log(1+Q) predictive draw | NDLM q99.9 | Matched exDQLM max |
|---|---:|---:|---:|
| `20211221 / ndlm_main_keep` | `224194.044466` | `38945.777515` | `3.470764` |
| `20221225 / ndlm_main_keep` | `112010.555753` | `28906.226106` | `2.375397` |
| `20211221 / ndlm_main_drop` | `40267.985239` | `7986.784081` | `4.360883` |
| `20221225 / ndlm_main_drop` | `38339.242196` | `8214.858762` | `0.939044` |

The corresponding exported NDLM forecast quantiles are also extreme:

| Run | Max NDLM q95 | Matched ensemble max q95 | Matched exDQLM q95 |
|---|---:|---:|---:|
| `20211221 / ndlm_main_keep` | `1406.190757` | `1.537233` | `5.610840` |
| `20221225 / ndlm_main_keep` | `959.238068` | `1.601519` | `7.807540` |
| `20211221 / ndlm_main_drop` | `193.614553` | `1.537233` | `6.211220` |
| `20221225 / ndlm_main_drop` | `224.435235` | `1.601519` | `2.083724` |

This is too large to be explained by a modest likelihood penalty or by ordinary multivariate diffusion.

## Root Cause Found

The multivariate NDLM predictive sampler in [post_ndlm_predictive_draws](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:189) was flattening the full `3 x n_draws` `samp.sigma_50_NDLM_synth_DISC` matrix with `as.numeric(sigma_draws)` and then using the first `n_eff` entries as if they were the predictive sigma draws for the USGS target series.

For multivariate NDLM, the sigma matrix rows correspond to:

- `usgs`
- `nws`
- `glofas`

So the old code was mixing the much larger `nws` and `glofas` sigma draws into the USGS predictive draw generation.

## Numerical Replay

Using the preserved prelaunch smoke artifact:

- [DISC_variables_50_NDLM_synth_DISC.RData](</data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/prelaunch_validation_20260421T045415Z/smoke_runs/ndlm_main_keep/smoke_ndlm_main_keep/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData>)

the sigma row means were:

- `usgs = 0.018317`
- `nws = 0.878655`
- `glofas = 8.646275`

Replaying the old flattening bug produced:

- q99.9 = `2067.945949`
- max = `7365.636641`

Replaying with the USGS row only produced:

- q99.9 = `1.031747`
- max = `1.100605`

Explosion factors:

- q99.9 ratio = `2004.315515`
- max ratio = `6692.354087`

## Fix Applied

[post_ndlm_predictive_draws](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R:189) now:

- detects matrix-valued sigma draws
- selects the `usgs` row when row names are available
- falls back to row 1 if row names are absent
- records `sigma_source_used` in the returned object

Regression coverage:

- [test_ndlm_postcorrection_reaudit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/testthat/test_ndlm_postcorrection_reaudit.R)

## Conclusion

The predictive-generation path contained a real implementation bug in the multivariate NDLM post sampler. This bug is sufficient to explain the catastrophic upper-tail behavior in the current corrected rerun scores.

As a result, the current multivariate NDLM CRPS values from that rerun should not be treated as trustworthy until the rerun is repeated from the fixed predictive sampler.

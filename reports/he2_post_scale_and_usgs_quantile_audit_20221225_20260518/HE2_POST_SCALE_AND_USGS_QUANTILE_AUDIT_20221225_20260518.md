# HE2 Post Scale And USGS Quantile Audit

## Scope
This audit covers the representative `exAL-M-T1` rerun for cutoff `2022-12-25` at:

- run root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep`

The goal was:
1. explain how forecast-window USGS quantiles are actually constructed;
2. confirm the post-stage scale contract;
3. patch the active post path so it respects `analysis_scale_post_internal = log1p_cms`;
4. rerun `post` only on the existing fit artifacts.

## Forecast-window USGS quantiles: the real construction
The forecast-window USGS quantiles are not observed USGS values and they are not formed by subtracting a finished discrepancy quantile from a finished GloFAS quantile.

They are predictive quantities built in four steps.

1. The forecast-window state is propagated forward under the fitted multivariate state-space model.
2. For each quantile row, the code projects the propagated state to the USGS target channel using the forecast-window selector weights.
3. In `keep` mode, that projection includes the transfer state weight, so the projected USGS location contains the retained transfer contribution.
4. The exAL observation model generates predictive draws for each quantile row, and `synthesize_samples()` fuses the seven row-specific predictive draw arrays into one synthesized USGS predictive sample matrix. The plotted quantiles are then empirical quantiles of that synthesized matrix.

The key code path is:
- `R/environmetrics/40_figures_smoke_fast.R:451-527`
- `R/environmetrics/40_figures_smoke_fast.R:624-773`
- `R/environmetrics/40_figures_smoke_fast.R:2372-2398`

This aligns with the revised-doc theory section:
- `Evironmetrics---REVISED-DOC-Corrected/wileyNJD-APA.tex:111-152`
- `Evironmetrics---REVISED-DOC-Corrected/wileyNJD-APA.tex:164-190`
- `Evironmetrics---REVISED-DOC-Corrected/wileyNJD-APA.tex:332`
- `Evironmetrics---REVISED-DOC-Corrected/wileyNJD-APA.tex:407-411`

Important distinction:
- post-cutoff USGS observations are used only as held-out verification overlays and for scoring, not to generate the predictive quantiles.

## Scale contract
For this representative rerun, the resolved config says the active post contract is already `log1p_cms`:
- `resolved_config.yaml:434-437`

The active post runner confirms the multivariate current workflow uses:
- `30_univariate_and_misc.R`
- `40_figures_smoke_fast.R`
- `publication_figure_rewrite`

Evidence:
- `post/logs/post_runner.log`

## What was wrong
The active multivariate smoke-fast post lane had already been partially patched, but the broader active current workflow still contained stale helpers that assumed `log_log1p_cms`.

The main issue was that predictive objects already on `log1p_cms` were still being passed through legacy `log_log1p -> log1p` conversion helpers in the post layer.

That inflated forecast-window quantiles massively in the old canonical outputs.

## What was fixed
Patched files:
- `R/environmetrics/02_helpers_core.R`
- `R/unified/stages/stage_post.R`
- `R/environmetrics/30_univariate_and_misc.R`
- `R/environmetrics/40_figures_smoke_fast.R`

Key fixes:
1. added scale-aware post helpers that respect `UNIFIED_ANALYSIS_SCALE_POST_INTERNAL`;
2. exported `UNIFIED_ANALYSIS_SCALE_POST_INTERNAL` from `stage_post`;
3. switched the active helper in `30_univariate_and_misc.R` from hardcoded `post_transform_loglog1p_array()` to the scale-aware helper;
4. switched the smoke-fast multivariate synthesis path to the scale-aware helper;
5. made the NDLM-oriented smoke-fast band helper scale-aware too, so it no longer hardcodes `log_log1p` when asked to convert internal predictive moments to plotting scale.

## Post rerun
I archived the original stage outputs before rebuilding:
- `post_pre_scale_fix_20260518_000815/`
- `validate_pre_scale_fix_20260518_000815/`
- `report_pre_scale_fix_20260518_000815/`

Then I reran only:
- `post`
- `validate`
- `report`

using the existing fit artifacts and the same run root.

The rebuilt post runner completed here:
- `post/logs/post_runner.log`

## Evidence that the scale fix is active
The regenerated forecast transform report now says:
- `from_scale=log1p_cms`
- `to_scale=log1p_cms`
- `transform=identity`

File:
- `post/cache/exdqlm_multivar_synth_keep__mode-keep__synth_multivar_forecast_exp_guard.txt`

That is the key proof that the active canonical post path is no longer applying an extra exponentiation for this cutoff.

## What changed in the canonical quantiles
Comparison file:
- `reports/he2_post_scale_and_usgs_quantile_audit_20221225_20260518/pre_vs_post_quantile_ranges.csv`

Representative forecast-window changes:
- old `q95` max: about `4.818e12`
- new `q95` max: about `29.15`
- old `q80` max: about `4.441e10`
- new `q80` max: about `5.61`
- old `q50` max: about `37.97`
- new `q50` max: about `3.54`

So the previous figure inflation was a real post-transform bug.

## What remains wrong scientifically
Even after the scale fix, the representative run is still not scientifically healthy.

The regenerated forecast-window lower quantiles are still negative on a claimed `log1p(cms)` scale:
- forecast `q05` range: about `-26.61` to `-16.83`
- forecast `q20` range: about `-2.97` to `-0.16`
- forecast `q35` still crosses below zero on some days

So:
- the post-scale bug is real and now fixed for this cutoff;
- but the model-side predictive object is still pathological.

That means the next investigation should target the predictive draws themselves, not the old post transform.

## Current outputs to inspect
Canonical regenerated figure:
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep/post/outputs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep/exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.png`

Canonical regenerated quantiles CSV:
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep/post/outputs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep/exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv`

Separate augmented diagnostic bundle:
- `reports/he2_exal_m_t1_augmented_synthesis_diagnostic_20221225_20260518/`

## Note on validate/report replay
The post-only replay finished and regenerated the outputs correctly, but the replayed `validate/report` summary still flags unrelated bookkeeping failures in deterministic-climate/report metadata. Those failures do not negate the main post-scale fix; they are replay-contract issues caused by rerunning downstream stages without replaying earlier stages.

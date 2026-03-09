# Unified Multimodel Future Covariate Audit

Date: 2026-03-08

Scope:
- Repo audited: `/data/muscat_data/jaguir26/project1_ucsc_phd`
- Secondary repo checked: `/data/muscat_data/jaguir26/exDQLM---Ensemble`
- This document started as an audit and now also records the implemented deterministic climate covariate wiring and run-readiness checks.

## Checklist
- [x] Unified stage order confirmed from code
- [x] Run-scoped shared-input materialization path confirmed
- [x] Forecast bundle ingestion path confirmed
- [x] Multivar `drop` vs `keep` covariate behavior confirmed
- [x] Univar fit-time covariate behavior confirmed
- [x] Univar post-time forecast covariate behavior confirmed
- [x] Post-time direct project-root PPT/SOIL/PCA reads confirmed
- [x] Current source of future observed PPT/SOIL/PCA in fit identified
- [x] Current source of future observed PPT/SOIL/PCA in post identified
- [x] Current effective flow forecast horizon measured from run-scoped bundles
- [x] Cross-cutoff configuration drift checked in existing resolved runs
- [x] Deterministic-forecast design options compared
- [x] Preliminary deterministic covariate recommendation written
- [x] Final implementation plan approved
- [x] Cross-cutoff hyperparameter regime frozen for each model family
- [x] Run-scoped deterministic covariate series materialized
- [x] Fit/post switched to common run-scoped covariate series
- [ ] Validation/report metadata updated to record deterministic covariate provenance

Implementation note:
- Sections 1-12D preserve the original audit reasoning.
- Section 12E below records the implemented state that now supersedes the earlier pre-implementation notes.

## 1. Workflow Overview

Confirmed from `scripts/unified_run.R:162-215`, the unified orchestration runs stages in this exact order:

1. `forecats`
2. `data_prep_shared`
3. `fit`
4. `post`
5. `validate`
6. `report`

The stage dispatcher is in `scripts/unified_run.R:186-195`.

At a high level:
- `forecats` ingests or snapshots the cutoff-aware flow bundle: retros, NWS, GloFAS.
- `data_prep_shared` builds run-scoped shared inputs under `inputs/shared/*`.
- `fit` launches the enabled model families and passes run-scoped paths through environment variables.
- `post` rebuilds synthesis inputs and generates combined figures/tables.
- `validate` compares post outputs to canonical outputs and writes compare reports.
- `report` summarizes what was produced and which model artifacts are present.

The secondary repo `/data/muscat_data/jaguir26/exDQLM---Ensemble` does not appear to be an active code dependency for this unified workflow. A filesystem check found only `README.md`, `main.tex`, `main.pdf`, and a small LaTeX helper script. I found no unified runner, family modules, or model-execution code there.

## 2. Stage-By-Stage Data Flow

### 2.1 `forecats`

Primary code:
- `R/unified/stages/stage_forecats.R:611-827`
- `config/forecats_pipeline.template.yaml`

What it does:
- Runs `scripts/forecats_pipeline.R` when `inputs.forecats.mode = build` (`R/unified/stages/stage_forecats.R:611-637`).
- Creates a run-scoped snapshot of the flow bundle under `inputs/shared/forecats_bundle` by default (`R/unified/stages/stage_forecats.R:654-668`).
- Copies bundle artifacts such as:
  - `meta.yaml`
  - `inputs/retros_daily.csv`
  - `inputs/nws_weighted_daily.csv`
  - `inputs/glofas_weighted_daily.csv`
  - member-level `inputs/nws_members.csv`
  - member-level `inputs/glofas_members.csv`
  - alias files `retros.csv`, `nws_forecast.csv`, `glofas_forecast.csv`
  - `snapshot_source_map.txt`
  (`R/unified/stages/stage_forecats.R:660-827`)

What it does not do:
- It does not materialize PPT, SOIL, or PCA climate covariates.
- It does not create deterministic climate forecast series.

Conclusion:
- `stage_forecats` is responsible for cutoff-aware flow bundle ingestion and snapshotting only.

### 2.2 `data_prep_shared`

Primary code:
- `R/unified/stages/stage_data_prep_shared.R:3-390`

What it creates:
- `inputs/shared/parameters/parameters.txt`
- `inputs/shared/retros/retros.csv`
- `inputs/shared/forecasts/nws_forecast.csv`
- `inputs/shared/forecasts/glofas_forecast.csv`
- `inputs/shared/covariates/*.csv`
- `inputs/shared/source_map.txt`
- optionally `inputs/shared/data_start_filter_summary.txt`

Key behavior:
- Creates run-scoped shared directories (`R/unified/stages/stage_data_prep_shared.R:3-15`).
- Prefers the `forecats` snapshot when configured (`R/unified/stages/stage_data_prep_shared.R:115-178`).
- Copies shared flow inputs into the run bundle (`R/unified/stages/stage_data_prep_shared.R:193-235`).
- Copies fit covariates into `inputs/shared/covariates` either from `inputs.fit.covariates` or `inputs.shared_covariates` (`R/unified/stages/stage_data_prep_shared.R:237-271`).
- Optionally date-filters shared inputs and covariates from `dates.data_start` forward (`R/unified/stages/stage_data_prep_shared.R:274-376`).

Important negative finding:
- This stage only copies and optionally filters covariate CSVs.
- It does not splice observed history with deterministic forecasts.
- It does not generate cutoff-specific future climate covariate forecasts.

Conclusion:
- `stage_data_prep_shared` is the current run-scoped shared-input materialization point.
- It is the cleanest existing place to later materialize deterministic climate covariate series.

### 2.3 `fit`

Primary code:
- `R/unified/stages/stage_fit.R:153-199`
- `R/unified/stages/stage_fit.R:294-515`
- `R/unified/stages/stage_fit.R:550-745`

What it does:
- Resolves shared covariate paths from the run bundle (`R/unified/stages/stage_fit.R:153-199`).
- Launches multivariate exDQLM by quantile and transfer mode (`R/unified/stages/stage_fit.R:294-515`).
- Launches univariate exDQLM with run-scoped shared inputs and run-scoped covariate CSVs (`R/unified/stages/stage_fit.R:550-745`).
- Also launches NDLM if enabled.

Important detail:
- `stage_fit` already passes run-scoped PPT/SOIL/PCA CSV paths into multivar via:
  - `DISC_W_PRISM_PATH`
  - `DISC_W_SOIL_PATH`
  - `DISC_W_PCA_PATH`
  (`R/unified/stages/stage_fit.R:496-505`)
- `stage_fit` already passes run-scoped covariate CSVs into univar via:
  - `UNIV_PPT_CSV`
  - `UNIV_SOIL_CSV`
  - `UNIV_PCA_CSV`
  (`R/unified/stages/stage_fit.R:610-624`)

Conclusion:
- If run-scoped deterministic PPT/SOIL CSVs are materialized before `fit`, the multivar and univar launch plumbing mostly already exists.

### 2.4 `post`

Primary code:
- `R/unified/stages/stage_post.R:43-134`
- `R/unified/stages/stage_post.R:371-443`
- `scripts/run_environmetrics_figures.R:348-445`
- `R/unified/post_module_plan.R:1-58`

What it creates:
- run-scoped post adapter inputs under `post/inputs`
- post logs under `post/logs`
- figures/tables under `post/outputs/<run_id>` via the modular Environmetrics stack

What it does:
- Reuses run-scoped shared retros/NWS/GloFAS when available (`R/unified/stages/stage_post.R:43-78`).
- Adapts those CSVs into post adapter files (`R/unified/stages/stage_post.R:83-134`).
- Passes only retros/NWS/GloFAS env overrides into post (`R/unified/stages/stage_post.R:371-405`).
- Does not pass PPT/SOIL/PCA override paths into post.
- Selects post modules based on enabled families; univariate runs still source `30_univariate_and_misc.R` (`R/unified/post_module_plan.R:46-58`).

Conclusion:
- `post` is the combined synthesis stage.
- It is currently not run-scoped for climate covariates, even when `fit` is.

### 2.5 `validate`

Primary code:
- `R/unified/stages/stage_validate.R:34-130`

What it creates:
- `validate/canonical.sha256`
- `validate/current.sha256`
- `validate/compare_report.txt`
- `validate/compare_report.json`
- `validate/diff/*`
- optionally `validate/env_drift_report.json`

What it does:
- Compares current post outputs to canonical outputs.
- Does not itself read PPT/SOIL/PCA.

Conclusion:
- No deterministic covariate algorithm change is required here, but validation metadata should later record which deterministic covariate policy was used.

### 2.6 `report`

Primary code:
- `R/unified/stages/stage_report.R:143-240`

What it creates:
- `report/summary.md`
- optionally `report/profile_summary.md`

What it does:
- Summarizes artifact presence, transfer modes, quantiles found, and validation status.
- Does not itself read PPT/SOIL/PCA.

Conclusion:
- No deterministic covariate algorithm change is required here either, but the report should later surface deterministic covariate provenance.

## 3. Model-Family-Specific Covariate Usage

### 3.1 Multivariate exDQLM (`exdqlm_multivar`)

Entrypoints:
- `scripts/run_DISC_Optimal_Synth_Ranges_W.R:45-60`
- `DISC_Optimal_Synth_Ranges_W.r`
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- `R/disc_w/01_paths_inputs.R:16-35`
- `R/disc_w/03_covariates_standardize.R:13-212`

Wrapper behavior:
- `scripts/run_DISC_Optimal_Synth_Ranges_W.R:45-60` chooses the entrypoint from `DISC_W_FORECAST_TRANSFER_MODE`.
- `drop` loads `DISC_Optimal_Synth_Ranges_W.r`.
- `keep` loads `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`.

Current covariate sourcing:
- Multivar path defaults to project-root PRISM, ERA5 soil, and PCA unless env overrides are provided (`R/disc_w/01_paths_inputs.R:25-35`).
- In unified runs, `stage_fit` does provide run-scoped overrides (`R/unified/stages/stage_fit.R:496-505`).

Confirmed covariate construction:
- `R/disc_w/03_covariates_standardize.R:82-123` builds:
  - historical `X_ppt`, `X_soil`, `X_pca` from rows `time <= cutoff_date`
  - future `X_ppt_f`, `X_soil_f`, `X_pca_f` from rows `time >= forecast_start_date`
- `R/disc_w/03_covariates_standardize.R:129-133` merges them into `X` and `X_f`.
- `R/disc_w/03_covariates_standardize.R:154-204` standardizes them and adds lagged forecast covariate terms.

Critical horizon behavior:
- `select_future_window()` sizes future covariates to `ranges[1]` and pads with persistence if the series is too short (`R/disc_w/03_covariates_standardize.R:19-72`).

#### Multivar `drop`

Confirmed behavior:
- It still builds `X_f` (`DISC_Optimal_Synth_Ranges_W.r:895-900`).
- Historical covariates are embedded in the fit-time state when `use_covariates` is true (`DISC_Optimal_Synth_Ranges_W.r:1031-1062`).
- Forecast propagation then drops transfer/covariate state for the forecast window (`DISC_Optimal_Synth_Ranges_W.r:1096-1107`).

Conclusion:
- `drop` mode does not use future PPT/SOIL/PCA to drive the forecast window.
- It is not the primary target for deterministic post-cutoff covariate replacement.

#### Multivar `keep`

Confirmed behavior:
- It builds the same `X_f` (`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:895-900`).
- Historical covariates enter the fit-time state (`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1031-1062`).
- Forecast propagation explicitly injects `X_f` segment-by-segment into the transfer block (`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1121-1165`).

Conclusion:
- Multivar `keep` is the main fit-time consumer of future PPT/SOIL/PCA after cutoff.

### 3.2 Univariate exDQLM (`exdqlm_univar`)

Entrypoints:
- `scripts/run_exdqlm_univar.R:47-122`
- `R/unified/families/exdqlm_univar/01_inputs.R:49-110`
- `R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R:76-120`
- `R/unified/families/exdqlm_univar/zz_run.R`

Confirmed fit-time behavior:
- `R/unified/families/exdqlm_univar/01_inputs.R:49-98` loads retros and covariate CSVs.
- Each covariate series is aligned to historical target length `Tn`, not to a future forecast horizon (`R/unified/families/exdqlm_univar/01_inputs.R:36-47`, `75-98`).
- There is no separate `X_f` object in the theory-aligned fit path.
- `R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R:76-120` uses only `inputs$y` and historical `inputs$X`.

Conclusion:
- The theory-aligned univariate fit path does not use future PPT/SOIL/PCA after cutoff.
- If your prior assumption was that univariate fit itself behaves like multivar `keep`, that assumption is wrong.

### 3.3 Univariate post-time forecasting

Active post module:
- `R/environmetrics/30_univariate_and_misc.R`

Confirmed behavior:
- The module header explicitly lists `X_f` as an input dependency (`R/environmetrics/30_univariate_and_misc.R:74-83`).
- The univariate forecast propagation block injects `X_f` into `Gx` (`R/environmetrics/30_univariate_and_misc.R:563-590`).

Conclusion:
- Univariate fit is historical-only.
- Univariate forecasting in `post` does use future `X_f`.
- Later deterministic covariate substitution must therefore update `post`, not just `fit`.

### 3.4 NDLM

Primary code:
- `DISC_Optimal_Synth_Ranges_NDLM.r`

Confirmed fit-time behavior:
- NDLM builds `X` and `X_f` from PPT/SOIL/PCA in the same split pattern as multivar (`DISC_Optimal_Synth_Ranges_NDLM.r:937-1088`).
- Future covariates are sized to `forecast_horizon`.
- Historical covariates are injected into the fit-time state (`DISC_Optimal_Synth_Ranges_NDLM.r:1220-1234`).

Conclusion:
- If NDLM remains in scope later, it is also affected by post-cutoff deterministic PPT/SOIL replacement.
- Your current stated priority is multivar `keep` and univar forecasting, but NDLM is not isolated from this design.

## 4. Exact Current Source Of Future PPT/SOIL/PCA In Fit

### 4.1 Multivar fit

Current source chain:
- `stage_data_prep_shared` copies whichever covariate CSVs are configured into `inputs/shared/covariates/*.csv` (`R/unified/stages/stage_data_prep_shared.R:237-271`).
- `stage_fit` maps those run-scoped files into `DISC_W_PRISM_PATH`, `DISC_W_SOIL_PATH`, `DISC_W_PCA_PATH` (`R/unified/stages/stage_fit.R:496-505`).
- `R/disc_w/01_paths_inputs.R:25-35` uses those env vars if present; otherwise it falls back to project-root files.
- `R/disc_w/03_covariates_standardize.R:82-123` constructs `X` from rows `<= cutoff_date` and `X_f` from rows `>= forecast_start_date`.

Therefore:
- In unified runs with shared covariates configured, future PPT/SOIL/PCA in fit come from the run-scoped covariate CSV copies.
- Those run-scoped copies are still currently just copies of the observed PRISM / ERA5 soil / PCA files.
- No deterministic forecast splicing is happening yet.

### 4.2 Univar fit

Current source chain:
- `stage_fit` passes run-scoped `UNIV_PPT_CSV`, `UNIV_SOIL_CSV`, `UNIV_PCA_CSV` (`R/unified/stages/stage_fit.R:610-624`).
- `R/unified/families/exdqlm_univar/01_inputs.R:75-98` truncates or pads those series to the historical retrospective length `Tn`.

Therefore:
- Univar fit currently consumes only historical portions of those covariate CSVs.
- Future rows after cutoff are not used in the theory-aligned fit path.

### 4.3 NDLM fit

Current source chain:
- Same pattern as multivar, but through `NDLM_PPT_CSV`, `NDLM_SOIL_CSV`, `NDLM_PCA_CSV`.
- `DISC_Optimal_Synth_Ranges_NDLM.r:937-1088` builds `X_f` from rows after the forecast start date.

## 5. Exact Current Source Of Future PPT/SOIL/PCA In Post

Primary files:
- `R/environmetrics/00_paths.R:153-173`
- `R/environmetrics/10_data_inputs.R:28-257`
- `R/environmetrics/20_model_setup.R:188-227`
- `R/environmetrics/30_univariate_and_misc.R:563-590`

Confirmed from code:
- `R/environmetrics/00_paths.R:165-167` hardcodes:
  - `PPT_PATH <- file.path(PROJECT_ROOT, "prism_precipitation_santa_cruz_1987_2023.csv")`
  - `SOIL_PATH <- file.path(PROJECT_ROOT, "soil_moisture_data", "soil_moisture_big_trees_daily_avg_1987_2023.csv")`
  - `PCA_PATH <- file.path(PROJECT_ROOT, "pca.csv")`
- `stage_post` does not override those paths; it only overrides retros/NWS/GloFAS (`R/unified/stages/stage_post.R:371-405`).
- `R/environmetrics/10_data_inputs.R:139-190` rebuilds `X` and `X_f` directly from those project-root files.
- `R/environmetrics/10_data_inputs.R:148-180` sizes future climate covariates to `ranges[1]`.
- `R/environmetrics/20_model_setup.R:188-227` uses `X_f` for multivar keep-mode post synthesis.
- `R/environmetrics/30_univariate_and_misc.R:563-590` uses `X_f` for univariate forecast synthesis.

Conclusion:
- Post currently ignores run-scoped covariate overrides.
- Even if `fit` were changed tomorrow to use deterministic post-cutoff PPT/SOIL, `post` would remain inconsistent until this path is updated.

## 6. Which Models Truly Depend On Future Climate Covariates After Cutoff

Confirmed from code:

- `exdqlm_multivar`, `drop`:
  - historical covariates matter
  - post-cutoff future PPT/SOIL/PCA do not drive forecast propagation

- `exdqlm_multivar`, `keep`:
  - yes, future PPT/SOIL/PCA are used in fit-time forecast propagation
  - yes, future PPT/SOIL/PCA are used again in post-time keep-mode synthesis

- `exdqlm_univar`, `theory_aligned` fit:
  - no, future PPT/SOIL/PCA are not used in fit

- `exdqlm_univar`, post-time forecasting:
  - yes, future `X_f` is used in `R/environmetrics/30_univariate_and_misc.R`

- `ndlm_main`:
  - yes in legacy/theory bridge fit path if enabled, because it builds and uses `X_f`
  - post-time impact is lower-priority for your current stated goal, but it should be treated as affected if NDLM stays enabled

Bottom line:
- Your current mental model is only half-right.
- The two highest-priority change points are:
  1. multivar `keep`
  2. post-time forecast synthesis, including univariate forecasting

## 7. Effective Flow Forecast Window And Why It Constrains Covariate Choice

This is the critical operational constraint.

I measured the run-scoped snapshots already present for your five cutoffs in:
- `repro/runs/multimodel_20210123/inputs/shared/forecats_bundle`
- `repro/runs/multimodel_20211112/inputs/shared/forecats_bundle`
- `repro/runs/multimodel_20211221/inputs/shared/forecats_bundle`
- `repro/runs/multimodel_20220511/inputs/shared/forecats_bundle`
- `repro/runs/multimodel_20221225/inputs/shared/forecats_bundle`

Observed daily horizons from those bundles:
- GloFAS member bundle: 28 daily leads for all five cutoffs
- NWS member bundle: 8 daily leads for four cutoffs, 10 daily leads for `2022-12-25`

This matches the code in `R/environmetrics/10_data_inputs.R:112-129`, where:
- `ensembles[[1]]` is GloFAS
- `ensembles[[2]]` is NWS
- `ranges[1]` becomes the longest ensemble horizon and is then used to size `X_f`

Therefore:
- The current unified forecast window is effectively 28 days, because GloFAS is the longest active flow forecast source.
- Any future deterministic climate covariate replacement that is intended to preserve the current flow forecast horizon must supply at least 28 daily post-cutoff values.

This matters immediately for your candidate climate forecasts:
- GEFS precipitation (`APCP`) covers 35 days, so it can support the current 28-day window.
- GEFS soil layers (`SOILW`) cover 35 days, so they can support the current 28-day window.
- NWM precipitation (`RAINRATE`) only covers short/medium forcing, so about 10 days. It cannot support the current 28-day window without truncation.
- NWM cross-range `SOILSAT_TOP` covers short + medium + long land, so about 30 days. It can support the current 28-day window.
- NWM `SOIL_M` only exists in medium-range land, so about 10 days. It cannot support the current 28-day window without truncation.

Implication:
- If you choose a deterministic covariate forecast shorter than 28 days, you must reduce the flow forecast window to that shorter horizon.
- The current code will otherwise pad missing climate covariates with persistence, which is a modeling decision. For your stated goal, that should not happen silently.

Recommendation on principle:
- Do not silently persist future climate covariates to reach the flow horizon.
- If a deterministic climate forecast cannot cover the required horizon, truncate the downstream flow forecast horizon to the minimum supported deterministic covariate horizon.

## 8. Preliminary Deterministic Forecast Recommendation

You asked which forecast to keep, or which deterministic summary of a probabilistic forecast to keep, so future observed covariates can be replaced realistically.

### 8.0 Daily aggregation policy

There is one important unit/aggregation constraint to freeze before implementation:

- Soil should be handled as a daily average at the model time step.
- Precipitation should be handled as a daily total, not a daily mean rate, if the goal is to remain consistent with the current PRISM covariate file.

Reason:
- The current soil covariate file is `soil_moisture_big_trees_daily_avg_1987_2023.csv`, which is explicitly a daily average soil-moisture series.
- The current precipitation covariate file is `prism_precipitation_santa_cruz_1987_2023.csv` with `PRCP_mm`, which is a daily precipitation amount.

So the implementation-ready rule should be:
- soil deterministic series: daily average
- precipitation deterministic series: daily total

I do not recommend mixing forecast daily mean precipitation rates with PRISM daily totals unless PRISM is also converted to daily mean-rate units.

### 8.1 Precipitation

Recommended default:
- Use GEFS daily precipitation derived from `APCP`, summarized as the ensemble mean.

Reason:
- It is the only candidate already audited here that cleanly covers the full current 28-day flow forecast window.
- It remains in the same daily accumulated precipitation units used by the PRISM covariate workflow.
- NWM precipitation is too short for the current 28-day flow window.

Secondary note:
- If you want a robustness sensitivity later, compare GEFS mean vs GEFS median, but mean is the cleaner first deterministic replacement for a covariate series.
- Implementation-ready summary rule: first aggregate each GEFS member to daily precipitation totals, then take the daily ensemble mean.

### 8.2 Soil

Recommended default:
- Use NWM cross-range `SOILSAT_TOP` as the primary deterministic soil forecast series, converted to the same volumetric soil-moisture units used by the existing soil covariate workflow.

Reason:
- It is the only NWM soil target that spans short, medium, and long ranges, so it can cover the current 28-day flow forecast window.
- It matches your stated preference to use NWM soil across ranges when possible.
- Medium-range-only `SOIL_M` is valuable, but it is too short to be the production replacement covariate for a 28-day window.

Required caution:
- `SOILSAT_TOP` is not natively the same quantity as the current ERA5 soil covariate. It represents top-soil saturation fraction, not direct volumetric water content.
- If `SOILSAT_TOP` is used, the run-scoped deterministic covariate build step must make the unit conversion explicit and reproducible.
- Implementation-ready summary rule:
  - short-range land: keep the deterministic `member_det` values
  - medium-range and long-range land: compute one daily value per member, then take the daily ensemble mean

Fallback if the conversion is judged too fragile:
- Use GEFS top-layer `SOILW` ensemble mean as the production deterministic soil covariate.
- Keep NWM `SOILSAT_TOP` and `SOIL_M` as diagnostic comparisons, not the fit-time covariate.

### 8.3 PCA

Recommended default:
- Keep PCA1 unchanged for now, exactly as requested.

## 9. Proposed Future Deterministic-Forecast Integration Points

You asked for design options before implementation. Here they are.

### Option 1: extend `stage_forecats` to include deterministic climate forecast artifacts

Pros:
- Keeps all cutoff-aware forecast assets created early.
- Creates one run-scoped snapshot area for flow and climate forecast artifacts.

Cons:
- `stage_forecats` is currently scoped to flow bundle ingestion and snapshotting.
- Mixing flow-forecast bundle logic with climate-covariate forecast logic would broaden the stage too much.
- Naming and artifact semantics would become muddier.

Assessment:
- Possible, but not the cleanest choice.

### Option 2: extend `stage_data_prep_shared` to materialize cutoff-aware run-scoped climate covariate series

What this would do:
- Build run-scoped covariate CSVs that splice:
  - observed history through cutoff
  - deterministic forecast values after cutoff
- Write them into `inputs/shared/covariates`

Pros:
- This stage already owns run-scoped shared input materialization.
- `stage_fit` already consumes run-scoped covariate CSVs from this location.
- Minimal change to family code, especially multivar.
- Backward compatibility is easy:
  - if deterministic climate override is disabled, keep copying the observed covariate CSVs unchanged

Cons:
- The stage will need a new source manifest or config pointing to climate forecast artifacts.

Assessment:
- This is the cleanest place to materialize the actual spliced covariate series.

### Option 3: modify fit and post consumers to read run-scoped climate covariate series

What this would do:
- Keep model code mostly unchanged.
- Stop `post` from hardcoding project-root PRISM/SOIL/PCA.
- Make `post` use the same run-scoped series used by `fit`.

Pros:
- Necessary for consistency.
- Prevents fit/post mismatch.

Cons:
- Requires changes in `stage_post`, `R/environmetrics/00_paths.R`, and possibly a few summary labels.

Assessment:
- Required in combination with Option 2.

### Cleanest design

The cleanest architecture is:

1. Keep `stage_forecats` focused on flow retros/NWS/GloFAS.
2. Extend `stage_data_prep_shared` to build run-scoped deterministic climate covariate series.
3. Change `post` to read those same run-scoped covariate series instead of project-root PRISM/ERA5/PCA files.

Why this is the best fit:
- It respects current stage responsibilities.
- It reuses the existing run-scoped covariate plumbing already present in `stage_fit`.
- It minimizes edits to multivar family code.
- It forces `fit` and `post` to stay consistent.
- It preserves backward compatibility by allowing a mode where shared covariates are copied unchanged.

## 10. Exact Later Change Points

### Fit-side changes

Needed:
- `R/unified/stages/stage_data_prep_shared.R`
  - add a deterministic-climate materialization branch for PPT and SOIL
  - write run-scoped spliced covariate CSVs into `inputs/shared/covariates`
  - record source provenance in a new run-scoped metadata file

Likely no family-code change needed for:
- multivar fit path, because it already reads `DISC_W_PRISM_PATH` and `DISC_W_SOIL_PATH`

No fit-side future-covariate change needed for:
- theory-aligned univariate fit, because it only uses historical `X`

Fit-side change still needed for:
- NDLM if enabled, because it builds `X_f`

### Post-side changes

Required:
- `R/unified/stages/stage_post.R`
  - pass run-scoped PPT/SOIL/PCA override env vars into post
- `R/environmetrics/00_paths.R`
  - stop hardcoding project-root PPT/SOIL/PCA when run-scoped overrides are available
- `R/environmetrics/10_data_inputs.R`
  - keep rebuilding `X` and `X_f`, but from the run-scoped spliced covariate CSVs

This is what keeps consistent:
- multivar keep-mode post synthesis in `R/environmetrics/20_model_setup.R:188-227`
- univariate post-time forecasting in `R/environmetrics/30_univariate_and_misc.R:563-590`
- figures/tables driven by the post stack

### Validate/report changes

Algorithmic changes are probably not required.

But metadata changes are advisable:
- `validate` can stay as-is, because it compares post artifacts only.
- `report` should later surface the deterministic covariate policy used:
  - precipitation source and summary
  - soil source and conversion policy
  - effective truncated horizon, if any

## 11. Risks, Ambiguities, And Things To Verify Before Implementation

### Confirmed architectural risks

- Fit/post inconsistency exists today:
  - fit can already be pointed at run-scoped covariate CSVs
  - post currently ignores them and reads project-root PRISM/ERA5/PCA directly

- Silent persistence padding exists today:
  - both `R/disc_w/03_covariates_standardize.R:19-72` and `R/environmetrics/10_data_inputs.R:33-64` extend short climate covariate horizons with persistence
  - this is not acceptable as an implicit substitute for missing deterministic forecasts if realism is the goal

### Source-selection risks

- NWM `SOILSAT_TOP` requires an explicit and documented conversion to the soil-moisture units used by the current covariate series.
- NWM `SOIL_M` is attractive physically, but only covers about 10 days, so it cannot be the sole production covariate without truncating the flow forecast window.
- NWM precipitation cannot currently replace PRISM for the existing 28-day workflow because its horizon is too short.

### Ambiguities

- The current model only consumes one scalar `SOIL` covariate series, while GEFS exposes four soil layers and NWM exposes multiple soil products.
- Because of that, "all possible soil layers" can be retained as forecast assets, but only one deterministic soil series can drive the current workflow unless the model itself is broadened.

### Current best interpretation

- Keep the full extracted GEFS/NWM soil archive for diagnostics and future experiments.
- For the immediate deterministic covariate substitution:
  - precipitation: GEFS `APCP` ensemble mean
  - soil: NWM cross-range `SOILSAT_TOP` converted to the current soil-covariate units
  - medium-range `SOIL_M`: auxiliary diagnostic and calibration input, not the production series

## 12. Implementation Plan For The Next Turn

1. Add a run-scoped deterministic climate covariate manifest for each cutoff that records:
   - precipitation source
   - soil source
   - ensemble summary rule
   - unit conversion rule
   - supported daily horizon

2. Add a `data_prep_shared` mode that writes spliced run-scoped climate covariate CSVs:
   - observed history through cutoff
   - deterministic forecast after cutoff
   - unchanged PCA series

3. Add a hard horizon contract:
   - compute `effective_horizon_days = min(flow_forecast_horizon, ppt_horizon, soil_horizon)`
   - if `effective_horizon_days < flow_forecast_horizon`, truncate flow ensemble inputs instead of padding climate covariates

4. Update `stage_post` plus `R/environmetrics/00_paths.R` so post reads the same run-scoped covariate CSVs.

5. Re-run one cutoff in a dry-run or smoke mode and verify:
   - multivar `keep` fit uses deterministic PPT/SOIL after cutoff
   - univariate forecasting in post uses the same deterministic PPT/SOIL after cutoff
   - figures and tables reflect the same covariate series used in fit

6. Only after that, backfill all five cutoffs.

## 12A. Run-Ready Deterministic Covariate Policy

This is the current recommended policy to implement once you approve the common hyperparameter regime.

### Production deterministic climate covariates

- Precipitation:
  - source: GEFS `APCP`
  - summary: ensemble mean
  - aggregation: daily total
  - reason: covers at least 28 days and matches PRISM covariate semantics

- Soil:
  - source: NWM cross-range `SOILSAT_TOP`
  - summary:
    - short-range: deterministic value as-is
    - medium-range: ensemble mean
    - long-range: ensemble mean
  - aggregation: daily average
  - reason: spans short + medium + long ranges and can cover the current 28-day window

- PCA:
  - source: existing project-root/run-scoped PCA CSV
  - summary: none
  - aggregation: unchanged

### Horizon contract

- Current effective flow forecast horizon: 28 days
- Deterministic climate covariate policy above supports that 28-day window without truncation
- Therefore the planned first implementation should preserve the current 28-day flow forecast window

### Output expectation per cutoff

For each of the five cutoffs:
- one spliced precipitation covariate series:
  - observed PRISM through cutoff
  - deterministic GEFS mean `APCP` daily totals after cutoff
- one spliced soil covariate series:
  - observed ERA5 soil through cutoff
  - deterministic NWM `SOILSAT_TOP` daily values after cutoff
- one unchanged PCA series

## 12B. Cross-Cutoff Hyperparameter Harmonization Audit

I checked the existing resolved unified runs:
- [multimodel_20210123/resolved_config.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20210123/resolved_config.yaml)
- [multimodel_20211112/resolved_config.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20211112/resolved_config.yaml)
- [multimodel_20211221/resolved_config.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20211221/resolved_config.yaml)
- [multimodel_20220511/resolved_config.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20220511/resolved_config.yaml)
- [multimodel_20221225/resolved_config.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20221225/resolved_config.yaml)

### Stable across all five cutoffs

Confirmed stable implementation modes in the existing five resolved runs:
- `exdqlm_multivar.implementation_mode = legacy_bridge`
- `exdqlm_univar.implementation_mode = legacy_bridge`
- `ndlm_main.implementation_mode = legacy_bridge`
- `ndlm_main.kalman_backend = cpp`

Confirmed stable for multivar state evolution:
- `df_t = 0.9999`
- `df_s1 = 0.9999`
- `df_s2 = 0.9999`
- `df_s67 = 0.9999`
- `df_discrep = 0.999`
- `lambda = 0.97`
- `df_trans = 0.999999`
- `df_covs = 0.999999`

Confirmed stable for univar state evolution:
- `df_t = 0.9999`
- `df_s1 = 0.9999`
- `df_s2 = 0.9999`
- `df_s67 = 0.9999`
- `lambda = 0.97`
- `df_trans = 0.999999`
- `df_covs = 0.999999`

Confirmed stable:
- quantile grid: `[0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95]`

### Not stable across the five cutoffs

Multivar transfer-mode coverage is inconsistent:
- `2021-01-23`: `forecast_transfer_modes = drop` only
- `2021-11-12`: `forecast_transfer_modes = [drop, keep]`
- `2021-12-21`: `forecast_transfer_modes = [drop, keep]`
- `2022-05-11`: `forecast_transfer_modes = drop` only
- `2022-12-25`: `forecast_transfer_modes = drop` only

References:
- [multimodel_20210123/resolved_config.yaml#L38](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20210123/resolved_config.yaml#L38)
- [multimodel_20211112/resolved_config.yaml#L38](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20211112/resolved_config.yaml#L38)
- [multimodel_20211221/resolved_config.yaml#L38](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20211221/resolved_config.yaml#L38)
- [multimodel_20220511/resolved_config.yaml#L36](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20220511/resolved_config.yaml#L36)
- [multimodel_20221225/resolved_config.yaml#L38](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20221225/resolved_config.yaml#L38)

Multivar legacy `lam1/lam2` drift is real:
- `2021-01-23`: `lam1 = lam2 = 1.0`
- `2021-11-12`: `lam1 = lam2 = 1.0`
- `2021-12-21`: `lam1 = lam2 = 1.0`
- `2022-05-11`: `lam1 = lam2 = 0.5`
- `2022-12-25`: `lam1 = lam2 = 0.4`

References:
- [multimodel_20210123/resolved_config.yaml#L162](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20210123/resolved_config.yaml#L162)
- [multimodel_20211112/resolved_config.yaml#L164](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20211112/resolved_config.yaml#L164)
- [multimodel_20211221/resolved_config.yaml#L164](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20211221/resolved_config.yaml#L164)
- [multimodel_20220511/resolved_config.yaml#L161](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20220511/resolved_config.yaml#L161)
- [multimodel_20221225/resolved_config.yaml#L162](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20221225/resolved_config.yaml#L162)

Multivar legacy `forecast_cov.c_factor` also drifts:
- `2021-01-23`: `1000.0`
- `2021-11-12`: `1.0`
- `2021-12-21`: `1.0`
- `2022-05-11`: `10000.0`
- `2022-12-25`: `1.0`

This matters because the existing cross-cutoff multivar runs were not generated under one frozen specification.

### Pre-implementation gate

Before deterministic covariate substitution is implemented, freeze a single cross-cutoff regime for each model family.

Minimum decisions to freeze:
- whether multivar will run `drop` only or both `drop` and `keep`
- multivar `lam1`
- multivar `lam2`
- multivar `forecast_cov.c_factor`
- whether any keep-specific settings differ from the common regime

Recommended process:
- pick one canonical multivar regime
- pick one canonical univar regime
- pick one canonical NDLM regime if NDLM remains enabled
- only then wire in deterministic covariates across all five cutoffs

### User-selected provisional overrides

You have now chosen these cross-cutoff multivar legacy settings:
- `lam1 = 1.0`
- `lam2 = 1.0`
- `forecast_cov.c_factor = 1.0`

Given those choices, the five-cutoff regime is aligned on the multivar legacy fit settings except for the still-unresolved transfer-mode coverage.

## 12C. Provisional Canonical Cross-Cutoff Parameter Set

This is the current canonical parameter set implied by the existing resolved runs plus your override decisions.

### exDQLM multivar

- implementation mode: `legacy_bridge`
- forecast transfer primary mode: `drop`
- forecast transfer coverage:
  - unresolved, because current runs are mixed between `drop` only and `[drop, keep]`
- state evolution:
  - `df_t = 0.9999`
  - `df_s1 = 0.9999`
  - `df_s2 = 0.9999`
  - `df_s67 = 0.9999`
  - `df_discrep = 0.999`
  - `lambda = 0.97`
  - `df_trans = 0.999999`
  - `df_covs = 0.999999`
- gamma/sigma fit policy:
  - `warmup_freeze_iters = 5`
  - `min_update_iters = 50`
  - `min_total_iters = 50`
  - `max_iter = 100`
  - `convergence_tol = 1e-6`
  - `freeze_target = gamma_sigma`
  - init mode `robust`
  - `sigma_floor = 0.001`
  - `sigma_scale = 1.0`
  - objective guard enabled, mode `adaptive_freeze`, penalty `1e12`
  - `transfer_compare_fast.enabled = false`
- legacy fit settings:
  - `lam1 = 1.0`
  - `lam2 = 1.0`
  - `n_samp = 2000`
  - `sims_enabled = true`
  - `use_covariates = true`
  - `forecast_cov.c_factor = 1.0`

### exDQLM univar

- implementation mode: `legacy_bridge`
- state evolution:
  - `df_t = 0.9999`
  - `df_s1 = 0.9999`
  - `df_s2 = 0.9999`
  - `df_s67 = 0.9999`
  - `lambda = 0.97`
  - `df_trans = 0.999999`
  - `df_covs = 0.999999`
- gamma/sigma fit policy:
  - `warmup_freeze_iters = 5`
  - `min_update_iters = 50`
  - `min_total_iters = 50`
  - `max_iter = 800`
  - `convergence_tol = 1e-6`
  - `elbo_rel_tol = 2.5e-4`
  - init mode `robust`
  - `sigma_floor = 0.001`
  - `sigma_scale = 1.0`
  - objective guard enabled, mode `adaptive_freeze`, penalty `1e12`
- legacy fit settings:
  - `lam1 = 1.0`
  - `lam2 = 1.0`
  - `n_samp = 2000`
  - `sims_enabled = true`
  - `use_covariates = true`

### NDLM main

- implementation mode: `legacy_bridge`
- kalman backend: `cpp`
- state evolution:
  - `df_t = 0.9999`
  - `df_s1 = 0.9999`
  - `df_s2 = 0.9999`
  - `df_s67 = 0.9999`
  - `df_discrep = 0.999`
  - `lambda = 0.97`
  - `df_trans = 0.999999`
  - `df_covs = 0.999999`
- gamma/sigma fit policy:
  - `min_total_iters = 50`
  - `max_iter = 2000`
  - `convergence_tol = 1e-6`
  - `elbo_rel_tol = 2.5e-4`
- legacy fit settings:
  - `lam1 = 1.0`
  - `lam2 = 1.0`
  - `n_samp = 2000`
  - `sims_enabled = true`
  - `use_covariates = true`

### Shared across all planned cutoff runs

- quantiles:
  - `0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95`
- site:
  - USGS `11160500`
- deterministic climate covariate plan:
  - precipitation: GEFS `APCP` ensemble mean, daily total
  - soil: NWM `SOILSAT_TOP`, daily average, deterministic short-range + ensemble mean medium/long range
  - PCA: unchanged

## 12D. Overwrite Targets, Figure Backup, And Execution Order

### Run directories to overwrite

These are the five run directories that should be overwritten on rerun:
- [multimodel_20210123](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20210123)
- [multimodel_20211112](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20211112)
- [multimodel_20211221](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20211221)
- [multimodel_20220511](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20220511)
- [multimodel_20221225](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/multimodel_20221225)

### Baseline posterior PNG backup

Before any overwrite, I copied all existing `posterior_samples_*.png` files from those five runs into:
- [posterior_samples_baseline_20260309T014133Z](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/tmp/posterior_samples_baseline_20260309T014133Z)

This backup preserves the current baseline figures for later comparison against the deterministic-covariate reruns.

### Existing bundle sources to reuse

Current run-scoped configs resolve to these existing flow-bundle sources:
- `2021-01-23`
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/data/forecats_inputs/site=11160500/cutoff_date=2021-01-23/run_id=20260305_single_retro_policy_pre1080_gapfix_r01/meta.yaml`
- `2021-11-12`
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/data/forecats_inputs/site=11160500/cutoff_date=2021-11-12/run_id=20260219_single_retro_policy_pre1080_r01/meta.yaml`
- `2021-12-21`
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/data/forecats_inputs/site=11160500/cutoff_date=2021-12-21/run_id=20260219_single_retro_policy_pre1080_r01/meta.yaml`
- `2022-05-11`
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/data/forecats_inputs/site=11160500/cutoff_date=2022-05-11/run_id=20260219_single_retro_policy_pre1080_r01/meta.yaml`
- `2022-12-25`
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/forecats_inputs_compat/site=11160500/cutoff_date=2022-12-25/run_id=20260220_single_retro_policy_pre20_r01_compat_fullhist2010`

Note:
- For the first four cutoffs, `existing_bundle_path` currently points at `meta.yaml`.
- `R/unified/stages/stage_forecats.R:594-606` already handles that by promoting the parent directory to `bundle_root`.

### Planned execution order

Run the five cutoffs in this exact batch order:

1. Batch 1
   - `multimodel_20210123`
   - `multimodel_20211112`
2. Batch 2
   - `multimodel_20211221`
   - `multimodel_20220511`
3. Batch 3
   - `multimodel_20221225`

### Ready-to-run gate before launch

The reruns are ready from a planning standpoint once these are true:
- the deterministic covariate implementation is in place
- the multivar dual-mode choice remains `drop + keep`
- the canonical parameters in Section 12C are reflected in the launch configs
- overwrite behavior still targets the five run directories above
- comparison figures continue to write outside the overwrite targets, with the baseline backup already preserved

Current status:
- all five conditions are now satisfied

## 12E. Implemented Deterministic Covariate Wiring

Implemented code changes:
- `R/unified/deterministic_climate_covariates.R`
  - new helper module that materializes run-scoped deterministic precipitation and soil covariates from the GEFS/NWM handoff cache
  - precipitation policy:
    - GEFS `APCP`
    - daily total by actual `target_date`
    - ensemble reduction supports `mean` or `median`
  - soil policy:
    - NWM `SOILSAT_TOP`
    - daily average by actual `target_date`
    - medium-range and long-range land stitched by date priority
    - converted from saturation fraction to estimated volumetric water content using a site-level porosity estimated from medium-range `SOIL_M` layers 0 and 1
  - horizon contract:
    - derived from the run-scoped GloFAS forecast horizon unless explicitly overridden
    - requires full coverage across the post-cutoff window when `require_full_horizon = yes`

- `R/unified/stages/stage_data_prep_shared.R`
  - still snapshots the run-scoped shared bundle
  - now, when `inputs.deterministic_climate.enabled = yes`, it rewrites the run-scoped `PPT` and `SOIL` covariate CSVs so they contain:
    - observed history through the cutoff date
    - deterministic forecast values from `cutoff + 1` through the full flow horizon
  - writes provenance/debug artifacts under:
    - `inputs/shared/deterministic_climate/`

- `R/unified/stages/stage_post.R`
  - now resolves the same run-scoped shared covariate bundle used by fit
  - passes:
    - `ENV_COV_ELI_PATH`
    - `ENV_COV_ONI_PATH`
    - `ENV_PPT_PATH`
    - `ENV_SOIL_PATH`
    - `ENV_PCA_PATH`
    into the post stack

- `R/environmetrics/00_paths.R`
  - now resolves climate covariates from the run-scoped env overrides
  - in strict mode it fails fast if those run-scoped paths are missing
  - in non-strict mode it still preserves backward-compatible fallback behavior

- `R/unified/config.R`
  - added config support for `inputs.deterministic_climate.*`
  - added path resolution and validation for the handoff root
  - updated `lam1/lam2` validation to allow the user-selected boundary value `1.0`

- `config/unified_run.template.yaml`
  - now documents the deterministic climate config surface

- `scripts/unified_run.R`
  - now sources the deterministic climate helper module

Run-config preparation completed:
- The five overwrite-target configs now all:
  - enable `forecats`, `data_prep_shared`, and `fit`
  - enable deterministic climate substitution
  - use multivar `forecast_transfer_modes = [drop, keep]`
  - use `lam1 = 1.0`
  - use `lam2 = 1.0`
  - use `forecast_cov.c_factor = 1.0`
  - use `df_t = df_s1 = df_s2 = df_s67 = 0.99999` across multivar, univar, and NDLM state-evolution blocks

Smoke tests passed:
- Config validation for all five cutoff configs:
  - `multimodel_20210123`
  - `multimodel_20211112`
  - `multimodel_20211221`
  - `multimodel_20220511`
  - `multimodel_20221225`
- End-to-end `forecats + data_prep_shared` deterministic-climate smoke:
  - [detclim_smoke_20211112](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/tmp/detclim_smoke_20211112)
  - confirmed:
    - run-scoped `cov_03_PPT.csv` and `cov_04_SOIL.csv` were rewritten
    - post-cutoff windows contain exactly 28 future rows
    - those future rows match the deterministic forecast export files exactly
- Compatibility-bundle smoke:
  - [detclim_smoke_20221225](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/tmp/detclim_smoke_20221225)
  - confirmed the same deterministic wiring works for the alternate `existing_bundle_path` layout used by `2022-12-25`
- Strict post path-resolution smoke:
  - confirmed `R/environmetrics/00_paths.R` resolves run-scoped `ELI`, `ONI`, `PPT`, `SOIL`, and `PCA` paths instead of project-root climate files

Practical effect:
- The future observed PRISM/soil covariates are no longer the source of truth once a run uses `inputs.deterministic_climate.enabled = yes`.
- Fit and post now share the same run-scoped covariate series, so the main fit/post leakage path has been removed.
- PCA remains unchanged, as requested.

Ready-to-run status:
- The code wiring is complete.
- The launch configs for the five target cutoffs are prepared.
- The planned execution order remains:
  1. `multimodel_20210123`, `multimodel_20211112`
  2. `multimodel_20211221`, `multimodel_20220511`
  3. `multimodel_20221225`
- The workflow is ready for the staged reruns.

## 13. File-By-File Audit Map

### Unified orchestration

- `scripts/unified_run.R`
  - top-level stage orchestrator; source of truth for stage order and dispatch
  - future-covariate relevance: indirect only

- `R/unified/config.R`
  - default config, transfer-mode resolution, path resolution
  - future-covariate relevance: high for later config plumbing

- `config/unified_run.template.yaml`
  - operator-facing template for stages, model toggles, and fit covariate paths
  - future-covariate relevance: high for later deterministic-covariate config surface

### Stage logic

- `R/unified/stages/stage_forecats.R`
  - builds or snapshots retros/NWS/GloFAS bundle
  - future-covariate relevance: no direct PPT/SOIL/PCA handling today

- `R/unified/stages/stage_data_prep_shared.R`
  - copies shared parameters, flow inputs, and covariate CSVs into `inputs/shared/*`
  - now also materializes deterministic PPT/SOIL splices when `inputs.deterministic_climate.enabled = yes`
  - future-covariate relevance: implemented run-scoped insertion point for deterministic PPT/SOIL

- `R/unified/stages/stage_fit.R`
  - launches family fits and passes run-scoped covariate paths through env vars
  - future-covariate relevance: already has the needed path plumbing

- `R/unified/stages/stage_post.R`
  - launches synthesis/post stack and passes retros/NWS/GloFAS plus run-scoped covariate env overrides
  - future-covariate relevance: implemented fit/post covariate consistency bridge

### Multivariate exDQLM fit path

- `scripts/run_DISC_Optimal_Synth_Ranges_W.R`
  - wrapper that selects `drop` vs `keep`
  - future-covariate relevance: small but explicit mode switch

- `DISC_Optimal_Synth_Ranges_W.r`
  - multivar `drop` implementation
  - future-covariate relevance: builds `X_f` but does not use it for forecast propagation

- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
  - multivar `keep` implementation
  - future-covariate relevance: primary fit-time consumer of post-cutoff `X_f`

- `R/disc_w/01_paths_inputs.R`
  - resolves path defaults for multivar fit
  - future-covariate relevance: key fallback point to project-root covariate files

- `R/disc_w/02_io_loaders.R`
  - CSV readers and input loaders
  - future-covariate relevance: low; mostly type-safe I/O helpers

- `R/disc_w/03_covariates_standardize.R`
  - builds `X`, `X_f`, `Y`, and standardizes covariates
  - future-covariate relevance: central fit-side split and horizon logic

### Univariate exDQLM fit path

- `scripts/run_exdqlm_univar.R`
  - theory-aligned univariate runner wrapper
  - future-covariate relevance: indirect

- `R/unified/families/exdqlm_univar/01_inputs.R`
  - loads retros and covariates, aligns them to historical length `T`
  - future-covariate relevance: confirms no fit-time `X_f`

- `R/unified/families/exdqlm_univar/02_model_spec.R`
  - defines the univariate state/model specification
  - future-covariate relevance: none identified in this audit

- `R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R`
  - variational or fit-loop updates over historical `y` and `X`
  - future-covariate relevance: confirms fit uses only historical `X`

- `R/unified/families/exdqlm_univar/zz_run.R`
  - thin runner that wires load-inputs to fit
  - future-covariate relevance: low

### Post and synthesis path

- `scripts/run_environmetrics_figures.R`
  - modular post runner
  - future-covariate relevance: selects and sources the modules that later rebuild `X_f`

- `R/environmetrics/00_paths.R`
  - central path inventory for post
  - future-covariate relevance: currently hardcodes PRISM / ERA5 soil / PCA project-root files

- `R/environmetrics/10_data_inputs.R`
  - rebuilds flow ensemble matrices plus climate covariate `X` and `X_f`
  - future-covariate relevance: central post-side split and horizon logic

- `R/environmetrics/20_model_setup.R`
  - post-time multivar setup
  - future-covariate relevance: keep-mode consumes `X_f`

- `R/environmetrics/40_figures.R`
  - full mixed-family figures/tables
  - future-covariate relevance: downstream consumer of already-built post objects; not the primary place to change sourcing

- `R/environmetrics/40_figures_multivar_only.R`
  - multivar-only figure path
  - future-covariate relevance: downstream consumer; also compares forecasts with realized future USGS, not climate covariate sources

### Additional file that matters even though it was not in the original required list

- `R/environmetrics/30_univariate_and_misc.R`
  - active post module in univariate and multivar-only module plans
  - future-covariate relevance: confirmed user-facing univariate forecast synthesis depends on `X_f`

## 12F. Validate/Report Wiring Status

Deterministic-climate provenance is now wired through `data_prep_shared`, `post`, `validate`, and `report`.

Confirmed smoke coverage:
- `repro/tmp/detclim_validate_report_smoke_20211112`
- `repro/tmp/detclim_validate_report_smoke_20221225`

Confirmed behavior:
- `validate/compare_report.json` now includes a `deterministic_climate` section and fails if required run-scoped deterministic covariate artifacts are missing or inconsistent.
- `report/summary.json` and `report/summary.md` now surface deterministic climate enablement, source family, reduction, horizon, and artifact paths.
- `post` resolves run-scoped covariate overrides via `ENV_PPT_PATH`, `ENV_SOIL_PATH`, `ENV_PCA_PATH`, `ENV_COV_ELI_PATH`, and `ENV_COV_ONI_PATH`, closing the prior project-root fallback leakage path in strict mode.

Operational note:
- The five cutoff configs already set `validation.compare.mode: none`, so these deterministic-covariate reruns will not be compared against the old retrospective-covariate canonical outputs.

## 12G. Ordered Batch Execution Plan

Launcher:
- `scripts/run_unified_detclim_cutoff_batches.sh`

Execution order:
1. `multimodel_20210123`
2. `multimodel_20211112`
3. `multimodel_20211221`
4. `multimodel_20220511`
5. `multimodel_20221225`

Batch grouping preserved:
- batch 1: `20210123`, `20211112`
- batch 2: `20211221`, `20220511`
- batch 3: `20221225`

Execution policy:
- sequential within batch for robustness
- stop on first failure
- delete the target run directory before rerun so stale artifacts do not survive an overwrite
- write per-cutoff logs plus a batch-level status ledger under `repro/tmp/unified_detclim_batches_<timestamp>/`

# exDQLM Multivariate Keep Freeze and Epsilon/Discount Grid Plan

Date: 2026-05-24

Status: investigation and implementation plan for the next parameter-specification exploration. No new launch is authorized by this document.

## Executive Decision

The 2026-05-23 near-zero all-cutoff `exdqlm_multivar_keep` campaign is a valid freeze point for the repaired `log1p_only` workflow:

- all five cutoffs completed fit/post/validate/report;
- all seven quantiles were fit per cutoff;
- current post outputs include the main publication-style cutoff-window figures, ELBO overview, CRPS tables, input-health tables, gamma/sigma summaries, and final-time covariate-effect summaries;
- `.RData` artifacts under the campaign root have already been cleaned successfully.

The campaign is **not** a complete component-diagnostics freeze point. It ran the smoke-fast post path, which intentionally skips the retained-state component diagnostics. The future epsilon/discount-factor grid must therefore run the new component-diagnostic gate while `.RData` is still present, then delete `.RData` only after those diagnostics and CRPS tables pass.

Do not simply switch off smoke-fast and run the entire legacy full post stack for `log1p_only` production. The q50 component-diagnostic path has now been repaired and gated for the grid workflow, but the intended production mode is smoke-fast outputs plus the dedicated q50 component module, not the broad legacy figure stack.

## Current Freeze Evidence

Runtime root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_nearzero_20260523`

Tracked launch package:

- `docs/exdqlm_multivar_keep_allcutoffs_fullhistory_nearzero_launch_20260523.md`
- `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_fullhistory_nearzero_20260523.template.yaml`
- `config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_fullhistory_nearzero_20260523.yaml`

Observed runtime facts from the campaign root:

| check | value |
| --- | ---: |
| completed cutoff runs | 5 |
| `post_artifacts_summary.json` files | 5 |
| `tables/crps_forecast_summary.csv` files | 5 |
| `tables/crps_forecast_per_time.csv` files | 5 |
| `tables/covariate_effects_summary.csv` files | 5 |
| retained `.RData` / `.rda` files under the current root | 0 |
| `multivar_transfer_coefficients_window_q50.csv` files | 0 |

Per-cutoff post logs show `POST_SMOKE_FAST: TRUE` and execution of `40_figures_smoke_fast.R`, not `40_figures_multivar_only.R`.

The smoke-fast post artifact contract passed for each cutoff. Example contract fields from the 2021-01-23 run:

- `outputs_nonempty=true`
- `has_figure=true`
- `synthesis_cache_files_present=true`
- `synthesis_core_shapes_ok=true`
- `table_exports_present=true`
- `missing_paths=[]`

## Locked Working Contract

The current freeze used:

- cutoffs: `20210123`, `20211112`, `20211221`, `20220511`, `20221225`;
- quantiles: `0.05`, `0.20`, `0.35`, `0.50`, `0.65`, `0.80`, `0.95`;
- history start: `1987-05-29`;
- transform policy: `log1p_only`;
- post/fit internal scale: `log1p_cms`;
- transfer mode: `keep`;
- harmonics: enabled indices `[1, 2, 3]`;
- transfer covariates: `PPT`, `SOIL`, `PCA`, `PPT_sq`, `SOIL_sq`, `PPT_x_SOIL`, `PPT_lag1`, `PPT_lag2`, `PPT_lag3`, `SOIL_lag1`, `SOIL_lag2`, `SOIL_lag3`;
- state discounts: `df_t=0.99999`, `df_s1=df_s2=df_s67=df_discrep=0.9999`, `lambda=0.97`, `df_trans=df_covs=0.9999999`;
- forecast covariance prior: `epsilon=365`, `c_factor=1`;
- VB budget: `max_iter=100`, `min_update_iters=50`;
- near-zero fallback: `enabled=true`, `mode=sigma_only`, `gamma_anchor=full_candidate`;
- one numerical thread per quantile worker and seven workers per cutoff row.

The generated run configs point to the canonical 20260510 shared-input bundle for all cutoffs. The run-scoped snapshots contain the expected retrospective, GLOFAS, NWS, USGS, deterministic precipitation/soil, and engineered covariate-feature files under `inputs/shared/`.

## Current Post-Stage Wiring

The current unified post stage resolves run-scoped multivariate `.RData` paths and passes them through `UNIFIED_DISC_W_RDATA_PATHS` to `scripts/run_environmetrics_figures.R` (`R/unified/stages/stage_post.R:355-411`, `R/unified/stages/stage_post.R:591-686`).

For multivar-only runs, `stage_post` forces smoke-fast mode when `post.force_isolation_smoke_fast=true`; see `R/unified/stages/stage_post.R:510-528`. The module selector then chooses:

- smoke-fast multivar-only path: `30_univariate_and_misc.R` plus `40_figures_smoke_fast.R`;
- full multivar-only path: `30_univariate_and_misc.R` plus `40_figures_multivar_only.R`.

This selection is encoded in `R/unified/post_module_plan.R:57-67`.

The runner writes post artifacts and then enforces the post artifact contract in `scripts/run_environmetrics_figures.R:513-545`. The `.RData` cleanup happens only after post succeeds when `CLEANUP_RDATA_AFTER_POST=1`; see `scripts/unified_run.R:193-218` and `scripts/unified_run.R:296-306`.

## Diagnostic Gap

The current smoke-fast path emits the CRPS/grid-selection artifacts we need:

- `tables/crps_forecast_summary.csv`
- `tables/crps_forecast_per_time.csv`
- `tables/crps_input_health.csv`
- `tables/crps_input_health_per_time.csv`
- `tables/gamma_summary.csv`
- `tables/sigma_summary.csv`
- `tables/covariate_effects_summary.csv`
- cutoff-window synthesis sample/quantile CSVs and figures

It does not emit the retained-state component diagnostics:

- `multivar_transfer_state_window_q50.csv`
- `multivar_transfer_coefficients_window_q50.csv`
- `multivar_transfer_state_contract_q50.csv`
- `multivar_transfer_identity_check_q50.csv`
- `multivar_transfer_contract_q50.csv`
- `multivar_forecast_window_q50_summary.csv`
- `multivar_forecast_window_q50_metrics.csv`
- `multivar_trace_summary_q50.csv`
- q50 trend/season/transfer/source decomposition figures.

Those retained-state outputs are implemented in `R/environmetrics/40_figures_multivar_only.R:1260-1641`, but the current completed root no longer has `.RData`, so these outputs cannot be reconstructed for the 2026-05-23 root without rerunning a representative fit or using another retained `.RData` source.

## Log1p Hazard in the Full Component Module

The original component module had loglog-era assumptions that were unsafe for the current `log1p_only` workflow:

- `R/environmetrics/40_figures_multivar_only.R:112-118` reads `San_Lorenzo_Daily_USGS_R$data0` as `flow_log1p` and then applies `log(...)`, producing loglog values when the current post input is already `log1p_cms`;
- `R/environmetrics/40_figures_multivar_only.R:1315-1484` labels multiple plots as `log(log(flow + 1))`;
- the smoke-fast multivar cutoff-window path already uses log1p-scale helpers such as `smoke_usgs_log1p_by_dates()` in `R/environmetrics/40_figures_smoke_fast.R:618-639` and log1p-scale plotting labels in `R/environmetrics/40_figures_smoke_fast.R:1147-1196`.

Therefore the next implementation should not just set `post.smoke_fast=false`. It should either repair `40_figures_multivar_only.R` for `log1p_only` or extract a new lightweight component-diagnostics module that reuses the log1p-safe helpers from smoke-fast.

Implementation status on 2026-05-24: repaired for the q50 component-diagnostic gate. `R/environmetrics/02_helpers_core.R` now provides a scale-aware helper for shared USGS `data0` truth, `R/environmetrics/40_figures_multivar_only.R` uses that helper and dynamic labels, and `tests/testthat/test_scale_contract_adapters.R` covers the log1p identity and explicit loglog conversion behavior.

## Grid Selection Contract

For each epsilon/discount specification and cutoff, the primary model-selection table is:

`post/outputs/<run_id>/tables/crps_forecast_per_time.csv`

The primary score is the `exdqlm_multivar_synth_keep` row on `score_scale=log_cms_plus1`.

Recommended ranking:

1. Require fit/post/validate/report pass for all seven quantiles and all selected cutoffs.
2. Require post artifact contract pass and input-health pass.
3. Require component-diagnostic contract pass when component diagnostics are enabled.
4. Rank by pooled mean CRPS over all available forecast-window days and cutoffs for `exdqlm_multivar_synth_keep`.
5. Report both pooled CRPS and per-cutoff mean CRPS; do not hide cutoff-specific failures behind the pooled score.
6. Use median CRPS, worst-cutoff mean CRPS, and input-health margins as tie-breakers.
7. Keep GLOFAS and NWS ensemble rows as controls, but select epsilon/discount specs only from the synthesis row.

The current per-run CRPS summary contains model/run fields but not enough explicit spec metadata for a multi-spec ranking. The grid aggregator must join CRPS rows to a frozen spec manifest containing:

- `grid_spec_id`;
- `epsilon`;
- `c_factor`;
- all discount factors;
- `max_iter`;
- `min_update_iters`;
- transform policy;
- harmonics;
- transfer covariate contract;
- data-start and bundle root;
- code commit;
- generated config path and run root.

## Required Implementation Plan

### P0. Freeze Current Successful Campaign

1. Keep the 2026-05-23 runtime root as the repaired baseline.
2. Keep the copied temporary figure review folder untracked.
3. Do not attempt to regenerate component diagnostics from this root because its `.RData` files have already been removed.
4. Record the current post gap explicitly in the launch doc and tracker.

### P1. Repair Component Diagnostics for `log1p_only`

Status: implemented and tested on 2026-05-24.

1. Replace loglog-era truth conversion in `40_figures_multivar_only.R` with a scale-aware helper:
   - if `UNIFIED_ANALYSIS_SCALE_POST_INTERNAL=log1p_cms`, use `data0` directly;
   - if `log_log1p_cms`, convert to loglog only when explicitly requested;
   - otherwise use `unified_convert_scale()` or fail closed.
2. Rename or relabel component figures so the y-axis states `log1p cms` under the current contract.
3. Reuse the smoke-fast `smoke_usgs_log1p_by_dates()` logic or move a shared helper into `02_helpers_core.R`.
4. Add tests for the scale-aware future-truth helper and labels.

### P2. Add a Production Component-Diagnostic Mode

Status: implemented and tested on 2026-05-24.

Add a config switch such as:

```yaml
post:
  smoke_fast: true
  force_isolation_smoke_fast: true
  multivar_component_diagnostics:
    enabled: true
    quantile: 0.50
    pre_days: 30
    fail_fast: true
```

The intended behavior:

- run smoke-fast outputs for public figures, synthesis caches, CRPS, and tables;
- additionally run the repaired q50 component diagnostics before `.RData` cleanup;
- fail post if the component contract fails.

This avoids using the entire full legacy post stack while still producing the retained-state diagnostics we need.

Implemented wiring:

- `R/unified/config.R` adds and validates `post.multivar_component_diagnostics`;
- `R/unified/stages/stage_post.R` exports the component-diagnostic environment only when multivariate exDQLM is active;
- `scripts/run_environmetrics_figures.R` logs the switch, appends the component module to the selected post modules, and passes the gate into the artifact contract;
- `R/unified/post_module_plan.R` keeps smoke-fast as the main post route and appends `40_figures_multivar_only.R` only when the component gate is enabled.

Production grid configs should keep `post.multivar_component_diagnostics.fail_fast=true`. The switch is wired through for debug runs, but the production cleanup policy depends on the default fail-fast behavior.

### P3. Strengthen the Post Artifact Contract

Status: implemented and tested on 2026-05-24.

When `post.multivar_component_diagnostics.enabled=true`, require:

- `multivar_trace_summary_q50.csv`;
- `multivar_forecast_window_q50_summary.csv`;
- `multivar_forecast_window_q50_metrics.csv`;
- `multivar_transfer_state_window_q50.csv`;
- `multivar_transfer_coefficients_window_q50.csv`;
- `multivar_transfer_state_contract_q50.csv`;
- `multivar_transfer_identity_check_q50.csv`;
- `multivar_transfer_contract_q50.csv`;
- q50 trend/season/transfer/source figures;
- contract fields showing finite forecast transfer retention in `keep` mode.

The contract must pass before `.RData` cleanup. If it fails, `.RData` should remain for debugging.

Implemented in `R/unified/post_artifact_contract.R`. The new gate requires the q50 CSV/PNG diagnostics and checks `multivar_transfer_contract_q50.csv` for retained-transfer semantics under `keep`, including finite forecast zeta and finite `mu_without_transfer` rows.

### P4. Add a Grid Aggregator

Status: grid launch matrix prepared; full post-run CRPS/spec aggregator still deferred until outputs exist.

The frozen user grid now lives in:

- `config/he2_grid_specs/exdqlm_multivar_keep_epsilon_discount_grid_20260524.csv`
- `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_epsilon_discount_grid_20260524.template.yaml`

The grid config builder is:

- `scripts/build_he2_exdqlm_multivar_keep_grid_configs.py`

Prepared scope:

| item | value |
| --- | ---: |
| discount cases | 6 |
| epsilon values per case | 5 |
| grid specs | 30 |
| cutoffs | 5 |
| spec-cutoff rows | 150 |
| quantile fits | 1050 |
| concurrent rows | 8 |
| workers per row | 7 |
| max active quantile workers | 56 |

The queue is intentionally configured to continue after failed spec-cutoff rows. Those failures are expected to be
kept as evidence in the later ranking report rather than treated as launch-controller failures.

Detailed evaluation and per-cutoff selection plan:

- `docs/exdqlm_multivar_keep_grid_evaluation_plan_20260524.md`

Create a reproducible script that consumes one or more grid runtime roots and writes under `reports/`:

- `grid_crps_per_time.csv`;
- `grid_crps_summary_by_spec_cutoff.csv`;
- `grid_crps_summary_by_spec.csv`;
- `grid_spec_rankings.csv`;
- `grid_input_health_summary.csv`;
- `grid_component_contract_summary.csv`;
- CRPS-by-lead and CRPS-by-cutoff plots.

The script should never infer epsilon/discount values from run names alone; it must read the frozen spec manifest or resolved configs.

### P5. Add Prelaunch Validation

Status: static validation implemented and passed for the prepared 2026-05-24 grid.

Validator:

- `scripts/validate_he2_exdqlm_multivar_keep_grid_prelaunch.py`

Runtime validation result under the prepared matrix root:

- `PRELAUNCH_VALIDATION.md`
- `prelaunch_validation_summary.json`
- `prelaunch_validation_checks.csv`

Observed validation result: `8720` checks, `0` failures.

Before any grid launch, validate:

- every cutoff uses the canonical 20260510 shared-input bundle or an explicitly approved successor;
- every cutoff starts at `1987-05-29`;
- transform policy is `log1p_only`;
- harmonics are `[1, 2, 3]`;
- transfer mode is `keep`;
- full engineered transfer covariates are present;
- `CLEANUP_RDATA_AFTER_POST=1` is active for production grid rows;
- component diagnostics are enabled and required before cleanup;
- spec metadata in the frozen manifest matches each generated config.

### P6. Smoke Then Launch Grid

Recommended launch sequence:

1. one cutoff, three quantiles (`q05`, `q50`, `q95`) for each proposed spec;
2. one full cutoff with all seven quantiles for the best few specs;
3. all five cutoffs only after the post component-diagnostic gate and CRPS aggregator pass.

For large grids, do not launch all specs x five cutoffs x seven quantiles at once. The working 35-core all-cutoff baseline is safe for one spec; multiply concurrency only after storage and runtime pressure are measured.

### P7. Cleanup Policy

Future grid runs should not retain `.RData` after successful post. The cleanup rule is:

1. fit writes `.RData`;
2. smoke-fast post writes public figures, CRPS, table exports, and synthesis caches;
3. repaired component diagnostics write retained-state summaries and figures;
4. post artifact contract passes;
5. validate/report pass;
6. `.RData` cleanup removes only files under that run root.

If any of steps 2-4 fail, preserve `.RData` for diagnosis.

## Ready/Not Ready

Ready now:

- the repaired near-zero fit workflow;
- all-cutoff baseline public figures and CRPS tables;
- current `.RData` cleanup behavior after post success;
- existing smoke-fast synthesis/CRPS path for `log1p_only`.
- repaired log1p-safe q50 component diagnostics;
- `post.multivar_component_diagnostics` wiring for smoke-fast plus component diagnostics;
- post artifact contract checks for q50 component outputs and retained-transfer `keep` semantics.
- frozen 30-spec epsilon/discount manifest;
- generated 150-row all-cutoff grid matrix;
- static prelaunch validation for the generated configs;
- queue support for `--continue-on-fail` and `--skip-compares`;
- monitor support for spec-aware all-cutoff/all-grid live status tables.

Not ready yet:

- retrospective production of full component paths from the already-cleaned 2026-05-23 root;
- final grid ranking without a spec-aware CRPS aggregator;
- production epsilon/discount grid launch, because a smoke/prelaunch execution pass and ranking/reporting scripts still need to be executed.

Immediate next engineering work:

1. run a one-cutoff retained-diagnostics smoke with cleanup disabled for inspection;
2. rerun that smoke with cleanup enabled to verify `.RData` removal only after diagnostics pass;
3. launch the prepared grid if the smoke passes;
4. add/run the grid CRPS/spec aggregator once outputs exist;
5. freeze per-cutoff winners and rejected/failing specs in a final grid-selection report.

## Validation Added on 2026-05-24

The pre-grid component gate was validated with:

- parse checks for `R/environmetrics/02_helpers_core.R`, `R/environmetrics/40_figures_multivar_only.R`, `R/unified/config.R`, `R/unified/stages/stage_post.R`, `R/unified/post_artifact_contract.R`, `R/unified/post_module_plan.R`, and `scripts/run_environmetrics_figures.R`;
- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_module_plan.R')"`: pass, 22 expectations;
- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_artifact_contract.R')"`: pass, 46 expectations;
- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_config_mode_resolution.R')"`: pass, 64 expectations;
- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_scale_contract_adapters.R')"`: pass, 18 expectations.

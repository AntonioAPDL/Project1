# HE2 exdqlm_univar Post Blocker Fix Plan

## Purpose

Isolate the current `exdqlm_univar` no-launch validation failure and define a clean, minimal, well-tested fix path that preserves the corrected shared-input relaunch contract.

This plan does **not** launch anything.

## Resolution status

Resolved.

- the smoke-figure block now uses probability-aware univariate quantile selection
- the validator now honors the disabled sentinel for the generic `full_pipeline_quantile` path
- the exact-final-batch no-launch validator completed and wrote `prelaunch_validation_summary.json`
- the representative univariate full-pipeline smoke passed under:
  - `smoke_runs/full_pipeline/quantile_univar/exdqlm_univar/20210123/full_pipeline_exdqlm_univar_20210123_qsubset`

## Current state

The `exdqlm_univar` shared-spec package is structurally in good shape:

- corrected shared bundle lineage passes
- full-history cutoff smokes pass `5/5`
- family smoke passes
- validator internal tests pass
- q50-sensitive fit smoke passes
- representative full-pipeline fit and sampling pass

The remaining blocker is in the representative full-pipeline `post` stage.

## Exact failure

Representative case:

- run root:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_exact_final_batch_20260516/smoke_runs/full_pipeline/quantile/exdqlm_univar/20210123/full_pipeline_exdqlm_univar_20210123_qsubset`
- failing log:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_exact_final_batch_20260516/smoke_runs/full_pipeline/quantile/exdqlm_univar/20210123/full_pipeline_exdqlm_univar_20210123_qsubset/post/logs/post_runner.log`

Observed error:

```text
Error in (function (cond)  :
  error in evaluating the argument 'x' in selecting a method for function 'as.matrix': subscript out of bounds
Calls: source ... col_quantiles -> matrix_sample_time -> as.matrix -> <Anonymous>
```

Failure occurs when the post runner enters:

- `R/environmetrics/40_figures_smoke_fast.R`

## Main issue

The representative univariate full-pipeline smoke is intentionally reduced to three quantiles:

- active q probs: `0.35, 0.50, 0.65`
- evidence cache: `post/cache/univar_active_q_probs.rds`

The post cache confirms the reduced quantile shape:

- `y_forecast_uni.rds`: `3 x 512 x 28`
- `univar_raw_forecast_quantiles_log1p.rds`: `3 x 28`
- `synth_univar_forecast_quantiles_log1p.rds`: `3 x 28`

But the smoke-figure module still assumes the full seven-quantile lattice and directly indexes:

- `xb_forecast[1, , ]`
- `xb_forecast[4, , ]`
- `xb_forecast[7, , ]`
- `y_forecast[4, , ]`

Source:

- `R/environmetrics/40_figures_smoke_fast.R:1486`
- `R/environmetrics/40_figures_smoke_fast.R:1493`

That assumption is invalid for the reduced representative case, where only three quantiles are present. The immediate out-of-bounds fault is caused by the hard-coded `4` and `7` row access against a first dimension of `3`.

## Why this is the right root cause

The evidence lines up cleanly:

1. `post` has already completed the univariate synthesis prep and written the expected post caches.
2. The active quantile set is explicitly saved as `0.35, 0.50, 0.65`.
3. The failing figure block uses positional indexing instead of probability-aware lookup.
4. The failure occurs before `validate` or `report` start.

This is therefore a **post smoke-figure compatibility bug**, not:

- a bundle-lineage bug
- a fit-stage bug
- a sampling-stage bug
- a launch-controller bug

## Blast radius

### Primary fault site

- `R/environmetrics/40_figures_smoke_fast.R`
- section:
  - `profile_section("figures_smoke_fast.univar_forecast_window", ...)`

### Closely related code to audit

- `R/environmetrics/40_figures_smoke_fast.R:210`
  - `build_univar_location_forecast_summary()`
- `R/environmetrics/30_univariate_and_misc.R:738`
  - writes `univar_active_q_probs.rds`
- `R/environmetrics/30_univariate_and_misc.R:809`
  - determines requested univariate quantile bundle set

### Risk profile

The issue appears **localized**, not broad:

- the failure is in a single univariate forecast-window smoke subsection
- the existing fallback builder already supports degraded quantile availability conceptually
- the post cache already contains enough information to support a probability-aware fix

## Preferred fix strategy

### Principle

Do **not** force the representative univariate smoke back to seven quantiles just to satisfy a smoke-only figure assumption.

Instead:

1. keep the reduced representative smoke (`q35/q50/q65`)
2. make the smoke figure code robust to the active quantile set actually present
3. preserve the existing corrected relaunch package shape

### Why this is preferable

- keeps the representative smoke lightweight
- preserves the deliberate reduced validation slice
- avoids masking future quantile-subset bugs
- makes smoke figures more reusable across partial-quantile validation modes

## Concrete implementation plan

### Stage 1: freeze evidence and add a precise reproducer

Objective:

- make the failure reproducible without rerunning the entire validator

Actions:

1. record the exact failing case root in the validation-status docs
2. add a focused repro note or helper that loads:
   - `univar_active_q_probs.rds`
   - `y_forecast_uni.rds`
   - `univar_raw_forecast_quantiles_log1p.rds`
   - `synth_univar_forecast_quantiles_log1p.rds`
3. document the dimensional mismatch explicitly

Success criteria:

- one command or short script can restate the failure context and the shapes involved

### Stage 2: replace positional quantile indexing with probability-aware lookup

Objective:

- remove the invalid hard-coded `1/4/7` assumption from the univariate forecast-window smoke block

Preferred implementation:

1. add a small helper in `R/environmetrics/40_figures_smoke_fast.R` that:
   - accepts available quantile probabilities or row names
   - maps requested display targets (`0.05`, `0.50`, `0.95`) to:
     - exact row if available
     - nearest available row if not available
     - or fallback cached summary if raw sample arrays are not suitable
2. use:
   - `univar_active_q_probs.rds`
   - cached quantile matrices already written by `30_univariate_and_misc.R`
3. stop indexing raw arrays at `[4, , ]` or `[7, , ]` without checking dimension and active probability support first

Success criteria:

- the forecast-window smoke block does not assume seven quantiles
- the representative `q35/q50/q65` case can render the smoke figures without crashing

### Stage 3: decide the cleanest data source for the smoke figure block

Objective:

- choose one consistent source of truth for the univariate forecast-window display

Options:

1. **Preferred**: use cached quantile summaries already written to `post/cache/`
   - pros:
     - directly aligned with active quantile set
     - minimal recomputation
     - avoids fragile positional assumptions on raw sample arrays
2. use the existing `build_univar_location_forecast_summary()` fallback path
   - pros:
     - already handles degraded availability conceptually
   - cons:
     - still partly anchored to explicit `5/50/95` deterministic labels
3. keep using raw `xb_forecast` / `y_forecast`
   - not preferred
   - most fragile under reduced quantile subsets

Recommendation:

- use cached quantile summaries as the primary source
- use `build_univar_location_forecast_summary()` as fallback

### Stage 4: add regression tests

Objective:

- ensure this exact failure mode cannot silently return

Tests to add:

1. focused unit test for probability-aware univariate quantile selection:
   - case A: full 7-quantile support
   - case B: reduced `q35/q50/q65`
2. focused smoke compatibility test for the forecast-window block:
   - verifies no hard dependency on row indices `1/4/7`
3. update existing univariate shared-spec package tests to require:
   - representative full-pipeline smoke quantile set remains `q35/q50/q65`
   - figure-smoke path is compatible with reduced quantile availability

Success criteria:

- the reduced representative case is covered by automated tests
- tests fail if hard-coded seven-quantile assumptions are reintroduced

### Stage 5: rerun exact-final-batch no-launch validation

Objective:

- confirm the fix works in the real validation path, not just in a unit test

Required reruns:

1. exact-final-batch univariate validator
2. rebuild validation status artifacts

Success criteria:

- representative full-pipeline case clears:
  - `fit`
  - `post`
  - `validate`
  - `report`
- status moves from:
  - `fit_passed_post_pending`
  - to a true pass state

### Stage 6: launch decision boundary

Objective:

- define the exact point where `exdqlm_univar` becomes eligible for live launch

Launch only if all are true:

1. cutoff smokes still pass `5/5`
2. family smoke still passes
3. q50-sensitive fit smoke still passes
4. representative full-pipeline case passes fully
5. validation-status docs confirm `ready_for_launch_after_validation=true`

Then and only then:

- launch `exdqlm_univar`
- move from `14` live cores to the full `21`-core posture alongside `keep` and `drop`

## Recommended code changes

Expected touched files:

- `R/environmetrics/40_figures_smoke_fast.R`
- likely tests under:
  - `tests/python/`
- possible documentation refresh:
  - `reports/he2_exdqlm_univar_shared_relaunch_plan_20260516/HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_VALIDATION_STATUS_20260516.md`
  - `repro/run/HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_PLAN_20260516.md`

Expected untouched areas:

- live `keep` relaunch root
- live `drop` relaunch root
- queue/controller logic
- bundle builder contract

## Clean fix acceptance criteria

The fix is clean only if it satisfies all of these:

1. no launch is required to validate the repair
2. no multivariate workflow is disturbed
3. no bundle paths or scientific relaunch specs are changed unnecessarily
4. the reduced representative univariate smoke remains reduced
5. the smoke-figure code becomes compatible with active quantile subsets
6. automated tests cover the exact reduced-subset scenario

## Recommended next action

Implement **Stage 2** and **Stage 4** together:

1. patch `R/environmetrics/40_figures_smoke_fast.R` to use probability-aware quantile selection / cached quantile summaries
2. add focused regression tests for reduced univariate quantile subsets
3. rerun the exact-final-batch univariate validator

That is the smallest fix with the highest confidence.

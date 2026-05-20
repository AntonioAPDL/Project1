# exDQLM Patching Strategy

Date: 2026-05-20

## Purpose

This document records the recommended patching and versioning strategy before implementing the next
round of exDQLM theory-aligned fixes.

The goal is:

1. keep the patch series reviewable,
2. keep the implementation reproducible,
3. make rollback straightforward if changes are harmful,
4. avoid mixing core code changes with generated artifacts and run reports.

## Current git state

Checked on branch:
- `feature/export_posterior_tables`

Base commit:
- `f2414957654c61df92371ae51c876f21f8684c21`

Current working tree is **not clean**.

Current dirty inventory:
- `12` code files
- `5` theory docs
- `8` tests
- `10` scripts
- `40` generated report directories

### Dirty code files currently present

- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- `R/disc_w/02_io_loaders.R`
- `R/disc_w/03_covariates_standardize.R`
- `R/disc_w/_init.R`
- `R/environmetrics/10_data_inputs.R`
- `R/unified/config.R`
- `R/unified/families/shared_input_helpers.R`
- `R/unified/stages/stage_data_prep_shared.R`
- `R/unified/stages/stage_fit.R`
- `R/unified/stages/stage_post.R`
- `R/disc_w/08_gamsig_schedule.R`
- `R/disc_w/09_state_blend.R`

### Dirty docs currently present

- `docs/exdqlm_theory_source_map.md`
- `docs/exdqlm_sigma_gamma_equation_sheet.md`
- `docs/exdqlm_keep_drop_clarification.md`
- `docs/exdqlm_sigma_gamma_objective_audit.md`
- `docs/exdqlm_laplace_delta_audit.md`

### Dirty tests currently present

- `tests/testthat/test_univar_featurecov_design_contract.R`
- `tests/python/test_data_start_usgs_filter_contract.py`
- `tests/python/test_he2_exal_m_t1_discount_refresh_scaffold.py`
- `tests/python/test_prepare_reduced_defaultvb_temporal_bundle.py`
- `tests/testthat/test_disc_w_state_blend.R`
- `tests/testthat/test_disc_w_state_refresh_schedule.R`
- `tests/testthat/test_disc_w_warm_start_io.R`
- `tests/testthat/test_unified_gamma_sigma_state_refresh_schedule_config.R`

### Dirty scripts currently present

- `scripts/render_exal_m_t1_usgs_location_dynamics_review.R`
- `scripts/audit_he2_exal_m_t1_dimension_contract.R`
- `scripts/build_he2_exal_m_t1_discount_refresh_scaffold.py`
- `scripts/prepare_reduced_defaultvb_temporal_bundle.py`
- `scripts/render_exal_m_t1_fit_trace_review.py`
- `scripts/render_exal_m_t1_input_context_review.py`
- `scripts/render_exal_m_t1_newtheta_exps_review.R`
- `scripts/render_exal_m_t1_reducedspec_trend_identifiability_audit.R`
- `scripts/render_exal_m_t1_reducedspec_trend_zeta_correlation_audit.R`
- `scripts/render_exal_m_t1_retained_exps_components_review.R`

### Dirty generated artifacts currently present

There are currently `40` untracked report directories under `reports/`.

These are generated artifacts and should not be mixed into the core patch series unless explicitly
desired.

## Main constraint

Because the working tree is already dirty, the safe move is **not**:
- hard reset
- bulk checkout
- destructive cleanup

The safe move is:

1. preserve the current working state,
2. separate implementation patches from generated artifacts,
3. patch in small reversible steps.

## Recommended versioning strategy

### Strategy V1: checkpoint first, then patch in a focused series

This is the recommended approach.

1. Create a **checkpoint commit** for the current patch-relevant working tree.
2. Exclude the generated `reports/` directories from that core checkpoint commit.
3. If reports must be versioned, store them in:
   - a separate archival commit, or
   - a separate archival branch/tag,
   but not in the main implementation patch series.
4. After the checkpoint, implement the new theory-aligned fixes as a short sequence of focused
   commits.

Why this is optimal:
- we can revert implementation changes without disturbing audit/report artifacts
- diffs stay readable
- bisection stays possible
- regression debugging is much easier

### Strategy V2: patch without checkpointing

This is **not recommended**.

Reason:
- the current tree already mixes multiple strands of work
- new patching would make attribution harder
- rollback would be riskier and more ambiguous

## Recommended commit structure

The next implementation work should be split into a small patch series.

### Commit group A: optimization-theory alignment

Target:
- implement split optimization policy near `gamma = 0`

Why first:
- highest-priority theory-alignment gap from Stage 5
- likely highest impact on unstable behavior near zero

Files likely involved:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- possibly `R/disc_w/_init.R` if policy flags are added there
- tests for branch selection and mode choice

### Commit group B: exact moment cleanup

Target:
- replace generic Delta approximations with exact `u`-only moment formulas where available

Examples:
- `E[sigma]`
- `E[1/sigma]`

Why next:
- low-risk, theory-improving, numerically cleaner

Files likely involved:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- dedicated unit tests

### Commit group C: covariance and fallback semantics

Target:
- clarify covariance naming and semantics
- make fallback outputs explicitly non-Laplace
- fix namespace fragility in `Expected_f`

Examples:
- replace bare `hessian(...)` with `numDeriv::hessian(...)`
- rename or alias `Hess.LD` behavior clearly
- document or tag regularized/fallback covariance states

Why:
- strong implementation-quality improvement
- lowers maintenance and audit risk

### Commit group D: stale-path quarantine

Target:
- clearly annotate or quarantine stale duplicate paths

Primary candidate:
- `R/environmetrics/20_model_setup.R` duplicate Laplace path

Why last:
- not the active runtime path
- useful cleanup once the active path is improved

## Testing strategy

All implementation changes should be validated at four levels.

### T1. Unit tests

Examples:
- transform/Jacobian checks
- sign-split mode selection tests near `gamma = 0`
- exact-moment formula checks against closed form
- Hessian/covariance sign convention checks

### T2. Regression tests

Examples:
- compare old vs new expectation outputs on frozen synthetic fixtures
- compare mode location and covariance on known inputs
- ensure no unintended change away from near-zero `gamma` cases

### T3. Smoke workflow tests

Examples:
- one small reduced run
- confirm no startup failures
- confirm no objective guard explosions
- confirm returned structures remain consumable downstream

### T4. Empirical behavior checks

Examples:
- inspect problematic quantiles
- inspect sigma/gamma traces
- inspect fallback frequency
- inspect whether near-zero behavior improves

## Rollback strategy

Rollback should be designed before patching.

### R1. Small commits

Each logical patch group should be a separate commit so we can revert:
- mode-search changes
- moment changes
- semantics changes

independently.

### R2. Preserve baseline before touching theory-critical code

The checkpoint commit should represent the pre-patch audited baseline.

### R3. Avoid mixing generated outputs into the patch series

If generated outputs are mixed with code changes, rollback becomes noisy and harder to trust.

## Recommended immediate next steps

Before implementing any new patch:

1. create a checkpoint of the current patch-relevant working tree
2. exclude or isolate generated report directories from that checkpoint
3. implement Commit group A first
4. run tests for Commit group A before touching Commit group B

## Final recommendation

The optimal forward path is:

1. **checkpoint the current code/docs/tests/scripts state**
2. **keep generated reports out of the core patch series**
3. **patch in the order A -> B -> C -> D**
4. **require theory checks plus tests after each group**

This is the safest way to make the implementation more faithful, more robust, and easier to unwind
if any change proves harmful.

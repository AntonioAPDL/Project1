# exDQLM Patching Strategy

Date: 2026-05-20

## Purpose

This document is the implementation plan for the next round of theory-aligned exDQLM patching.
It is intentionally broader and more operational than the earlier strategy note.

The goals are:

1. keep the patch sequence theoretically grounded,
2. keep the implementation reproducible and reversible,
3. separate code changes from generated run artifacts,
4. verify behavior before patching, during patching, and after patching,
5. make it easy to determine whether a change improved or harmed the algorithm.

This document is a **plan only**. It does not authorize patch implementation by itself.

## Current baseline

### Repository baseline

Checked on branch:
- `feature/export_posterior_tables`

Checkpoint commit:
- `91d690e` `Checkpoint exdqlm theory audits and run-prep baseline`

This checkpoint has already been pushed to origin and is the reference baseline for the patch series.

Current tracked code/docs/tests/scripts state:
- clean relative to the checkpoint baseline

Current untracked state:
- generated report directories under `reports/`

These report directories are audit/runtime artifacts and should remain outside the core patch commit series.

### Theory baseline already completed

The following audit docs define the current understanding of the active model path:

- `docs/exdqlm_theory_source_map.md`
- `docs/exdqlm_sigma_gamma_equation_sheet.md`
- `docs/exdqlm_keep_drop_clarification.md`
- `docs/exdqlm_sigma_gamma_objective_audit.md`
- `docs/exdqlm_laplace_delta_audit.md`

These documents establish:

1. source precedence,
2. the active model contract,
3. the `keep`/`drop` distinction,
4. the active joint objective for `(sigma, gamma)`,
5. the current Laplace-Delta implementation and its gaps.

### Runtime baseline already established

Current runtime work is isolated under runtime roots and does not require tracked source edits.
The live runs are operational context only; they are not part of the patch series.

Implication:
- patching should be evaluated against controlled tests and short validation runs,
- not against ad hoc interpretation of unrelated runtime artifacts alone.

## Main findings that motivate patching

These are the findings that matter most for implementation work.

### Confirmed correct and should remain stable

1. The active `(sigma, gamma)` objective matches the canonical manuscript kernel term-by-term.
2. The active implementation uses the logistic `gamma` transform with the correct Jacobian.
3. The active `keep` vs `drop` forecast distinction is coherent with current theory and code.

These parts should be treated as **stable contracts**, not rewritten casually.

### Confirmed implementation gaps or risks

1. **Near-zero `gamma` mode search is not manuscript-aligned.**
   - The manuscript recommends split optimization over `gamma < 0` and `gamma > 0` when the mode is near zero.
   - Current code relies on clipping, damping, and fallbacks instead.

2. **Exact pure-`u` moments are not being used where available.**
   - The manuscript provides exact expressions for moments such as `E[sigma]` and `E[1/sigma]`.
   - Current code still uses generic second-order Delta approximations for those cases.

3. **Covariance semantics are unclear.**
   - `Hess.LD` is misnamed: it stores covariance, not the Hessian itself.
   - This is not a math bug, but it increases audit and maintenance risk.

4. **Fallback outputs are not clearly typed as non-Laplace fallbacks.**
   - Runtime safety fallbacks are acceptable, but they should not be indistinguishable from successful Laplace results.

5. **Ridge regularization is practical but needs explicit diagnostics and validation.**
   - Regularized covariance is not exactly the pure Laplace covariance.
   - We need to surface when that stabilization is used and how often.

6. **Namespace fragility remains in the Delta path.**
   - `numDeriv::hessian` should be explicitly qualified everywhere it is intended.

7. **A stale duplicate path still exists.**
   - The duplicate implementation in `R/environmetrics/20_model_setup.R` is no longer a safe source of truth.
   - It should be quarantined or clearly marked stale.

## Non-goals for this patch series

The following are explicitly out of scope unless a later finding forces them into scope:

1. redesigning the base exAL / exDQLM likelihood,
2. redesigning `keep` vs `drop`,
3. retuning discount factors as part of the theory patch series,
4. broad refactors outside the active sigma/gamma/Laplace path,
5. changing historical runtime artifacts in place.

## Patch objectives

The patch series should achieve all of the following.

1. bring the active implementation closer to the manuscript where the manuscript is clear,
2. preserve current behavior where the current implementation is already correct,
3. improve numerical robustness without hiding deviations from the theory,
4. make fallback states explicit and auditable,
5. keep downstream consumers working during the transition.

## Source-of-truth hierarchy during patching

No patch should be justified from an old note alone.

Source precedence for this patch series is:

1. canonical manuscript source (`main.tex`),
2. current active implementation path,
3. current audit docs listed above,
4. historical notes only if they agree with 1-3.

If an old note conflicts with both the manuscript and the current active implementation, the note is stale and should not drive behavior.

## High-level patch sequence

The patch series should be split into five implementation groups plus one final verification group.

### Group 0: pre-patch baseline lock

Purpose:
- freeze the baseline before any theory-sensitive edits.

Tasks:
1. preserve `91d690e` as the patch baseline,
2. optionally add an annotated tag before the first code patch,
3. capture a minimal baseline verification record,
4. keep generated `reports/` outside the patch commits.

Deliverables:
- annotated baseline reference if desired,
- pre-patch verification note,
- no code changes beyond documentation if needed.

### Group A: near-zero gamma optimization alignment

Purpose:
- implement the manuscript-recommended split optimization policy near `gamma = 0`.

Expected effect:
- reduce optimization ambiguity and branch instability near the nonsmooth point.

Core requirement:
- if the mode is near zero or if the combined search is ambiguous, optimize the transformed objective separately on the negative and positive `gamma` branches and select the better mode explicitly.

Likely files:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- possibly `R/disc_w/_init.R` if explicit controls are added
- possibly a new helper under `R/disc_w/`

Tests to add:
- branch-selection unit tests,
- near-zero synthetic objective tests,
- regression test confirming stable behavior away from zero.

Acceptance criteria:
- branch policy is explicit,
- selected mode is logged or recorded,
- behavior matches current results away from near-zero cases,
- targeted near-zero fixtures improve or at least become explainable.

### Group B: exact pure-u moment replacement

Purpose:
- replace generic Delta approximations with exact closed forms when the theory provides them.

Priority moments:
- `E[sigma]`
- `E[1/sigma]`
- any other pure exponential-in-`u` quantities currently passed through generic Delta unnecessarily

Likely files:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- possibly helper extraction into `R/disc_w/`

Tests to add:
- closed-form equality tests,
- comparison against current Delta approximation on known fixtures,
- numerical sanity across a range of variances.

Acceptance criteria:
- exact formulas are used where valid,
- generic Delta remains only for functions that actually require it,
- unit tests prove equivalence to closed-form expectations.

### Group C: covariance, fallback, and namespace semantics

Purpose:
- clean up semantics around the Laplace object without destabilizing the algorithm.

Required changes:
1. make covariance naming accurate,
2. make fallback objects explicitly typed as fallback/non-Laplace,
3. qualify `numDeriv::hessian` wherever intended,
4. expose whether ridge regularization was applied.

Compatibility requirement:
- preserve downstream compatibility either through a transition alias or a compatibility wrapper.

Likely files:
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- `R/disc_w/_init.R`
- any downstream consumers of the returned Laplace object

Tests to add:
- object-structure contract tests,
- fallback-flag tests,
- namespace regression tests,
- ridge diagnostics presence tests.

Acceptance criteria:
- downstream code still works,
- successful Laplace objects and fallback objects are clearly distinguishable,
- covariance semantics are no longer ambiguous.

### Group D: stale-path quarantine

Purpose:
- prevent the stale duplicate path from confusing future audits or runtime work.

Required changes:
- annotate, quarantine, or otherwise clearly separate the stale duplicate path in `R/environmetrics/20_model_setup.R`.

Important constraint:
- do not remove historical material recklessly,
- do make it impossible to mistake it for the active path.

Tests to add:
- none required at runtime if the stale path is not executed,
- but documentation and comments must be explicit.

Acceptance criteria:
- future readers can identify the active path quickly,
- stale transform logic is not presented as current truth.

### Group E: documentation and diagnostics completion

Purpose:
- make the patch series auditable after the fact.

Required outputs:
1. update theory docs when implementation semantics change,
2. add a short operator-facing note for new diagnostics/flags,
3. add a concise patch summary describing what changed and why.

Likely files:
- `docs/exdqlm_laplace_delta_audit.md`
- `docs/exdqlm_patching_strategy.md`
- possibly a new implementation note under `docs/`

Acceptance criteria:
- documentation matches the post-patch implementation,
- new runtime semantics are described in one place.

### Group F: post-patch integrated verification

Purpose:
- prove the patched implementation is both theoretically aligned and operationally sound.

Required validation layers:
1. unit tests,
2. regression tests,
3. smoke workflow tests,
4. empirical behavior checks on controlled runs.

Acceptance criteria:
- all validation layers pass or are explained with explicit disposition,
- no hidden runtime breakages remain,
- the patch series is ready for sustained use.

## Exact pre-patch verification checklist

Before the first code patch, complete the following checklist.

### V0.1 Baseline reference

- baseline commit is `91d690e`
- confirm branch matches pushed baseline
- do not mix report artifacts into the patch commits

### V0.2 Theory lock confirmation

Confirm these docs remain the patch reference set:
- `docs/exdqlm_theory_source_map.md`
- `docs/exdqlm_sigma_gamma_equation_sheet.md`
- `docs/exdqlm_keep_drop_clarification.md`
- `docs/exdqlm_sigma_gamma_objective_audit.md`
- `docs/exdqlm_laplace_delta_audit.md`

### V0.3 Baseline tests to run before patching

At minimum, rerun the tests that protect the already modified support infrastructure and active Laplace helpers.

Recommended baseline test set:
- `tests/python/test_prepare_reduced_defaultvb_temporal_bundle.py`
- `tests/testthat/test_disc_w_state_blend.R`
- `tests/testthat/test_disc_w_state_refresh_schedule.R`
- `tests/testthat/test_disc_w_warm_start_io.R`
- `tests/testthat/test_unified_gamma_sigma_state_refresh_schedule_config.R`

Add a focused pre-patch laplace/sigma-gamma test set once those tests exist.

### V0.4 Baseline numerical fixtures

Before changing the active Laplace logic, capture a small set of frozen numerical fixtures from the current implementation.

Fixtures should include:
1. a clearly negative `gamma` case,
2. a clearly positive `gamma` case,
3. a near-zero `gamma` case,
4. a ridge-regularized case if one can be generated,
5. a fallback-triggering case if one can be generated safely.

Stored fixture outputs should include at least:
- optimized transformed mode,
- `sigma_exp`,
- `gamma_exp`,
- covariance matrix,
- ridge indicator if present,
- fallback indicator if present.

Purpose:
- allow precise before/after comparison.

## Exact tests to add by patch group

### Group A tests

1. split-search chooses the better branch when synthetic surfaces are asymmetric,
2. split-search remains consistent with the unsplit path far from zero,
3. selected mode and branch are recorded,
4. near-zero cases no longer depend on accidental local optimizer behavior alone.

### Group B tests

1. exact `E[sigma]` matches `exp(mu + 0.5 * var_u)`,
2. exact `E[1/sigma]` matches `exp(-mu + 0.5 * var_u)`,
3. current generic Delta and exact formulas agree in low-variance regimes,
4. exact formulas behave better in broader-variance regimes.

### Group C tests

1. successful Laplace result object contains explicit covariance semantics,
2. fallback object contains explicit fallback flags,
3. ridge usage is surfaced in the returned object or diagnostics,
4. downstream consumers still accept the object contract.

### Group D tests

No runtime unit tests are mandatory unless the stale path is still executable.
If the stale path remains loadable, add one defensive test that the active path is the one being invoked in the supported workflow.

### Group F workflow tests

1. one tiny synthetic or short-horizon smoke run,
2. one reduced real-data smoke run with the active family,
3. one problematic quantile inspection run if needed.

These should be used to inspect:
- startup stability,
- objective guard behavior,
- fallback frequency,
- sigma/gamma traces,
- whether near-zero behavior is better behaved.

## Regression and empirical verification plan

### Numerical regression layer

For each patch group, compare against frozen baseline fixtures and classify changes as:

1. expected improvement,
2. neutral/no material change,
3. suspicious regression.

No behavior change should be treated as automatically good just because tests pass.

### Workflow regression layer

After Groups A-C are in place, compare the patched implementation to the baseline on a controlled reduced run.

Focus on:
- problematic quantiles,
- sigma spikes,
- gamma behavior near zero,
- state-norm pathologies,
- fallback and ridge frequency.

### Empirical acceptance signals

Signals in favor of the patch series:
- fewer pathological sigma explosions,
- clearer near-zero gamma behavior,
- fewer opaque fallback states,
- stable downstream objects,
- easier interpretation of diagnostics.

Signals against the patch series:
- increased fallback frequency,
- widespread divergence from stable non-near-zero fixtures,
- broken downstream consumers,
- unstable mode selection far from zero.

## Commit structure and sequencing

Recommended commit order:

1. `patch(A): split gamma mode search near zero`
2. `patch(B): use exact u-only sigma moments`
3. `patch(C): clarify covariance and fallback semantics`
4. `patch(C2): add ridge and laplace diagnostics if needed`
5. `patch(D): quarantine stale duplicate laplace path`
6. `docs: finalize post-patch theory and operator notes`

Rule:
- run the relevant tests after each commit group,
- do not stack multiple theory-sensitive changes without validation.

## Rollback strategy

Rollback must remain trivial.

### R1. Small commits

Each logical behavior change belongs in its own commit.

### R2. Baseline preservation

`91d690e` remains the revert anchor.

### R3. Revert triggers

Immediately pause or revert a patch group if:
- it breaks object contracts downstream,
- it worsens non-near-zero regression fixtures without explanation,
- it increases fallback frequency materially,
- it introduces unexplained instability in smoke workflow tests.

### R4. Artifact isolation

Do not rely on generated reports for rollback.
Rollback should be possible from git history alone.

## Documentation requirements during patching

Every patch group should leave behind:

1. updated inline comments where behavior is non-obvious,
2. updated tests proving the new semantics,
3. updated docs if operator-facing behavior changed,
4. a concise summary of why the change was needed.

At the end of the series, produce a short implementation note with:
- what changed,
- what remained unchanged,
- what is still approximate,
- what remains to be investigated.

## Execution status: 2026-05-20

The patch series described above has now been executed from the baseline
checkpoint `91d690e`.

### Baseline anchors

- baseline tag: `exdqlm-prepatch-20260520`
- baseline commit: `91d690e`

### Executed patch bundle commits

1. `f3f76f9`
   - `docs: lock exdqlm pre-patch verification plan`
2. `01a69cd`
   - `patch(A): split gamma mode search near zero`
3. `f2c8c41`
   - `patch(B): use exact u-only sigma moments`
4. `5f1ed2a`
   - `patch(C): clarify Laplace covariance semantics`
5. `d9f4b21`
   - `patch(DE): quarantine stale path and document runtime semantics`

### Verification result

The post-patch verification pass completed cleanly.

Focused and broader checks passed:

- `tests/testthat/test_disc_w_gamsig_laplace.R`
- `tests/testthat/test_disc_w_sampling_contracts.R`
- `tests/testthat/test_disc_w_state_blend.R`
- `tests/testthat/test_disc_w_state_refresh_schedule.R`
- `tests/testthat/test_disc_w_warm_start_io.R`
- `tests/testthat/test_stage_fit_preflight.R`
- `tests/testthat/test_unified_gamma_sigma_state_refresh_schedule_config.R`
- `tests/python/test_prepare_reduced_defaultvb_temporal_bundle.py`
- `tests/python/test_data_start_usgs_filter_contract.py`
- `tests/python/test_stage_fit_quantile_gamma_sigma_overrides.py`
- `tests/python/test_he2_exal_m_t1_discount_refresh_scaffold.py`

### Final state of the plan

- Group A: completed
- Group B: completed
- Group C: completed
- Group D: completed
- Group E: completed
- Group F: completed

## Final recommendation

The patch series is now in a good state for empirical comparison runs.

The next high-value step is not more theory patching.
The next high-value step is controlled empirical validation on representative
problem cases, using the new diagnostics to inspect:

1. near-zero gamma branch selection,
2. fallback frequency,
3. ridge-regularization frequency,
4. sigma spikes and tail instability,
5. downstream state-path behavior.

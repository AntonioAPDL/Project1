# exDQLM Multivariate Keep Ultimate Audit Plan

Date: 2026-05-20

## Purpose

This document is the master audit plan for the active multivariate `exdqlm keep` workflow in this
repository.

Its purpose is to give us one rigorous place to:

1. define the exact audit scope,
2. identify what has already been audited,
3. separate confirmed facts from open questions,
4. lay out the theory-to-code checks we still need,
5. define runtime stability checks and plotting requirements,
6. define the testing and promotion standards for any findings or fixes.

This plan is intentionally stricter than an ordinary debugging note. We are treating the current
behavior as potentially affected by a deep algorithmic issue, so the audit needs to be:

- theoretically grounded,
- implementation-specific,
- reproducible,
- numerically rigorous,
- and explicit about what has and has not been confirmed.

This document does **not** take old notes for granted. No statement should be treated as
"confirmed" unless it agrees with:

1. the canonical theory source, and
2. the current active implementation path.

## Execution Status

Audit execution artifacts produced from this plan:

1. source lock:
   - [exdqlm_multivar_keep_source_lock.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_source_lock.md)
2. state-space contract:
   - [exdqlm_multivar_keep_state_contract_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_state_contract_audit.md)
   - [exdqlm_multivar_keep_dimension_contract.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_dimension_contract.csv)
   - [exdqlm_multivar_keep_symbol_map.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_symbol_map.csv)
3. ensemble/Wishart contract:
   - [exdqlm_multivar_keep_wishart_ensemble_contract_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_wishart_ensemble_contract_audit.md)
4. latent and pseudo-data tests/helpers:
   - [11_latent_pseudodata_audit_helpers.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/11_latent_pseudodata_audit_helpers.R)
   - [test_exdqlm_multivar_keep_latent_pseudodata_audit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R)
5. latent audit:
   - [exdqlm_multivar_keep_latent_st_ut_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_latent_st_ut_audit.md)
6. pseudo-data/Kalman audit:
   - [exdqlm_multivar_keep_pseudodata_kalman_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_pseudodata_kalman_audit.md)
   - [run_exdqlm_keep_kalman_fixture.R](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/audits/run_exdqlm_keep_kalman_fixture.R)
7. runtime audit:
   - [exdqlm_multivar_keep_runtime_stability_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_runtime_stability_audit.md)
   - [exdqlm_keep_runtime_stability_audit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/audits/exdqlm_keep_runtime_stability_audit.R)
8. final findings:
   - [exdqlm_multivar_keep_final_findings.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_final_findings.md)
   - [exdqlm_multivar_keep_final_mismatch_matrix.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_final_mismatch_matrix.csv)
9. repair and transform-regression plan:
   - [exdqlm_multivar_keep_repair_and_transform_regression_plan.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_repair_and_transform_regression_plan.md)

One production-code defect was found and fixed locally during execution: forecast-member `update_uts`
now indexes forecast columns with `TT_sub` instead of bare `T` in
[DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r).
Existing saved runtime evidence remains pre-fix evidence.

## Why this audit is needed

Current live runs are showing behavior that is too severe to dismiss as ordinary under-convergence.
Across multiple campaigns we have seen combinations of:

- catastrophic or nonsensical ELBO values,
- exploding `sigma` values,
- saturated or unstable `gamma` behavior,
- large and asymmetric `state_norm_sq / TT`,
- bad median/tail lanes under otherwise similar settings,
- and trend/state trajectories that look implausible across quantiles.

We have already removed several implementation failures in the Laplace/Delta path. That work was
necessary, but it has not fully explained the remaining numerical pathologies.

So at this point the most responsible interpretation is:

1. the problem may involve the `sigma/gamma` approximation,
2. the problem may involve the `s_t` / `u_t` latent updates,
3. the problem may involve the state-space / Kalman filtering and smoothing layer,
4. or the problem may come from interaction across those layers.

This audit is designed to isolate those possibilities rather than guess.

## Audit rule

For this audit, a statement is only treated as confirmed if it satisfies both:

1. it appears in a primary theory source or the current implementation source, and
2. it is consistent with the current active implementation path.

If a historical note conflicts with either the canonical theory or the current implementation, it
is treated as stale until reconciled.

## In-scope model

The model in scope is the active multivariate exAL / exDQLM `keep` workflow using the DISC
Wishart/ensemble path.

Primary implementation anchor:
- [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r)

Active workflow map:
- [DISC_W_WORKFLOW.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/DISC_W_WORKFLOW.md)

Key structural implementation anchors:
- exAL coefficient/support helpers:
  - [02_helpers_core.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R)
- forecast `keep` / `drop` state construction:
  - [20_model_setup.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R)
- Wishart/ensemble contract:
  - [06_ensemble_spec.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/06_ensemble_spec.R)
  - [04_ensemble_bookkeeping.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/04_ensemble_bookkeeping.R)
- Laplace/covariance helpers:
  - [10_gamsig_laplace.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/10_gamsig_laplace.R)
- save-state surface:
  - [05_save_state.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/05_save_state.R)

## Explicit out-of-scope items

Unless new evidence forces expansion, the following are out of scope for this audit:

1. univariate exDQLM implementation,
2. NDLM production behavior as a direct target,
3. broad workflow orchestration issues unrelated to the active model math,
4. discount-factor tuning as the primary explanation,
5. post-stage forecast reporting bugs unless they contaminate fit-stage diagnostics.

NDLM audits may still be used as methodological references, but not as direct proof for this
workflow.

## What has already been audited

### A. Strong prior theory/code work already completed

These documents are strong inputs and should be reused rather than duplicated.

1. source hierarchy and active theory anchors:
   - [exdqlm_theory_source_map.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_theory_source_map.md)
2. equation sheet for the active exDQLM path:
   - [exdqlm_sigma_gamma_equation_sheet.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_sigma_gamma_equation_sheet.md)
3. `keep` vs `drop` clarification:
   - [exdqlm_keep_drop_clarification.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_keep_drop_clarification.md)
4. joint `sigma/gamma` objective audit:
   - [exdqlm_sigma_gamma_objective_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_sigma_gamma_objective_audit.md)
5. Laplace/Delta audit:
   - [exdqlm_laplace_delta_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_laplace_delta_audit.md)
6. recent repair cycle for covariance/fallback hardening:
   - [exdqlm_parallelpatch_repair.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_parallelpatch_repair.md)

### B. Strong symptom-level audits already completed

1. reduced-spec trend identifiability audit:
   - [README.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_reducedspec_trend_identifiability_audit_20260519/README.md)
2. retained `exps` / component reviews:
   - [warmstart PNG bundle](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_retained_exps_components_review_20221225_iter1000_reducedspec_h1_ppt_warmstart_pngonly_20260520)
   - [schedhold10 PNG bundle](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_retained_exps_components_review_20221225_iter1000_reducedspec_h1_ppt_schedhold10_pngonly_20260520)

### C. Useful adjacent reference audits

These are not direct proof for the exDQLM keep workflow, but they are useful references for audit
style and rigor.

1. NDLM Wishart prior audit:
   - [wishart_prior_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/wishart_prior_audit.md)
2. NDLM covariance dynamics audit:
   - [ndlm_covariance_dynamics_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_covariance_dynamics_audit.md)
3. NDLM multivariate contract audit:
   - [ndlm_multivar_contract_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_multivar_contract_audit.md)

### D. Additional implementation and contract references

These are not primary theory documents, but they materially strengthen the audit wiring and should
be treated as first-line implementation references.

1. static used-code inventory for the original Wishart runner:
   - [audit_used_code.md](/data/muscat_data/jaguir26/project1_ucsc_phd/audit_used_code.md)
2. Wishart workflow optimization/refactor inventory and baseline reproducibility notes:
   - [OPTIMIZATION_TRACKER.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/OPTIMIZATION_TRACKER.md)
3. historical multivariate keep contract freeze / golden workflow context:
   - [HE2_EXDQLM_MULTIVAR_KEEP_GOLDEN_CONTRACT_20260512.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/HE2_EXDQLM_MULTIVAR_KEEP_GOLDEN_CONTRACT_20260512.md)
4. family-level unified contract references:
   - [UNIFIED_FAMILY_CONTRACTS_v1.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/contracts/UNIFIED_FAMILY_CONTRACTS_v1.md)
   - [FAMILY_POST_OBJECT_CONTRACT_MAP_v1.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/contracts/FAMILY_POST_OBJECT_CONTRACT_MAP_v1.md)
5. compiled Kalman contract reference from the broader audit history:
   - [shared_kalman_contract.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/docs/kalman_cpp_audit/20260221T003811Z/shared_kalman_contract.md)
6. historical tracker context for transfer/keep work:
   - [TRACKER_multivar_keep_drop_post_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/TRACKER_multivar_keep_drop_post_audit.md)
   - [TRACKER_transfer_forecast_modelC.md](/data/muscat_data/jaguir26/project1_ucsc_phd/TRACKER_transfer_forecast_modelC.md)

These references are important because they give us:
- the static used-code map for the original DISC runner,
- the reproducibility baseline for the Wishart workflow,
- the strongest existing contract documentation around family outputs and runtime expectations,
- and prior Kalman-contract audit structure we can reuse instead of inventing a new style.

## What is still missing

We do **not** yet have one authoritative audit that jointly confirms all of the following for the
multivariate `keep` workflow:

1. the full state-space equations actually used in the live code path,
2. the Wishart/ensemble contract and its dimensions,
3. the exact `s_t` conditional and implementation,
4. the exact `u_t` conditional/moment formulas and implementation,
5. the construction of `FFF`, `QQQ`, `FFF_forecast`, and `QQQ_forecast`,
6. the compiled Kalman/RTS state-update congruence for this workflow,
7. the numerical stability of those objects over real runs,
8. the correspondence between those internal quantities and the pathological plots we are seeing.

That missing joined-up audit is the target of this plan.

## Main hypotheses to test

This audit should explicitly test the following competing explanations.

### H1. The `sigma/gamma` update block is still the primary instability source
Expected signature:
- `sigma` or `gamma` becomes pathological before state norms drift badly,
- bad `FFF/QQQ` construction follows from bad latent expectations,
- state-space instability is downstream rather than primary.

### H2. The `s_t` / `u_t` updates are the hidden instability source
Expected signature:
- `E[s_t]`, `E[s_t^2]`, `E[u_t]`, `E[1/u_t]`, or `E[log u_t]` become implausible first,
- this corrupts pseudo-data and then destabilizes the state update.

### H3. The Kalman/state-space layer is the primary instability source
Expected signature:
- pseudo-data remains plausible,
- but the filtered/smoothed state path, covariance recursion, or forecast-state assembly drifts or
  fails anyway.

### H4. Trend identifiability + persistence is the dominant driver
Expected signature:
- state-space algebra is internally correct,
- but trend/transfer/discrepancy decomposition is not sufficiently identified under the current
  persistence structure,
- especially in median/tail lanes.

### H5. The failure is interactional, not isolated
Expected signature:
- no single block is obviously wrong in isolation,
- but the combined updates create a numerically unstable loop.

## Canonical theory sources for this audit

Primary manuscript source:
- [/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex)
- [/data/muscat_data/jaguir26/exDQLM---Ensemble/main.pdf](/data/muscat_data/jaguir26/exDQLM---Ensemble/main.pdf)

Project-local manuscript mirror:
- [article.txt](/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt)

Important theory anchors already identified:
- Model A: observation + transfer
- Model B: retrospective discrepancy
- Model C-T: forecast keep variant
- `v_t` and `s_t` conditionals
- VB pseudo-data
- Laplace-Delta `(sigma, gamma)` block

See:
- [exdqlm_theory_source_map.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_theory_source_map.md)
- [exdqlm_sigma_gamma_equation_sheet.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_sigma_gamma_equation_sheet.md)

## Recommended read / execution order

To keep the audit rigorous and avoid circular reasoning, the preferred order is:

1. **Source and contract spine**
   - `docs/exdqlm_theory_source_map.md`
   - `docs/exdqlm_sigma_gamma_equation_sheet.md`
   - `docs/exdqlm_keep_drop_clarification.md`
   - `audit_used_code.md`
   - `repro/OPTIMIZATION_TRACKER.md`

2. **Existing implementation-sensitive audits**
   - `docs/exdqlm_sigma_gamma_objective_audit.md`
   - `docs/exdqlm_laplace_delta_audit.md`
   - `docs/exdqlm_parallelpatch_repair.md`

3. **Symptom and runtime evidence**
   - reduced trend/state audit bundle
   - retained component/trace review bundles
   - current live run diagnostics and targeted-lane reproductions

4. **New state / latent / pseudo-data audit work**
   - state-space contract
   - `s_t` and `u_t` derivations
   - `FFF/QQQ` construction
   - Kalman congruence
   - runtime stability evidence

This read order is intentional: it moves from fixed contract -> active code -> known repaired defects ->
symptoms -> new theory/code/runtime audit.

## Audit artifact map

The final audit should maintain a clean separation between tracked reasoning docs and untracked runtime
evidence.

### Tracked docs in `docs/`
- source maps
- theory equation sheets
- state/latent/pseudo-data/Kalman audit writeups
- final findings summary

### Untracked evidence in `reports/`
- targeted lane bundles
- runtime trace plots
- pseudo-data range summaries
- covariance / PSD diagnostics
- run-specific CSV manifests

### Reproducibility anchors in `repro/`
- baseline workflow trackers
- contract freezes
- broader theory-to-code precedents
- Kalman contract reference material

This separation is required so we can keep the audit reproducible without turning large runtime bundles
into tracked git history.

## Audit workstreams

The audit should be executed in the following workstreams.

### Workstream 1: source lock and scope freeze

Goal:
- freeze the exact theory and code sources to be audited.

Tasks:
1. confirm source precedence,
2. identify the exact active implementation path,
3. mark stale or duplicate sources as non-authoritative,
4. define which runtime families and quantiles are in scope.

Deliverable:
- source-lock appendix inside the final audit.

Success condition:
- every later conclusion can be tied back to a frozen source set.

### Workstream 2: full multivariate `keep` state-space contract

Goal:
- derive from scratch the active state-space contract for the multivariate `keep` workflow.

Must include:
1. historical observation equations,
2. retrospective discrepancy equations,
3. forecast `keep` observation equations,
4. full stacked state definitions,
5. transfer-retained block structure,
6. measurement-loadings used historically and in forecast,
7. block dimensions by source/lead.

Code anchors to check directly:
- [20_model_setup.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R)
- [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r)

Deliverable:
- an explicit equation section with a dimension table.

Success condition:
- no ambiguity remains about the exact state and measurement objects used by the live path.

### Workstream 3: Wishart/ensemble contract audit

Goal:
- confirm the in-memory ensemble contract and all covariance-shape assumptions that feed the state
  update.

Tasks:
1. audit ensemble construction and ordering,
2. audit dimensions and axis conventions,
3. audit forecast-member bookkeeping,
4. audit the contract between the R layer and compiled Kalman layer,
5. confirm that historical and forecast covariance blocks are assembled consistently.

Primary references:
- [DISC_W_WORKFLOW.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/DISC_W_WORKFLOW.md)
- [06_ensemble_spec.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/06_ensemble_spec.R)
- [04_ensemble_bookkeeping.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/04_ensemble_bookkeeping.R)

Deliverable:
- contract table with exact object shapes and semantic meaning.

Success condition:
- every object entering the Kalman core has a confirmed dimension and interpretation.

### Workstream 4: `s_t` audit

Goal:
- re-derive and verify the truncated-normal latent update from scratch.

Tasks:
1. extract the theoretical conditional of `s_t`,
2. derive the implemented `sts.mu` and `sts.sig2`,
3. confirm positivity and truncation semantics,
4. verify all moments used downstream,
5. confirm forecast-member update path matches historical path up to intended indexing changes.

Code anchors:
- historical update:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1795](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1795)
- historical loop:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3901](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3901)
- forecast loop:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4661](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4661)

Deliverable:
- `s_t` theory-to-code derivation table.

Success condition:
- `sts.mu`, `sts.sig2`, `E[s_t]`, `E[s_t^2]`, and entropy are all accounted for from first principles.

### Workstream 5: `u_t` audit

Goal:
- re-derive and verify the latent `u_t` / `v_t` update from scratch.

Tasks:
1. extract the theoretical conditional,
2. derive the implemented `lambda`, `psi`, and `chi` quantities,
3. verify the GIG moment formulas actually used,
4. verify all moments consumed downstream:
   - `E[u_t]`
   - `E[1/u_t]`
   - `E[log u_t]`
5. confirm consistency between fit-stage updates and sampling-stage use.

Code anchors:
- historical update:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1833](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1833)
- historical loop:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3911](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3911)
- forecast loop:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4689](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4689)

Deliverable:
- `u_t` theory-to-code derivation table.

Success condition:
- the conditional family, parameterization, moments, and entropy are all verified against the active code.

### Workstream 6: pseudo-data construction audit (`FFF`, `QQQ`)

Goal:
- verify the exact algebra and stability of the pseudo-observation terms that drive the Gaussian
  state update.

Tasks:
1. derive `FFF` from the theory,
2. derive `QQQ` from the theory,
3. audit historical construction,
4. audit forecast construction,
5. verify dimensions, positivity, finiteness, and expected magnitudes.

Critical code anchors:
- seed construction:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3344](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3344)
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3345](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3345)
- live construction:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3539](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3539)
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3540](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3540)
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3555](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3555)
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3558](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3558)

Deliverable:
- theory-to-code map for `FFF` / `QQQ` plus a runtime health checklist.

Success condition:
- we can explain how bad `s_t/u_t/sigma/gamma` values would propagate into the Gaussian layer.

### Workstream 7: Kalman / smoother congruence audit

Goal:
- verify that the state update path itself is coherent and not introducing hidden numerical defects.

Tasks:
1. identify the exact compiled entry point used by the workflow,
2. verify the R-to-C++ contract,
3. construct small deterministic fixtures,
4. compare against a reference implementation when feasible,
5. check PSD/symmetry/finite behavior of state covariance objects,
6. verify that smoothed state reconstruction and fitted moments are internally coherent.

Anchors:
- compiled source load:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:47](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:47)
- compiled update call:
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3670](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3670)
- workflow map:
  - [DISC_W_WORKFLOW.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/DISC_W_WORKFLOW.md)

Deliverable:
- Kalman congruence section with fixture-based evidence.

Success condition:
- either the state-update path is cleared, or we isolate a reproducible mismatch.

### Workstream 8: runtime stability and plotting audit

Goal:
- examine dynamic behavior directly rather than only trusting formulas.

Required plotting set:
1. `E[s_t]` traces by quantile and source,
2. `E[s_t^2]` traces by quantile and source,
3. `E[u_t]` traces by quantile and source,
4. `E[1/u_t]` traces by quantile and source,
5. `E[log u_t]` traces by quantile and source,
6. `FFF` range summaries over time,
7. `QQQ` range summaries over time,
8. state norm traces,
9. selected state-coordinate traces,
10. trend / transfer / discrepancy decompositions where useful.

Required diagnostic checks:
1. finiteness checks,
2. positivity/domain checks,
3. quantile-lane comparison,
4. first-iteration, mid-run, and late-run comparisons,
5. comparison of healthy vs pathological lanes.

Success condition:
- we can visually identify whether the instability appears first in latent updates, pseudo-data, or states.

### Workstream 9: targeted quantile-lane reproductions

Goal:
- isolate problematic behavior in a small, controllable setting.

Recommended lane set:
1. one stable control lane,
2. `q35`,
3. `q50`,
4. `q95`,
5. optionally `q05` if tail asymmetry remains suspicious.

For each targeted lane, collect:
- full fit logs,
- latent summaries,
- state summaries,
- pseudo-data summaries,
- any fallback / guard events,
- compact diagnostic plots.

Success condition:
- we can reproduce the instability without needing a full seven-lane production campaign.

### Workstream 10: final mismatch matrix

Goal:
- produce a final theory/code/runtime verdict table.

Required columns:
- component,
- theory expression,
- implementation path,
- runtime evidence,
- status (`confirmed`, `questionable`, `failed`, `inconclusive`),
- fix priority,
- notes.

Success condition:
- we leave the audit with a clear prioritized fix list, not just observations.

## Testing and validation requirements

This audit must include both static derivation checks and executable checks.

### Static derivation checks

Required:
1. every major formula written from scratch,
2. every implementation expression mapped to its theory analogue,
3. explicit notation table where symbols differ across manuscript and code,
4. dimension table for all major stacked state objects.

### Unit tests to add or extend

Candidates:
1. `s_t` parameter/moment consistency tests,
2. `u_t` parameter/moment consistency tests,
3. `FFF/QQQ` algebra consistency tests,
4. pseudo-data positivity/domain tests,
5. small deterministic Kalman congruence tests,
6. fixture-based checks for state covariance symmetry / PSD.

### Runtime smoke checks

Required:
1. one-quantile reproductions for suspect lanes,
2. stable-control lane run,
3. log-based checks for non-finite values,
4. state/path plotting checks,
5. explicit health criteria for passing or failing a lane.

### Empirical acceptance criteria

A component should only be considered cleared if:
1. theory and code agree,
2. tests pass,
3. runtime behavior is numerically sane on targeted reproductions,
4. and no new pathology is introduced in control lanes.

## Documentation requirements

This audit should be documented in a way that future debugging does not need to repeat the same
search from scratch.

Required outputs:
1. one master audit document,
2. supporting derivation appendices,
3. supporting tables/CSVs where useful,
4. runtime plot bundles,
5. a final findings summary,
6. a final recommended action list.

Documentation standards:
- every statement sourced,
- every figure labeled with run/root/window,
- every codepath anchored to a file reference,
- every historical note clearly marked as historical,
- no silent reliance on stale derivations.

## Deliverable structure

Recommended tracked docs under `docs/`:
1. `docs/exdqlm_multivar_keep_ultimate_audit_plan.md` (this file)
2. `docs/exdqlm_multivar_keep_state_contract_audit.md`
3. `docs/exdqlm_multivar_keep_latent_st_ut_audit.md`
4. `docs/exdqlm_multivar_keep_pseudodata_kalman_audit.md`
5. `docs/exdqlm_multivar_keep_runtime_stability_audit.md`
6. `docs/exdqlm_multivar_keep_final_findings.md`

Recommended untracked runtime/report outputs under `reports/`:
1. targeted lane audit bundles,
2. latent/state trace bundles,
3. pseudo-data trace bundles,
4. fixture validation outputs,
5. final runtime evidence manifest.

## Decision gate after the audit

At the end of the audit, we should be able to make one of the following decisions cleanly.

### Decision A: the state-space path is basically correct
Implication:
- prioritize further work on latent updates or identifiability.

### Decision B: the latent `s_t/u_t` block is incorrect or unstable
Implication:
- prioritize theory-to-code fixes there before more production launches.

### Decision C: the Kalman/state path is incorrect or numerically unstable
Implication:
- pause further production relaunches until fixed and revalidated.

### Decision D: the algebra is correct but the model is poorly identified under current persistence
Implication:
- move toward targeted model-design or discount-structure revision rather than purely implementation fixes.

### Decision E: multiple interacting defects remain
Implication:
- prioritize fixes by reproducibility and local isolation, not by speculation.

## Current recommendation

The highest-value next audit pass is:

1. full state-space contract extraction,
2. `s_t` / `u_t` derivation and implementation audit,
3. pseudo-data (`FFF/QQQ`) audit,
4. targeted quantile-lane runtime stability study,
5. then Kalman congruence checks if the earlier layers do not already isolate the failure.

This is the most likely path to catching something genuinely new.

## Relationship to patching work

The completed Laplace/Delta patch work remains important and should not be discarded.
However, the remaining numerical pathologies suggest that a broader model-side audit is now
necessary.

Relevant prior patch/audit materials:
- [exdqlm_patching_strategy.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_patching_strategy.md)
- [exdqlm_patch_series_summary.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_patch_series_summary.md)
- [exdqlm_parallelpatch_repair.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_parallelpatch_repair.md)

The role of this new audit is different:
- patching established and hardened one important subsystem,
- this audit tests whether the deeper problem is elsewhere.

## Reproducibility note

This document is planning and audit scaffolding only.

It does not modify:
- the current live runs,
- runtime roots,
- or generated report artifacts.

Generated runtime outputs should continue to live under `reports/` and remain outside the core git
patch series unless we explicitly decide to promote a summarized artifact.

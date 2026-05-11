# HE2 exAL Median Stabilization Tracker (2026-05-10)

## Scope
Canonical failing case:
- cutoff: `2021-01-23`
- family: `exdqlm_multivar_keep`
- quantile: `q = 0.50`
- base row: `multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_multivar_keep`

## Goal
Stabilize the median `update_gamma_sigma()` path with a model-side fix that is:
- reproducible
- documented
- testable
- safe to promote into the production relaunch workflow

## Stages
1. Freeze failing reference case
- Status: complete
- Evidence: `repro/run/HE2_EXAL_MEDIAN_WARMUP_PROBES_20260510.md`

2. Standalone probe harness
- Status: complete
- Evidence: `scripts/run_exdqlm_median_warmup_probes.py`

3. Warmup-only probe campaign
- Status: complete
- Result: no healthy winner from warmup-only tuning

4. Model-side stabilization patch v1
- Status: complete
- Changes:
  - bounded transformed optimization
  - regularized Hessian-to-covariance construction
  - conservative median sigma-only fallback on guarded failure
- Result:
  - removed the old immediate `non-finite dq_transf` / Hessian crash at the first live median update
  - did **not** produce a healthy median fit; state norm still exploded by `iter=7`

5. Model-side stabilization patch v2
- Status: complete
- Changes:
  - median-only step damping added to the accepted gamma/sigma update
  - damping moved to exact gamma/log-sigma caps rather than theta-space scaling
- Result:
  - median path now advances further without the earlier immediate crash
  - default damping (`gamma=0.25`, `log sigma=0.5`) survives through `iter=8`
  - state norm still exceeds the screening threshold, so there is still no healthy winner yet

6. Median step-cap screen
- Status: in progress
- Config: `config/median_model_stabilization_step_caps_exdqlm_multivar_keep_20210123_q50_20260510.yaml`
- Artifact root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_median_step_caps_probes_20260510`
- Early findings:
  - `gamma=0.15`, `log sigma=0.35` is materially better than the wider default cap
  - it still becomes unstable by `iter=8`
  - tighter-cap variants are being screened to see whether a healthy winner exists

7. Median state-growth guard
- Status: in progress
- Changes:
  - median-only rollback guard after the accepted gamma/sigma update
  - rejects a candidate if `state_norm_sq` exceeds an absolute cap or grows too fast relative to the previous iteration
  - restores the previous latent state, gamma/sigma state, and covariance state, then refreezes
- Current state-guard policy:
  - `median_state_norm_max_ratio = 25`
  - `median_state_norm_abs_cap = 1e8`
  - `median_state_guard_refreeze_iters = 10`
- Next check:
  - rerun the step-cap screen with this guard enabled and see whether any capped policy becomes genuinely healthy

8. Clean state-guard rerun
- Status: running
- Config:
  - `config/median_model_stabilization_step_caps_state_guard_exdqlm_multivar_keep_20210123_q50_20260510b.yaml`
- Artifact root:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_median_step_caps_state_guard_probes_20260510b`
- Verified:
  - the generated config carries the median state-guard block
  - the live fit log now prints the expanded `[gamsig_policy]` line with:
    - `median_state_guard=true`
    - `median_state_norm_max_ratio=25`
    - `median_state_norm_abs_cap=1e+08`
    - `median_state_guard_refreeze_iters=10`
- Purpose:
  - confirm the runtime is executing the patched model-side stabilization path on a clean artifact root, not recycling stale probe evidence

## Acceptance criteria
A candidate is only promotable if it satisfies all of these in screening mode:
- zero `non-finite dq_transf` guard failures
- zero `non-invertible Hessian` failures
- finite `conv_check`
- at least `8` real gamma/sigma updates
- no pathological `sigma_exp` explosion
- no pathological `state_norm_sq` explosion

## Current conclusion
The median issue is no longer a workflow/launcher problem.
It is a narrow model-side numerical stabilization problem, and we now have:
- reproducible failing case
- reproducible standalone probe harness
- documented model-side stabilization surface
- evidence that bounded optimization and exact median step damping improve behavior

The remaining task is to finish the step-cap screen and pick the first genuinely healthy median policy before promoting it to the production relaunch workflow.

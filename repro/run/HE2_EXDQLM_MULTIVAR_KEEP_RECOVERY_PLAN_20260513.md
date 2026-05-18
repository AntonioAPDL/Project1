# HE2 exdqlm_multivar_keep Recovery Plan

Date: 2026-05-13

## Goal

Finish the real all-cutoff `exdqlm_multivar_keep` rollout on the validated `log1p` contract, handle the live `20211221 q50` / `20221225 q65` incident cleanly, and resume only the remaining cutoffs without risking model inputs or already-completed rows.

## Current Facts

As of `2026-05-13T07:32:54Z`:

- completed cutoffs:
  - `20210123`: passed through `report`
  - `20211112`: passed through `report`
  - `20220511`: passed through `report`
- active cutoff:
  - `20211221`: still in `fit`
- remaining cutoff:
  - `20221225`: not started

The real rollout root is:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_20260512`

The active controller is:

- `python3 scripts/run_multimodel_v8_queue.py ... --ordinary-max-concurrent 2 ... --heavy-cutoff-max-concurrent 1`

The `log1p` validator already passed:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_log1p_20260512/prelaunch_validation_summary.json`

## Incident Read

The only incomplete submodel is:

- `20211221`, `q50`

Important evidence:

- `q50` fit log reached:
  - `VB converged: 100 iterations, 1944.922 seconds`
  - `Sampling Started`
- `q50` has not yet written:
  - `DISC_variables_50_exAL_synth_DISC.RData`
  - `multivar_forecast_health.txt`
- the worker is still live and CPU-active:
  - PID `324531`
  - state `R`
  - CPU about `99.2%`
- bounded liveness sample from `2026-05-13T07:32:49Z` to `2026-05-13T07:32:54Z`:
  - state stayed `R`
  - CPU stayed `99.2%`
  - `wchar` and `write_bytes` stayed flat during that 5-second window

Current interpretation:

- both affected quantiles are beyond the normal same-family sampling window
- both affected quantiles are stuck after `Sampling Started`
- both generated configs still carry `run.seed: 777`
- an unchanged rerun risks replaying the same pathological sampling path

Current posture:

- do **not** rerun the full campaign
- do **not** rerun the remaining cutoffs unchanged
- do a **seed-scoped recovery rerun** for the remaining cutoffs only

## Disk-Space Verdict

Disk space is not the issue.

Evidence:

- `/data` free space is about `496G`
- the active `20211221` row footprint is about `46G`
- queue launch thresholds are:
  - `pause_free_gb=25`
  - `launch_free_gb=35`
  - `heavy_free_gb=35`

So the current run has substantial headroom, and the active incident is not consistent with a storage exhaustion failure.

## Queue Behavior Verdict

`20221225` has not launched because of the current heavy-lane policy, not because the controller is broken.

The queue currently enforces:

- `ordinary_max_concurrent=2`
- `heavy_cutoff_max_concurrent=1`
- `heavy_cutoff_blocks_ordinary=true`

Under that policy, `20221225` waits until no ordinary cutoff is active. Since `20211221` is still active, the current one-row state is expected.

## Recovery Strategy

### Phase 1: Confirm the quiet-sampling diagnosis before intervention

Do not interrupt `20211221` yet.

Instead, observe `20211221 q50` in bounded windows and use a stricter definition of stall:

- observe every `10` minutes
- keep a short incident table with:
  - UTC timestamp
  - PID
  - process state
  - CPU%
  - `fit.log` mtime
  - `wchar`
  - `write_bytes`
  - presence of `DISC_variables_50_exAL_synth_DISC.RData`
  - presence of `multivar_forecast_health.txt`

Treat the run as still alive if any of the following remain true:

- process state is `R` or `S`
- CPU stays materially above idle, for example `>20%`
- any output artifact appears
- log grows
- stage status changes

Declare a real stall only if all of the following hold across at least `3` consecutive checks spanning at least `30` minutes:

- CPU stays effectively idle, for example `<5%`
- `fit.log` mtime does not change
- `wchar` and `write_bytes` do not change
- no output artifact appears
- row stage remains `fit/pending`

Recommended command:

```bash
python3 scripts/audit_he2_bayesian_publication_relaunch_liveness.py \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_20260512 \
  --run-id multimodel_20211221_v8_he2pubgdpc1r1_exdqlm_multivar_keep \
  --quantile 50 \
  --sample-seconds 5
```

### Phase 2: If the row clears naturally before intervention, do not touch it

If `20211221` reaches `post` and then `report`:

- let the cleanup hook prune the heavy fit `.RData`
- confirm `rdata_present=false` across its quantiles after `post`
- let the controller auto-launch `20221225`
- do not change queue policy mid-campaign

This is the preferred path because it preserves the cleanest audit trail.

### Phase 3: If `20211221 q50` / `20221225 q65` remain in quiet sampling, recover only the remaining cutoffs

If the bounded liveness gate confirms a real stall, do **not** use a global campaign reset.

That would archive and reset already-successful cutoffs unnecessarily.

Instead:

1. freeze evidence for the incident:
   - `matrix_status.csv`
   - `queue.log`
   - `run_manifest.yaml`
   - row run log
   - `q50` fit log
   - completed quantile health files for `20211221`
   - current row directory size and disk-free snapshot
2. stop the controller cleanly
3. archive and reset only:
   - `20211221`
   - `20221225`
4. relaunch only the remaining cutoffs:
   - `20211221`
   - `20221225`
5. change only the per-cutoff `run.seed` values before relaunch

## Recovery Contract

The scientifically conservative recovery path is:

- preserve the validated `log1p` contract
- preserve the tuned quantile override map already used in the successful family rollout
- preserve completed cutoffs `20210123`, `20211112`, and `20220511`
- rerun only `20211221` and `20221225`
- change only the per-cutoff `run.seed`

Recommended recovery seeds:

- `20211221`: `20211221`
- `20221225`: `20221225`

Why this is the cleanest change:

- it avoids replaying the exact same RNG path anchored at `777`
- it does not change discounts, epsilon, transform policy, or sample count
- it is reproducible and easy to audit in generated configs and reports

The dedicated recovery batch file is:

- `config/he2_relaunch_batches/exdqlm_multivar_keep_remaining_cutoffs_seed_recovery_20260513.yaml`

The focused diagnostic batch file is:

- `config/he2_relaunch_batches/exdqlm_multivar_keep_problem_quantiles_diagnostic_20260513.yaml`

The paired phase-2 control batch file is:

- `config/he2_relaunch_batches/exdqlm_multivar_keep_phase2_controls_diagnostic_20260514.yaml`

This diagnostic lane is intentionally narrower than the production recovery rerun:

- `20211221` is reduced to `q50` only
- `20221225` is reduced to `q65` only
- `fit.exdqlm_multivar.legacy.n_samp` is reduced to `128`
- sampling heartbeats, phase markers, and wall-time guard are enabled
- `20211221 q50` enables a terminal fail-fast guard that trips only when the median state guard fires on the terminal VB endpoint and the row remains frozen into sampling

Use this lane to isolate the sampling block before another full relaunch.

If the focused lane reproduces the same silent post-`Sampling Started` region, escalate to the paired phase-2 control lane before changing priors or discounts:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_phase2_controls_diagnostic_20260514.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_phase2_controls_diagnostic_20260514.yaml \
  --profile disk_guarded_dual_recovery \
  --skip-validate
```

What this phase-2 lane adds:

- `20211221`: problem `q50` plus healthy sibling `q65`
- `20221225`: problem `q65` plus healthy sibling `q80`
- `fit_parallel_workers=2` and `mc_cores=2` so each paired row runs concurrently
- `fit.exdqlm_multivar.legacy.n_samp=8`
- dedicated `sampling_diagnostics.log` files under each quantile log directory
- stricter pre-sampling gamma/sigma validity stop before the pathological q50 terminal handoff

## Required Tooling Hardening Before a Forced Rerun

Before forcing a rerun, add or confirm two small operational improvements:

### 1. Selective cutoff reset

Extend the reset path so we can archive and reset selected cutoffs only, instead of the full campaign.

Recommended interface:

```bash
python3 scripts/reset_he2_bayesian_publication_relaunch_state.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --cutoffs 20211221 20221225 \
  --reset-tag 20260513_q50_recovery
```

Behavior:

- archive only the targeted run roots and matching run logs
- preserve completed cutoffs `20210123`, `20211112`, and `20220511`
- rebuild `matrix_status.csv` so only the selected cutoffs return to `not_started`
- preserve a `reset_summary.json` and `RESET_SUMMARY.md`

### 2. Liveness auditor

Add a small recovery-facing auditor that reports whether a row is:

- active
- quiet but healthy
- likely stalled

Inputs:

- run manifest
- process table
- log mtime
- `/proc/<pid>/io`

This can stay as a standalone audit tool first; it does not need to be embedded into the queue controller immediately.

### 3. Focused diagnostic lane

Run the problem quantiles in isolation before another full rerun:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_problem_quantiles_diagnostic_20260513.yaml \
  --profile disk_guarded_dual_recovery \
  --skip-validate
```

Expected diagnostic behavior:

- `20211221 q50` either exits sampling quickly or fails explicitly with a terminal median-guard message
- `20221225 q65` emits phase markers / heartbeats that identify whether the hang is in latent sampling, retrospective synth, forecast synth, or the final `mvrnorm` sweep

## Rerun Procedure If Recovery Is Needed

If the remaining rows are still trapped in quiet sampling:

1. archive incident evidence
2. stop the current controller
3. stop the two active row trees
4. selectively reset `20211221` and `20221225`
5. rebuild selected configs from the same validated template using the seed-recovery batch file
6. relaunch only the remaining cutoffs under the recovery profile

Recommended commands:

```bash
python3 scripts/reset_he2_bayesian_publication_relaunch_state.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --cutoffs 20211221 20221225 \
  --reset-tag 20260513_seed_recovery_r01

python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_remaining_cutoffs_seed_recovery_20260513.yaml \
  --profile disk_guarded_dual_recovery \
  --skip-validate
```

Expected post-rebuild checks:

- `20211221` generated config contains `run.seed: 20211221`
- `20221225` generated config contains `run.seed: 20221225`
- both rows still show `log1p_cms` for fit/post internal scales
- queue launches both remaining cutoffs jointly

Recommended relaunch command:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --profile disk_guarded_dual_recovery \
  --skip-validate
```

Why this command is the preferred recovery restart:

- it preserves the full 5-cutoff campaign matrix
- completed cutoffs are rediscovered as `pass` from their existing manifests
- only the reset cutoffs relaunch
- `disk_guarded_dual_recovery` lets `20211221` and `20221225` run together

Why `--skip-validate` is acceptable in the recovery case:

- the `log1p` validator already passed for the template
- the recovery target is operational, not a new model-spec change
- we are reusing the same validated config lineage

If code changes are made to support selective reset or liveness auditing, run focused tests first, then use the relaunch command above.

## Testing Requirements

Any recovery tooling change should include:

1. unit tests for selective cutoff reset:
   - archives only selected run directories
   - preserves completed non-selected cutoffs
   - rewrites matrix state correctly
2. unit tests for liveness classification:
   - active CPU-bound sampling
   - true idle stall
   - already-finished row
3. a runbook update:
   - exact commands
   - evidence paths
   - recovery decision thresholds

## Documentation Requirements

The recovery work should leave behind:

- this recovery plan
- an incident note under `repro/reports/` or `repro/run/`
- reset summary artifacts
- a post-recovery checkpoint note stating:
  - whether `20211221` finished without restart or required rerun
  - when `20221225` launched
  - whether cleanup fired as expected after `post`

## Exit Criteria

This incident is resolved when all of the following are true:

1. `20211221` passes through `report`
2. `20221225` launches and passes through `report`
3. completed rows do not retain heavy fit `.RData`
4. protected inputs remain untouched
5. the recovery path is documented and reproducible


## Phase-3 Root-Cause Split After The Control Proof Lane

The phase-2 control lane produced the decisive split:

- `20211221 q50` should no longer be treated as a sampling bug first; it is an invalid terminal VB endpoint with repeated median state-guard events
- `20221225 q65` should no longer be treated as a generic family problem; it is a runtime failure inside forecast latent-state sampling on the real `keep` path

### Implemented Runtime Guard For Q65

The `keep` entrypoint now includes:

- per-member forecast latent-state phase markers
- numeric-health summaries for sampler inputs
- fail-fast checks on invalid `uts.lambda`, `uts.psi`, `uts.chi`, `sts.mu`, and `sts.sig2`
- configurable `fit.exdqlm_multivar.legacy.sampling_diagnostics.member_walltime_seconds`

### Implemented Next Proof Lanes

1. q65 runtime proof:
   - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q65_runtime_diagnostic_20260514.template.yaml`
   - `config/he2_relaunch_batches/exdqlm_multivar_keep_q65_runtime_diagnostic_20260514.yaml`
2. q50 stabilization proof:
   - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_stabilization_diagnostic_20260514.template.yaml`
   - `config/he2_relaunch_batches/exdqlm_multivar_keep_q50_stabilization_diagnostic_20260514.yaml`

### Decision Gate Before Production Resume

Do not resume the remaining production cutoffs until:

- `20221225 q65` either completes or fails with a precise named sampler/input cause under the q65 runtime proof lane
- `20211221 q50` proves it can clear the `min_update_iters=50` gate under a coherent stabilization policy
- the healthy controls (`q80`, `q65`) remain healthy in those proof lanes

## Phase-4 Follow-On Proof Lanes After The First Split Proof

The first split proof pass produced two concrete outcomes:

- `20211221 q50` improved from `28` to `38` gamma/sigma updates under the lighter hold policy, but still failed the hard pre-sampling gate before sampling
- `20221225 q65` no longer failed in an unbounded “sampling” region; it localized to the forecast-member lower-truncated-normal draw on the corrected `keep` path

### Implemented Follow-On Runtime Fix For Q65

The next q65 runtime pass now includes:

- a hardened lower-truncated-normal sampler for extreme left-tail regimes
- continued per-member phase markers and wall-time guards
- `sts.alpha` summaries at the member level
- post-draw numeric validation for sampled latent-state outputs

### Implemented Follow-On Stabilization Candidate For Q50

The next q50 candidate now includes:

- `freeze_target=states`
- `median_state_hold_after_guard_iters=0`
- `median_state_blend_alpha=0.5`
- `median_cov_blend_alpha=0.5`
- `median_max_abs_gamma_step=0.15`
- `median_max_abs_log_sigma_step=0.25`

The hard pre-sampling gate remains unchanged.

### Follow-On Proof Lanes

1. q65 truncnorm runtime proof:
   - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q65_truncnorm_runtime_diagnostic_20260514.template.yaml`
   - `config/he2_relaunch_batches/exdqlm_multivar_keep_q65_truncnorm_runtime_diagnostic_20260514.yaml`
2. q50 state-freeze stabilization proof:
   - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_diagnostic_20260514.template.yaml`
   - `config/he2_relaunch_batches/exdqlm_multivar_keep_q50_statefreeze_stabilization_diagnostic_20260514.yaml`

### Phase-4 Gate

Do not advance to the combined 4-quantile confirmation suite until:

- `20221225 q80` remains healthy under the truncnorm-hardened runtime lane
- `20221225 q65` either completes or fails explicitly with a parameter-localized truncnorm error
- `20211221 q65` remains healthy under the new q50 candidate lane
- `20211221 q50` either clears the `min_update_iters=50` gate or fails with clearly improved diagnostics under the state-freeze candidate

## Phase-5 Q65 Closure And Q50-Only Overnight Ladder

The phase-4 proof result closes the q65 runtime track provisionally:

- `20221225 q65` completed end to end on the truncnorm-runtime proof lane
- `20221225 q80` control completed end to end on the same lane
- the old q65 runtime hang did not reproduce under the hardened truncnorm/runtime path

The only remaining blocker is now `20211221 q50`.

### Q50 Engineering Root Cause

The latest q50 state-freeze candidate did not fail on the old median terminal-VB path.
It failed earlier because the blend step was combining:

- materialized state payloads from `cur.theta.out`
- raw flattened C++ payloads from `DISC_update_theta_synth_cpp_W`

That produced:

- `blend dim mismatch for theta$sm_ens[[1]]`

### Q50 Repair Decision

The next move is intentionally narrow:

1. fix the materialized/raw theta blend mismatch
2. rerun the exact same q50 state-freeze candidate with the same q65 control
3. only if that rerun still fails scientifically, escalate to a q50-only damping ladder

### Overnight Q50 Ladder

Run these in order, stopping at the first pass:

1. baseline rerun:
   - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_rerun_20260515.template.yaml`
   - `config/he2_relaunch_batches/exdqlm_multivar_keep_q50_statefreeze_stabilization_rerun_20260515.yaml`
2. stepcap10:
   - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap10_20260515.template.yaml`
   - `config/he2_relaunch_batches/exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap10_20260515.yaml`
   - q50 caps: gamma `0.10`, log-sigma `0.20`
3. stepcap075:
   - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap075_20260515.template.yaml`
   - `config/he2_relaunch_batches/exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap075_20260515.yaml`
   - q50 caps: gamma `0.075`, log-sigma `0.15`

Use the overnight runner:

- `python3 scripts/run_q50_statefreeze_overnight_ladder.py`
- it uses the dedicated `overnight_q50_ladder` queue profile (`ordinary_max_concurrent=4`, `fit_parallel_workers=2`, `mc_cores=2`)

## Phase-6 Proof Promotion Into The Remaining Production Resume

The overnight q50 ladder completed without needing the tighter fallback rungs:

- `20211221 q50` passed end to end on the repaired baseline rerun
- `20211221 q65` control also passed on the same lane
- the q50 baseline rerun is the winning proof candidate

The q65 runtime proof also held through the old bad region:

- `20221225 q65` passed end to end on the truncnorm/runtime proof lane
- `20221225 q80` control also passed

At this point the correct next move is no longer more proof work. It is a selective production resume for the two unfinished cutoffs only.

### Winning Promotion Contract

Use a dedicated promotion batch:

- `config/he2_relaunch_batches/exdqlm_multivar_keep_remaining_cutoffs_proof_promotion_20260515.yaml`

This batch does three things deliberately:

1. selects only the unfinished cutoffs:
   - `20211221`
   - `20221225`
2. promotes the winning q50 proof policy only to `20211221 q50`
3. leaves the previously healthy `20221225 q50` policy alone

Promoted q50 proof settings for `20211221 q50`:

- `freeze_target=states`
- `median_state_hold_after_guard_iters=0`
- `median_state_blend_alpha=0.5`
- `median_cov_blend_alpha=0.5`
- `median_max_abs_gamma_step=0.15`
- `median_max_abs_log_sigma_step=0.25`
- terminal sampling guard:
  - `mode=fail_fast`
  - `min_guard_count=1`
  - `max_guard_lag_iters=0`
  - `require_frozen=true`

Preserved q50 settings for `20221225 q50`:

- `median_state_hold_after_guard_iters=10`
- `median_state_blend_alpha=1.0`
- `median_cov_blend_alpha=1.0`

Shared production-resume observability settings:

- sampling heartbeats enabled
- `heartbeat_seconds=30`
- phase markers enabled
- `walltime_seconds=900`
- `member_walltime_seconds=20`

### Proof-Promotion Validation

The promotion batch is covered by the builder/template test suite:

- `tests/python/test_he2_publication_relaunch_template.py`
- `tests/python/test_he2_publication_relaunch_builder_selection.py`

Those tests enforce:

- only `20211221` and `20221225` are selected
- `20211221 q50` receives the winning proof settings
- `20221225 q50` does not inherit the `20211221` q50-only policy
- seeds remain cutoff-specific:
  - `20211221`
  - `20221225`
- recovery resources remain `fit_parallel_workers=7` and `mc_cores=7`

### Selective Reset And Relaunch

Reset only the unfinished rows in the production root:

```bash
python3 scripts/reset_he2_bayesian_publication_relaunch_state.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --cutoffs 20211221 20221225 \
  --reset-tag 20260515_proof_promotion_resume_r01
```

Reset archive:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_20260512/control/restart_resets/20260515_proof_promotion_resume_r01`

Relaunch the remaining production work with:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_remaining_cutoffs_proof_promotion_20260515.yaml \
  --profile disk_guarded_dual_recovery \
  --skip-validate
```

Observed launch result:

- controller PID: `986815`
- launched `20211221` row PID: `986944`
- launched `20221225` row PID: `987589`

### Current Live Resume State

As of the launch verification window:

- both remaining cutoffs are active in `fit/pending`
- queue is in the expected recovery steady state:
  - `active=2`
  - free space about `539.9G`
- generated configs exist for both rows under:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_20260512/control/generated_configs`

The production-resume incident bundle is:

- `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/reports/he2_relaunch_incidents/20260515_production_resume_r01`

This is now the authoritative path forward unless one of the two remaining cutoffs regresses under the promoted settings.

## Phase-7 20221225 Q50-Specific Recovery Fork

The first proof promotion into the main remaining-cutoff production resume produced a mixed result:

- `20211221 q50` remained healthy under the promoted state-freeze winner
- `20221225 q65` remained healthy under the hardened runtime path
- `20221225 q50` failed before sampling under the older gamma/sigma freezer regime

### Why This Is Not A `max_iter` Problem

`20221225 q50` did not merely run out of iterations near convergence.
It reached `iter=100` with only `2` gamma/sigma updates and repeated median state-guard refreeze cycles.

The failure signature was:

- `freeze_target=gamma_sigma`
- `median_state_hold_after_guard_iters=10`
- repeated state-guard windows at `8, 19, 30, 41, 52, 63, 74, 85, 96`
- terminal preflight stop:
  - `got=2 required=50`

Therefore the next move is **not** `max_iter=200`.
The next move is a q50-specific stabilization transplant on cutoff `20221225`.

### Operational Fork

To isolate that work cleanly:

1. preserve evidence for the failing `20221225` production row
2. stop only the `20221225` row process tree
3. pause the main production controller so `20221225` cannot be auto-relaunched while `20211221` continues
4. keep the active `20211221` production row running untouched
5. launch a dedicated `20221225 q50 + q80` proof lane using the winning q50 state-freeze policy

### Dedicated Proof Lane

Template:

- `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20221225_q50_statefreeze_diagnostic_20260515.template.yaml`

Batch:

- `config/he2_relaunch_batches/exdqlm_multivar_keep_20221225_q50_statefreeze_diagnostic_20260515.yaml`

This lane:

- selects only cutoff `20221225`
- runs problem `q50` plus healthy same-cutoff control `q80`
- keeps `seed=20221225`
- uses `n_samp=8`
- uses `fit_parallel_workers=2` and `mc_cores=2`
- applies the winning q50 proof policy:
  - `freeze_target=states`
  - `median_state_hold_after_guard_iters=0`
  - `median_state_blend_alpha=0.5`
  - `median_cov_blend_alpha=0.5`
  - `median_max_abs_gamma_step=0.15`
  - `median_max_abs_log_sigma_step=0.25`
  - terminal sampling guard `mode=fail_fast`

### Follow-On Promotion Batch

If that proof passes, promote only `20221225` with:

- `config/he2_relaunch_batches/exdqlm_multivar_keep_20221225_q50_proof_promotion_20260515.yaml`

That batch preserves the already-running `20211221` row and applies the winning q50 policy only to `20221225` on the next targeted resume.

## Phase-8 20221225 Q50 Proof Promotion Into Main Production

The dedicated `20221225 q50 + q80` proof lane passed end to end, so the winning q50 state-freeze policy was promoted into the main production rollout for `20221225` only.

Promotion execution:

```bash
python3 scripts/reset_he2_bayesian_publication_relaunch_state.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --cutoffs 20221225 \
  --reset-tag 20260515_20221225_q50_proof_promotion_r01

python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_20221225_q50_proof_promotion_20260515.yaml \
  --profile disk_guarded_dual_recovery \
  --skip-validate
```

Operational result:

- proof lane archived under:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/reports/he2_relaunch_incidents/20260515_20221225_q50_production_promotion_r01`
- selective reset archive:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_20260512/control/restart_resets/20260515_20221225_q50_proof_promotion_r01`
- relaunched cutoff:
  - `20221225` only
- preserved completed rows:
  - `20210123`, `20211112`, `20220511`, `20211221`

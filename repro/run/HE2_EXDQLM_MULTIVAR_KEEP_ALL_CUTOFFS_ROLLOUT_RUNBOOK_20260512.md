# HE2 exdqlm_multivar_keep All-Cutoffs Rollout Runbook

Date: 2026-05-12

## Goal

Scale the repaired `exdqlm_multivar_keep` family from the successful `20210123` proof row to all 5 HE2 publication cutoffs under the canonical shared-input / GDPC relaunch workflow.

This rollout now follows a strict transform rule:

- retros, forecast ensembles, observations, fit internals, and post internals stay on `log1p_cms`
- `log_log1p_cms` is not allowed in the current relaunch workflow

## Inputs

- template:
  - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml`
- batch:
  - `config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_quantile_map_20260512.yaml`
- cleanup manifest:
  - `config/he2_recent_runtime_cleanup_20260512.yaml`
- golden contract:
  - `repro/run/HE2_EXDQLM_MULTIVAR_KEEP_GOLDEN_CONTRACT_20260512.md`
- transform policy:
  - `repro/run/LOG1P_ONLY_TRANSFORM_POLICY_20260512.md`

## Workflow classes covered

The validator for this template explicitly covers both cutoff action classes:

- representative short-history cutoff requiring `rebuild_full_history_and_refresh_GDPC`
  - `20210123`
- representative full-history cutoff requiring `refresh_GDPC_only`
  - `20211221`

## Queue profile

This rollout uses a disk-guarded serial queue contract:

- `ordinary_max_concurrent=1`
- `pause_free_gb=25`
- `launch_free_gb=35`
- `heavy_free_gb=35`
- `heavy_cutoff_max_concurrent=1`

The intent is to avoid the earlier launch stall caused by unrealistic free-space thresholds.

For higher throughput after validation passes, the template also exposes a dual-row profile:

- profile: `disk_guarded_dual`
- ordinary rows in parallel: `2`
- per row fit workers: `7`
- per row `mc_cores`: `7`
- effective quantile-model concurrency: `14`

This is the efficient launch mode for the all-cutoff family rollout. A literal batch size of `15` is not natural for this family because each row contains `7` quantile submodels, so the clean parallelism units are `7` or `14`.

Recovery profile:

- profile: `disk_guarded_dual_recovery`
- ordinary rows in parallel: `2`
- per row fit workers: `7`
- per row `mc_cores`: `7`
- heavy cutoff block on ordinary rows: disabled

Use this only when resuming the final ordinary cutoff jointly with the heavy `20221225` cutoff after a targeted recovery reset.

Dedicated remaining-cutoff seed recovery batch:

- `config/he2_relaunch_batches/exdqlm_multivar_keep_remaining_cutoffs_seed_recovery_20260513.yaml`

Dedicated focused diagnostic batch:

- `config/he2_relaunch_batches/exdqlm_multivar_keep_problem_quantiles_diagnostic_20260513.yaml`

Dedicated phase-2 control diagnostic batch:

- `config/he2_relaunch_batches/exdqlm_multivar_keep_phase2_controls_diagnostic_20260514.yaml`

## Cleanup policy

Before rollout, prune large superseded HE2 runtime artifacts while preserving compact evidence:

```bash
python3 scripts/cleanup_he2_runtime_artifacts.py \
  --config config/he2_recent_runtime_cleanup_20260512.yaml
python3 scripts/cleanup_he2_runtime_artifacts.py \
  --config config/he2_recent_runtime_cleanup_20260512.yaml \
  --apply
```

## Validation

Run the family-wide prelaunch validator:

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_quantile_map_20260512.yaml
```

Expected result:

- all 5 cutoff bundle checks pass
- representative multivariate quantile fit smokes pass for `20210123` and `20211221`
- representative multivariate full-pipeline smokes pass for `20210123` and `20211221`
- smoke `.RData` payloads are pruned automatically after successful validation

## Launch

After validation passes, launch via the relaunch controller:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_quantile_map_20260512.yaml \
  --profile disk_guarded_dual
```

## Incident Recovery

If a live cutoff appears stalled during rollout, use the recovery plan:

- `repro/run/HE2_EXDQLM_MULTIVAR_KEEP_RECOVERY_PLAN_20260513.md`

Key recovery tools:

- liveness audit:
  - `python3 scripts/audit_he2_bayesian_publication_relaunch_liveness.py --artifact-root <artifact_root> --run-id <run_id> --quantile 50 --sample-seconds 5`
- selective reset:
  - `python3 scripts/reset_he2_bayesian_publication_relaunch_state.py --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml --cutoffs 20211221 20221225 --reset-tag <tag>`

Recommended seed-scoped recovery relaunch:

- `python3 scripts/launch_he2_bayesian_publication_relaunch.py --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_remaining_cutoffs_seed_recovery_20260513.yaml --profile disk_guarded_dual_recovery --skip-validate`

Important recovery note:

- do not rerun the remaining cutoffs unchanged with `run.seed: 777`
- the recovery batch file changes only the per-cutoff `run.seed`
- it keeps the validated `log1p` contract and the tuned quantile policy map intact

If the remaining quantiles repeatedly re-enter silent sampling, do not keep blind-relaunching them. Use the focused diagnostic lane first:

- `python3 scripts/launch_he2_bayesian_publication_relaunch.py --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_problem_quantiles_diagnostic_20260513.yaml --profile disk_guarded_dual_recovery --skip-validate`

What this diagnostic lane changes:

- isolates only `20211221 q50` and `20221225 q65`
- lowers `fit.exdqlm_multivar.legacy.n_samp` to `128`
- enables sampling phase markers, heartbeats, and a wall-time guard
- enables a q50 terminal fail-fast guard only for the pathological median endpoint case

If the focused lane confirms the same post-`Sampling Started` silent region, move to the paired control suite before touching production again:

- `python3 scripts/launch_he2_bayesian_publication_relaunch.py --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_phase2_controls_diagnostic_20260514.template.yaml --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_phase2_controls_diagnostic_20260514.yaml --profile disk_guarded_dual_recovery --skip-validate`

What this phase-2 control suite changes:

- pairs each problem quantile with a healthy sibling in the same cutoff
- `20211221` runs `q50` plus `q65`
- `20221225` runs `q65` plus `q80`
- lowers `fit.exdqlm_multivar.legacy.n_samp` further to `8`
- keeps cutoff-specific seeds and the validated `log1p` contract intact
- writes dedicated per-quantile `sampling_diagnostics.log` files

Important operational note:

- `20221225` is treated as the heavy cutoff
- with `heavy_cutoff_blocks_ordinary=true`, it will wait until no ordinary cutoff is active
- a one-row tail at the end of the campaign is therefore expected under the current queue policy

## Retention expectation

Successful rows should keep post/report/validate outputs and should not retain large fit `.RData` payloads after `post`.

## Exit criteria

1. all 5 `exdqlm_multivar_keep` cutoffs launch and complete
2. q35 remains stable across the family rollout
3. retained artifacts stay compact enough for broader HE2 scale-up


## Phase-3 Follow-Up After The Phase-2 Proof Lane

The phase-2 proof lane established two separate failure tracks:

- `20211221 q50` is a median-path fit-stability problem and is now correctly blocked before bad sampling
- `20221225 q65` is a forecast latent-state sampling runtime problem

The next proof lanes are therefore split:

### Q65 Runtime Proof Lane

Use this lane to validate the forecast-member sampling guards, numeric-health checks, and per-member wall-time control on the real `keep` path:

- `python3 scripts/launch_he2_bayesian_publication_relaunch.py --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q65_runtime_diagnostic_20260514.template.yaml --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_q65_runtime_diagnostic_20260514.yaml --profile disk_guarded_dual_recovery --skip-validate --reset-state`

What it changes:

- isolates only cutoff `20221225`
- runs problem `q65` plus healthy control `q80`
- keeps `n_samp=8`
- enables sampling phase markers, heartbeats, and a per-member wall-time guard
- keeps the validated `log1p` contract intact

### Q50 Stabilization Proof Lane

Use this lane only after the q65 runtime path is proven or while testing q50 stabilization independently:

- `python3 scripts/launch_he2_bayesian_publication_relaunch.py --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_stabilization_diagnostic_20260514.template.yaml --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_q50_stabilization_diagnostic_20260514.yaml --profile disk_guarded_dual_recovery --skip-validate --reset-state`

What it changes:

- isolates only cutoff `20211221`
- runs problem `q50` plus healthy control `q65`
- keeps the q50 terminal fail-fast guard active
- tests a lighter q50 hold policy with `median_state_hold_after_guard_iters=0`
- keeps the validated `log1p` contract intact

### Phase-4 Follow-On Proof Lanes

The first split proof pass established:

- `20211221 q50` is no longer a sampling mystery; it fails safely before sampling when the VB endpoint is invalid
- the first q50 candidate improved updates from `28` to `38`, but still failed the `min_update_iters=50` gate
- `20221225 q65` no longer hangs vaguely in “sampling”; it localizes to the forecast-member lower-truncated-normal draw on the real `keep` path

Use the next two proof lanes after freezing the previous artifacts:

1. q65 truncnorm runtime proof:
   - `python3 scripts/launch_he2_bayesian_publication_relaunch.py --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q65_truncnorm_runtime_diagnostic_20260514.template.yaml --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_q65_truncnorm_runtime_diagnostic_20260514.yaml --profile disk_guarded_dual_recovery --skip-validate --reset-state`
2. q50 state-freeze stabilization proof:
   - `python3 scripts/launch_he2_bayesian_publication_relaunch.py --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_diagnostic_20260514.template.yaml --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_q50_statefreeze_stabilization_diagnostic_20260514.yaml --profile disk_guarded_dual_recovery --skip-validate --reset-state`

What changed for the new q65 runtime lane:

- the truncated-normal sampler itself is hardened for extreme lower-tail truncation
- forecast-member diagnostics now record `sts.alpha` and sampled-draw summaries
- the lane remains limited to problem `q65` plus healthy control `q80`

What changed for the new q50 stabilization lane:

- `q50` switches to `freeze_target=states`
- median hold remains disabled after guard events
- median state / covariance blending is reduced to `0.5`
- median gamma and log-sigma step caps are tightened to `0.15` and `0.25`
- the hard pre-sampling guard remains in place

### Phase-5 Q50 Repair And Overnight Ladder

The phase-4 proof result closes the q65 runtime path provisionally:

- `20221225 q65` passed end to end on the truncnorm-runtime proof lane
- `20221225 q80` control also passed

The only remaining blocker is `20211221 q50`.

The current q50 repair sequence is:

1. fix the materialized/raw theta blend mismatch in the legacy runtime
2. rerun the exact same q50 state-freeze candidate
3. if it still fails scientifically, step through a q50-only damping ladder

Launch the overnight ladder with:

- `python3 scripts/run_q50_statefreeze_overnight_ladder.py`
- it uses the dedicated `overnight_q50_ladder` queue profile (`ordinary_max_concurrent=4`, `fit_parallel_workers=2`, `mc_cores=2`)

The ladder uses these rungs, stopping at first pass:

1. baseline rerun:
   - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_rerun_20260515.template.yaml`
   - `config/he2_relaunch_batches/exdqlm_multivar_keep_q50_statefreeze_stabilization_rerun_20260515.yaml`
2. stepcap10:
   - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap10_20260515.template.yaml`
   - `config/he2_relaunch_batches/exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap10_20260515.yaml`
3. stepcap075:
   - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap075_20260515.template.yaml`
   - `config/he2_relaunch_batches/exdqlm_multivar_keep_q50_statefreeze_stabilization_stepcap075_20260515.yaml`

## Phase-6 Production Resume After Proof Promotion

The focused proof work is complete enough to resume the real remaining production rows.

Closed proof results:

- `20221225 q65` passed on the truncnorm/runtime proof lane with same-cutoff control `q80`
- `20211221 q50` passed on the repaired state-freeze baseline rerun with same-cutoff control `q65`
- the tighter q50 fallback ladder rungs were therefore not needed

### Promotion Batch

Use:

- `config/he2_relaunch_batches/exdqlm_multivar_keep_remaining_cutoffs_proof_promotion_20260515.yaml`

This batch:

- selects only `20211221` and `20221225`
- applies the winning q50 proof policy only to `20211221 q50`
- preserves the previously healthy q50 policy on `20221225`
- keeps sampling diagnostics enabled for production observability
- keeps recovery resources at `fit_parallel_workers=7` and `mc_cores=7`

### Reset Only The Remaining Production Rows

```bash
python3 scripts/reset_he2_bayesian_publication_relaunch_state.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --cutoffs 20211221 20221225 \
  --reset-tag 20260515_proof_promotion_resume_r01
```

### Relaunch The Remaining Production Work

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_remaining_cutoffs_proof_promotion_20260515.yaml \
  --profile disk_guarded_dual_recovery \
  --skip-validate
```

Observed launch result:

- controller PID: `986815`
- `20211221` row PID: `986944`
- `20221225` row PID: `987589`

### Launch Verification Contract

Immediately after relaunch, confirm all of the following:

1. `matrix_status.csv` shows both `20211221` and `20221225` in `fit/pending`
2. `queue.log` shows `active=2`
3. generated configs exist for both rows under the main production root
4. `20211221 q50` generated config contains the winning proof settings:
   - `freeze_target=states`
   - `median_state_hold_after_guard_iters=0`
   - `median_state_blend_alpha=0.5`
   - `median_cov_blend_alpha=0.5`
   - `median_max_abs_gamma_step=0.15`
   - `median_max_abs_log_sigma_step=0.25`
   - terminal sampling guard `mode=fail_fast`
5. `20221225 q50` generated config still uses the previously healthy baseline q50 settings
6. both rows retain sampling diagnostics:
   - `heartbeat_seconds=30`
   - `walltime_seconds=900`
   - `member_walltime_seconds=20`

### Operational Posture

After relaunch:

- do not reopen proof lanes unless one of the two remaining production rows regresses
- do not broaden the batch to already-completed cutoffs
- monitor the two former problem quantiles most closely:
  - `20211221 q50`
  - `20221225 q65`
- let the resumed campaign continue through `post`, `validate`, and `report` if fit behaves normally

## Phase-7 20221225 Q50 Fork After The First Production Resume

If the first proof-promotion production resume shows:

- `20211221 q50` healthy
- `20221225 q65` healthy
- but `20221225 q50` failing its pre-sampling update gate under the older q50 policy

then do **not** extend `max_iter` first.

Instead:

1. preserve the `20221225` evidence bundle
2. stop only the `20221225` row
3. pause the main production controller while leaving `20211221` running
4. launch a dedicated `20221225 q50 + q80` proof lane with the winning q50 state-freeze policy

Launch command:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20221225_q50_statefreeze_diagnostic_20260515.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_20221225_q50_statefreeze_diagnostic_20260515.yaml \
  --profile disk_guarded_dual_recovery \
  --skip-validate
```

If that proof passes, use the dedicated follow-on promotion batch:

- `config/he2_relaunch_batches/exdqlm_multivar_keep_20221225_q50_proof_promotion_20260515.yaml`

This keeps the q50 policy transplant local to `20221225` instead of broadening another production reset.

## Phase-8 20221225-Only Proof Promotion Resume

Once the dedicated `20221225 q50 + q80` proof lane passes, resume the main production campaign by promoting the passing q50 policy into `20221225` only.

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

This keeps the q50 promotion local to `20221225` and leaves all previously healthy completed cutoffs untouched.

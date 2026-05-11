# HE2 exAL Median Overnight Experiment Plan (2026-05-11)

## Objective
Run a broad, sidecar-only overnight investigation for the sensitive median case:
- cutoff: `2021-01-23`
- family: `exdqlm_multivar_keep`
- quantile: `q=0.50`

The goal is not to force a production patch tonight. The goal is to wake up with:
- a ranked set of candidate stabilization policies
- a clean summary of which ideas helped and which did not
- one or more clear directions for the next production-safe fix

## Current evidence
What we already know from today:
- Warmup-only tuning did not produce a healthy winner.
- Bounded gamma/sigma optimization and Hessian regularization removed the old immediate optimizer crash.
- Exact gamma/log-sigma step damping improved the path materially.
- The new median state-growth guard is active and catches the explosive state jump.
- The remaining blocker is now clearly **state-side** rather than purely optimizer-side.

That means an overnight plan that only tweaks warmup is too narrow.

## Key constraint
This campaign must remain **sidecar-only**:
- no contamination of the production relaunch workflow
- no changes to the current 45-row campaign machinery
- all outputs live under dedicated runtime artifact roots
- all configs live under dedicated `config/median_*overnight*` files

## Recommended overnight strategy
Use a **three-layer overnight campaign** instead of one monolithic sweep.

1. Anchor and control runs
- establish clear baselines under the current patched code
- confirm that our current best-known candidates behave the same way on clean artifact roots

2. Broad warmup and gamma/sigma diversity
- screen genuinely different warmup shapes and gamma/sigma stabilization policies
- not just tiny perturbations of one setting

3. State-side recovery diversity
- this is the highest-value overnight layer
- because the current failure is now predominantly state-side

## Important recommendation
Do **not** use all 64 cores at once.

Reason:
- each probe launches a full unified run with expensive R package and model setup
- high fan-out will create unnecessary compile/IO/memory contention
- we want stable overnight throughput, not maximum theoretical parallelism

Recommended concurrency:
- `24` concurrent single-core probes as the main overnight profile
- if the node stays comfortable, optionally scale to `32`
- do not start at `64`

## Campaign structure

### Batch A: Anchors and controls
Purpose:
- cleanly replicate the main reference behaviors under fresh roots
- give tomorrow a direct comparison set

Suggested probes:
1. `default_stabilized`
2. `gamma015_sigma035`
3. `gamma01_sigma025`
4. `gamma0075_sigma02`
5. `gamma005_sigma015`

Interpretation value:
- tells us whether the tighter caps are really monotone improvements
- gives a stable baseline table to compare against every later idea

### Batch B: Warmup geometry sweep
Purpose:
- test whether a broader warmup geometry can reduce the tendency to enter the bad state direction

Suggested dimensions:
- `warmup_freeze_iters`: `5, 10, 15`
- `guard_refreeze_iters`: `10, 20, 30`
- `freeze_target`: mostly `gamma_sigma`, with only `1-2` `states` controls

Recommended subset, not full Cartesian product:
1. `freeze10_refreeze10`
2. `freeze10_refreeze20`
3. `freeze15_refreeze20`
4. `freeze15_refreeze30`
5. `freeze10_states_refreeze20`
6. `freeze15_states_refreeze30`

Interpretation value:
- checks whether the current instability is partly a timing problem in the first live update window
- but keeps this batch bounded because warmup-only evidence is already weak

### Batch C: Initialization sweep
Purpose:
- test whether the median path is highly sensitive to starting sigma/gamma geometry

Suggested dimensions:
- `init_sigma_floor`: `1e-3, 1e-2, 1e-1`
- `init_sigma_scale`: `1.0, 0.5, 0.25`
- `init_gamma`: `0.0, -0.05, +0.05`

Recommended subset:
1. `floor1e-2_scale1_gamma0`
2. `floor1e-2_scale0p5_gamma0`
3. `floor1e-1_scale0p5_gamma0`
4. `floor1e-2_scale0p5_gammaNeg005`
5. `floor1e-2_scale0p5_gammaPos005`
6. `floor1e-1_scale0p25_gamma0`

Interpretation value:
- checks whether the median path needs a less aggressive or more regularized start before the first live update

### Batch D: Gamma/sigma stabilization sweep
Purpose:
- explore richer optimizer-side stabilization combinations around the current best ideas

Suggested dimensions:
- tighter transformed bounds
- stronger Hessian ridge
- exact gamma/log-sigma caps
- sigma-only fallback tolerance

Recommended subset:
1. `caps010_025_plus_bounds`
2. `caps0075_020_plus_bounds`
3. `caps005_015_plus_bounds`
4. `caps010_025_plus_ridge1e4`
5. `caps0075_020_plus_ridge1e4`
6. `caps010_025_plus_bounds_plus_ridge1e4`
7. `caps0075_020_plus_bounds_plus_ridge1e4`
8. `caps010_025_sigmaFallback1e6`

Interpretation value:
- checks whether better local geometry around the optimizer still helps after today’s fixes
- likely useful, but not sufficient on its own

### Batch E: State-guard parameter sweep
Purpose:
- this is the most important overnight batch under the current evidence

Suggested dimensions:
- `median_state_norm_max_ratio`: `10, 15, 20, 25`
- `median_state_norm_abs_cap`: `1e7, 5e7, 1e8`
- `median_state_guard_refreeze_iters`: `10, 20, 30`

Recommended subset:
1. `ratio10_cap1e7_refreeze20`
2. `ratio10_cap5e7_refreeze20`
3. `ratio15_cap5e7_refreeze20`
4. `ratio15_cap1e8_refreeze20`
5. `ratio20_cap1e8_refreeze20`
6. `ratio10_cap1e7_refreeze30`
7. `ratio15_cap5e7_refreeze30`
8. `ratio20_cap1e8_refreeze30`

Interpretation value:
- tells us whether the median can be stabilized by stricter rollback criteria alone
- this is the first place I would expect a real overnight winner to emerge if no extra code is added

### Batch F: State-hold / state-blend ideas
Purpose:
- this is the most promising conceptual next step if we want a serious overnight campaign
- but it requires a **small sidecar-only code extension first**

Proposed sidecar-only knobs to add before the overnight run:
1. `median_state_hold_after_guard_iters`
- after a guard trigger, skip `update.theta` for `k` iterations
- keep the last stable state fixed while the rest of the system refreezes

2. `median_state_blend_alpha`
- when a state update is accepted, blend it with the current state:
  - `theta_new = alpha * theta_candidate + (1-alpha) * theta_current`
- candidate values: `0.25, 0.5, 0.75`

3. optional `median_cov_blend_alpha`
- same idea for covariance state if needed

Recommended subset if these knobs are added:
1. `hold5_blend050`
2. `hold10_blend050`
3. `hold5_blend025`
4. `hold10_blend025`
5. `hold10_noBlend`
6. `hold5_blend075`

Interpretation value:
- this is the strongest overnight direction because it directly targets the current failure layer

## Best overnight ordering
To maximize useful information by tomorrow morning:

### Wave 1: fast signal
Run first:
- Batch A
- Batch E
- best 2-3 from Batch D

Why:
- these have the highest chance of telling us whether we can stabilize the median without extra code

### Wave 2: broader diversity
Run next:
- Batch B
- Batch C
- remaining Batch D

Why:
- these deepen understanding, even if Wave 1 already points strongly in one direction

### Wave 3: only if we add state-hold/blend tonight
Run last:
- Batch F

Why:
- highest upside, but requires the extra sidecar-only stabilization knobs first

## Morning outputs we should require
By tomorrow morning, the campaign should produce:

1. machine-readable summary
- `probe_results.csv`
- `probe_results.json`
- `winner_summary.json`

2. human-readable summary
- ranked markdown report with:
  - best 10 probes
  - failed probes by failure mode
  - heatmap-style grouping by idea family

3. explicit classification columns
Every probe row should classify:
- optimizer crash
- Hessian failure
- sigma explosion
- state explosion
- guard rollback triggered
- reached minimum updates or not
- reached finite `conv_check` or not

4. tomorrow decision shortlist
The summary should explicitly label:
- `promotable now`
- `promising but needs longer confirmation`
- `informative failure`
- `discard`

## What I recommend we actually do tonight
If we want the strongest overnight campaign, I recommend this exact sequence:

### Option A: Strongest plan
1. Add two sidecar-only knobs first:
- `median_state_hold_after_guard_iters`
- `median_state_blend_alpha`
2. Then launch the full overnight campaign:
- Batches A-E for sure
- Batch F too, since the new knobs exist

This is the best scientific plan.

### Option B: Lower-risk plan
1. Do **not** add new code tonight
2. Launch a broad overnight campaign with:
- Batches A-E only
3. Tomorrow decide whether the next code move must be state-hold/blend

This is safer, but probably lower upside.

## My recommendation
I recommend **Option A**.

Reason:
- the current evidence already tells us the remaining blocker is state-side
- if we only sweep warmup/optimizer/guard thresholds overnight, we may wake up with a large table of cleaner failures but no actual winner
- adding state-hold/blend as sidecar-only knobs gives the overnight campaign a real chance to find something actionable

## Resource plan
Suggested overnight budget:
- `24` concurrent probes
- `1` core per probe
- three waves
- automatic early-abort kept enabled
- confirmation runs only for healthy winners or top `3` soft winners

## Non-contamination guarantee
Everything stays isolated by design:
- dedicated `config/median_*overnight*.yaml`
- dedicated runtime artifact roots
- no changes to production batch configs
- no changes to the 45-row relaunch matrix
- no promotion into production until tomorrow’s review

## Tomorrow morning decision tree
1. If a clearly healthy winner exists:
- rerun it once more for confirmation
- then decide whether to promote it into the production relaunch path

2. If no healthy winner exists but one family is clearly best:
- use that family as the basis for the next targeted model-side patch

3. If everything still fails similarly:
- stop searching warmup space
- move fully to a state-side stabilization redesign

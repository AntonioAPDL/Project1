# HE2 exAL Median Warmup Probe Plan (2026-05-10)

This note documents the standalone median-only warmup search for the sensitive
`20210123 exdqlm_multivar_keep q=0.50` case.

## Purpose

Keep the production relaunch workflow clean. We do not embed a warmup search loop
inside the main relaunch tooling. Instead we:

1. freeze the current production candidate config,
2. run a small external probe set for the median only,
3. choose the first clearly healthy warmup specification,
4. wire only that winning median warmup back into the production launcher.

## Fixed contract during screening

The probe phase keeps fixed:

- cutoff: `2021-01-23`
- family: `exdqlm_multivar_keep`
- likelihood: `exAL`
- tuned discount factors from the current relaunch candidate
- forecast covariance prior (`epsilon=360`, `c_factor=1`)
- full-history shared bundle (`1987-05-29 -> cutoff`)
- PPT, SOIL, and canonical GDPC covariates
- deterministic future climate handoff

Only the exdqlm multivariate gamma/sigma warmup policy changes.

## Probe driver

- config: [median_warmup_probes_exdqlm_multivar_keep_20210123_q50_20260510.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/median_warmup_probes_exdqlm_multivar_keep_20210123_q50_20260510.yaml)
- round 2 config: [median_warmup_probes_exdqlm_multivar_keep_20210123_q50_round2_20260510.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/median_warmup_probes_exdqlm_multivar_keep_20210123_q50_round2_20260510.yaml)
- round 3 config: [median_warmup_probes_exdqlm_multivar_keep_20210123_q50_round3_20260510.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/median_warmup_probes_exdqlm_multivar_keep_20210123_q50_round3_20260510.yaml)
- runner: [run_exdqlm_median_warmup_probes.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_exdqlm_median_warmup_probes.py)

## Screening rules

Screening uses a shortened fit horizon only to triage warmup stability:

- quantile set: `{0.50}`
- workers: `1`
- `mc_cores`: `1`
- stages: `data_prep_shared`, `fit`
- screening `min_update_iters=10`
- screening `min_total_iters=20`
- screening `max_iter=30`

A probe is considered healthy only if it avoids guard/Hessian failures and
keeps the median update path finite and bounded.

## Confirmation rule

If a screening winner is healthy, rerun the winning patch under production
median fit controls:

- `min_update_iters=50`
- `min_total_iters=50`
- `max_iter=100`

Only after that confirmation do we wire the winning median warmup into the
production launcher.

## Results Summary

### Round 1: freeze and sigma-seed tuning

Runtime report root:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_median_warmup_probes_20260510/reports`

Outcome:

- no healthy winner
- best-scoring candidate was still unhealthy:
  - `freeze15_refreeze20_sigmafloor1e2_scale05`
- main finding:
  - changing only freeze length, refreeze length, and sigma seeding reduced the
    number of guard events, but every candidate still failed on the first real
    gamma/sigma update with `non-finite dq_transf` and a non-invertible Hessian

### Round 2: freeze latent states instead of gamma/sigma

Runtime report root:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_median_warmup_probes_round2_20260510/reports`

Outcome:

- no healthy winner
- every meaningful candidate remained unhealthy
- main finding:
  - `freeze_target=states` does not rescue the median path
  - several candidates failed immediately at `iter=1`
  - larger `sigma_scale` moved the failure into forecast-centered branches
    (`j=2`, `j=3`) instead of fixing it

### Round 3: nonzero gamma seeds under the original gamma/sigma freeze

Runtime artifact root:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_median_warmup_probes_round3_20260510`

Outcome at the point the campaign was stopped:

- no evidence of a production-safe median override
- representative findings:
  - `gamma=+0.1` with the round-1 best sigma seed caused immediate latent-state
    explosion during the freeze window (`state_norm_sq` jumped to about
    `5.46e8` by `iter=2`)
  - `gamma=-0.1` under the same path also caused immediate latent-state
    explosion (`state_norm_sq` about `4.85e8` by `iter=2`)
  - `gamma=+0.25` was worse, with `state_norm_sq` about `1.66e9` by `iter=2`

## Decision

No median-specific warmup override is being wired into the production relaunch
workflow yet.

That is intentional. The probe campaigns show that:

1. longer gamma/sigma freezes alone are insufficient
2. freezing the latent states is not sufficient
3. nonzero gamma seeding under the original freeze path destabilizes the latent
   states before the first live update settles

So the median problem is not solved by a safe warmup-only patch at this stage.

## Workflow Status

What is ready and kept:

- quantile-specific warmup override support in
  [stage_fit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/stages/stage_fit.R)
- standalone reproducible probe driver and configs
- regression tests for the probe tooling and the quantile-override resolution

What is intentionally not applied:

- no production `q=0.50` override for `exdqlm_multivar_keep`

## Next Fix Class

The next fix should target the median update path itself, not just launcher
warmup knobs. The most likely next level is a model-side stabilization change in
the `update_gamma_sigma()` path, for example:

- Hessian regularization / trust-region fallback
- bounded retry logic around the first median gamma/sigma update
- a more principled median-specific initialization for the transformed
  gamma/sigma parameters

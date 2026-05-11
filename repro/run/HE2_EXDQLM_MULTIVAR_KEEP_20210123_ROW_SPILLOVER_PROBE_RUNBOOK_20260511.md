# HE2 exdQLM Multivariate Keep 20210123 Spillover Probe

Date: 2026-05-11

## Purpose

This sidecar experiment tests whether the validated `q50` stabilization policy also helps the other failing quantiles in the same real row.

Scope:

- cutoff: `20210123`
- family: `exdqlm_multivar_keep`
- manuscript label: `exAL-M-T1`
- active quantiles: full 7-quantile ladder
- promoted policy applied to:
  - `q20`
  - `q35`
  - `q50`
  - `q65`
  - `q80`
- untouched tail quantiles:
  - `q05`
  - `q95`

This stays isolated in a dedicated artifact root so it does not overwrite:

- the scoped median probe tree
- the original row pilot tree
- the broader publication relaunch tree

## Why these quantiles

From the first real row:

- `q20` failed the forecast-health gate
- `q35` did not produce a clean forecast-health artifact
- `q65` failed with SPD/eigen decomposition errors
- `q80` failed with SPD/eigen decomposition errors
- `q50` improved materially under the validated init + hold policy

So this probe asks one narrow question:

Can the same validated `q50` policy rescue the full middle/upper failing block without changing `q05` or `q95`?

## Files

- dedicated template:
  - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_row_spillover_20260511.template.yaml`
- sidecar batch recipe:
  - `config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_row_spillover_probe_20260511.yaml`
- validator:
  - `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`
- launcher:
  - `scripts/launch_he2_bayesian_publication_relaunch.py`

## Applied policy

Applied to `q20`, `q35`, `q50`, `q65`, and `q80`:

```yaml
init:
  mode: robust
  gamma: 0.0
  sigma_floor: 0.01
  sigma_scale: 0.5
stabilization:
  median_state_hold_after_guard_iters: 10
  median_state_blend_alpha: 1.0
  median_cov_blend_alpha: 1.0
```

`q05` and `q95` remain on the preserved base row spec.

## Validation focus

The dedicated validator targets the changed quantiles only:

- fit-smoke quantiles:
  - `0.20`
  - `0.35`
  - `0.50`
  - `0.65`
  - `0.80`
- full-pipeline quantiles:
  - `0.20`
  - `0.35`
  - `0.50`
  - `0.65`
  - `0.80`

## Commands

Validate:

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_row_spillover_20260511.template.yaml \
  --batch-file config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_row_spillover_probe_20260511.yaml
```

Launch after validation:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_row_spillover_20260511.template.yaml \
  --batch-file config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_row_spillover_probe_20260511.yaml \
  --skip-validate
```

## Acceptance Gate

Promote this idea only if the row completes cleanly through:

- `fit`
- `post`
- `validate`
- `report`

with no forecast-health aborts and no SPD/eigen decomposition failures in the modified quantiles.

# HE2 exdQLM Multivariate Keep 20210123 q35 Lighter Probe

Date: 2026-05-11

## Purpose

This sidecar probe isolates `q35`, because the copied `q50` policy improved `q20` but destabilized `q35`.

Scope:

- cutoff: `20210123`
- family: `exdqlm_multivar_keep`
- quantile: `q35` only

## Rationale

The spillover probe showed:

- `q20` responded well to the reduced-sigma `q50` policy
- `q35` did not

So this probe reverts `q35` to the lighter init candidate:

- old init scale/floor
- new state hold retained

## Applied policy

```yaml
init:
  mode: robust
  gamma: 0.0
  sigma_floor: 0.001
  sigma_scale: 1.0
stabilization:
  median_state_hold_after_guard_iters: 10
  median_state_blend_alpha: 1.0
  median_cov_blend_alpha: 1.0
```

## Files

- template:
  - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_q35_probe_20260511.template.yaml`
- batch recipe:
  - `config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_q35_lighter_probe_20260511.yaml`

## Commands

Validate:

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_q35_probe_20260511.template.yaml \
  --batch-file config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_q35_lighter_probe_20260511.yaml
```

## Acceptance gate

Promote this `q35` candidate only if it:

- clears fit smoke
- clears full-pipeline quantile smoke
- avoids the explosive sigma/state path seen under the copied `q50` policy

# HE2 exdQLM Multivariate Keep 20210123 Tail Probe

Date: 2026-05-11

## Purpose

This sidecar probe continues the copied-`q50` policy investigation for the remaining unresolved quantiles:

- `q50`
- `q65`
- `q80`

It intentionally excludes:

- `q20`, because that candidate already looks strong
- `q35`, because it needs its own lighter probe

## Applied policy

For `q50`, `q65`, and `q80`:

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

## Files

- template:
  - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_tail_probe_20260511.template.yaml`
- batch recipe:
  - `config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_tail_probe_20260511.yaml`

## Commands

Validate:

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_tail_probe_20260511.template.yaml \
  --batch-file config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_tail_probe_20260511.yaml
```

## Acceptance gate

Promote this tail candidate only if:

- `q50` remains healthy
- `q65` and/or `q80` show clear improvement over the failed row-pilot behavior
- full-pipeline smoke passes for the selected quantiles

# HE2 exdQLM Multivariate Keep 20210123 Final Row Relaunch

Date: 2026-05-12

## Purpose

This runbook defines the first full `20210123` row relaunch after the q35
transfer-path runtime fix and promotability recheck.

Scope:

- cutoff: `20210123`
- family: `exdqlm_multivar_keep`
- manuscript label: `exAL-M-T1`
- active quantiles: full 7-quantile ladder
- policy style: quantile-specific, evidence-based overrides only

This row is isolated in its own artifact root so it does not overwrite:

- the earlier q50-only row pilot
- the q35 sidecar campaigns
- the broader publication relaunch tree

## Evidence basis

We are carrying forward the following validated or provisionally accepted
quantile policies:

| Quantile | Policy basis |
|---|---|
| `q05` | preserved base spec |
| `q20` | reduced-sigma init rescue |
| `q35` | fixed transfer-path + state-freeze + generic state hold candidate |
| `q50` | validated median init + hold policy |
| `q65` | reduced-sigma init rescue candidate |
| `q80` | reduced-sigma init rescue candidate |
| `q95` | preserved base spec |

The q35 promotability check now passes under the explicit gate documented in:

- [HE2_EXDQLM_MULTIVAR_KEEP_20210123_Q35_PROMOTABILITY_RECHECK_RUNBOOK_20260512.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/HE2_EXDQLM_MULTIVAR_KEEP_20210123_Q35_PROMOTABILITY_RECHECK_RUNBOOK_20260512.md)

## Production-row files

- dedicated template:
  - [he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_row_final_20260512.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_row_final_20260512.template.yaml)
- row batch recipe:
  - [20210123_exdqlm_multivar_keep_row_final_quantile_map_20260512.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_row_final_quantile_map_20260512.yaml)
- builder:
  - `scripts/build_he2_bayesian_publication_relaunch_configs.py`
- validator:
  - `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`
- launcher:
  - `scripts/launch_he2_bayesian_publication_relaunch.py`

## Final quantile policy map

Applied only where evidence supports it:

```yaml
fit:
  exdqlm_multivar:
    gamma_sigma:
      quantile_overrides:
        q20:
          init:
            mode: robust
            gamma: 0.0
            sigma_floor: 0.01
            sigma_scale: 0.5
        q35:
          freeze_target: states
          warmup_freeze_iters: 8
          init:
            mode: robust
            gamma: 0.0
            sigma_floor: 0.01
            sigma_scale: 0.5
          stabilization:
            state_guard_enabled: true
            state_norm_max_ratio: 25
            state_norm_abs_cap: 1.0e12
            state_guard_refreeze_iters: 10
            state_hold_after_guard_iters: 10
            state_blend_alpha: 1.0
            cov_blend_alpha: 1.0
        q50:
          init:
            mode: robust
            gamma: 0.0
            sigma_floor: 0.01
            sigma_scale: 0.5
          stabilization:
            median_state_hold_after_guard_iters: 10
            median_state_blend_alpha: 1.0
            median_cov_blend_alpha: 1.0
        q65:
          init:
            mode: robust
            gamma: 0.0
            sigma_floor: 0.01
            sigma_scale: 0.5
        q80:
          init:
            mode: robust
            gamma: 0.0
            sigma_floor: 0.01
            sigma_scale: 0.5
```

`q05` and `q95` remain on the preserved base row spec.

## Validation profile

The dedicated template validates the modified quantile block directly:

- quantile fit smoke: `q20`, `q35`, `q50`, `q65`, `q80`
- full-pipeline quantile smoke: `q20`, `q35`, `q50`, `q65`, `q80`

The exdqlm multivariate smoke fit contract is relaxed from the older 10-iteration
probe shape to:

- `min_update_iters = 6`
- `min_total_iters = 12`
- `max_iter = 18`

This is intentional so the q35 candidate is exercised through the fixed runtime path
instead of being under-tested by the old smoke contract.

## Resources

The final row uses one core per quantile model:

- `fit_parallel_workers = 7`
- `mc_cores = 7`

Dedicated queue thresholds:

- `pause_free_gb = 110`
- `launch_free_gb = 120`
- `heavy_free_gb = 120`

## Commands

Validate the final row:

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_row_final_20260512.template.yaml \
  --batch-file config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_row_final_quantile_map_20260512.yaml
```

Launch the final row after validation:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_row_final_20260512.template.yaml \
  --batch-file config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_row_final_quantile_map_20260512.yaml \
  --skip-validate
```

## Acceptance gate

Promote this family to the remaining cutoffs only if this row completes cleanly through:

- `fit`
- `post`
- `validate`
- `report`

with the expected multivariate synthesis, figures, and CRPS/table artifacts present.

## Next step after success

If this row completes cleanly, the next move is:

- family: `exdqlm_multivar_keep`
- all 5 cutoffs
- same quantile-specific policy map

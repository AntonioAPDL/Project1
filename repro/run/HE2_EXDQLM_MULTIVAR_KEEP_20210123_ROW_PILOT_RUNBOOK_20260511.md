# HE2 exdQLM Multivariate Keep 20210123 Row Pilot

Date: 2026-05-11

## Purpose

This runbook defines the first **real production row** promoted after the scoped `q50` median validation pass.

Scope:

- cutoff: `20210123`
- family: `exdqlm_multivar_keep`
- manuscript label: `exAL-M-T1`
- active quantiles: full 7-quantile ladder
- special policy: only `q50` receives the validated median init + hold override

This pilot is intentionally isolated in its own artifact root so it does not interfere with:

- the scoped median probe tree
- the broader 45-row publication relaunch tree

## Evidence basis

The following scoped validator passed cleanly on a pushed commit:

- template:
  - `config/he2_bayesian_publication_relaunch_median_q50_probe_20260511.template.yaml`
- batch recipe:
  - `config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_q50_median_init_hold_probe_20260511.yaml`
- clean validator root:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_bayesian_publication_median_q50_probe_20260511/control/prelaunch_validation_20260511T184407Z`

That scoped validator passed:

- `fit_quantile`
- `full_pipeline_quantile`

and cleared the old post-stage gamma-bounds failure.

## Production-row files

- dedicated template:
  - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_row_20260511.template.yaml`
- row-pilot batch recipe:
  - `config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_row_pilot_20260511.yaml`
- builder:
  - `scripts/build_he2_bayesian_publication_relaunch_configs.py`
- validator:
  - `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`
- launcher:
  - `scripts/launch_he2_bayesian_publication_relaunch.py`

## q50-only override policy

Applied only to `q50`:

```yaml
fit:
  exdqlm_multivar:
    gamma_sigma:
      quantile_overrides:
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
```

All other quantiles retain the preserved publication-row spec.

## Resources

The production row uses one core per quantile model:

- `fit_parallel_workers = 7`
- `mc_cores = 7`

Dedicated queue thresholds for this one-row pilot:

- `pause_free_gb = 110`
- `launch_free_gb = 120`
- `heavy_free_gb = 120`

These thresholds are intentionally lower than the broad campaign defaults because this artifact root only runs one row and the current node headroom is about `125 GB` free. The lower values let the pilot launch on the current machine without changing concurrency or the model contract.

## Commands

Validate the pilot row:

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_row_20260511.template.yaml \
  --batch-file config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_row_pilot_20260511.yaml
```

Launch the pilot row after validation:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_row_20260511.template.yaml \
  --batch-file config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_row_pilot_20260511.yaml \
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

If this row completes cleanly, launch:

- `exdqlm_multivar_keep`
- all 5 cutoffs
- same `q50`-only override policy

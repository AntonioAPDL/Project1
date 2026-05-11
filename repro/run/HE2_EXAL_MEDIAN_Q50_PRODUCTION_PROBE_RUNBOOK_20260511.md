# HE2 exAL Median q50 Production-Path Probe

Date: 2026-05-11

## Purpose

This runbook defines the first **production-path** probe promoted from the sidecar overnight median campaign.

The goal is to test the median `q=0.50` policy in the same relaunch builder/validator/launch path we will later use for the broader campaign, while keeping the work isolated from the main relaunch artifact root.

## Evidence basis

The overnight sidecar campaign at:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_median_overnight_campaign_20260511`

produced two healthy probes with the same effective initialization policy:

- `init.mode = robust`
- `init.gamma = 0.0`
- `init.sigma_scale = 0.5`
- `init.sigma_floor in {0.01, 0.1}`

This production-path probe uses the less invasive healthy winner:

- `init.sigma_floor = 0.01`

## Scope

Single row only:

- cutoff: `20210123`
- family: `exdqlm_multivar_keep`
- manuscript label: `exAL-M-T1`
- active quantile subset: `q=0.50`

## Files

- sidecar template:
  - `config/he2_bayesian_publication_relaunch_median_q50_probe_20260511.template.yaml`
- batch recipe:
  - `config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_q50_median_init_probe_20260511.yaml`
- builder:
  - `scripts/build_he2_bayesian_publication_relaunch_configs.py`
- validator:
  - `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`
- launcher:
  - `scripts/launch_he2_bayesian_publication_relaunch.py`

## Override policy

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
```

All other median stabilization settings remain those already frozen in the current model code.

## Validation expectations

The scoped prelaunch validator should:

- build the canonical shared bundle
- regenerate the single-row config and audits
- run family and cutoff shared-input smokes
- run multivariate quantile fit smoke at `q=0.50`
- run multivariate quantile full-pipeline smoke at `q=0.50`
- skip NDLM and univariate quantile smokes because those families are intentionally absent from the scoped selection

## Commands

Build + validate:

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_median_q50_probe_20260511.template.yaml \
  --batch-file config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_q50_median_init_probe_20260511.yaml
```

Launch after validation:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_median_q50_probe_20260511.template.yaml \
  --batch-file config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_q50_median_init_probe_20260511.yaml \
  --skip-validate
```

## Acceptance gate

Promote to the next step only if the production-path probe shows:

- no non-finite gamma/sigma failure
- no Hessian failure
- real update progress beyond screening behavior
- no state explosion
- successful `fit -> post -> validate -> report` completion for the single row

## Next step after success

If this row completes cleanly, rerun the full `20210123 exdqlm_multivar_keep` family with all 7 quantiles, keeping the median override only on `q50`.

# HE2 Bayesian Relaunch Batch Operations

Date: 2026-05-10

## Purpose

This runbook defines the **operator workflow** for the HE2 Bayesian relaunch after the canonical `GDPC1` integration.

It exists to keep the relaunch campaign:

- reproducible
- restartable
- spec-preserving
- batch-selectable
- auditable before any real queue launch

This document is intentionally operational. It describes how to build, validate, reset, scope, and launch the campaign without relying on memory or one-off shell history.

## Source files

- template: `config/he2_bayesian_publication_relaunch_20260510.template.yaml`
- builder: `scripts/build_he2_bayesian_publication_relaunch_configs.py`
- validator: `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`
- launcher: `scripts/launch_he2_bayesian_publication_relaunch.py`
- reset helper: `scripts/reset_he2_bayesian_publication_relaunch_state.py`
- shared bundle builder: `scripts/build_multimodel_v8_histfix_bundles.py`
- tracker: `repro/run/HE2_BAYESIAN_FULL_RELAUNCH_TRACKER_20260510.md`

## Campaign contract

The relaunch campaign preserves the row-level specifications that produced the current CRPS table while replacing the shared input lineage.

The preserved row-level contract includes:

- cutoff date
- model family / manuscript label
- NDLM vs quantile family
- transfer mode
- discount-factor block
- likelihood mode
- multivariate epsilon / `c_factor` settings
- quantile grid
- sample-count settings

The replaced shared-input contract includes:

- USGS history from `1987-05-29` through the cutoff
- retrospective GloFAS and NWS history through the cutoff
- deterministic future precip/soil handoff bundle
- canonical `GDPC1` supplied through the existing `PCA` compatibility alias

## Validator smoke budget

The prelaunch validator uses the **same model code paths and same shared-input contract** as the real relaunch, but it is allowed to apply a lighter smoke budget so the gate finishes on a practical timescale.

Those smoke-only fit overrides live in the template under:

- `validation.smoke_fit_overrides`

Current smoke budget:

- quantile multivariate: `min_update_iters = 3`, `min_total_iters = 10`, `max_iter = 10`, `n_samp = 512`
- quantile univariate: `min_update_iters = 3`, `min_total_iters = 10`, `max_iter = 10`, `n_samp = 512`

Validation routing:

- the heavy multivariate quantile path is required at the **fit smoke** level
- the quantile **full-pipeline** smoke is routed through the univariate families so we still validate `fit -> post -> validate -> report` without paying the multivariate fit cost twice

These overrides apply only to validator-generated temporary smoke configs. They do **not** change:

- the frozen production spec recorded in `frozen_spec_manifest.csv`
- the generated relaunch configs under `control/generated_configs`
- the real queue launch settings

## Selection controls

The builder, validator, and launcher all accept the same selection surface.

### Filters

- `--cutoffs`
- `--families`
- `--manuscript-labels`
- `--run-ids`
- `--model-classes`
- `--quantiles`
- `--batch-file`
- `--profile`

### Resource overrides

- `--fit-parallel-workers`
- `--mc-cores`

### Batch-file config patch overrides

Batch files can also carry explicit config overrides so we can run a controlled probe without editing the campaign template or hand-editing a generated config.

Supported batch-file override blocks:

- `overrides.common_config_patch`
- `overrides.row_config_patches`

`common_config_patch` applies to every selected row in that batch.

`row_config_patches` applies only to rows that match the optional selectors:

- `cutoff`
- `family`
- `manuscript_label`
- `source_run_id`

Each matching row receives the nested `config_patch` via recursive merge before the frozen manifest is written.

This means the relaunch remains auditable:

- the generated run config records the applied patch in `debug_he2_publication_relaunch`
- `frozen_spec_manifest.csv` records:
  - `config_patch_applied`
  - `config_patch_source`
  - `config_patch_json`

Use this for targeted discount / epsilon probes and other narrowly scoped production experiments.

### Supported model classes

- `ndlm`
- `quantile_univariate`
- `quantile_multivariate`

### Quantile selection

Quantiles can be provided as any of:

- `0.05`
- `5`
- `q05`
- `q=0.05`

The relaunch tooling normalizes these to fractions in `(0,1)` and renders labels like `05`, `20`, `95` in the frozen audits.

## Profiles

The template defines queue/resource presets.

### `default`

- uses template queue settings
- uses full quantile grid unless overridden
- no forced single-core limits
- for quantile families with multiple active quantiles, defaults to:
  - `fit_parallel_workers = number of active quantiles`
  - `mc_cores = fit_parallel_workers`

This is the canonical production behavior for multi-quantile relaunches unless an explicit profile or CLI override asks for fewer workers.

### `serial_debug`

- `ordinary_max_concurrent = 1`
- `heavy_cutoff_max_concurrent = 1`
- `fit_parallel_workers = 1`
- `mc_cores = 1`
- default quantile subset: `0.05`

Use this for targeted validation or debugging.

### `single_core_full`

- `ordinary_max_concurrent = 1`
- `heavy_cutoff_max_concurrent = 1`
- `fit_parallel_workers = 1`
- `mc_cores = 1`

Use this when you want the full selected matrix but conservative per-run resource usage.

## Builder outputs

The builder writes the relaunch matrix and the frozen audits to:

- `matrix_plan.csv`
- `selection_summary.csv`
- `dependency_preservation.csv`
- `frozen_spec_manifest.csv`
- `frozen_spec_manifest.json`
- `cutoff_bundle_audit.csv`
- `cutoff_bundle_audit.json`
- `batch_request_snapshot.yaml`
- `matrix_metadata.yaml`
- `campaign_snapshot.yaml`
- `he2_publication_relaunch_scope.md`
- `launch_settings.env`

## What the new audits mean

### `frozen_spec_manifest.csv`

One row per selected run config. This is the machine-readable freeze of the row-level production spec.

It records, among other fields:

- source publication run/config
- likelihood mode
- transfer mode
- discount factors
- `lambda`
- `lam1`, `lam2`
- `n_samp`
- full quantile grid
- active quantile subset
- effective fit workers / MC cores
- fit/model-prior epsilon and `c_factor`

### `cutoff_bundle_audit.csv`

One row per selected cutoff. This is the machine-readable freeze of the shared cutoff bundle.

It records:

- retrospective start/end/row counts
- duplicate and missing date counts
- GloFAS source/product identifiers
- NWS primary/tail-fill identifiers and selection rule
- USGS source path
- deterministic forecast handoff metadata
- GDPC alias path and date coverage
- legacy log-repair counts

## Required prelaunch checks

Before a real queue launch, require all of the following.

1. `matrix_plan.csv` exists and matches the requested scope.
2. `frozen_spec_manifest.csv` exists and preserves the intended production spec.
3. `cutoff_bundle_audit.csv` exists and confirms shared-input lineage per cutoff.
4. The validator passes:
   - bundle build
   - within-cutoff bundle alignment
   - family data-prep smokes
   - cutoff data-prep smokes
   - NDLM fit smoke
   - quantile fit smoke
   - NDLM full-pipeline smoke
   - quantile full-pipeline smoke
5. No live relaunch controller is still running from a prior attempt.
6. If relaunch state is stale, archive it with the reset helper before queue launch.

## Standard command patterns

### 1. Build the full 45-row matrix

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_20260510.template.yaml
```

### 2. Build all 9 models for one cutoff

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_20260510.template.yaml \
  --cutoffs 20211112
```

### 3. Build all NDLM rows across all cutoffs

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_20260510.template.yaml \
  --model-classes ndlm
```

### 4. Build all quantile rows across all cutoffs

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_20260510.template.yaml \
  --model-classes quantile_univariate quantile_multivariate
```

### 5. Build one manuscript label across all cutoffs

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_20260510.template.yaml \
  --manuscript-labels exAL-M-T1
```

### 6. Build one single-row debug batch with one quantile

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_20260510.template.yaml \
  --cutoffs 20210123 \
  --manuscript-labels exAL-M-T1 \
  --quantiles 0.05 \
  --fit-parallel-workers 1 \
  --mc-cores 1
```

### 7. Build a row-specific discount probe from a batch file

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_20260510.template.yaml \
  --batch-file config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_discount_probe_20260510.yaml
```

That batch file can target a single row and patch only the desired nested fields, for example:

- `df_s1`
- `df_s2`
- `df_s67`
- `df_discrep`
- `df_covs`

## Validation command patterns

### 1. Scoped debug validation

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_20260510.template.yaml \
  --cutoffs 20210123 \
  --families ndlm_univar_keep exdqlm_multivar_keep \
  --profile serial_debug
```

### 2. Full prelaunch validation

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_20260510.template.yaml
```

## Reset and restart

Use the reset helper when the matrix directory already contains stale status, stale compare outputs, or partial run directories from an old campaign attempt.

```bash
python3 scripts/reset_he2_bayesian_publication_relaunch_state.py \
  --template config/he2_bayesian_publication_relaunch_20260510.template.yaml
```

The helper archives:

- `matrix_status.csv`
- `queue.log`
- `controller_state/`
- selected run directories
- selected compare output directories

It writes:

- `reset_summary.json`
- `RESET_SUMMARY.md`

under `control/restart_resets/<timestamp>/`.

## Current status before real queue launch

The relaunch tooling is now strong enough to scope, audit, reset, and validate batches reproducibly.

However, a real queue launch should still be treated as **blocked** until the quantile smoke issue is resolved or explicitly waived.

Current blocker captured by the validator:

- validator outdir:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_bayesian_publication_relaunch_20260510/control/prelaunch_validation_20260510T210212Z`
- failing smoke row:
  - `exdqlm_multivar_keep`, cutoff `20210123`, quantile `q=05`
- terminating error:
  - `FFF_list iter=8[[1]] contains non-finite values`

A direct univariate probe at the same cutoff and quantile also failed, so this should be treated as a real prelaunch blocker rather than a validator artifact.

## Real queue launch

After validation passes, launch via the wrapper so the builder/validator/queue settings stay coupled.

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_20260510.template.yaml \
  --reset-state
```

For a non-launch dry preview:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_20260510.template.yaml \
  --dry-run
```

## Recommended operating sequence

1. Build the desired scope.
2. Inspect `selection_summary.csv`.
3. Inspect `frozen_spec_manifest.csv`.
4. Inspect `cutoff_bundle_audit.csv`.
5. Run the validator on the same scope/profile.
6. If stale runtime state exists, reset it.
7. Launch the queue.
8. Monitor `queue.log`, `matrix_status.csv`, and controller state.

## Notes on flexibility

This setup is intentionally flexible for tuning and debugging.

You can now do all of the following without editing code:

- one cutoff, all 9 rows
- one family across all cutoffs
- all NDLM rows only
- all quantile rows only
- one manuscript label across cutoffs
- one exact run id
- a one-quantile debug subset
- single-core launches via profile or explicit overrides

The point is to keep the campaign reproducible while still making it easy to run small, targeted experiments when we need them.

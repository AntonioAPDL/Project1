# exAL-M-T1 Discount Grid Runbook

## Purpose

This campaign tests whether `exAL-M-T1` forecast-window CRPS changes when we keep the current HE-table best-epsilon source for each cutoff, but vary only the `exdqlm_multivar.state_evolution` discount-factor block.

The experiment is intentionally isolated from the published HE2 and earlier discount-probe artifacts. This exact-input relaunch preserves the selected source run's full `inputs/shared` snapshot byte-for-byte before fit, so forecast-window PPT/SOIL covariates, deterministic-climate futures, and `covariate_features.csv` remain identical to the HE-table source run.

It writes to:

- Artifact root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_exalm_t1_discount_grid_exact_20260424`
- Matrix dir: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_exalm_t1_discount_grid_exact_20260424/control/exalm_t1_discount_grid_exact_v1`
- Generated configs: `config/unified_runs_exalm_t1_discount_grid_exact_20260424/`

## Scope

- Model family: `exdqlm_multivar_keep`
- Manuscript label: `exAL-M-T1`
- Likelihood: `exal`
- Forecast transfer: `keep`
- Cutoffs: `20210123`, `20211112`, `20211221`, `20220511`, `20221225`
- Discount sets: `set01` through `set09`
- Total planned runs: `45`

## Best-Epsilon Source Contract

Each row inherits the cutoff-specific current HE2 best epsilon from `reports/ndlm_parity_audit/spec_parity_matrix.csv`, then resolves the actual executed `featurecov_cf1_eps_sweep` source run through that compare bundle's `source_provenance.csv`.

| Cutoff | Best Epsilon |
|---|---:|
| `20210123` | `eps360cf1` |
| `20211112` | `eps180cf1` |
| `20211221` | `eps1cf1` |
| `20220511` | `eps180cf1` |
| `20221225` | `eps360cf1` |

Generated configs preserve the corrected proper-featurecov/blended-input contract from the selected source snapshot:

- Fit covariates: `PPT`, `SOIL`, `PCA`
- Deterministic climate: enabled
- Engineered covariates: lags `1,2,3`, squares, and `PPT_x_SOIL`
- USGS daily truth: durable local `usgs_cache_path`
- Exact shared-input preservation: `inputs.shared.exact_source_snapshot_root` points to the selected HE source run's `inputs/shared` tree, and `data_prep_shared` copies that tree directly before validation.
- If the selected HE source run did not preserve `inputs/shared/usgs/usgs_daily.csv`, `data_prep_shared` supplements only that one file from `inputs.fit.usgs_cache_path` so strict post scoring remains reproducible.

## Parallelism Contract

Each run inherits the selected source config's fit parallelism for that cutoff:

- `fit.parallel.mode` is copied from the selected source config
- `fit.parallel.workers` is copied from the selected source config
- `run.threads.mc_cores` is copied from the selected source config

The queue launches at most `4` rows concurrently:

- Peak fit-core budget: source-worker dependent, capped by `4` concurrent rows
- `ordinary_max_concurrent = 4`
- `heavy_cutoff_max_concurrent = 4`
- `heavy_cutoff_blocks_ordinary = false`

## Commands

Build only:

```bash
bash scripts/run_multimodel_v8_exalm_t1_discount_grid.sh
```

Prelaunch validation:

```bash
python3 scripts/validate_exalm_t1_discount_grid_prelaunch.py \
  --config config/multimodel_v8_exalm_t1_discount_grid_exact_20260424.template.yaml
```

Launch:

```bash
bash scripts/run_multimodel_v8_exalm_t1_discount_grid.sh --launch
```

Health check:

```bash
python3 scripts/check_multimodel_v8_matrix_health.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_exalm_t1_discount_grid_exact_20260424/control/exalm_t1_discount_grid_exact_v1 \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_exalm_t1_discount_grid_exact_20260424
```

## Acceptance Gates

- Builder emits `45` configs and `45` matrix rows.
- Prelaunch validation passes config sanity, selection parity, generated-config contract checks, and representative data-prep smoke runs.
- Representative smoke runs reproduce the selected HE source `inputs/shared` snapshot with exact recursive file-hash equality.
- Queue completes with `45 / 45` run manifests at report `pass`.
- Compare bundles exist for every `(cutoff, discount_set, source_epsilon)` cell.
- Post-run CRPS/input-health artifacts must be inspected for numerical failures. In particular, huge finite CRPS values, infinite draw standard deviations, or enormous draw magnitudes must be treated as numerical failures even if the run-level manifest says `pass`.

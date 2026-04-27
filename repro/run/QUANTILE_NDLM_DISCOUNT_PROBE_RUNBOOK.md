# Quantile NDLM-Discount Probe

This runbook defines the corrected, non-destructive experiment scaffold for `multimodel_v8_quantile_featurecov_ndlm_discount_probe_20260422`.

## Goal

- rerun only the 6 quantile-family rows used in the HE2 CRPS table
- preserve the current HE2 winning source selection cutoff-by-cutoff
- keep the relaunch fully on the corrected proper-featurecov contract
  - `PPT`, `SOIL`, `PCA`
  - deterministic blended climate enabled
  - engineered covariates enabled
  - `PPT_sq`, `SOIL_sq`, `PPT_x_SOIL`, `PPT_lag1..3`, `SOIL_lag1..3`
- replace only the AL/exAL state-evolution discount block with the corrected-NDLM-style block
- run one CPU core per quantile model
  - `fit_parallel_workers = 7` per row
- keep the experiment isolated from existing campaigns

## Why This Supersedes The Earlier Draft

The earlier draft traced the parity matrix all the way back to the legacy selected source configs, which incorrectly carried forward the old `ELI/ONI/PPT/SOIL/PCA` lineage with deterministic climate and engineered covariates off.

This corrected scaffold resolves the actual source rows this way:

- multivariate AL/exAL rows:
  - use the HE2 best-epsilon selections from `spec_parity_matrix.csv`
  - but resolve the source config from the executed `source_run` listed in the selected compare bundle `source_provenance.csv`
- univariate AL/exAL rows:
  - use the finished `univar_featurecov_he2_v1` rerun outputs directly

So the new relaunch is consistent with the proper forecast blend, proper inputs, and proper covariates.

## Scientific Contract

- Families in scope:
  - `exdqlm_multivar_keep`
  - `exdqlm_multivar_drop`
  - `dqlm_multivar_al_keep`
  - `dqlm_multivar_al_drop`
  - `exdqlm_univar`
  - `dqlm_univar_al`
- Source-selection authority:
  - `reports/ndlm_parity_audit/spec_parity_matrix.csv` for the multivariate best-epsilon choices
  - `multimodel_v8_univar_featurecov_he2_rerun_20260422` for the univariate HE2 corrected rows
- Compare-bundle authority:
  - the corrected postfix NDLM compare bundles from `multimodel_v8_ndlm_featurecov_rerun_postfix_20260421`

The resulting compare bundles will therefore hold:

- corrected postfix NDLM rows
- raw ensembles
- newly rerun quantile rows with NDLM-style discounts

## Discount Override Contract

Underlying model keys affected:

- `models.exdqlm_multivar.state_evolution`
- `models.exdqlm_univar.state_evolution`

Applied values:

- `df_t = 0.99999999`
- `df_s1 = 0.99999999`
- `df_s2 = 0.99999999`
- `df_s67 = 0.99999999`
- `lambda = 0.97`
- `df_trans = 0.9999999`
- `df_covs = 0.99999999`
- multivar only: `df_discrep = 0.99999999`

Everything else is preserved from the current HE2 source config, including:

- likelihood mode
- transfer mode
- best-epsilon lineage for the multivariate rows
- corrected proper-featurecov univariate contract

## Queue Contract

- `ordinary_max_concurrent = 4`
- `fit_parallel_workers = 7` for every row
- `heavy_cutoff_max_concurrent = 4`
- `heavy_cutoff_blocks_ordinary = false`
- `poll_seconds = 15`

This runs in batches of 4 rows at a time while still honoring the one-core-per-quantile requirement, for a peak fit budget of `28` cores.

## Build And Validate

```bash
python3 scripts/build_multimodel_v8_quantile_ndlm_discount_probe_matrix_configs.py \
  --config config/multimodel_v8_quantile_ndlm_discount_probe_20260422.template.yaml

python3 scripts/validate_quantile_ndlm_discount_probe_prelaunch.py \
  --config config/multimodel_v8_quantile_ndlm_discount_probe_20260422.template.yaml
```

## Launch When Ready

```bash
bash scripts/run_multimodel_v8_quantile_ndlm_discount_probe.sh \
  --config config/multimodel_v8_quantile_ndlm_discount_probe_20260422.template.yaml \
  --launch
```

## Expected Outputs

- a 30-row matrix:
  - 5 cutoffs
  - 6 quantile families
- generated configs under `config/unified_runs_quantile_featurecov_ndlm_discount_probe_20260422/`
- matrix metadata and selection summary under the experiment `control/` tree
- compare bundles that replace all 6 quantile rows against the corrected postfix NDLM baseline

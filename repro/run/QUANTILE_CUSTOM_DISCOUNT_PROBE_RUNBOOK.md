# Quantile Custom-Discount Probe

This runbook defines a clean, isolated quantile sensitivity batch using the exact HE row selection and the user-specified discount factors.

## Scope

- same HE quantile panel as the completed apples-to-apples comparison
  - `6` families
  - `5` cutoffs
  - `30` row-cutoff cells total
- same proper-featurecov / blended-input contract
  - `PPT`, `SOIL`, `PCA`
  - deterministic blended climate enabled
  - engineered `PPT_sq`, `SOIL_sq`, `PPT_x_SOIL`, `PPT_lag1..3`, `SOIL_lag1..3`
- same published HE row selection
  - best-epsilon multivariate rows
  - corrected univariate featurecov rows

## Goal

Test the user-requested AL/exAL discount block while changing nothing else in the current HE quantile panel.

This means:

- same cutoff
- same family
- same best-epsilon lineage for multivariate rows
- same corrected univariate lineage
- same proper forecast blend
- same proper covariates
- same one-core-per-quantile fit contract

## Applied Discount Profile

Univariate AL/exAL:

- `df_t = 0.99999`
- `df_s1 = 0.9995`
- `df_s2 = 0.9995`
- `df_s67 = 0.9999`
- `lambda = 0.97`
- `df_trans = 0.9999999`
- `df_covs = 0.9999`

Multivariate AL/exAL:

- `df_t = 0.99999`
- `df_s1 = 0.9995`
- `df_s2 = 0.9995`
- `df_s67 = 0.9999`
- `df_discrep = 0.997`
- `lambda = 0.97`
- `df_trans = 0.9999999`
- `df_covs = 0.9999`

## Queue Contract

- `ordinary_max_concurrent = 4`
- `fit_parallel_workers = 7` for every row
- one core per quantile model
- peak fit budget: `28` cores
- fresh artifact root, so no overwrite risk to the finished HE reruns or prior probes

## Build And Validate

```bash
python3 scripts/build_multimodel_v8_quantile_ndlm_discount_probe_matrix_configs.py \
  --config config/multimodel_v8_quantile_featurecov_custom_discount_probe_20260422.template.yaml

python3 scripts/validate_quantile_ndlm_discount_probe_prelaunch.py \
  --config config/multimodel_v8_quantile_featurecov_custom_discount_probe_20260422.template.yaml
```

## Launch Later If Wanted

```bash
bash scripts/run_multimodel_v8_quantile_ndlm_discount_probe.sh \
  --config config/multimodel_v8_quantile_featurecov_custom_discount_probe_20260422.template.yaml \
  --launch
```

## Expected Outputs

- generated configs under `config/unified_runs_quantile_featurecov_custom_discount_probe_20260422/`
- control tree under:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_quantile_featurecov_custom_discount_probe_20260422/control/quantile_featurecov_custom_discount_probe_v1`
- compare bundles that swap only the 6 HE quantile rows against the corrected NDLM baseline

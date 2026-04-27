# Quantile Hybrid-Discount Probe

This runbook defines a second, non-destructive quantile discount experiment for the same HE apples-to-apples panel.

## Scope

- same HE quantile panel as the completed comparison:
  - `6` families
  - `5` cutoffs
  - `30` total rows
- same proper-featurecov / blended-input contract:
  - `PPT`, `SOIL`, `PCA`
  - deterministic blended climate enabled
  - engineered `PPT_sq`, `SOIL_sq`, `PPT_x_SOIL`, `PPT_lag1..3`, `SOIL_lag1..3`
- same published HE row selection:
  - best-epsilon multivariate rows
  - corrected univariate featurecov rerun rows

## Goal

Test a midpoint discount block after the first NDLM-tight probe showed:

- the `T0` drop rows sometimes improved materially
- the `T1` keep rows usually degraded

This probe changes only the discount components that differ between the published HE AL/exAL rows and the corrected NDLM block:

- `df_s1`
- `df_s2`
- `df_s67`
- `df_covs`
- multivar only: `df_discrep`

Everything else is preserved from the current HE source rows.

## Hybrid Midpoint Profile

Applied overrides:

- univariate:
  - `df_s1 = 0.99999`
  - `df_s2 = 0.99999`
  - `df_s67 = 0.99999`
  - `df_covs = 0.999999`
- multivariate:
  - `df_s1 = 0.99999`
  - `df_s2 = 0.99999`
  - `df_s67 = 0.99999`
  - `df_covs = 0.999999`
  - `df_discrep = 0.99999`

Preserved from the source rows:

- `df_t`
- `lambda`
- `df_trans`
- likelihood mode
- transfer mode
- best-epsilon source selection
- proper blended forecast / covariate contract

## Queue Contract

- `ordinary_max_concurrent = 4`
- `fit_parallel_workers = 7` for every row
- one core per quantile model
- peak fit budget: `28` cores
- fresh artifact root, no overwrite of prior experiments

## Build And Validate

```bash
python3 scripts/build_multimodel_v8_quantile_ndlm_discount_probe_matrix_configs.py \
  --config config/multimodel_v8_quantile_featurecov_hybrid_discount_probe_20260422.template.yaml

python3 scripts/validate_quantile_ndlm_discount_probe_prelaunch.py \
  --config config/multimodel_v8_quantile_featurecov_hybrid_discount_probe_20260422.template.yaml
```

## Launch Later If Wanted

```bash
bash scripts/run_multimodel_v8_quantile_ndlm_discount_probe.sh \
  --config config/multimodel_v8_quantile_featurecov_hybrid_discount_probe_20260422.template.yaml \
  --launch
```

## Expected Outputs

- generated configs under `config/unified_runs_quantile_featurecov_hybrid_discount_probe_20260422/`
- control tree under:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_quantile_featurecov_hybrid_discount_probe_20260422/control/quantile_featurecov_hybrid_discount_probe_v1`
- compare bundles that swap only the 6 quantile HE rows against the corrected NDLM baseline

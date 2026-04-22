# NDLM Featurecov Postfix Rerun Workflow

Last updated: 2026-04-21  
Status: active

## Purpose

Relaunch the full `15`-row NDLM featurecov campaign after the multivariate predictive sigma-row bug fix, so the NDLM manuscript values can be regenerated from the corrected post path.

## Why This Is Needed

The earlier corrected NDLM rerun used the right shared featurecov input contract, but the post-correction reaudit found that the multivariate NDLM post predictor was incorrectly mixing `nws` and `glofas` sigma draws into the `usgs` predictive sampler.

That bug has now been fixed in:

- [R/environmetrics/02_helpers_core.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/02_helpers_core.R)

The previous rerun results should therefore be treated as provisional.

## Main Surfaces

- Template:
  [multimodel_v8_ndlm_featurecov_rerun_postfix_20260421.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421.template.yaml)
- Launcher:
  [launch_multimodel_v8_ndlm_featurecov_rerun.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/launch_multimodel_v8_ndlm_featurecov_rerun.py)
- Runtime root:
  [/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421)

## Prelaunch Gate

Passed evidence:

- [prelaunch_validation_summary.json](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/control/prelaunch_validation_20260421T222408Z/prelaunch_validation_summary.json)

What it covered:

- matrix build
- Python regression tests
- R regression tests
- smoke runs for:
  - `ndlm_main_keep`
  - `ndlm_main_drop`
  - `ndlm_univar_keep`

## Launch Command

```bash
python3 scripts/launch_multimodel_v8_ndlm_featurecov_rerun.py \
  --template config/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421.template.yaml
```

## Current Live State

- queue controller running in background
- controller state:
  - [controller.pid](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/control/ndlm_featurecov_v1/controller_state/controller.pid)
  - [last_launch.json](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/control/ndlm_featurecov_v1/controller_state/last_launch.json)
- queue log:
  [queue.log](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/control/ndlm_featurecov_v1/queue.log)
- matrix state:
  [matrix_status.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/control/ndlm_featurecov_v1/matrix_status.csv)

## Latest Operational Read

At the latest documented check:

- `20210123`: complete
- `20211112`: complete
- `20211221 / ndlm_main_keep`: active
- `20211221 / ndlm_main_drop`: active

This means the postfix rerun is already progressing beyond setup and validation and is actively regenerating the multivariate NDLM rows under the corrected predictive path.

## Expected Next Use

When the campaign completes:

1. extract the new NDLM forecast-window CRPS values
2. compare them to the provisional NDLM values currently in HE2
3. update the corrections repo with the refreshed NDLM rows

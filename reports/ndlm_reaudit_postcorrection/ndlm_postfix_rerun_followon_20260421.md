# NDLM Post-Correction Reaudit: Follow-On Rerun Note

Date: 2026-04-21  
Status: in progress

## Purpose

The post-correction reaudit found a concrete multivariate NDLM predictive-sampling bug. This note records the follow-on rerun setup created to regenerate the `15` NDLM rows from the fixed code path.

## New Template

- [multimodel_v8_ndlm_featurecov_rerun_postfix_20260421.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421.template.yaml)

Key campaign identifiers:

- `campaign_id = multimodel_v8_ndlm_featurecov_rerun_postfix_20260421`
- `spec_id = ndlm_featurecov_v1_postfix`

## Intended Scope

- `15` rows
- families:
  - `ndlm_main_keep`
  - `ndlm_main_drop`
  - `ndlm_univar_keep`
- cutoffs:
  - `20210123`
  - `20211112`
  - `20211221`
  - `20220511`
  - `20221225`

## Current Runtime Root

- [/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421)

## Current State

The rerun launch was started through:

- [launch_multimodel_v8_ndlm_featurecov_rerun.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/launch_multimodel_v8_ndlm_featurecov_rerun.py)

using the new postfix template.

At the time this note was written:

- matrix build had completed
- prelaunch validation had started
- the `ndlm_main_keep` smoke run was in `fit`

Evidence:

- [build_stdout.log](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/control/prelaunch_validation_20260421T222408Z/build_stdout.log)
- [run_manifest.yaml](</data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/control/prelaunch_validation_20260421T222408Z/smoke_runs/ndlm_main_keep/smoke_ndlm_main_keep/run_manifest.yaml>)
- [fit_stage.log](</data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421/control/prelaunch_validation_20260421T222408Z/smoke_runs/ndlm_main_keep/smoke_ndlm_main_keep/fit/logs/fit_stage.log>)

## Read

This follow-on rerun should be treated as the practical remediation path that follows the completed reaudit. The audit conclusion itself is already complete and does not depend on this rerun finishing.

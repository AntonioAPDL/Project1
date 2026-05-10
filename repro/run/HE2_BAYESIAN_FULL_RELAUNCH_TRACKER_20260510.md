# HE2 Bayesian Full Relaunch Tracker

Date: 2026-05-10

## Purpose

This tracker freezes the prelaunch contract for the **full 45-row HE2 Bayesian relaunch** after the canonical GDPC1 replacement.

The goal is to preserve the current published row-level model specifications while replacing the shared-input lineage so that:

- every row uses the canonical `GDPC1` covariate through the existing `PCA` alias path
- every row within a cutoff shares the **same** observational and forecast-window bundle
- retrospective support runs from `1987-05-29` through the cutoff for every row
- prelaunch validation proves the cutoff bundle is hash-identical across the 9 rows

## Source of truth

- publication manifest: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
- within-cutoff alignment audit: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/he2_bayesian_publication_alignment.csv`
- historical-support audit: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/historical_support_audit_20260507/historical_support_audit.csv`

## Workload summary

- row launches: `45`
- quantile row launches: `30`
- NDLM row launches: `15`
- quantile submodels: `210`
- NDLM submodels: `15`
- total fitted submodels: `225`

## Current publication freeze by campaign lineage

| Campaign lineage | Rows |
|---|---:|
| `exalm_t1_discount_grid_exact_20260424:set09_override` | `1` |
| `featurecov_cf1_eps_sweep_20260416` | `19` |
| `ndlm_featurecov_rerun_postfix_20260421` | `15` |
| `univar_featurecov_he2_rerun_20260422` | `10` |

## Why all 45 rows need relaunch

1. The canonical climate factor is now `GDPC1`, replacing the old frozen PCA-like artifact.
2. The current publication rows still point at four older campaign lineages whose builders rewrite inputs from older `resolved_config.yaml` snapshots.
3. Three cutoffs (`20210123`, `20211112`, `20221225`) still use short-history effective retrospective support across all 9 rows within the cutoff.
4. Even the two full-history cutoffs (`20211221`, `20220511`) still need reruns so that the fit covariate lineage is the canonical GDPC-backed one and the within-cutoff bundles are rebuilt under one explicit contract.

## Cutoff-level bundle status

| Cutoff | Rows | Full 1987 history currently? | Required action |
|---|---:|---|---|
| `20210123` | `9` | `No` | `rebuild_full_history_and_refresh_GDPC` |
| `20211112` | `9` | `No` | `rebuild_full_history_and_refresh_GDPC` |
| `20211221` | `9` | `Yes` | `refresh_GDPC_only` |
| `20220511` | `9` | `Yes` | `refresh_GDPC_only` |
| `20221225` | `9` | `No` | `rebuild_full_history_and_refresh_GDPC` |

## Builder surfaces that must be rewired before launch

- `scripts/build_multimodel_v8_featurecov_cf1_eps_matrix_configs.py`
- `scripts/build_multimodel_v8_all9_feature_matrix_configs.py`
- `scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py`

These builders currently materialize each run by copying fit/forecast/covariate paths from an older `selected_source_config` / `resolved_config.yaml` snapshot.

Relevant functions:

- `_rewrite_inputs_from_source_snapshot(...)`
- `_rewrite_fit_covariates_from_source_snapshot(...)`

For the full relaunch, those rewrites should target a **new canonical per-cutoff shared bundle**, not the old source-run snapshots.

## Required canonical shared-bundle contract per cutoff

Every one of the 9 rows within a cutoff must point to the same versions of:

- `parameters.txt`
- `retros.csv`
- `nws_forecast.csv`
- `glofas_forecast.csv`
- `usgs_daily.csv`
- `cov_01_PPT.csv`
- `cov_02_SOIL.csv`
- `cov_03_PCA.csv` or `cov_05_PCA.csv` as the compatibility alias to canonical `GDPC1`
- `covariate_features.csv`
- deterministic climate future precip bundle
- deterministic climate future soil bundle

## Prelaunch validation gates

1. Per cutoff, hash all shared-input artifacts above across the 9 row configs and require `all_equal = True`.
2. Require `effective_common_start = 1987-05-29` in `inputs/shared/data_start_filter_summary.txt` for every row.
3. Require fit covariates to resolve to `PPT|SOIL|PCA`, where `PCA` is now the canonical `GDPC1` compatibility alias.
4. Require deterministic-climate and engineered-covariate feature flags to remain enabled exactly as in the publication freeze.
5. Require one smoke run per family against the new shared bundle contract before launching the full matrix.

## Row-level relaunch matrix

| Cutoff | Label | Family | Campaign | Current CRPS | Current start | Full history? | Selected spec | Submodels |
|---|---|---|---|---:|---|---|---|---:|
| `01/23/2021` | `AL-M-T0` | `dqlm_multivar_al_drop` | `featurecov_cf1_eps_sweep_20260416` | `0.3267` | `2018-02-08` | `False` | `eps30cf1` | `7` |
| `01/23/2021` | `AL-M-T1` | `dqlm_multivar_al_keep` | `featurecov_cf1_eps_sweep_20260416` | `0.1604` | `2018-02-08` | `False` | `eps180cf1` | `7` |
| `01/23/2021` | `AL-U-T1` | `dqlm_univar_al` | `univar_featurecov_he2_rerun_20260422` | `0.2449` | `2018-02-08` | `False` | `univar_featurecov_he2_v1` | `7` |
| `01/23/2021` | `N-M-T0` | `ndlm_main_drop` | `ndlm_featurecov_rerun_postfix_20260421` | `0.5311` | `2018-02-08` | `False` | `ndlm_featurecov_v1_postfix` | `1` |
| `01/23/2021` | `N-M-T1` | `ndlm_main_keep` | `ndlm_featurecov_rerun_postfix_20260421` | `0.5275` | `2018-02-08` | `False` | `ndlm_featurecov_v1_postfix` | `1` |
| `01/23/2021` | `N-U-T1` | `ndlm_univar_keep` | `ndlm_featurecov_rerun_postfix_20260421` | `0.3520` | `2018-02-08` | `False` | `ndlm_featurecov_v1_postfix` | `1` |
| `01/23/2021` | `exAL-M-T0` | `exdqlm_multivar_drop` | `featurecov_cf1_eps_sweep_20260416` | `0.3292` | `2018-02-08` | `False` | `eps30cf1` | `7` |
| `01/23/2021` | `exAL-M-T1` | `exdqlm_multivar_keep` | `featurecov_cf1_eps_sweep_20260416` | `0.1569` | `2018-02-08` | `False` | `eps360cf1` | `7` |
| `01/23/2021` | `exAL-U-T1` | `exdqlm_univar` | `univar_featurecov_he2_rerun_20260422` | `0.2229` | `2018-02-08` | `False` | `univar_featurecov_he2_v1` | `7` |
| `11/12/2021` | `AL-M-T0` | `dqlm_multivar_al_drop` | `featurecov_cf1_eps_sweep_20260416` | `2.2435` | `2018-11-28` | `False` | `eps30cf1` | `7` |
| `11/12/2021` | `AL-M-T1` | `dqlm_multivar_al_keep` | `featurecov_cf1_eps_sweep_20260416` | `0.0391` | `2018-11-28` | `False` | `eps180cf1` | `7` |
| `11/12/2021` | `AL-U-T1` | `dqlm_univar_al` | `univar_featurecov_he2_rerun_20260422` | `0.1493` | `2018-11-28` | `False` | `univar_featurecov_he2_v1` | `7` |
| `11/12/2021` | `N-M-T0` | `ndlm_main_drop` | `ndlm_featurecov_rerun_postfix_20260421` | `0.0565` | `2018-11-28` | `False` | `ndlm_featurecov_v1_postfix` | `1` |
| `11/12/2021` | `N-M-T1` | `ndlm_main_keep` | `ndlm_featurecov_rerun_postfix_20260421` | `0.0722` | `2018-11-28` | `False` | `ndlm_featurecov_v1_postfix` | `1` |
| `11/12/2021` | `N-U-T1` | `ndlm_univar_keep` | `ndlm_featurecov_rerun_postfix_20260421` | `0.2486` | `2018-11-28` | `False` | `ndlm_featurecov_v1_postfix` | `1` |
| `11/12/2021` | `exAL-M-T0` | `exdqlm_multivar_drop` | `featurecov_cf1_eps_sweep_20260416` | `1.2744` | `2018-11-28` | `False` | `eps30cf1` | `7` |
| `11/12/2021` | `exAL-M-T1` | `exdqlm_multivar_keep` | `featurecov_cf1_eps_sweep_20260416` | `0.0284` | `2018-11-28` | `False` | `eps180cf1` | `7` |
| `11/12/2021` | `exAL-U-T1` | `exdqlm_univar` | `univar_featurecov_he2_rerun_20260422` | `0.1506` | `2018-11-28` | `False` | `univar_featurecov_he2_v1` | `7` |
| `12/21/2021` | `AL-M-T0` | `dqlm_multivar_al_drop` | `featurecov_cf1_eps_sweep_20260416` | `0.6511` | `1987-05-29` | `True` | `eps360cf1` | `7` |
| `12/21/2021` | `AL-M-T1` | `dqlm_multivar_al_keep` | `featurecov_cf1_eps_sweep_20260416` | `0.3482` | `1987-05-29` | `True` | `eps1cf1` | `7` |
| `12/21/2021` | `AL-U-T1` | `dqlm_univar_al` | `univar_featurecov_he2_rerun_20260422` | `1.2283` | `1987-05-29` | `True` | `univar_featurecov_he2_v1` | `7` |
| `12/21/2021` | `N-M-T0` | `ndlm_main_drop` | `ndlm_featurecov_rerun_postfix_20260421` | `1.5616` | `1987-05-29` | `True` | `ndlm_featurecov_v1_postfix` | `1` |
| `12/21/2021` | `N-M-T1` | `ndlm_main_keep` | `ndlm_featurecov_rerun_postfix_20260421` | `0.6071` | `1987-05-29` | `True` | `ndlm_featurecov_v1_postfix` | `1` |
| `12/21/2021` | `N-U-T1` | `ndlm_univar_keep` | `ndlm_featurecov_rerun_postfix_20260421` | `1.1768` | `1987-05-29` | `True` | `ndlm_featurecov_v1_postfix` | `1` |
| `12/21/2021` | `exAL-M-T0` | `exdqlm_multivar_drop` | `featurecov_cf1_eps_sweep_20260416` | `0.4720` | `1987-05-29` | `True` | `eps1cf1` | `7` |
| `12/21/2021` | `exAL-M-T1` | `exdqlm_multivar_keep` | `featurecov_cf1_eps_sweep_20260416` | `0.2369` | `1987-05-29` | `True` | `eps1cf1` | `7` |
| `12/21/2021` | `exAL-U-T1` | `exdqlm_univar` | `univar_featurecov_he2_rerun_20260422` | `1.2691` | `1987-05-29` | `True` | `univar_featurecov_he2_v1` | `7` |
| `05/11/2022` | `AL-M-T0` | `dqlm_multivar_al_drop` | `featurecov_cf1_eps_sweep_20260416` | `0.0433` | `1987-05-29` | `True` | `eps30cf1` | `7` |
| `05/11/2022` | `AL-M-T1` | `dqlm_multivar_al_keep` | `featurecov_cf1_eps_sweep_20260416` | `0.0214` | `1987-05-29` | `True` | `eps90cf1` | `7` |
| `05/11/2022` | `AL-U-T1` | `dqlm_univar_al` | `univar_featurecov_he2_rerun_20260422` | `0.0551` | `1987-05-29` | `True` | `univar_featurecov_he2_v1` | `7` |
| `05/11/2022` | `N-M-T0` | `ndlm_main_drop` | `ndlm_featurecov_rerun_postfix_20260421` | `0.0241` | `1987-05-29` | `True` | `ndlm_featurecov_v1_postfix` | `1` |
| `05/11/2022` | `N-M-T1` | `ndlm_main_keep` | `ndlm_featurecov_rerun_postfix_20260421` | `0.0416` | `1987-05-29` | `True` | `ndlm_featurecov_v1_postfix` | `1` |
| `05/11/2022` | `N-U-T1` | `ndlm_univar_keep` | `ndlm_featurecov_rerun_postfix_20260421` | `0.1572` | `1987-05-29` | `True` | `ndlm_featurecov_v1_postfix` | `1` |
| `05/11/2022` | `exAL-M-T0` | `exdqlm_multivar_drop` | `featurecov_cf1_eps_sweep_20260416` | `0.0694` | `1987-05-29` | `True` | `eps30cf1` | `7` |
| `05/11/2022` | `exAL-M-T1` | `exdqlm_multivar_keep` | `featurecov_cf1_eps_sweep_20260416` | `0.0210` | `1987-05-29` | `True` | `eps180cf1` | `7` |
| `05/11/2022` | `exAL-U-T1` | `exdqlm_univar` | `univar_featurecov_he2_rerun_20260422` | `0.0541` | `1987-05-29` | `True` | `univar_featurecov_he2_v1` | `7` |
| `12/25/2022` | `AL-M-T0` | `dqlm_multivar_al_drop` | `featurecov_cf1_eps_sweep_20260416` | `2.2601` | `2020-01-10` | `False` | `eps1cf1` | `7` |
| `12/25/2022` | `AL-M-T1` | `dqlm_multivar_al_keep` | `featurecov_cf1_eps_sweep_20260416` | `0.6186` | `2020-01-10` | `False` | `eps360cf1` | `7` |
| `12/25/2022` | `AL-U-T1` | `dqlm_univar_al` | `univar_featurecov_he2_rerun_20260422` | `1.1038` | `2020-01-10` | `False` | `univar_featurecov_he2_v1` | `7` |
| `12/25/2022` | `N-M-T0` | `ndlm_main_drop` | `ndlm_featurecov_rerun_postfix_20260421` | `2.3485` | `2020-01-10` | `False` | `ndlm_featurecov_v1_postfix` | `1` |
| `12/25/2022` | `N-M-T1` | `ndlm_main_keep` | `ndlm_featurecov_rerun_postfix_20260421` | `0.5363` | `2020-01-10` | `False` | `ndlm_featurecov_v1_postfix` | `1` |
| `12/25/2022` | `N-U-T1` | `ndlm_univar_keep` | `ndlm_featurecov_rerun_postfix_20260421` | `2.1451` | `2020-01-10` | `False` | `ndlm_featurecov_v1_postfix` | `1` |
| `12/25/2022` | `exAL-M-T0` | `exdqlm_multivar_drop` | `featurecov_cf1_eps_sweep_20260416` | `2.3365` | `2020-01-10` | `False` | `eps1cf1` | `7` |
| `12/25/2022` | `exAL-M-T1` | `exdqlm_multivar_keep` | `exalm_t1_discount_grid_exact_20260424:set09_override` | `0.4375` | `2020-01-10` | `False` | `set09` | `7` |
| `12/25/2022` | `exAL-U-T1` | `exdqlm_univar` | `univar_featurecov_he2_rerun_20260422` | `1.1189` | `2020-01-10` | `False` | `univar_featurecov_he2_v1` | `7` |

## Implemented control layer

The relaunch tooling now exposes the following operator-facing controls:

- shared selection filters on builder, validator, and launcher
  - `--cutoffs`
  - `--families`
  - `--manuscript-labels`
  - `--run-ids`
  - `--model-classes`
  - `--quantiles`
  - `--batch-file`
  - `--profile`
- resource overrides
  - `--fit-parallel-workers`
  - `--mc-cores`
- frozen row-level spec audit
  - `frozen_spec_manifest.csv`
- frozen cutoff shared-bundle audit
  - `cutoff_bundle_audit.csv`
- reset/archive path for stale queue state
  - `scripts/reset_he2_bayesian_publication_relaunch_state.py`
- documented batch recipes
  - `repro/run/HE2_BAYESIAN_RELAUNCH_BATCH_OPERATIONS_20260510.md`

These controls are meant to support both the final 45-row campaign and targeted tuning/debug subsets without changing code.

## Current validation blocker

As of `2026-05-10`, the expanded prelaunch validator is correctly **blocking real launch** on the quantile fit path under the new shared-input contract.

Observed failures:

- scoped validator outdir:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_bayesian_publication_relaunch_20260510/control/prelaunch_validation_20260510T210212Z`
- failing smoke row:
  - family: `exdqlm_multivar_keep`
  - cutoff: `20210123`
  - quantile subset: `q=05`
- terminating fit error:
  - `FFF_list iter=8[[1]] contains non-finite values`

Additional direct probe:

- candidate univariate smoke:
  - run root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_bayesian_publication_relaunch_20260510/control/candidate_quantile_smokes/20210123_exdqlm_univar_q05`
- failing row:
  - family: `exdqlm_univar`
  - cutoff: `20210123`
  - quantile subset: `q=05`
- terminating fit error:
  - `univariate fit failed for quantile 0.05 (implementation_mode=legacy_bridge)`

Interpretation:

- the batch-selection / frozen-spec / bundle-audit tooling is working
- NDLM smoke passes under the new bundle contract
- the relaunch campaign should remain blocked until the `20210123` quantile-path instability is understood or the launch policy is updated deliberately

## Recommended next implementation order

1. Build five canonical shared bundles, one per cutoff.
2. Patch the three matrix builders so they consume those bundles instead of older source-run snapshots.
3. Add a dedicated prelaunch validator for the full 45-row relaunch contract.
4. Regenerate the 45-row matrix from the publication freeze and confirm hash-equality within each cutoff.
5. Smoke-test one row per family against the new bundle contract.
6. Only then launch the full 45-row rerun campaign.

## Machine-readable outputs

- CSV: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/publication_replay/he2_bayesian_full_relaunch_matrix_20260510.csv`
- JSON: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/publication_replay/he2_bayesian_full_relaunch_matrix_20260510.json`


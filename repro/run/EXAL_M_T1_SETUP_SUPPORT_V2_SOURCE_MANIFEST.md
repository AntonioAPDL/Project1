# exAL-M-T1 Setup/Support v2 Source Manifest

Date: 2026-05-07

## Purpose

This document freezes the **canonical source contract** for the corrected cutoff-specific setup/input/support figure workflow.

It exists because the current `setup_support_by_cutoff_20260506` family is **not** faithful enough to be the final reproducibility contract. The model-side cutoff bundles appear mostly correct, but the current figure derivation layer:

- uses the wrong plotting surfaces for `usgs.png` and the covariate figure,
- loses important `forecats_bundle` versioning metadata in the replay-packaged roots,
- and therefore does not meet the stricter reproducibility standard required for the revised article.

This manifest is the authoritative answer to:

1. which model run each cutoff must match,
2. which bundle root each figure family must be derived from,
3. which retrospective/forecast/versioning policy applies at each cutoff,
4. and which exact files each figure must use.

## Governing rule

For every cutoff, the corrected figure family must satisfy both of these conditions:

1. it must remain linked to the **published `exAL-M-T1` CRPS row** for that cutoff;
2. it must render from the **authoritative input bundle** that matches the cutoff’s actual retrospective/forecast/versioning policy.

That means each cutoff has two linked provenance anchors:

- a **selected model run root**:
  the verified `exAL-M-T1` run that reproduces the published CRPS row;
- a **figure-input bundle root**:
  the authoritative forecats/histfix bundle that best records the cutoff-specific retrospective and forecast-source policy.

## Figure-level source rules

These rules are the heart of the corrected workflow.

### `usgs.png`

Canonical data source:
- `selected_run_root/inputs/shared/usgs/usgs_daily.csv`

Canonical time window:
- start at the **actual retrospective support start used by the model fit** for that cutoff;
- end at `cutoff_date`.

Do not:
- build this figure from `timestamps` / `Y`;
- build it from a merged model matrix;
- label it as a full-record figure unless the underlying support really is full-record.

Important note:
- for the short-window cutoffs, this figure is expected to start late if the model fit only used a short retrospective support window;
- for the histfix cutoffs, this figure should extend back to `1987-05-29`.

### `precip_soilmoisture_climatePC1_faceted_labeled.png`

Canonical data sources:
- `selected_run_root/inputs/shared/covariates/cov_01_PPT.csv`
- `selected_run_root/inputs/shared/covariates/cov_02_SOIL.csv`
- `selected_run_root/inputs/shared/covariates/cov_03_PCA.csv`

Canonical time window:
- same historical fit-support window as the retrospective series for that cutoff.

Do not:
- build this figure from `X`;
- let it inherit row truncation from `all_data` merges;
- silently use a different support span from the retrospective figure.

### `retrospective_log_discharge_plot_faceted.png`

Canonical data source precedence:

1. `figure_bundle_root/inputs/retros_source_lineage.csv` when available;
2. otherwise `figure_bundle_root/inputs/retros_daily.csv` plus selection policy from `figure_bundle_root/meta.yaml`;
3. only if needed for QA, `selected_run_root/inputs/shared/retros/retros.csv` as a narrow consistency check, not as the primary provenance source.

Canonical rules:
- use the actual cutoff-specific selected retrospective lineage;
- reflect the correct GloFAS and NWS retrospective source policy;
- do not use hard-coded y-limits.

### `forecats.png`

Canonical data source precedence:

1. `figure_bundle_root/meta.yaml`
2. `figure_bundle_root/inputs/glofas_weighted_daily.csv`
3. `figure_bundle_root/inputs/nws_weighted_daily.csv`
4. `figure_bundle_root/inputs/retros_daily.csv`
5. `selected_run_root/inputs/shared/usgs/usgs_daily.csv` when the bundle does not already carry a local `usgs_daily.csv`

Canonical rules:
- use the bundle-native plot window from bundle metadata;
- preserve the cutoff-specific retrospective policy for the “before cutoff” context;
- preserve the exact forecast-member/weighted-forecast files associated with the cutoff.

This figure should be built on the `forecats_plot_bundle.R` logic, not on the merged model matrices.

## Canonical cutoff-by-cutoff source map

| Cutoff | Published `exAL-M-T1` CRPS | Selected model run root | Canonical figure bundle root | Bundle class | NWS retrospective policy | GloFAS retrospective policy | Historical support start |
|---|---:|---|---|---|---|---|---|
| `2021-01-23` | `0.1569` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_publication_replay_representatives_20260506/20210123_exal_m_t1/runs/multimodel_20210123_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1` | `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/frozen_shared_inputs/exalm_t1_authoritative_20260505/cutoff_date=2021-01-23/forecats_bundle` | `short_window_synth_bundle` | `nws_synth_retro_ens_mean` keep-source policy | `glofas_hist_v21_htessel_cons` | `2018-02-08` |
| `2021-11-12` | `0.0284` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_publication_replay_representatives_20260506/20211112_exal_m_t1/runs/multimodel_20211112_v8_eps180cf1_exdqlm_multivar_keep_featurecov_cf1` | `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/frozen_shared_inputs/exalm_t1_authoritative_20260505/cutoff_date=2021-11-12/forecats_bundle` | `short_window_synth_bundle` | `nws_synth_retro_ens_mean` keep-source policy | `glofas_hist_v31_lisflood_cons` | `2018-11-28` |
| `2021-12-21` | `0.2369` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_publication_replay_representatives_20260506/20211221_exal_m_t1/runs/multimodel_20211221_v8_eps1cf1_exdqlm_multivar_keep_featurecov_cf1` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_histfix_20260407/stable_inputs/site=11160500/cutoff_date=2021-12-21/run_id=20260407_long_history_r01` | `histfix_long_history_bundle` | `nws_retro_v21` with `nws_retro_v30` tail fill after natural v21 coverage end | `glofas_hist_v31_lisflood_cons` | `1987-05-29` |
| `2022-05-11` | `0.0210` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_publication_replay_representatives_20260506/20220511_exal_m_t1/runs/multimodel_20220511_v8_eps180cf1_exdqlm_multivar_keep_featurecov_cf1` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_histfix_20260407/stable_inputs/site=11160500/cutoff_date=2022-05-11/run_id=20260407_long_history_r01` | `histfix_long_history_bundle` | `nws_retro_v21` with `nws_retro_v30` tail fill after natural v21 coverage end | `glofas_hist_v31_lisflood_cons` | `1987-05-29` |
| `2022-12-25` | `0.4375` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_publication_replay_representatives_20260506/20221225_exal_m_t1/runs/multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_histfix_20260407/stable_inputs/site=11160500/cutoff_date=2022-12-25/run_id=20260407_long_history_r01` | `histfix_long_history_bundle` | `nws_retro_v21` with `nws_retro_v30` tail fill after natural v21 coverage end | `glofas_hist_v31_lisflood_cons` | `1987-05-29` |

## Figure-bundle details by bundle class

### A. `short_window_synth_bundle`

Canonical examples:
- `2021-01-23`
- `2021-11-12`

Bundle characteristics:
- authoritative frozen bundle under `repro/frozen_shared_inputs/exalm_t1_authoritative_20260505/.../forecats_bundle`
- carries:
  - `meta.yaml`
  - `snapshot_source_map.txt`
  - `inputs/retros_daily.csv`
  - `inputs/glofas_weighted_daily.csv`
  - `inputs/nws_weighted_daily.csv`
  - `inputs/glofas_members.csv`
  - `inputs/nws_members.csv`
  - top-level `retros.csv`, `glofas_forecast.csv`, `nws_forecast.csv`
- does **not** currently carry a local `usgs_daily.csv`

Operational implication:
- `usgs.png` must pull USGS from the selected model run root;
- `forecats.png` can still use the bundle-native plotter with a small adapter layer that injects USGS.

### B. `histfix_long_history_bundle`

Canonical examples:
- `2021-12-21`
- `2022-05-11`
- `2022-12-25`

Bundle characteristics:
- authoritative bundle under `multimodel_v8_histfix_20260407/stable_inputs/...`
- carries:
  - `meta.yaml`
  - `inputs/retros_daily.csv`
  - `inputs/retros_source_lineage.csv`
  - `inputs/glofas_weighted_daily.csv`
  - `inputs/nws_weighted_daily.csv`
  - `inputs/glofas_members.csv`
  - `inputs/nws_members.csv`
  - `retros.csv`
  - `retros_source_lineage.csv`
  - `nws_forecast.csv`
  - `glofas_forecast.csv`
- metadata explicitly records:
  - `glofas_hist_v31_lisflood_cons`
  - `nws_retro_v21`
  - `nws_retro_v30` tail fill

Operational implication:
- this is the strongest provenance source for the long-history cutoffs;
- the retrospective figure should use the lineage CSV directly.

## Current `v1` status

The current derived family:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exal_m_t1_setup_support_by_cutoff_20260506`

is now considered:
- useful as an audit/debugging artifact,
- but **not** the final canonical source for article-facing cutoff figures.

Why:
- it used the verified replay runs as provenance anchors correctly,
- but it derived the figures from the wrong plotting layer and with incomplete bundle metadata recovery.

## Required downstream use

The next implementation pass must use this manifest as the source-of-truth table for:

1. the corrected `v2` workflow config,
2. the corrected runtime output family,
3. the article-side mirrored bundle,
4. and the final manuscript-side figure provenance notes.

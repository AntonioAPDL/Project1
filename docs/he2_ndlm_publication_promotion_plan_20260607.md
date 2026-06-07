# HE2 NDLM Publication Promotion Plan - 2026-06-07

## Objective

Close the remaining HE2 Bayesian publication benchmark gap by rerunning and
promoting the three NDLM comparison families on the same canonical input-bundle
contract already used by the promoted quantile families.

Current publication gate evidence:

- `reports/he2_publication_manifest/he2_publication_parity_gate.md`
- generated at `2026-06-07T00:38:48Z`
- promoted rows: `30`
- pending rows: `15`
- pending labels: `N-M-T0`, `N-M-T1`, `N-U-T1`
- canonical bundle:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
- bundle run id: `20260510_publication_shared_r01`

This plan targets exactly those 15 pending rows:

| Label | Family | Transfer mode | Cutoffs | Rows |
|---|---|---|---:|---:|
| `N-U-T1` | `ndlm_univar_keep` | keep | 5 | 5 |
| `N-M-T0` | `ndlm_main_drop` | drop | 5 | 5 |
| `N-M-T1` | `ndlm_main_keep` | keep | 5 | 5 |

## Why a Fresh Root

The previous Wave A NDLM root is not authoritative:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_bayesian_publication_relaunch_wave_a_ndlm_20260516`

Observed state:

- `matrix_status.csv` has 15 rows: one `report/pass`, two stale
  `fit/pending`, and 12 `not_started`.
- `queue.log` records `controller signal signame=SIGTERM signum=15` at
  `2026-05-16T21:19:00Z`.
- No retained `.RData` / `.rdata` / `.Rda` / `.rda` files were found under the
  old root.
- Disk footprint is only about `126M`.

Interpretation: the old root is a stopped partial queue, not a model-failure
diagnosis and not a clean publication source. The June 7 promotion uses a fresh
tracked template and batch so the matrix, configs, validation, launch logs, and
post artifacts are internally consistent.

## New Tracked Controls

Template:

`config/he2_bayesian_publication_relaunch_wave_a_ndlm_promotion_20260607.template.yaml`

Batch:

`config/he2_relaunch_batches/he2_wave_a_ndlm_remaining_families_promotion_20260607.yaml`

Fresh artifact root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_bayesian_publication_relaunch_wave_a_ndlm_promotion_20260607`

Generated matrix:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_bayesian_publication_relaunch_wave_a_ndlm_promotion_20260607/control/publication_relaunch_matrix`

Generated configs:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_bayesian_publication_relaunch_wave_a_ndlm_promotion_20260607/control/generated_configs`

The generated matrix contains exactly 15 rows: 5 cutoffs times 3 NDLM families.

## Input-Bundle Contract

All rows must use the canonical 20260510 publication bundle:

| Field | Required value |
|---|---|
| bundle root | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510` |
| bundle run id | `20260510_publication_shared_r01` |
| data start | `1987-05-29` |
| cutoffs | `20210123`, `20211112`, `20211221`, `20220511`, `20221225` |
| internal scale | `log1p_cms` |
| scoring/figure post scale | canonical post workflow scale |

Generated audit evidence:

`.../control/publication_relaunch_matrix/cutoff_bundle_audit.csv`

Required checks in that file:

- `retros_start = 1987-05-29` for every cutoff.
- `retros_end` equals the cutoff date for every cutoff.
- `retros_duplicate_dates = 0`.
- `retros_missing_days = 0`.
- GloFAS historical source is `glofas_hist_v21_htessel_cons`.
- NWS retrospective rule is v2.1 through natural coverage end, then v3.0 daily
  retrospective tail fill.
- Forecast files are the canonical NWS and GloFAS forecast files embedded in
  the 20260510 bundle.
- Deterministic covariates use GEFS:
  - precip source `gefs_apcp`
  - precip reduction `q85`
  - soil source `gefs_soilw_0_0.1m`
  - soil reduction `q85`
- GDPC alias path is
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510/supporting_inputs/covariates/cov_05_PCA.csv`.
- GDPC alias support range is `1987-05-29` to `2023-01-22`.

## Covariate and Transfer-Function Contract

The active NDLM configs must use the same publication covariate contract as the
quantile promotion:

| Slot | Meaning |
|---|---|
| `PPT` | deterministic precipitation covariate |
| `SOIL` | deterministic soil moisture covariate |
| `PCA` | GDPC first principal component alias |

Generated config checks:

- `debug_he2_publication_relaunch.canonical_fit_covariate_contract =
  PPT|SOIL|PCA(alias=GDPC1)`.
- `inputs.fit.covariates` names are exactly `PPT`, `SOIL`, `PCA`.
- `inputs.covariate_features.lag_orders = [1, 2, 3]`.
- `inputs.covariate_features.include_squares = true`.
- `inputs.covariate_features.include_interaction = true`.
- The same checks are enforced by
  `tests/python/test_he2_publication_relaunch_builder_selection.py`.

## NDLM Model-Spec Contract

All rows are normal-likelihood NDLM comparison rows. They must remain separate
from the exAL/AL quantile families.

### NDLM main drop/keep

| Parameter | Value |
|---|---:|
| implementation mode | `theory_aligned` |
| Kalman backend | `cpp` |
| `df_t` | `0.99999999` |
| `df_s1` | `0.99999999` |
| `df_s2` | `0.99999999` |
| `df_s67` | `0.99999999` |
| `df_discrep` | `0.99999999` |
| `lambda` | `0.97` |
| `df_trans` | `0.9999999` |
| `df_covs` | `0.99999999` |
| `lam1` | `0.999999` |
| `lam2` | `0.9` |
| `n_samp` | `2000` |
| forecast covariance `c_factor` | `1.0` |
| forecast covariance `epsilon` | `null` |

Seasonality:

| Model | Period | Harmonics |
|---|---:|---|
| `ndlm_main_drop` / `ndlm_main_keep` | `363.5854` | `1`, `2`, `1/6.8068493` |

The third entry is the non-integer value `1/6.8068493`
(`0.14691084757818865`). It must not be replaced by literal harmonic `3`.

### NDLM univar keep

| Parameter | Value |
|---|---:|
| implementation mode | `theory_aligned_closed_form` |
| Kalman backend | `cpp` |
| forecast transfer mode | `keep` |
| `df_t` | `0.99999999` |
| `df_s1` | `0.99999999` |
| `df_s2` | `0.99999999` |
| `df_s67` | `0.99999999` |
| `lambda` | `0.97` |
| `df_trans` | `0.9999999` |
| `df_covs` | `0.99999999` |
| `posterior_draws` | `64` |
| `horizon_cap` | `90` |

Seasonality:

| Model | Period | Harmonics |
|---|---:|---|
| `ndlm_univar_keep` | `363.5854` | `1`, `2`, `1/6.8068493` |

The NDLM univariate path follows the same harmonic-value contract as the NDLM
main path. Literal harmonic `3` is not allowed in NDLM seasonality configs.

## Queue and Cleanup Contract

The promotion batch is intentionally conservative:

| Field | Value |
|---|---:|
| `fit_parallel_workers` | `1` |
| `mc_cores` | `1` |
| `ordinary_max_concurrent` | `5` |
| `heavy_cutoff_max_concurrent` | `1` |
| `heavy_cutoff_blocks_ordinary` | `false` |
| `pause_free_gb` | `120` |
| `launch_free_gb` | `140` |
| `heavy_free_gb` | `160` |
| `poll_seconds` | `60` |

Expected production behavior:

1. Build 15 generated configs.
2. Run all 15 rows through fit, post, validate, report.
3. Remove fit `.RData` artifacts after post.
4. Keep post outputs, CRPS tables, manifests, plots, and reports.
5. End with zero retained `.RData` / `.rdata` / `.Rda` / `.rda` files under
   successful run roots.

## Validation Gates

### Code and deterministic tests

Already executed in this promotion pass:

```bash
python3 -m py_compile \
  scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  scripts/build_he2_bayesian_publication_relaunch_configs.py \
  scripts/launch_he2_bayesian_publication_relaunch.py

python3 -m unittest \
  tests.python.test_he2_publication_relaunch_validator \
  tests.python.test_he2_publication_relaunch_template -v

python3 -m unittest \
  tests.python.test_he2_publication_relaunch_builder_selection.HE2PublicationRelaunchBuilderSelectionTests.test_wave_a_ndlm_promotion_batch_builds_canonical_bundle_matrix \
  -v
```

Covered behavior:

- multi-case NDLM full-pipeline smoke normalization in
  `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`;
- promotion template/batch structure;
- generated 15-row matrix;
- canonical bundle root/run id/data start;
- q85 deterministic precip/soil;
- GDPC alias support;
- `PPT`, `SOIL`, `PCA` covariate slots;
- lag orders, squares, and interaction terms;
- one-core NDLM rows;
- high-discount NDLM spec;
- NDLM main harmonics `[1, 2, 1/6.8068493]`;
- NDLM univar harmonics `[1, 2, 1/6.8068493]`.

### Real prelaunch validation

Command:

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_wave_a_ndlm_promotion_20260607.template.yaml \
  --batch-file config/he2_relaunch_batches/he2_wave_a_ndlm_remaining_families_promotion_20260607.yaml
```

Successful validation output root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_bayesian_publication_relaunch_wave_a_ndlm_promotion_20260607/control/prelaunch_validation_20260607T203117Z`

The earlier validation attempt at
`.../control/prelaunch_validation_20260607T191317Z` was superseded before
production launch because the NDLM-main full-pipeline smoke was accidentally
using production `gamma_sigma` iteration depth. The tracked template now applies
a validation-only NDLM-main smoke override:
`fit.ndlm_main.gamma_sigma.min_total_iters = 1` and
`fit.ndlm_main.gamma_sigma.max_iter = 1`. The generated production configs still
retain `fit.ndlm_main.gamma_sigma.min_total_iters = 20` and
`fit.ndlm_main.gamma_sigma.max_iter = 100`; this separation is tested in
`tests/python/test_he2_publication_relaunch_builder_selection.py`.

The intermediate successful validation at
`.../control/prelaunch_validation_20260607T193033Z` was also superseded before
production launch because it predated the final NDLM harmonic correction. The
authoritative validation root is `.../control/prelaunch_validation_20260607T203117Z`,
which rebuilds the 15 generated configs after forcing NDLM main and NDLM univar
seasonality to `[1, 2, 1/6.8068493]`. The final NDLM-main keep smoke reached
runtime with `NDLM_SEASONAL_HARMONICS=1,2,0.146910847578189`, confirming that
the noninteger third harmonic value, not literal `3`, is wired through the
runtime path.

Final status:

- bundle build: pass
- config build: pass
- internal Python tests: pass
- data-prep smokes for all three NDLM families: pass
- data-prep smokes for all five cutoffs: pass
- fit smoke for `ndlm_univar_keep` at `20210123`: pass
- full-pipeline smoke for `ndlm_univar_keep` at `20210123`: pass
- full-pipeline smoke for `ndlm_main_drop` at `20210123`: pass
- full-pipeline smoke for `ndlm_main_keep` at `20210123`: pass
- selected scope: 15 rows, 5 cutoffs, 3 NDLM families
- smoke runs: 14 total; 12 passed and 2 quantile smokes intentionally skipped
  because this batch is NDLM-only
- cleanup: 16 temporary fit files removed, `297866711` bytes removed
- retained `.RData` / `.rdata` / `.Rda` / `.rda` files under the June 7
  promotion root after validation: `0`

Summary evidence:

`.../control/prelaunch_validation_20260607T203117Z/prelaunch_validation_summary.json`

The full-pipeline smoke outputs also confirm the post/report wiring by producing
the NDLM ELBO figure, recent-fit figure, forecast-window raw-cms quantile figure,
CRPS tables, posterior table export manifest, post artifact manifest, and NDLM
diagnostic tables for all three NDLM families at the early cutoff.

## Production Launch Command

Do not run the production launch until the validation gate above is complete.

After a clean prelaunch validation pass, the efficient launch command is:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_wave_a_ndlm_promotion_20260607.template.yaml \
  --batch-file config/he2_relaunch_batches/he2_wave_a_ndlm_remaining_families_promotion_20260607.yaml \
  --skip-validate \
  --start-monitor \
  --monitor-out-dir reports/he2_ndlm_promotion_20260607_live \
  --monitor-interval 300 \
  --monitor-max-snapshots 288
```

If any tracked config, validator, builder, or NDLM runtime code changes after
the validation pass, remove `--skip-validate` and rerun the validator as part of
the launch.

## Monitoring and Acceptance

During the launch, monitor:

- `matrix_status.csv`;
- queue log;
- per-row `run_manifest.yaml`;
- per-row post `outputs/`;
- per-row report `summary.md`;
- live monitor snapshots in `reports/he2_ndlm_promotion_20260607_live`.

Acceptance criteria:

| Gate | Required result |
|---|---|
| row count | 15 rows |
| final row statuses | all `report/pass` |
| labels | `N-U-T1`, `N-M-T0`, `N-M-T1` |
| cutoffs | all five publication cutoffs |
| input bundle | canonical 20260510 root for every row |
| covariates | `PPT`, `SOIL`, `PCA(alias=GDPC1)` |
| feature terms | lags 1/2/3, squares, interaction |
| post outputs | CRPS tables, figure manifests, cutoff-window figures |
| cleanup | zero retained `.RData` files after post/report |

## Promotion After Successful Launch

Only after the 15-row launch passes:

1. Update the HE2 Bayesian publication manifest builder to resolve the three
   NDLM labels from the June 7 promotion root.
2. Rebuild:

```bash
python3 scripts/build_he2_bayesian_publication_manifest.py
python3 scripts/build_he2_publication_parity_gate.py
python3 scripts/build_he2_master_workflow_audit_tracker.py
```

3. Update parity tests so the expected publication state is 45 promoted rows,
   0 pending rows, and final 9-model benchmark ready.
4. Refresh article-side CRPS and ablation assets in:

`/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-2`

5. Commit repo changes and article changes separately so the runtime promotion
   and manuscript refresh remain reviewable.

## Current Checklist

| Step | Status | Evidence |
|---|---|---|
| Fresh NDLM promotion template | done | `config/he2_bayesian_publication_relaunch_wave_a_ndlm_promotion_20260607.template.yaml` |
| Fresh NDLM promotion batch | done | `config/he2_relaunch_batches/he2_wave_a_ndlm_remaining_families_promotion_20260607.yaml` |
| 15-row matrix build | done | `.../control/publication_relaunch_matrix/matrix_plan.csv` |
| Bundle/covariate audit | done | `.../control/publication_relaunch_matrix/cutoff_bundle_audit.csv` |
| Frozen spec audit | done | `.../control/publication_relaunch_matrix/frozen_spec_manifest.csv` |
| Deterministic tests | done | unittest and py_compile commands above |
| Full prelaunch validation | done | `.../control/prelaunch_validation_20260607T203117Z/prelaunch_validation_summary.json` |
| Production launch | not started | validation passed; awaiting explicit launch approval |
| Manifest/parity promotion | not started | gated on 15 production rows passing |
| Article CRPS/table refresh | not started | gated on manifest promotion |

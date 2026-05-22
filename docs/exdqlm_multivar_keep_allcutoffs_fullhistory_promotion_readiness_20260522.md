# exDQLM Multivariate Keep All-Cutoff Full-History Promotion Readiness

Date: 2026-05-22

Status: launch package implemented and preflighted; no full model campaign launched by this document.

## Decision Lock

This package promotes the repaired `log1p_cms` multivariate `exdqlm keep` workflow to all five HE2 publication
cutoffs with full history from `1987-05-29` through each cutoff. It implements the current decision to keep `.RData`
available through the fit and post stages, then allow the default cleanup wrapper to remove `.RData` after post
finishes. The no-cleanup queue patch is intentionally skipped.

Durable evidence for this run must therefore come from post outputs, exported tables, smoke-fast figures, held-out
USGS figures, CRPS metrics, and generated diagnostics. Any future diagnostic that needs raw `theta.out`/fit-state
objects after post must either be integrated into post or run before cleanup.

## Tracked Package

| artifact | path |
| --- | --- |
| all-cutoff template | `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522.template.yaml` |
| all-cutoff batch | `config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522.yaml` |
| implementation plan | `docs/exdqlm_multivar_keep_multicutoff_promotion_plan_20260522.md` |
| generated preflight root | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522` |
| generated config dir | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522/control/generated_configs` |
| generated matrix dir | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522/control/publication_relaunch_matrix` |

The generated preflight produced five configs and five matrix rows. It did not launch any fits.

## Locked Model Contract

| item | value |
| --- | --- |
| family | `exdqlm_multivar_keep` |
| cutoffs | `20210123`, `20211112`, `20211221`, `20220511`, `20221225` |
| history start | `1987-05-29` |
| quantiles | `0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95` |
| transform | `log1p_cms`, `transform_policy: log1p_only` |
| VB max iterations | `100` |
| transfer mode | `keep` |
| trend | enabled |
| harmonics | indices `[1, 2, 3]`, mapping to values `c(1, 2, 1/6.8068493)` |
| base transfer covariates | `PPT`, `SOIL`, `PCA` |
| engineered transfer terms | `PPT_sq`, `SOIL_sq`, `PPT_x_SOIL`, `PPT_lag1`, `PPT_lag2`, `PPT_lag3`, `SOIL_lag1`, `SOIL_lag2`, `SOIL_lag3` |
| discount factors | `df_t=0.99999`, `df_s1=df_s2=df_s67=df_discrep=0.9999`, `lambda=0.97`, `df_trans=df_covs=0.9999999` |
| forecast Wishart prior | `epsilon=365.0`, `c_factor=1.0` |
| quantile workers | `7` per cutoff |
| per-process thread caps | `omp=openblas=mkl=veclib=numexpr=1` |
| launch queue | five cutoff rows allowed concurrently, yielding `5 * 7 = 35` quantile workers |
| cleanup | `scripts/run_unified_with_cleanup.sh`, so `.RData` is removed after post |

The harmonic source is active code, not a stale note:

- `R/environmetrics/00_constants.R` defines `harmonics = c(1, 2, 1/6.8068493)`;
- `R/unified/families/exdqlm_multivar_structure.R` exposes the same default basis;
- `tests/testthat/test_exdqlm_multivar_structure_contract.R` verifies `[1, 2, 3]` maps to that full legacy basis.

## Input-Bundle Verification

The package uses the canonical 20260510 HE2 shared input bundle:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`

The support manifest locks the current covariate sources:

- `supporting_inputs/support_manifest.json` points `PPT` to `supporting_inputs/covariates/cov_03_PPT.csv`;
- `supporting_inputs/support_manifest.json` points `SOIL` to `supporting_inputs/covariates/cov_04_SOIL.csv`;
- `supporting_inputs/support_manifest.json` points `PCA` to `supporting_inputs/covariates/cov_05_PCA.csv`;
- the same manifest points the canonical GDPC/PCA alias source to
  `data/canonical_gdpc_master/v20260509/outputs/compat/cov_05_PCA.csv`.

The generated `cutoff_bundle_audit.csv` confirmed:

| cutoff | retros start | retros end | GDPC/PCA alias start | GDPC/PCA alias end |
| --- | --- | --- | --- | --- |
| `20210123` | `1987-05-29` | `2021-01-23` | `1987-05-29` | `2023-01-22` |
| `20211112` | `1987-05-29` | `2021-11-12` | `1987-05-29` | `2023-01-22` |
| `20211221` | `1987-05-29` | `2021-12-21` | `1987-05-29` | `2023-01-22` |
| `20220511` | `1987-05-29` | `2022-05-11` | `1987-05-29` | `2023-01-22` |
| `20221225` | `1987-05-29` | `2022-12-25` | `1987-05-29` | `2023-01-22` |

The generated configs also preserve the blended deterministic PPT/SOIL forecast handoff inherited from the selected
publication source configs:

- handoff root contains `gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z`;
- precipitation source is `gefs_apcp`, reduction `q85`, with noisy and observed blends enabled;
- soil source is `gefs_soilw_0_0.1m`, reduction `q85`, with noisy and observed blends enabled;
- `require_full_horizon: true` remains set.

## Runtime Guard Contract

The all-cutoff batch keeps the promoted repair guards:

- robust `sigma/gamma` initialization and adaptive objective guard;
- near-zero gamma split support;
- state guard configured but with `state_guard_start_iter=1000`, so it should not fire during a `max_iter=100` run;
- terminal sampling guard in `fail_fast` mode;
- latent cap `mode: cap_e_inv_u`, `e_inv_u_cap=5000`;
- pseudo-data guard in `fail` mode with caps on `FFF`, `QQQ`, `E[s]`, `E[s^2]`, `E[u]`, and `E[1/u]`;
- forecast-health guard in `fail_fast` mode;
- heartbeat and phase-marker sampling diagnostics.

This is not meant to hide instability. It is meant to fail early if the repaired log1p path produces numerically
unsafe pseudo-data or forecast-state quantities.

## Validation Completed

Commands run:

```bash
python3 -m unittest tests.python.test_he2_publication_relaunch_template -v
python3 -m unittest tests.python.test_multimodel_v8_queue_contract -v
python3 -m unittest tests.python.test_he2_publication_relaunch_builder_selection.HE2PublicationRelaunchBuilderSelectionTests.test_exdqlm_allcutoffs_fullhistory_promotion_batch_builds_guarded_configs -v
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_structure_contract.R')"
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522.template.yaml --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522.yaml
python3 scripts/launch_he2_bayesian_publication_relaunch.py --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522.template.yaml --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522.yaml --skip-validate --dry-run
```

Results:

| validation | result |
| --- | --- |
| template contract tests | pass, 20 tests |
| queue cleanup contract tests | pass, 3 tests |
| all-cutoff generated-config test | pass |
| harmonic source contract | pass, 6 expectations |
| actual builder preflight | pass, 5 configs and 5 plan rows generated |
| launch dry-run | pass, printed queue command only |

## Launch Boundary

Ready for a full launch after explicit user approval. The launch command should be:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522.yaml
```

Expected launch settings from the preflight:

```text
ORDINARY_MAX_CONCURRENT=5
HEAVY_CUTOFF_MAX_CONCURRENT=1
HEAVY_CUTOFF_BLOCKS_ORDINARY=0
POLL_SECONDS=30
```

Dry-run queue command produced:

```bash
python3 scripts/run_multimodel_v8_queue.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522/control/publication_relaunch_matrix \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522 \
  --ordinary-max-concurrent 5 \
  --pause-free-gb 25.0 \
  --launch-free-gb 35.0 \
  --heavy-free-gb 35.0 \
  --heavy-cutoff-max-concurrent 1 \
  --poll-seconds 30 \
  --no-heavy-cutoff-blocks-ordinary
```

This will run the queue through `scripts/run_unified_with_cleanup.sh`. `.RData` files should be considered temporary
until post completes; post outputs are the retained artifacts.

## Remaining Work After Launch

1. Start live monitoring immediately after launch and track cutoff, quantile, iteration, ELBO, `gamma_exp`,
   `sigma_exp`, and state norm squared divided by history length.
2. Confirm every cutoff reaches post completion and cleanup happens only after post.
3. Check all-seven ELBO plots for every cutoff.
4. Check held-out USGS forecast-window synthesis plots for every cutoff.
5. Export and compare CRPS metrics across all cutoffs.
6. Write a final campaign report with failures, guard events, and any quantile-specific anomalies.

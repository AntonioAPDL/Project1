# HE2 Remaining Quantile AL/exAL Publication Relaunch

Date: 2026-06-03

## Scope

This wave covers the three remaining quantile families in the 9-model HE2 Bayesian publication table:

| label | family | source contract | target root |
|---|---|---|---|
| `AL-M-T0` | `dqlm_multivar_al_drop` | paired AL clone of promoted current-code `exAL-M-T0` | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_from_exal_drop_20260603` |
| `exAL-U-T1` | `exdqlm_univar` | univariate exAL shared-spec relaunch on canonical bundle | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_univar_al_exal_publication_relaunch_20260603` |
| `AL-U-T1` | `dqlm_univar_al` | univariate AL shared-spec relaunch on canonical bundle | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_univar_al_exal_publication_relaunch_20260603` |

The remaining Gaussian/NDLM families are deliberately out of scope for this wave: `N-U-T1`, `N-M-T0`, and `N-M-T1`.

## Canonical Input Contract

All launched rows must use the 20260510 publication bundle contract:

- bundle root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
- bundle run id: `20260510_publication_shared_r01`
- data start: `1987-05-29`
- cutoffs: `20210123`, `20211112`, `20211221`, `20220511`, `20221225`
- covariates: `PPT`, `SOIL`, `PCA` where `PCA` is the canonical GDPC1 alias
- deterministic PPT/SOIL forecasts: blended `gefs_apcp` and `gefs_soilw_0_0.1m` reductions at `q85`
- covariate features: lags `1,2,3`, squares enabled, PPT-SOIL interaction enabled
- scale policy: log1p-only internal legacy fit/post scale (`log1p_cms`)

## AL-M-T0 Pairing Decision

`AL-M-T0` is not rebuilt from the older April `dqlm_multivar_al_drop` manifest row. It is cloned from the promoted
current-code `exAL-M-T0` package:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602`

The intended scientific change is exactly:

`models.exdqlm_multivar.likelihood_mode: exal -> al`

The clone validator checks that the following are preserved exactly: input paths, cutoff dates, data start, transfer-drop
mode, trend/full-harmonic structure, state discount factors, `epsilon=30`, `c_factor=1`, active quantiles, max_iter,
and scale contract.

## New Tracked Wiring

- AL-drop builder: `scripts/build_he2_dqlm_multivar_al_drop_from_exal_drop.py`
- AL-drop prelaunch validator: `scripts/validate_he2_dqlm_multivar_al_drop_from_exal_drop_prelaunch.py`
- univariate template: `config/he2_bayesian_publication_relaunch_univar_al_exal_20260603.template.yaml`
- univariate batch: `config/he2_relaunch_batches/univar_al_exal_publication_relaunch_20260603.yaml`
- combined launcher: `scripts/launch_he2_remaining_quantile_al_exal.py`
- focused tests: `tests/python/test_he2_remaining_quantile_al_exal_relaunch.py`

## Validation Gates

Before launch:

```bash
python3 scripts/build_he2_dqlm_multivar_al_drop_from_exal_drop.py
python3 scripts/validate_he2_dqlm_multivar_al_drop_from_exal_drop_prelaunch.py
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_univar_al_exal_20260603.template.yaml \
  --batch-file config/he2_relaunch_batches/univar_al_exal_publication_relaunch_20260603.yaml \
  --profile disk_guarded_parallel
python3 -m unittest tests.python.test_he2_remaining_quantile_al_exal_relaunch -v
```

The validators run deterministic data-prep checks, canonical-bundle alignment checks, q50 fit-only smoke rows, q35+q50
univariate full-pipeline smoke rows, and post-success heavy-artifact cleanup checks. The q35+q50 full-pipeline scope is
intentional because the legacy univariate post repair requires at least two fitted quantiles.

## Launch

The combined launcher validates unless `--skip-validation` is provided, then starts two detached queue controllers:

```bash
python3 scripts/launch_he2_remaining_quantile_al_exal.py
```

Expected max active quantile workers:

| controller | rows at once | quantiles per row | max workers |
|---|---:|---:|---:|
| `AL-M-T0` | 2 | 7 | 14 |
| `AL-U-T1` + `exAL-U-T1` | 2 | 7 | 14 |
| total | 4 | 7 | 28 |

Both queues use `scripts/run_unified_with_cleanup.sh`, which sets `CLEANUP_RDATA_AFTER_POST=1`.

## Promotion Rule

Do not update the project publication manifest or revised-article CRPS table for these three families until every cutoff
has `fit`, `post`, `validate`, and `report` stages marked `pass`, CRPS summary tables exist, publication figure manifests
exist, and no `.RData`, `.rda`, or `.Rda` files remain under the run roots.

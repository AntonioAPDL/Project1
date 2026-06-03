# HE2 Remaining Quantile AL/exAL Publication Relaunch

Date: 2026-06-03

## Scope

This wave covered the three remaining quantile families in the 9-model HE2 Bayesian publication table:

| label | family | source contract | target root |
|---|---|---|---|
| `AL-M-T0` | `dqlm_multivar_al_drop` | paired AL clone of promoted current-code `exAL-M-T0` | blocked after fit-stage sigma/PSD failures |
| `exAL-U-T1` | `exdqlm_univar` | univariate exAL shared-spec relaunch on canonical bundle | passed fit/post/validate/report |
| `AL-U-T1` | `dqlm_univar_al` | univariate AL shared-spec relaunch on canonical bundle | passed fit/post/validate/report |

The remaining Gaussian/NDLM families are deliberately out of scope for this wave: `N-U-T1`, `N-M-T0`, and `N-M-T1`.

## Runtime Outcome

The univariate rows completed successfully and are now promotable canonical-bundle rows:

| label | rows | status |
|---|---:|---|
| `AL-U-T1` | 5 | fit/post/validate/report pass; CRPS tables and publication figure manifests present; no retained `.RData/.rda` |
| `exAL-U-T1` | 5 | fit/post/validate/report pass; CRPS tables and publication figure manifests present; no retained `.RData/.rda` |

The `AL-M-T0` clone is not promotable. It completed data prep but all five cutoff rows failed in fit. The recurring
failure signatures are forecast-health `max_E_sigma` explosions, post-save `chol(G)` non-positive-definite failures,
and forecast `mvrnorm` non-positive-definite covariance failures. The promoted source `exAL-M-T0` drop rows are healthy
under the same input bundle, so the failure is specific to forcing this multivariate-drop contract into AL mode under
the cloned exAL spec.

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

## AL-M-T0 Pairing Decision And Blocker

`AL-M-T0` is not rebuilt from the older April `dqlm_multivar_al_drop` manifest row. It is cloned from the promoted
current-code `exAL-M-T0` package:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602`

The intended scientific change is exactly:

`models.exdqlm_multivar.likelihood_mode: exal -> al`

The clone validator checks that the following are preserved exactly: input paths, cutoff dates, data start, transfer-drop
mode, trend/full-harmonic structure, state discount factors, `epsilon=30`, `c_factor=1`, active quantiles, max_iter,
and scale contract.

That exact clone was a useful scientific control, but it is now blocked. Do not relaunch it broadly. The next AL-M-T0
step is the no-launch targeted diagnostic package documented in:

`docs/he2_al_m_t0_blocked_diagnostic_plan_20260603.md`

## New Tracked Wiring

- AL-drop builder: `scripts/build_he2_dqlm_multivar_al_drop_from_exal_drop.py`
- AL-drop prelaunch validator: `scripts/validate_he2_dqlm_multivar_al_drop_from_exal_drop_prelaunch.py`
- univariate template: `config/he2_bayesian_publication_relaunch_univar_al_exal_20260603.template.yaml`
- univariate batch: `config/he2_relaunch_batches/univar_al_exal_publication_relaunch_20260603.yaml`
- combined launcher: `scripts/launch_he2_remaining_quantile_al_exal.py` now skips blocked `AL-M-T0` unless
  `--include-blocked-al-drop` is passed explicitly
- AL-M-T0 no-launch diagnostic builder: `scripts/build_he2_dqlm_multivar_al_drop_diagnostic_plan.py`
- AL-M-T0 no-launch diagnostic validator: `scripts/validate_he2_dqlm_multivar_al_drop_diagnostic_plan.py`
- AL-M-T0 discount-spec template: `config/he2_relaunch_batches/al_m_t0_diagnostic_discount_spec_template_20260603.yaml`
- focused tests: `tests/python/test_he2_remaining_quantile_al_exal_relaunch.py`

## Validation Gates

Before any future launch:

```bash
python3 scripts/build_he2_dqlm_multivar_al_drop_diagnostic_plan.py --lane-scope representative
python3 scripts/validate_he2_dqlm_multivar_al_drop_diagnostic_plan.py --lane-scope representative
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_univar_al_exal_20260603.template.yaml \
  --batch-file config/he2_relaunch_batches/univar_al_exal_publication_relaunch_20260603.yaml \
  --profile disk_guarded_parallel
python3 -m unittest tests.python.test_he2_remaining_quantile_al_exal_relaunch -v
```

The validators run deterministic data-prep checks, canonical-bundle alignment checks, q50 fit-only smoke rows, q35+q50
univariate full-pipeline smoke rows, and post-success heavy-artifact cleanup checks. The q35+q50 full-pipeline scope is
intentional because the legacy univariate post repair requires at least two fitted quantiles.

## Launch Safety

The combined launcher now validates unless `--skip-validation` is provided and starts only the univariate controller by
default. It records `AL-M-T0` as blocked rather than starting it:

```bash
python3 scripts/launch_he2_remaining_quantile_al_exal.py
```

`AL-M-T0` can only be included with the explicit override flag:

```bash
python3 scripts/launch_he2_remaining_quantile_al_exal.py --include-blocked-al-drop
```

Do not use that override until the targeted diagnostics or a new AL-specific discount/epsilon/c_factor spec have been
approved.

## Promotion Rule

Promote `AL-U-T1` and `exAL-U-T1` because every cutoff has `fit`, `post`, `validate`, and `report` stages marked `pass`,
CRPS summary tables exist, publication figure manifests exist, and no `.RData`, `.rda`, or `.Rda` files remain under the
run roots.

Do not promote `AL-M-T0` until all five cutoffs pass the same gates after targeted diagnostics and any required
AL-specific discount/epsilon/c_factor adjustment.

# HE2 Remaining Quantile AL/exAL Publication Relaunch

Date: 2026-06-03

## Scope

This wave covered the three remaining quantile families in the 9-model HE2 Bayesian publication table:

| label | family | source contract | target root |
|---|---|---|---|
| `AL-M-T0` | `dqlm_multivar_al_drop` | paired AL clone of promoted current-code `exAL-M-T0` plus promoted P5 AL policy | publication-promoted through P5 closeout |
| `exAL-U-T1` | `exdqlm_univar` | univariate exAL shared-spec relaunch on canonical bundle | passed fit/post/validate/report |
| `AL-U-T1` | `dqlm_univar_al` | univariate AL shared-spec relaunch on canonical bundle | passed fit/post/validate/report |

The remaining Gaussian/NDLM families are deliberately out of scope for this wave: `N-U-T1`, `N-M-T0`, and `N-M-T1`.

## Runtime Outcome

The univariate rows completed successfully and are now promotable canonical-bundle rows:

| label | rows | status |
|---|---:|---|
| `AL-U-T1` | 5 | fit/post/validate/report pass; CRPS tables and publication figure manifests present; no retained `.RData/.rda` |
| `exAL-U-T1` | 5 | fit/post/validate/report pass; CRPS tables and publication figure manifests present; no retained `.RData/.rda` |

The original raw `AL-M-T0` clone was not promotable. It completed data prep but all five cutoff rows failed in fit. The
recurring failure signatures were forecast-health `max_E_sigma` explosions, post-save `chol(G)` non-positive-definite
failures, and forecast `mvrnorm` non-positive-definite covariance failures. That raw clone remains a historical
diagnostic control only.

As of 2026-06-06, the AL-M-T0 rebuild path is unblocked by the promoted P5 policy:

- high-discount AL policy with `epsilon=365`, `c_factor=1`;
- q65/q80 gamma-sigma warm-up freeze set to 40 iterations;
- post-save objective diagnostics hardened so optional KL/JSD failures after `disc_w_save_state(...)` are logged and
  do not invalidate an already saved fit.

The isolated `20210123 q80` P5 diagnostic passed the fit stage and saved its RData, with the old post-save KL covariance
failure caught after save. See `docs/he2_al_m_t0_p5_postsave_objective_repair_plan_20260606.md`.

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

## AL-M-T0 Pairing Decision And P5 Promotion

`AL-M-T0` is not rebuilt from the older April `dqlm_multivar_al_drop` manifest row. It is cloned from the promoted
current-code `exAL-M-T0` package:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602`

The raw-clone scientific change is exactly:

`models.exdqlm_multivar.likelihood_mode: exal -> al`

That raw clone is still buildable only with `--no-policy-spec` for historical diagnostics. It is not the production
default.

The promoted production AL-M-T0 package preserves the canonical source input bundle paths, cutoff dates, data start,
transfer-drop mode, trend/full-harmonic structure, active quantiles, and scale contract, then applies the tracked P5
policy overlay:

`config/he2_relaunch_batches/al_m_t0_p5_q65_q80_warmup40_postsave_overlay_20260606.yaml`

The production root is:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p5_production_20260606`

## New Tracked Wiring

- AL-drop builder: `scripts/build_he2_dqlm_multivar_al_drop_from_exal_drop.py`
- AL-drop prelaunch validator: `scripts/validate_he2_dqlm_multivar_al_drop_from_exal_drop_prelaunch.py`
- univariate template: `config/he2_bayesian_publication_relaunch_univar_al_exal_20260603.template.yaml`
- univariate batch: `config/he2_relaunch_batches/univar_al_exal_publication_relaunch_20260603.yaml`
- combined launcher: `scripts/launch_he2_remaining_quantile_al_exal.py` now includes promoted P5 `AL-M-T0` by default;
  pass `--skip-al-drop` to omit it
- `--include-blocked-al-drop` remains accepted only as a deprecated no-op for old command compatibility
- AL-M-T0 no-launch diagnostic builder: `scripts/build_he2_dqlm_multivar_al_drop_diagnostic_plan.py`
- AL-M-T0 no-launch diagnostic validator: `scripts/validate_he2_dqlm_multivar_al_drop_diagnostic_plan.py`
- AL-M-T0 discount-spec template: `config/he2_relaunch_batches/al_m_t0_diagnostic_discount_spec_template_20260603.yaml`
- focused tests: `tests/python/test_he2_remaining_quantile_al_exal_relaunch.py`

## Validation Gates

Before a broad P5 AL-M-T0 production launch:

```bash
python3 -m unittest tests.python.test_he2_remaining_quantile_al_exal_relaunch -v
python3 scripts/validate_he2_dqlm_multivar_al_drop_from_exal_drop_prelaunch.py \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p5_production_20260606 \
  --policy-spec-yaml config/he2_relaunch_batches/al_m_t0_p5_q65_q80_warmup40_postsave_overlay_20260606.yaml \
  --skip-smoke
```

Before rebuilding the univariate AL/exAL families from this same combined launcher:

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_univar_al_exal_20260603.template.yaml \
  --batch-file config/he2_relaunch_batches/univar_al_exal_publication_relaunch_20260603.yaml \
  --profile disk_guarded_parallel
```

The old no-launch diagnostic package remains available for raw-clone investigations, but it is not the production P5
launch gate:

```bash
python3 scripts/build_he2_dqlm_multivar_al_drop_diagnostic_plan.py --lane-scope representative
python3 scripts/validate_he2_dqlm_multivar_al_drop_diagnostic_plan.py --lane-scope representative
```

The validators run deterministic data-prep checks, canonical-bundle alignment checks, overlay checks, q50 fit-only smoke
rows where requested, q35+q50 univariate full-pipeline smoke rows, and post-success heavy-artifact cleanup checks. The
q35+q50 full-pipeline scope is intentional because the legacy univariate post repair requires at least two fitted
quantiles.

## Launch Safety

The combined launcher validates unless `--skip-validation` is provided and starts the promoted P5 AL-M-T0 controller
plus the univariate controller by default:

```bash
python3 scripts/launch_he2_remaining_quantile_al_exal.py
```

Skip AL-M-T0 only when intentionally running the univariate families alone:

```bash
python3 scripts/launch_he2_remaining_quantile_al_exal.py --skip-al-drop
```

## Promotion Rule

Promote `AL-U-T1` and `exAL-U-T1` because every cutoff has `fit`, `post`, `validate`, and `report` stages marked `pass`,
CRPS summary tables exist, publication figure manifests exist, and no `.RData`, `.rda`, or `.Rda` files remain under the
run roots.

`AL-M-T0` is now publication-promoted through the P5 production root after all five production cutoffs passed the same
gates: fit, post, validate, report, CRPS table extraction, publication figure manifest generation, canonical-bundle
parity checks, and no retained `.RData`, `.rda`, or `.Rda` after successful post cleanup. See
`docs/he2_al_m_t0_p5_production_closeout_20260606.md`.

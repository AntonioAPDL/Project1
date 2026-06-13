# HE2 Table 1 Targeted Repair Relaunch 2026-06-12

## Goal

Prepare an isolated rerun package for the Table 1 rows flagged for repair, using
the current canonical HE2 publication input bundles and the revised discount /
forecast-covariance specification supplied on 2026-06-12.

## Current Status

Status as of 2026-06-13: **warmup-40 prelaunch validation passed and the
24-row isolated repair queue has been relaunched**.

The config builder and unit tests pass, and the frozen manifest matches the
requested override table for all overridden model rows. The first prelaunch
validation blocked the launch on the `20210123` / `exAL-M-T0` / `q05` smoke
lane under the inherited warmup-5 policy. A targeted 100-iteration diagnostic
confirmed this was not a 10-iteration smoke artifact:

- validation failure report: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/prelaunch_validation_20260612_final/smoke_runs/fit_quantile/exdqlm_multivar_drop/20210123/fit_smoke_exdqlm_multivar_drop_20210123_qsubset/fit/q=05/outputs/multivar_forecast_health.txt`
- diagnostic run root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/diagnostic_runs/diagnostic_20210123_exalm_t0_q05_user_spec_iter100`
- diagnostic health report: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/diagnostic_runs/diagnostic_20210123_exalm_t0_q05_user_spec_iter100/fit/q=05/outputs/multivar_forecast_health.txt`
- detailed diagnostic note: `docs/he2_table1_targeted_repair_validation_diagnostics_20260612.md`

The diagnostic `.RData` was removed after the health report was captured to keep
the runtime area from accumulating large intermediate artifacts.

The 2026-06-13 repair attempt keeps the scientific discount / epsilon table
unchanged and changes only the quantile VB warmup policy:

- `fit.exdqlm_univar.gamma_sigma.warmup_freeze_iters = 40`;
- `fit.exdqlm_multivar.gamma_sigma.warmup_freeze_iters = 40`;
- multivariate quantile override warmups for `q20`, `q35`, `q50`, `q65`, and
  `q80` are also pinned to `40`, so existing q-specific stabilization blocks do
  not accidentally retain shorter warmups.

`q05` and `q95` inherit the multivariate baseline warmup of `40`.

The first warmup-40 prelaunch run confirmed that the previously blocked
`20210123` / `exAL-M-T0` / `q05` lane is stabilized by the longer warmup:

- validation outdir:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/prelaunch_validation_20260613_warmup40`
- full-pipeline multivariate q05 health:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/prelaunch_validation_20260613_warmup40/smoke_runs/full_pipeline/quantile/exdqlm_multivar_drop/20210123/full_pipeline_exdqlm_multivar_drop_20210123_qsubset/fit/q=05/outputs/multivar_forecast_health.txt`
- observed health values: `max_abs_history_exps = 11.26204035`
  under the limit `25`, `state_norm_sq_per_T = 51.33741267` under
  the limit `10000`, and terminal status `ok`.

That same validation run then failed in the **univariate AL full-pipeline
post smoke**, not in the model fit. The post error was:
`legacy univariate repair requires at least two fitted quantiles.` The smoke had
only `q05`, whereas the production workflow always runs all seven quantiles and
the post repair contract requires at least two. The template now uses `q05` and
`q50` for the univariate full-pipeline smoke so the validation matches the post
contract while still exercising the low-tail lane.

The corrected warmup-40 validation then passed:

- validation outdir:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/prelaunch_validation_20260613_warmup40_q05q50`
- validation summary:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/prelaunch_validation_20260613_warmup40_q05q50/prelaunch_validation_summary.md`
- generated configs / plan rows / selected rows: `24 / 24 / 24`
- smoke runs: `18 passed`, `0 skipped`
- validation cleanup removed `18` temporary `.RData` files
  (`3,478,685,135` bytes)
- q05 multivariate full-pipeline terminal health:
  `state_norm_sq_per_T = 51.33741267`, `max_E_sigma = 0.2305429405`,
  `max_abs_history_exps = 11.26204035`
- q05 release evidence: after freeze through iteration `40`, iteration `41`
  released gamma/sigma with `sigma_exp = 0.145422`,
  `gamma_exp = -0.002706019`, and bounded `state_norm_sq = 574024.8`;
  terminal iteration `43` had `sigma_exp = 0.1833703`,
  `gamma_exp = -0.009039003`, and `state_norm_sq = 631142.2`
- univariate full-pipeline smoke passed with `q05` and `q50`, resolving the
  prior one-quantile post-contract mismatch.

The actual queue was launched at `2026-06-13T04:50:38Z` with queue controller
PID `3897384` and monitor PID `3897526`. Monitor outputs are written under:

`reports/he2_table1_targeted_repair_20260612_live_warmup40`

This package does not overwrite the publication freeze. It writes to:

- template: `config/he2_bayesian_publication_relaunch_table1_targeted_repair_20260612.template.yaml`
- batch: `config/he2_relaunch_batches/table1_targeted_repair_20260612.yaml`
- runtime root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612`
- campaign spec id: `he2tbl1fix20260612`

## Canonical Input Contract

The package uses the same current shared input-bundle contract as the publication
workflow:

- bundle root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
- bundle run id: `20260510_publication_shared_r01`
- data start: `1987-05-29`
- cutoff-specific historical windows ending at the requested cutoff
- covariates: `PPT`, `SOIL`, and `PCA` as the GDPC alias
- lag/interactions contract inherited from the publication relaunch builder
- scale policy: `log1p_cms` for fit and post internals

## Rerun Scope

The exact selected rows are:

| Cutoff | Manuscript labels |
|---|---|
| `20210123` | `N-M-T0`, `N-M-T1`, `AL-U-T1`, `exAL-U-T1`, `exAL-M-T0` |
| `20211112` | `AL-U-T1`, `exAL-U-T1`, `exAL-M-T0` |
| `20211221` | `N-U-T1`, `N-M-T1`, `AL-U-T1`, `exAL-U-T1`, `exAL-M-T0` |
| `20220511` | `AL-U-T1`, `AL-M-T0`, `AL-M-T1`, `exAL-U-T1`, `exAL-M-T0` |
| `20221225` | `N-U-T1`, `N-M-T1`, `AL-U-T1`, `AL-M-T0`, `exAL-U-T1`, `exAL-M-T0` |

`N-U-T1` and `AL-U-T1` are selected because they were in the requested repair
list. They are not in the 2026-06-12 override table, so their current
publication specs are preserved unless a later explicit override is supplied.

## Supplied Override Specs

| Model type | df_t | df_s1/s2/s67 | df_discrep | lambda | df_trans | df_covs | epsilon | c_factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `N-M-T0`, `N-M-T1` | 0.99999999 | 0.99999999 | 0.99999999 | 0.97 | 0.99999999 | 0.99999999 | NA | 1 |
| `exAL-U-T1` | 0.99999999 | 0.99999999 | NA | 0.97 | 0.9999999 | 0.9999999 | NA | NA |
| `exAL-M-T0` | 0.99999999 | 0.99999999 | 0.99999999 | 0.97 | 0.9999999 | 0.9999999 | 365 | 1 |
| `AL-M-T0` | 0.99999999 | 0.99999999 | 0.99999999 | 0.97 | 0.99999999 | 0.99999999 | 365 | 1 |
| `AL-M-T1` | 0.9999999 | 0.9999999 | 0.9999999 | 0.97 | 0.9999999 | 0.9999999 | 365 | 1 |

The active fit epsilon for multivariate AL/exAL rows is written under:

`fit.exdqlm_multivar.legacy.forecast_cov`

The state discount factors are written under the active model key:

- `models.ndlm_main.state_evolution` for `N-M-T0` / `N-M-T1`
- `models.exdqlm_univar.state_evolution` for `exAL-U-T1`
- `models.exdqlm_multivar.state_evolution` for `exAL-M-T0`, `AL-M-T0`, and `AL-M-T1`

## Runtime Policy

- The queue defaults to two run-level launches at once, so quantile families use
  up to roughly 14 fit workers when two seven-quantile rows are active.
- The heavy cutoff can run alongside one ordinary row, but only one heavy cutoff
  row is allowed at a time.
- The normal queue path uses `scripts/run_unified_with_cleanup.sh`; therefore
  `.RData` files are cleaned after post by default and the cleanup count is
  recorded in each run manifest.
- All selected quantile-family rows now use a warmup-freeze policy of `40`
  iterations before gamma/sigma updates are allowed. Normal/NDLM rows do not
  use the `s_t` / `u_t` / gamma-sigma VB layer and therefore do not have the
  same warmup semantics.
- The univariate AL full-pipeline smoke must include at least two quantiles;
  for this package it is pinned to `q05` and `q50`.

## Validation Commands

The NDLM fit smoke is intentionally capped at one full-history iteration. A
first attempted `max_iter=10` smoke showed that one NDLM iteration on the
1987-to-2021 history took roughly eight minutes, so a 10-iteration smoke would
turn prelaunch validation into an hour-scale job. The single-iteration smoke
still verifies the patched NDLM discount path and canonical input handoff.

Build only:

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_table1_targeted_repair_20260612.template.yaml
```

Prelaunch validation:

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_table1_targeted_repair_20260612.template.yaml \
  --outdir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/prelaunch_validation_20260612
```

Dry-run launch command:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_table1_targeted_repair_20260612.template.yaml \
  --dry-run
```

Actual launch:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_table1_targeted_repair_20260612.template.yaml \
  --skip-validate \
  --reset-state \
  --start-monitor \
  --monitor-out-dir reports/he2_table1_targeted_repair_20260612_live_warmup40 \
  --monitor-interval 300 \
  --monitor-max-snapshots 288
```

## Acceptance Gates

Before the repaired rows can replace Table 1 values:

1. `frozen_spec_manifest.csv` must match the supplied override table exactly for
   all overridden rows.
2. `cutoff_bundle_audit.csv` must show the canonical shared bundle for each
   selected cutoff.
3. Every selected run must pass `report`.
4. Compare outputs must be built for the repair campaign.
5. CRPS values must be merged into the corrected article Table 1 source.
6. The revised article, corrections article, and workflow repo must all point to
   the same authoritative source manifest after promotion.

# HE2 AL-M-T0 P5 Production Workflow Promotion - 2026-06-06

## Decision

Promote P5 as the default AL-M-T0 production rebuild workflow.

As of the P5 production closeout, this is also a publication-table promotion:
the five canonical cutoffs passed fit/post/validate/report, CRPS extraction,
publication figure manifest generation, canonical-bundle checks, and
post-success heavy-artifact cleanup.

## Authoritative Production Contract

- source family: `exAL-M-T0` / `exdqlm_multivar_drop`
- target family: `AL-M-T0` / `dqlm_multivar_al_drop`
- source root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602`
- target production root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p5_production_20260606`
- canonical bundle: 20260510 publication shared inputs
- data start: `1987-05-29`
- cutoffs: `20210123`, `20211112`, `20211221`, `20220511`, `20221225`
- active quantiles: `q05`, `q20`, `q35`, `q50`, `q65`, `q80`, `q95`
- transfer mode: `drop`
- likelihood switch: `exal -> al`
- preserved from source: input paths, cutoff dates, data start, transfer
  covariates/features, harmonic structure, active quantiles, and scale
  contract
- policy overlay:
  `config/he2_relaunch_batches/al_m_t0_p5_q65_q80_warmup40_postsave_overlay_20260606.yaml`

P5 policy summary:

| field | value |
|---|---|
| `df_t` | `0.99999999` |
| `df_s1`, `df_s2`, `df_s67`, `df_discrep` | `0.99999999` |
| `lambda` | `0.97` |
| `df_trans`, `df_covs` | `0.99999999` |
| `epsilon` | `365.0` |
| `c_factor` | `1.0` |
| base `max_iter` | `160` |
| q65 `max_iter` | `220` |
| q65/q80 warm-up freeze | `40` |
| q50 old override | dropped |
| state-freeze overrides | disallowed |
| post-save objective bridge | enabled, hardened after save |

## Runtime Evidence

Isolated diagnostic root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p5_postsave_warmup40_q80_20260606`

Diagnostic row:

`multimodel_20210123_v8_he2pubgdpc1r1_dqlm_multivar_al_drop_p5_warmup40_postsave_q80_fitonly_20260606`

Evidence from `fit/q=80/logs/fit.log`:

| line | evidence |
|---:|---|
| 111 | `warmup_freeze_iters=40`, `min_update_iters=50`, `min_total_iters=50`, `max_iter=160` |
| 630 | `iter=160`, `gamsig_update_iters=120`, `sigma_exp=0.06349834`, `gamma_exp=0`, `state_norm_sq=113508` |
| 1619 | sampling completed |
| 1620 | RData variables saved |
| 1621 | post-save forecast-error sample finite and covariance-Cholesky check passed |
| 1622 | old KL metric covariance failure caught as non-fatal |
| 1623 | empirical-Gaussian KL fallback logged |

Evidence from `fit/logs/fit_stage.log:4`:

- `stage_fit complete`

Tracked runtime summary:

`reports/he2_al_m_t0_p5_postsave_warmup40_q80_20260606/P5_Q80_REPAIR_SUMMARY.md`

## Promoted Wiring

| component | promoted behavior |
|---|---|
| `scripts/build_he2_dqlm_multivar_al_drop_from_exal_drop.py` | defaults to P5 policy and P5 production root |
| `scripts/validate_he2_dqlm_multivar_al_drop_from_exal_drop_prelaunch.py` | validates P5 by default |
| `scripts/launch_he2_remaining_quantile_al_exal.py` | includes AL-M-T0 by default under P5 |
| `--skip-al-drop` | opt-out for combined launcher |
| `--include-blocked-al-drop` | deprecated no-op kept for old commands |
| `--no-policy-spec` | raw historical exAL-to-AL clone diagnostic only |

## Prelaunch Gate

Run before any broad relaunch:

```bash
python3 -m unittest tests.python.test_he2_remaining_quantile_al_exal_relaunch -v

python3 scripts/validate_he2_dqlm_multivar_al_drop_from_exal_drop_prelaunch.py \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p5_production_20260606 \
  --policy-spec-yaml config/he2_relaunch_batches/al_m_t0_p5_q65_q80_warmup40_postsave_overlay_20260606.yaml \
  --skip-smoke
```

The validator must confirm generated config parity, policy overlay application,
canonical source cleanup, and Python compile checks.

## Publication Promotion Gate

The AL-M-T0 publication promotion gate is closed. All five cutoff rows passed:

- fit stage;
- post stage;
- validate stage;
- report stage;
- CRPS forecast summary extraction;
- publication figure manifest generation;
- canonical-bundle parity checks;
- no retained `.RData`, `.rda`, or `.Rda` after successful post cleanup.

Failures should remain visible in the matrix status rather than being silently
retried or hidden.

Closeout evidence:

- `docs/he2_al_m_t0_p5_production_closeout_20260606.md`
- `reports/he2_al_m_t0_p5_production_closeout_20260606/P5_PRODUCTION_CLOSEOUT.md`
- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.md`

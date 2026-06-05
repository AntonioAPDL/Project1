# HE2 AL-M-T0 P3 Production Promotion Plan - 2026-06-05

## Purpose

This note turns the completed AL-M-T0 P3 diagnostic into a production promotion
path for the manuscript-facing Bayesian HE2 table.

The diagnostic finding is recorded in:

`docs/he2_al_m_t0_scale_state_diagnostic_findings_20260604.md`

The important distinction is:

- P3 diagnostic evidence is complete and successful.
- AL-M-T0 is not yet promoted into the publication manifest because the P3 run
  was representative, fit-focused, and transfer-level-only.
- The next step must be a full-design, full-pipeline smoke before any five-cutoff
  production launch.

## Current Publication State

The publication parity gate currently reports:

| Status | Count |
|---|---:|
| promoted rows | 25 |
| pending rows | 20 |
| blocked rows | 5 |
| final 9-model benchmark ready | false |

Promoted families:

| label | family |
|---|---|
| `exAL-M-T1` | `exdqlm_multivar_keep` |
| `AL-M-T1` | `dqlm_multivar_al_keep` |
| `exAL-M-T0` | `exdqlm_multivar_drop` |
| `AL-U-T1` | `dqlm_univar_al` |
| `exAL-U-T1` | `exdqlm_univar` |

Pending families:

| label | reason |
|---|---|
| `AL-M-T0` | diagnostically unblocked but not production-promoted |
| `N-U-T1` | still needs canonical-bundle rerun/promotion |
| `N-M-T0` | still needs canonical-bundle rerun/promotion |
| `N-M-T1` | still needs canonical-bundle rerun/promotion |

## Production P3 Overlay

Tracked overlay:

`config/he2_relaunch_batches/al_m_t0_p3_production_overlay_20260605.yaml`

The overlay is applied explicitly by:

`scripts/build_he2_dqlm_multivar_al_drop_from_exal_drop.py --policy-spec-yaml ...`

It preserves from the promoted `exAL-M-T0` source configs:

- canonical 20260510 input bundle;
- data start `1987-05-29`;
- cutoff-specific retros and forecast files;
- full transfer-drop design;
- covariates `PPT`, `SOIL`, `PCA`;
- covariate lags `1,2,3`;
- square terms and PPT-SOIL interaction;
- harmonic indices `[1,2,3]`;
- log1p-only legacy fit/post scale;
- all seven quantiles.

It intentionally changes:

| Field | P3 production value |
|---|---|
| `models.exdqlm_multivar.likelihood_mode` | `al` |
| `state_evolution.df_*` | `0.99999999` for trend/seasonal/discrepancy/transfer/covariate blocks |
| `lambda` | `0.97` |
| `forecast_cov.epsilon` | `365.0` |
| `forecast_cov.c_factor` | `1.0` |
| `gamma_sigma.max_iter` | `160` |
| `gamma_sigma.min_update_iters` | `50` |
| `gamma_sigma.min_total_iters` | `50` |
| q35/q65 `freeze_target` | `gamma_sigma` |
| q35/q65 state guard | enabled |
| q35/q65 terminal sampling guard | `fail_fast` |
| legacy fit-save bridge | `post_save_objective_enabled=true` |

It also intentionally drops the stale source q50 `freeze_target=states`
gamma/sigma override from the earlier exAL-M-T0 repair campaign. The q50
override was valid context for that source campaign, but it is not part of the
P3 AL-M-T0 production policy. The builder records this as
`debug_he2_dqlm_al_drop_policy_overlay.gamma_sigma_dropped_quantile_overrides`,
and the validator now blocks any P3 production config that still contains a
quantile-level `freeze_target=states` override.

## Smoke Gate

Smoke artifact root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p3_smoke_20260605`

Smoke cutoffs:

| cutoff | reason |
|---|---|
| `20211112` | representative q35 risk lane in diagnostics |
| `20220511` | representative q65 risk lane in diagnostics |

Smoke must run all seven quantiles and the full post/validate/report pipeline.
Cleanup after post must be enabled.

Acceptance gates:

1. Both run manifests have `fit`, `post`, `validate`, and `report` as `pass`.
2. Every quantile has terminal health pass.
3. No q-lane has terminal two-cycle.
4. CRPS tables exist under each post output directory.
5. `publication_figure_manifest.csv` exists.
6. No `.RData`, `.rda`, or `.Rda` remains under successful run roots after post.
7. Any failure is kept as an explicit row and blocks promotion.

## Full Production Gate

Only after the two-cutoff smoke passes, prepare the full root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p3_production_20260605`

Full cutoffs:

- `20210123`
- `20211112`
- `20211221`
- `20220511`
- `20221225`

Queue policy:

- run two cutoff rows at once;
- one core per quantile model, seven workers per cutoff;
- cleanup after post enabled;
- continue-on-fail enabled;
- skip compare bundles during queue, aggregate CRPS/report afterward.

If the full production launch passes all gates, update:

- `scripts/build_he2_bayesian_publication_manifest.py`
- `scripts/build_he2_publication_parity_gate.py`
- related tests

Expected manifest transition after successful AL-M-T0 promotion:

| Gate | Before | After |
|---|---:|---:|
| promoted rows | 25 | 30 |
| pending rows | 20 | 15 |
| blocked rows | 5 | 0 for AL-M-T0 |

The three NDLM families will still block the final 9-model benchmark until they
are rerun or promoted on the same canonical 20260510 bundle.

## Commands

No-launch smoke validation:

```bash
python3 scripts/validate_he2_dqlm_multivar_al_drop_from_exal_drop_prelaunch.py \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p3_smoke_20260605 \
  --policy-spec-yaml config/he2_relaunch_batches/al_m_t0_p3_production_overlay_20260605.yaml \
  --cutoffs 20211112,20220511 \
  --skip-smoke \
  --outdir reports/he2_al_m_t0_p3_production_smoke_20260605/prelaunch_validation
```

Smoke launch:

```bash
python3 scripts/run_multimodel_v8_queue.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p3_smoke_20260605/control/publication_relaunch_matrix \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p3_smoke_20260605 \
  --ordinary-max-concurrent 2 \
  --pause-free-gb 25 \
  --launch-free-gb 35 \
  --heavy-free-gb 35 \
  --heavy-cutoff-max-concurrent 2 \
  --poll-seconds 30 \
  --continue-on-fail \
  --skip-compares \
  --no-heavy-cutoff-blocks-ordinary
```

Focused tests:

```bash
python3 -m unittest \
  tests.python.test_he2_remaining_quantile_al_exal_relaunch \
  tests.python.test_he2_al_m_t0_diagnostic_plan \
  tests.python.test_disc_sampling_diagnostics_source_contract \
  tests.python.test_he2_al_m_t0_gamsig_cycle_audit \
  -v
```

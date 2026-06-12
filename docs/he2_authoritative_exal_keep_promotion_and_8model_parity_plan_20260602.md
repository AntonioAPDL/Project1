# HE2 Authoritative exAL-M-T1 Promotion And 8-Model Parity Plan

Date: 2026-06-02

## Current Decision

2026-06-08 supersession note: this historical parity plan has been closed by
`docs/he2_publication_manifest_promotion_closeout_20260608.md`. The full
9-model benchmark now has 45 promoted rows, 0 pending rows, and the NDLM
families resolve to the June 7 promotion root.

The authoritative HE2 `exAL-M-T1` / `exdqlm_multivar_keep` results are the five CRPS-selected winners in:

`docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`

Those winners are from the completed canonical-input 20260524 epsilon/discount grid and use the 20260510 shared input
bundle:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`

The full 9-model HE2 Bayesian benchmark is now paper-ready for the current
snapshot. As of the 2026-06-08 closeout, all nine families are
canonical-bundle promoted, including the three NDLM Bayesian comparison
families.

Promotion update:

`docs/he2_three_family_publication_manifest_promotion_20260603.md` and `docs/he2_al_m_t0_p5_production_closeout_20260606.md`

## Promoted exAL-M-T1 Winners

| cutoff | spec | run id | mean CRPS |
| --- | --- | --- | ---: |
| 20210123 | `c04_eps365` | `multimodel_20210123_v8_he2grid_c04_eps365_exdqlm_multivar_keep` | 0.139709 |
| 20211112 | `c04_eps365` | `multimodel_20211112_v8_he2grid_c04_eps365_exdqlm_multivar_keep` | 0.047236 |
| 20211221 | `c03_eps030` | `multimodel_20211221_v8_he2grid_c03_eps030_exdqlm_multivar_keep` | 0.265372 |
| 20220511 | `c02_eps060` | `multimodel_20220511_v8_he2grid_c02_eps060_exdqlm_multivar_keep` | 0.032325 |
| 20221225 | `c05_eps030` | `multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep` | 0.665460 |

The source configuration and post-output validation matrix is generated under:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524/control/authoritative_winner_matrix`

Key files in that matrix:

- `matrix_plan.csv`
- `authoritative_winner_manifest_resolved.csv`
- `source_config_manifest.csv`
- `post_output_manifest.csv`
- `AUTHORITATIVE_PRELAUNCH_VALIDATION.md`

## What Was Wired

Project-side source of truth:

- `scripts/he2_exdqlm_keep_authoritative.py` loads and validates the authoritative YAML.
- `scripts/build_he2_exdqlm_multivar_keep_authoritative_matrix.py` freezes the five winner rows, source configs, and post-output hashes.
- `scripts/validate_he2_exdqlm_multivar_keep_authoritative_prelaunch.py` validates run roots, source configs, CRPS, post outputs, cleanup state, scale contract, harmonics, transfer covariates, lags, squares, and interactions.
- `scripts/build_he2_bayesian_publication_manifest.py` now points all nine
  benchmark families to canonical-bundle promoted roots, including the June 7
  NDLM promotion root.
- `scripts/build_he2_publication_parity_gate.py` builds a 45-cell gate: 45
  promoted cells and 0 pending comparison cells.
- `scripts/build_he2_master_workflow_audit_tracker.py` now uses that gate as the current status spine.

Article-side wiring:

- `Evironmetrics---REVISED-DOC-Corrected-2/config/runtime_bindings.json` points `exal_m_t1.keep_runtime_root` at the canonical grid runtime root and records the authoritative YAML path.
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/exal_m_t1_authoritative.py` reads the same YAML for article refresh scripts.
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_exal_m_t1_generated_assets.py` and `refresh_cutoff_synthesis_families.py` now derive the five exAL-M-T1 run IDs from the YAML.
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_current_model_output_support_figures.py` defaults the current-model multivariate support figures to the authoritative 20220511 winner.
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/render_current_model_output_support_figures.R` now supports the no-retained-`.RData` path through retained historical-support summaries.

Figure and table assets:

- The five promoted synthesis figures were rerendered with the fixed common `log1p(cms)` y-axis.
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_all_generated_assets.py --article-root Evironmetrics---REVISED-DOC-Corrected-2` completed successfully after the retained-support repair.
- The project publication manifest and generated tables now carry the promoted `exAL-M-T1`, `AL-M-T1`, `exAL-M-T0`, `AL-M-T0`, `AL-U-T1`, and `exAL-U-T1` rows, while still warning that the 3-family NDLM parity gate is open.

## Current Gate State

The publication manifest currently reports `30` promoted cells, `15` pending cells, and `35 / 50` required within-cutoff
input-alignment checks passing. This is expected in the transition state: the promoted `exAL-M-T1`, `AL-M-T1`,
`exAL-M-T0`, `AL-M-T0`, `AL-U-T1`, and `exAL-U-T1` rows use the canonical 20260510 bundle contract, while the three
NDLM families still point to older campaign roots.

Pending families:

| label | family | target action |
| --- | --- | --- |
| `N-U-T1` | `ndlm_univar_keep` | rerun/promote on 20260510 canonical bundle |
| `N-M-T0` | `ndlm_main_drop` | rerun/promote on 20260510 canonical bundle |
| `N-M-T1` | `ndlm_main_keep` | rerun/promote on 20260510 canonical bundle |

## Closed Package: AL-M-T1 From The exAL-M-T1 Winners

The first pending quantile-family relaunch was `AL-M-T1` / `dqlm_multivar_al_keep`, cloned from the five promoted
`exAL-M-T1` winner configs. This package is now complete and promoted in the project publication manifest.

Dedicated plan:

`docs/he2_al_multivar_keep_from_exal_winners_relaunch_plan_20260602.md`

Promoted artifact root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_from_exal_winners_20260602`

Tooling:

```bash
python3 scripts/build_he2_dqlm_multivar_al_keep_from_exal_winners.py
python3 scripts/validate_he2_dqlm_multivar_al_keep_from_exal_winners_prelaunch.py
python3 -m unittest tests.python.test_he2_dqlm_multivar_al_keep_from_exal_winners -v
```

Hard invariant: generated `AL-M-T1` configs must preserve the source exAL winner `inputs`, `dates`, `scale_contract`,
`stages`, state evolution, structure, transfer covariate engineering, epsilon, c_factor, and `max_iter=100`, while
switching `models.exdqlm_multivar.likelihood_mode` to `al`. The active R workflow supports this switch directly:
`DISC_W_LIKELIHOOD_MODE=al` defines `DISC_W_AL_MODE`, forces gamma to zero, and makes `update_sts(...)` return zero
VB moments for `s_t`.

Runtime result: all five cutoff rows reached `fit/post/validate/report=pass`, local CRPS tables and figure manifests
exist, and post-success `.RData/.rda` cleanup left no retained heavy artifacts.

Follow-on sequence after this package completed and validated:

1. `exAL-M-T0` / `exdqlm_multivar_drop` on the same 20260510 bundle contract: complete and promoted.
2. `AL-M-T0` / `dqlm_multivar_al_drop` as the paired AL run: next quantile-family target.
3. `exAL-U-T1` / `exdqlm_univar`.
4. `AL-U-T1` / `dqlm_univar_al`.
5. remaining NDLM families, unless the manuscript schedule prioritizes NDLM earlier.

## Current exAL-M-T0 Drop Gate

Do not promote the older completed `exAL-M-T0` / `exdqlm_multivar_drop` root as final:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516`

It is useful context because the rows reached `report/pass/closed` and no `.RData/.rda` files remain, but its
post-stage `exdqlm_multivar_synth_drop` draws are pathologically inflated and the CRPS table records very large
`log_cms_plus1` scores. Treat it as a stale/current-code-regression target, not a publication promotion target.

The refreshed current-code `exAL-M-T0` package is now promoted:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602`

Tooling:

```bash
python3 scripts/build_he2_exdqlm_multivar_drop_current_relaunch.py
python3 scripts/validate_he2_exdqlm_multivar_drop_current_prelaunch.py
python3 -m unittest tests.python.test_he2_exdqlm_multivar_drop_current_relaunch -v
```

This package uses the canonical 20260510 input bundle, `data_start=1987-05-29`, `log1p_cms` fit/post scale, `PPT|SOIL|PCA`
transfer covariates with lags `1,2,3`, squares and interaction, explicit `trend + harmonics 1,2,3`, `epsilon=30`,
`c_factor=1`, seven quantile workers per cutoff row, two cutoff rows at a time, post-success heavy-artifact cleanup, and the
promoted `20211112 q50` repair documented in `docs/he2_exdqlm_multivar_drop_q50_repair_promotion_20260602.md`.
Runtime result: all five cutoff rows reached `fit/post/validate/report=pass`, local CRPS tables and figure manifests
exist, post-success `.RData/.rda` cleanup left no retained heavy artifacts, and the 20211112 q50 terminal sampling
failure did not reproduce under the promoted policy.

The overnight sequence used the guarded handoff:

```bash
python3 scripts/launch_he2_exdqlm_drop_after_al_keep.py --poll-seconds 300
```

The handoff refuses to launch if AL-M-T1 failed, if any AL-M-T1 unified run is still active, if the drop matrix already
failed or is active, or if the current-code drop validator fails. Successful launch starts tmux session
`he2_exal_drop_q50repair_20260602` from the generated `launch_current_drop.sh`.

The final benchmark gate is closed only when:

1. all 45 rows are sourced from the same cutoff-specific canonical input bundle;
2. post-stage CRPS, tables, traces, and synthesis figures exist for every row;
3. heavy `.RData/.rda` files are cleaned after post evidence is frozen;
4. `scripts/build_he2_bayesian_publication_manifest.py` reports `50 / 50` required alignment checks;
5. `scripts/build_he2_publication_parity_gate.py` reports `final_9_model_benchmark_ready = true` after the pending rows are actually replaced.

The last condition is intentionally not true today.

## Implementation Plan For The Six Pending Families

1. Source-lock the canonical input bundle.
   Use `20260510_publication_shared_r01`, start date `1987-05-29`, `PPT|SOIL|PCA(alias=GDPC1)`, blended PPT/SOIL
   forecasts, lags `1,2,3`, squares, and interaction.

2. Build one launch matrix per family class.
   Use the promoted current-code multivariate drop package as the starting point for `AL-M-T0`; use the existing
   shared-spec templates as starting points for the univariate and NDLM families:
   `config/he2_bayesian_publication_relaunch_wave_a_ndlm_20260516.template.yaml`,
   `config/he2_bayesian_publication_relaunch_dqlm_univar_al_all_cutoffs_sharedspec_20260517.template.yaml`,
   `config/he2_bayesian_publication_relaunch_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.template.yaml`,
   and `config/he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml`.

3. Run smoke rows before any full launch.
   For quantile families, smoke at least `q05`, `q50`, and `q95` for one wet and one dry cutoff. For NDLM, smoke one
   keep/drop/univar row on one early and one late cutoff.

4. Launch full family batches with post-success cleanup.
   Quantile families should write post evidence first, then remove retained `.RData/.rda` files. NDLM families should
   preserve only the lightweight post outputs needed for metrics and figures.

5. Validate each family before publication promotion.
   Required checks: source-config hashes, input-bundle hash parity, CRPS tables, post-output manifests, synthesis
   figures, trace/state summaries where applicable, no retained heavy artifacts, and successful report stage.

6. Rebuild the publication manifest and article assets.
   Run `scripts/build_he2_bayesian_publication_manifest.py`, `scripts/build_he2_publication_parity_gate.py`, and then
   the article refresh only after every family passes validation.

7. Update manuscript prose only after the 45-row source is final.
   Until then, generated tables and asset manifests should keep the transition warning.

## Reproducibility Commands

```bash
python3 scripts/build_he2_exdqlm_multivar_keep_authoritative_matrix.py
python3 scripts/validate_he2_exdqlm_multivar_keep_authoritative_prelaunch.py
python3 scripts/build_he2_bayesian_publication_manifest.py
python3 scripts/build_he2_publication_parity_gate.py
python3 scripts/build_he2_master_workflow_audit_tracker.py
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_all_generated_assets.py --article-root Evironmetrics---REVISED-DOC-Corrected-2
```

Focused validation:

```bash
python3 -m unittest \
  tests.python.test_he2_exdqlm_keep_authoritative \
  tests.python.test_he2_bayesian_publication_manifest \
  tests.python.test_he2_publication_parity_gate \
  tests.python.test_he2_master_workflow_audit_tracker \
  tests.python.test_revised_article_stage1_refresh_contract -v
```

## Final Takeaway

All nine HE2 Bayesian benchmark families are now reproducibly promoted and
wired through the project manifest. The final 9-model HE2 benchmark is a
fair, reader-reproducible comparison for the current publication snapshot.

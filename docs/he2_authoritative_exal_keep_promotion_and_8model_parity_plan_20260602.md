# HE2 Authoritative exAL-M-T1 Promotion And 8-Model Parity Plan

Date: 2026-06-02

## Current Decision

The authoritative HE2 `exAL-M-T1` / `exdqlm_multivar_keep` results are the five CRPS-selected winners in:

`docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`

Those winners are from the completed canonical-input 20260524 epsilon/discount grid and use the 20260510 shared input
bundle:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`

The full 9-model HE2 Bayesian benchmark is not paper-final yet. The other eight Bayesian comparison families must be
rerun or promoted onto the same canonical 20260510 input-bundle contract before the manuscript table can be interpreted
as a final apples-to-apples comparison.

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
- `scripts/build_he2_bayesian_publication_manifest.py` now points all five `exAL-M-T1` rows to the canonical-grid winners and exposes the remaining 8-family transition gate.
- `scripts/build_he2_publication_parity_gate.py` builds a 45-cell gate: 5 promoted `exAL-M-T1` cells and 40 pending comparison cells.
- `scripts/build_he2_master_workflow_audit_tracker.py` now uses that gate as the current status spine.

Article-side wiring:

- `Evironmetrics---REVISED-DOC-2/config/runtime_bindings.json` points `exal_m_t1.keep_runtime_root` at the canonical grid runtime root and records the authoritative YAML path.
- `Evironmetrics---REVISED-DOC-2/scripts/exal_m_t1_authoritative.py` reads the same YAML for article refresh scripts.
- `Evironmetrics---REVISED-DOC-2/scripts/refresh_exal_m_t1_generated_assets.py` and `refresh_cutoff_synthesis_families.py` now derive the five exAL-M-T1 run IDs from the YAML.
- `Evironmetrics---REVISED-DOC-2/scripts/refresh_current_model_output_support_figures.py` defaults the current-model multivariate support figures to the authoritative 20220511 winner.
- `Evironmetrics---REVISED-DOC-2/scripts/render_current_model_output_support_figures.R` now supports the no-retained-`.RData` path through retained historical-support summaries.

Figure and table assets:

- The five promoted synthesis figures were rerendered with the fixed common `log1p(cms)` y-axis.
- `Evironmetrics---REVISED-DOC-2/scripts/refresh_all_generated_assets.py --article-root Evironmetrics---REVISED-DOC-2` completed successfully after the retained-support repair.
- The article manifest and generated tables now carry the promoted `exAL-M-T1` rows, while still warning that the 8-family parity gate is open.

## Current Gate State

The publication manifest currently reports `35 / 50` required within-cutoff input-alignment checks passing. This is
expected in the transition state: the promoted `exAL-M-T1` rows use the canonical 20260510 bundle, while the other eight
families still point to older campaign roots.

Pending families:

| label | family | target action |
| --- | --- | --- |
| `N-U-T1` | `ndlm_univar_keep` | rerun/promote on 20260510 canonical bundle |
| `N-M-T0` | `ndlm_main_drop` | rerun/promote on 20260510 canonical bundle |
| `N-M-T1` | `ndlm_main_keep` | rerun/promote on 20260510 canonical bundle |
| `AL-U-T1` | `dqlm_univar_al` | rerun/promote on 20260510 canonical bundle |
| `AL-M-T0` | `dqlm_multivar_al_drop` | rerun/promote on 20260510 canonical bundle |
| `AL-M-T1` | `dqlm_multivar_al_keep` | rerun/promote on 20260510 canonical bundle |
| `exAL-U-T1` | `exdqlm_univar` | rerun/promote on 20260510 canonical bundle |
| `exAL-M-T0` | `exdqlm_multivar_drop` | rerun/promote on 20260510 canonical bundle |

## Immediate Next Package: AL-M-T1 From The exAL-M-T1 Winners

The first pending quantile-family relaunch should be `AL-M-T1` / `dqlm_multivar_al_keep`, cloned from the five
promoted `exAL-M-T1` winner configs. This is deliberately not the older shared-spec AL package: the goal is exact
input-bundle and winner-spec parity with the current authoritative exAL keep rows, changing only the active likelihood
from `exal` to `al`.

Dedicated plan:

`docs/he2_al_multivar_keep_from_exal_winners_relaunch_plan_20260602.md`

Prepared no-launch artifact root:

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

Launch policy for this package: two cutoff rows at a time, seven quantile workers per row, maximum 14 active quantile
workers, with post-success `.RData/.rda` cleanup enabled.

Follow-on sequence after this package completes and validates:

1. `exAL-M-T0` / `exdqlm_multivar_drop` on the same 20260510 bundle contract;
2. `AL-M-T0` / `dqlm_multivar_al_drop` as the paired AL run;
3. `exAL-U-T1` / `exdqlm_univar`;
4. `AL-U-T1` / `dqlm_univar_al`;
5. remaining NDLM families, unless the manuscript schedule prioritizes NDLM earlier.

The final benchmark gate is closed only when:

1. all 45 rows are sourced from the same cutoff-specific canonical input bundle;
2. post-stage CRPS, tables, traces, and synthesis figures exist for every row;
3. heavy `.RData/.rda` files are cleaned after post evidence is frozen;
4. `scripts/build_he2_bayesian_publication_manifest.py` reports `50 / 50` required alignment checks;
5. `scripts/build_he2_publication_parity_gate.py` reports `final_9_model_benchmark_ready = true` after the pending rows are actually replaced.

The last condition is intentionally not true today.

## Implementation Plan For The Eight Pending Families

1. Source-lock the canonical input bundle.
   Use `20260510_publication_shared_r01`, start date `1987-05-29`, `PPT|SOIL|PCA(alias=GDPC1)`, blended PPT/SOIL
   forecasts, lags `1,2,3`, squares, and interaction.

2. Build one launch matrix per family class.
   Use the existing shared-spec templates as starting points:
   `config/he2_bayesian_publication_relaunch_wave_a_ndlm_20260516.template.yaml`,
   `config/he2_bayesian_publication_relaunch_dqlm_univar_al_all_cutoffs_sharedspec_20260517.template.yaml`,
   `config/he2_bayesian_publication_relaunch_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.template.yaml`,
   `config/he2_bayesian_publication_relaunch_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.template.yaml`,
   `config/he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml`, and
   `config/he2_bayesian_publication_relaunch_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.template.yaml`.

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
python3 Evironmetrics---REVISED-DOC-2/scripts/refresh_all_generated_assets.py --article-root Evironmetrics---REVISED-DOC-2
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

`exAL-M-T1` is now reproducibly promoted and wired through the project and revised article. The next scientific and
paper-readiness task is not more latent-debugging of that family; it is completing the same-bundle promotion for the
other eight model families so the final 9-model HE2 benchmark becomes a fair, reader-reproducible comparison.

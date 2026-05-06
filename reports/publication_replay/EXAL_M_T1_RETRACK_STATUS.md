# exAL-M-T1 Retrack Status

Date: 2026-05-06

## Scope

This note freezes the current state of the **narrow retrack goal**:

- reproduce and relaunch only the publication-relevant `exAL-M-T1` runs
- keep the runs aligned with the current HE2 CRPS table
- produce the outputs needed to refresh figures and tables for `Evironmetrics---REVISED-DOC-2`

This is **not** a request to reproduce the full 45-cell Bayesian HE2 table.

## Publication source of truth for exAL-M-T1

From `reports/he2_publication_manifest/he2_bayesian_publication_manifest.md`:

| Cutoff | Published CRPS | Run ID | Campaign |
|---|---:|---|---|
| `01/23/2021` | `0.1569` | `multimodel_20210123_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1` | `featurecov_cf1_eps_sweep_20260416` |
| `11/12/2021` | `0.0284` | `multimodel_20211112_v8_eps180cf1_exdqlm_multivar_keep_featurecov_cf1` | `featurecov_cf1_eps_sweep_20260416` |
| `12/21/2021` | `0.2369` | `multimodel_20211221_v8_eps1cf1_exdqlm_multivar_keep_featurecov_cf1` | `featurecov_cf1_eps_sweep_20260416` |
| `05/11/2022` | `0.0210` | `multimodel_20220511_v8_eps180cf1_exdqlm_multivar_keep_featurecov_cf1` | `featurecov_cf1_eps_sweep_20260416` |
| `12/25/2022` | `0.4375` | `multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep` | `exalm_t1_discount_grid_exact_20260424:set09_override` |

## Health check of the current side-work

This health check covers the representative replay work that was launched while debugging reproduction. It is kept here only so we can freeze it and avoid mixing it with the narrower exAL-M-T1 relaunch goal.

| Model | Cutoff | Current status | Fit | Post | Report | Active workers | Health summary |
|---|---|---|---|---|---|---:|---|
| `N-M-T1` | `01/23/2021` | `PASS` | complete | post log inconsistent | report present | `0` | report says pass, but post log still shows an older `isotone` inconsistency |
| `exAL-U-T1` | `01/23/2021` | `INCOMPLETE` | complete | failed | missing | `0` | fit finished, then post failed with headless graphics/X11 issue |
| `exAL-M-T1` | `01/23/2021` | `INCOMPLETE` | complete | failed | missing | `0` | fit finished, then post failed with headless graphics/X11 issue |
| `exAL-M-T1` | `12/25/2022` | `INCOMPLETE` | complete | failed | missing | `0` | fit finished, then post failed with headless graphics/X11 issue |

## Main conclusion

The narrow retrack path is now in a much stronger state:

1. the publication-aligned `exAL-M-T1` fits complete cleanly under the authoritative `R 4.4.0` runtime
2. the exact-snapshot deterministic-climate validation path is now consistent with the copied shared inputs
3. the smoke-fast multivariate post path now emits the posterior tables needed for the revised article

So the remaining work is no longer to debug the basic replay path. It is to finish the same verified path on the remaining publication cutoffs and then lock the final five-run provenance.

## 2026-05-06 implementation update

We applied the minimal headless-safe post fix in the workflow repo:

- `R/environmetrics/00_setup.R`
  - sets `options(bitmapType = "cairo")` when Cairo is available

Then we reran the two narrow `exAL-M-T1` canaries:

1. `01/23/2021`
   - `multimodel_20210123_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1`
2. `12/25/2022`
   - `multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep`

### What improved

The workflow-side fixes are now sufficient to support the narrow article refresh path:

1. `R/environmetrics/00_setup.R`
   - keeps the headless Cairo bitmap fix in place for the multivariate synthesis figures
2. `R/unified/stages/stage_data_prep_shared.R`
   - hydrates deterministic-climate metadata correctly when the run uses an exact copied shared snapshot
3. `R/environmetrics/40_figures_smoke_fast.R`
   - exports the multivariate posterior tables needed for the revised article:
     - `covariate_effects_summary.(csv,tex)`
     - `gamma_summary.(csv,tex)`
     - `sigma_summary.(csv,tex)`
     - `posterior_table_exports_manifest.csv`
     - `posterior_table_exports_README.md`

The fresh canary reruns now produce the key keep-lane synthesis outputs:
- `exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.(png,pdf)`
- `exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.(png,pdf)`
- `exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv`
- `exdqlm_multivar_synth_keep_cutoff_window_sample_subset.csv`

### Current canary status

| Cutoff | Status | Mean CRPS from rerun | Result |
|---|---|---:|---|
| `01/23/2021` | `PASS` | `0.15685973014263893` | matches the published `0.1569` row to rounding; synthesis figures and posterior tables present |
| `12/25/2022` | `PASS` | `0.43752505703872074` | matches the published `0.4375` row to rounding; exact-override deterministic-climate validation now passes |

### Current narrow-replay artifact contract now verified on both canaries

Both canaries now emit:

- synthesis figures:
  - `exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.(png,pdf)`
  - `exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.(png,pdf)`
- synthesis exports:
  - `..._quantiles.csv`
  - `..._sample_subset.csv`
- posterior tables:
  - `covariate_effects_summary.(csv,tex)`
  - `gamma_summary.(csv,tex)`
  - `sigma_summary.(csv,tex)`
  - `posterior_table_exports_manifest.csv`
  - `posterior_table_exports_README.md`
- CRPS tables:
  - `crps_forecast_summary.csv`
  - `crps_forecast_per_time.csv`
  - `crps_input_health.csv`
  - `crps_input_health_per_time.csv`

### Practical interpretation

- the narrow relaunch path is now healthy enough to scale
- the graphics-side blocker for the synthesis figures is resolved
- the exact-snapshot deterministic-climate validation issue is resolved
- the posterior table export gap for `tab:components_23_31` is resolved on the canaries

### Five-run execution status

The same authoritative replay path has now been extended to the remaining three publication-aligned `exAL-M-T1` rows:

1. `11/12/2021`
2. `12/21/2021`
3. `05/11/2022`

Current narrow five-run status:

| Cutoff | Run ID | Status | Mean CRPS from rerun | Notes |
|---|---|---|---:|---|
| `01/23/2021` | `multimodel_20210123_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1` | `PASS` | `0.15685973014263893` | matches the published `0.1569` row to rounding |
| `11/12/2021` | `multimodel_20211112_v8_eps180cf1_exdqlm_multivar_keep_featurecov_cf1` | `PASS` | `0.02838779803717152` | matches the published `0.0284` row to rounding |
| `12/21/2021` | `multimodel_20211221_v8_eps1cf1_exdqlm_multivar_keep_featurecov_cf1` | `RUNNING` | ~ | authoritative replay still in fit stage |
| `05/11/2022` | `multimodel_20220511_v8_eps180cf1_exdqlm_multivar_keep_featurecov_cf1` | `RUNNING` | ~ | authoritative replay still in fit stage |
| `12/25/2022` | `multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep` | `PASS` | `0.43752505703872074` | matches the published `0.4375` row to rounding |

### Current manuscript-side refresh status

The revised article repo has already been refreshed from the verified representative `12/25/2022` selected-model run:

- `DISC/posterior_samples_valid.png`
- `tab:components_23_31`
- `tab:gamma_sigma_intervals1`
- `tab:gamma_sigma_intervals2`
- local copied provenance bundle under `Evironmetrics---REVISED-DOC-2/generated/exal_m_t1_20221225/`

### Next execution step

1. let the `12/21/2021` and `05/11/2022` authoritative replays finish
2. verify their CRPS values and artifact contracts
3. then lock the final five-run provenance set for the revised manuscript

## What to ignore from the side-work

The following representative-replay machinery was useful for diagnosis, but it is broader than the narrow exAL-M-T1 relaunch goal:

- `config/publication_replay_representatives_20260506/`
- `config/unified_runs_publication_replay_representatives_20260506/`
- `reports/publication_replay/publication_representative_*`
- `repro/run/PUBLICATION_REPRESENTATIVE_REPLAYS_WORKFLOW.md`

These should be treated as debugging/support infrastructure, not as the main execution path for the next task.

## Narrow next target

The next operational goal should be:

1. relaunch only the **five publication-relevant `exAL-M-T1` runs** listed above
2. preserve the publication-aligned inputs/specifications associated with the current CRPS table
3. ensure those reruns emit the outputs needed for the revised manuscript:
   - predictive synthesis figures
   - covariate / posterior summary tables
   - any additional figure/table artifacts needed by `Evironmetrics---REVISED-DOC-2`
4. keep the relaunch workflow locked to the verified headless-safe and exact-snapshot-safe path

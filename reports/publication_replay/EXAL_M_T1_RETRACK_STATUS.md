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

The current debugging work established two useful facts:

1. the `exAL-M-T1` **fit stage is reproducible enough to complete** under the corrected runtime path
2. the current blocker has moved to the **post-processing layer**, not the model fitting layer

So the present bottleneck is not the VB fit itself. It is the manuscript-output / post-figure path.

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

- the fresh canary reruns now complete fit and produce the key keep-lane synthesis outputs:
  - `exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.(png,pdf)`
  - `exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.(png,pdf)`
  - `exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv`
  - `exdqlm_multivar_synth_keep_cutoff_window_sample_subset.csv`
- this means the headless graphics failure that previously stopped the replay immediately is no longer blocking the synthesis figures we need for the revised article

### Current canary status

| Cutoff | Status | Mean CRPS from rerun | Result |
|---|---|---:|---|
| `01/23/2021` | `PASS` | `0.15685973014263893` | matches the published `0.1569` row to rounding; canary passes |
| `12/25/2022` | `REPORT_PRESENT` | `0.43752505703872074` | matches the published `0.4375` row to rounding; synthesis outputs present, but validation still fails |

### Remaining blockers before scaling to all five runs

1. Posterior table exports are still missing for both canaries:
   - `covariate_effects_summary.(csv,tex,rds)`
   - `gamma_summary.csv`
   - `sigma_summary.csv`
   - `posterior_table_exports_manifest.csv`
   - `posterior_table_exports_README.md`

2. The `12/25/2022` exact-override canary still reports `validation_status=fail`
   - the failure is now in the deterministic-climate validation block
   - the replay still produced the correct synthesis outputs and the correct mean CRPS
   - so this is no longer a fit/post graphics problem; it is a report/validation consistency problem for the exact-override lane

### Practical interpretation

- the narrow relaunch path is now much healthier than before
- the graphics-side blocker for the article-critical synthesis figures is resolved
- but we should **not** scale to the remaining three cutoffs yet, because the canary gate is not fully green:
  - one canary passes cleanly
  - one canary reproduces the score and figures but still fails the deterministic-climate validation contract
  - neither canary emits the posterior table exports needed for `tab:components_23_31`

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
4. fix or bypass the post-layer graphics issue in the relaunch workflow so the outputs are actually produced headlessly

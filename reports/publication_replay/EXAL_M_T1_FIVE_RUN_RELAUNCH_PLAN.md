# exAL-M-T1 Five-Run Relaunch Plan

Date: 2026-05-06

## Goal

Reproduce and relaunch only the five publication-relevant `exAL-M-T1` runs tied to the current CRPS table, and make those reruns emit the outputs needed to refresh `Evironmetrics---REVISED-DOC-Corrected`.

This is a narrow execution plan. It is **not** a request to rerun the full HE2 table.

## Frozen scope

In scope:
- the five publication-facing `exAL-M-T1` cells in the current HE2 table,
- the post outputs needed to refresh the revised article,
- the minimal fix needed to let those reruns complete headlessly.

Out of scope:
- rerunning all HE2 families,
- reworking the broader representative-replay machinery,
- changing the current HE2 publication source of truth.

## Source of truth

Use these in this order:

1. `reports/he2_publication_manifest/he2_bayesian_publication_manifest.md`
2. `reports/publication_replay/EXAL_M_T1_RETRACK_STATUS.md`
3. `Evironmetrics---REVISED-DOC-Corrected/FIGURE_TABLE_PROVENANCE.md`
4. `Evironmetrics---REVISED-DOC-Corrected/wileyNJD-APA.tex`

## Exact five-run publication lineage

| Cutoff | Published CRPS | Run ID | Campaign | Epsilon | Discount block |
|---|---:|---|---|---:|---|
| `01/23/2021` | `0.1569` | `multimodel_20210123_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1` | `multimodel_v8_featurecov_cf1_eps_sweep_20260416` | `360` | baseline featurecov-cf1 |
| `11/12/2021` | `0.0284` | `multimodel_20211112_v8_eps180cf1_exdqlm_multivar_keep_featurecov_cf1` | `multimodel_v8_featurecov_cf1_eps_sweep_20260416` | `180` | baseline featurecov-cf1 |
| `12/21/2021` | `0.2369` | `multimodel_20211221_v8_eps1cf1_exdqlm_multivar_keep_featurecov_cf1` | `multimodel_v8_featurecov_cf1_eps_sweep_20260416` | `1` | baseline featurecov-cf1 |
| `05/11/2022` | `0.0210` | `multimodel_20220511_v8_eps180cf1_exdqlm_multivar_keep_featurecov_cf1` | `multimodel_v8_featurecov_cf1_eps_sweep_20260416` | `180` | baseline featurecov-cf1 |
| `12/25/2022` | `0.4375` | `multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep` | `multimodel_v8_exalm_t1_discount_grid_exact_20260424` | `360` | exact `set09` override |

### Discount blocks

Baseline featurecov-cf1 block:
- `df_t = 0.99999999`
- `df_s1 = 0.9999`
- `df_s2 = 0.9999`
- `df_s67 = 0.9999`
- `df_discrep = 0.999`
- `lambda = 0.97`
- `df_trans = 0.9999999`
- `df_covs = 0.99999`

Exact `set09` override block for `12/25/2022`:
- `df_t = 0.99999999`
- `df_s1 = 0.9998`
- `df_s2 = 0.9998`
- `df_s67 = 0.9999`
- `df_discrep = 0.998`
- `lambda = 0.97`
- `df_trans = 0.9999999`
- `df_covs = 0.9999999`

## Covariate and input contract

The relaunches should preserve the corrected featurecov/blended-input contract already visible in the publication-aligned resolved configs:
- fit covariates: `PPT`, `SOIL`, `PCA`
- deterministic climate: enabled
- forecast precipitation after the cutoff: enabled
- forecast soil moisture after the cutoff: enabled
- engineered features: lags `1,2,3`, squares, and `PPT x SOIL` interaction
- multivariate exAL keep lane: `likelihood_mode = exal`, `forecast_transfer_mode = keep`

## What the article actually needs

### Phase A: must-have outputs for the revised article

These are the outputs that directly support the current manuscript text and should be treated as the first refresh target.

| Manuscript object | Role in `Evironmetrics---REVISED-DOC-Corrected` | Locked provenance role | Required rerun outputs |
|---|---|---|---|
| `fig:synth1` | main-text predictive synthesis illustration | representative final cutoff `2022-12-25` | `exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.(png,pdf)`, `..._with_raw_ensembles.(png,pdf)`, `..._quantiles.csv`, `..._sample_subset.csv`, `publication_figure_manifest.csv` |
| `tab:components_23_31` | main-text covariate-effects table | representative final cutoff `2022-12-25` | `covariate_effects_summary.(csv,tex,rds)` |
| `fig:synth2` if retained | appendix historical-only contrast figure | representative final cutoff `2022-12-25` | `exdqlm_multivar_synth_drop_cutoff_window_posterior_samples.(png,pdf)`, `..._with_raw_ensembles.(png,pdf)`, `..._quantiles.csv`, `..._sample_subset.csv` |

### Phase B: secondary outputs that should not block the five-run relaunch

These still matter for the article, but they are historical-summary objects rather than the critical five-cell refresh target.

| Manuscript object | Current role | Suggested handling |
|---|---|---|
| `fig:dry_quantile` | main-text historical regime figure | revisit after Phase A; do not block relaunch |
| `fig:rainy_quantile` | main-text historical regime figure | revisit after Phase A; do not block relaunch |
| `fig:80_components` | appendix historical summary | revisit after Phase A |
| `tab:gamma_sigma_intervals1` | appendix `gamma` summary | revisit after Phase A |
| `tab:gamma_sigma_intervals2` | appendix `sigma` summary | revisit after Phase A |

## Audit findings that matter for the relaunch

### 1. The original publication-aligned source runs already prove the model itself can complete post

For both the standard cf1 lineage and the `12/25/2022` exact override, the existing publication runs already contain:
- `publication_figure_manifest.csv`
- `exdqlm_multivar_synth_keep_cutoff_window_posterior_samples.(png,pdf)`
- `exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.(png,pdf)`
- `exdqlm_multivar_synth_keep_cutoff_window_quantiles.csv`
- `exdqlm_multivar_synth_keep_cutoff_window_sample_subset.csv`

So the current problem is not that `exAL-M-T1` is incapable of producing the needed figures.

### 2. Posterior table exports are still the main gap

The publication-aligned source runs have:
- `post.export_tables = TRUE`

But the actual post outputs do **not** currently include:
- `covariate_effects_summary.csv`
- `gamma_summary.csv`
- `sigma_summary.csv`
- `posterior_table_exports_manifest.csv`

So the rerun acceptance contract must require the files themselves, not just the config flag.

### 3. The current replay failure is a headless post issue, not a fit issue

The side-work representative replays for:
- `20210123 exAL-M-T1`
- `20221225 exAL-M-T1`

both completed fit and then failed in `40_figures_smoke_fast.R` with:
- `unable to start device PNG`
- `unable to open connection to X11 display ''`

Relevant evidence:
- replay log: `.../multimodel_v8_publication_replay_representatives_20260506/.../post/logs/post_runner.log`
- smoke-fast plot entry: `R/environmetrics/40_figures_smoke_fast.R`
- current device helper: `R/environmetrics/utils_plot.R`

## Minimal post-layer fix to try first

The smallest defensible fix is:

1. set `options(bitmapType = "cairo")` early in `R/environmetrics/00_setup.R`
2. rerun one canary from each exAL-M-T1 lineage

Why this is the right first move:
- the failing replay stack is calling `png(...)` headlessly,
- the failure is consistent with X11-backed PNG device selection,
- and a local headless check already succeeds with `options(bitmapType = "cairo")` before `png(...)`.

### Recommended defensive hardening

If step 1 alone is not enough, then apply this secondary hardening:
- change `open_png()` in `R/environmetrics/utils_plot.R` to call `png(..., type = "cairo")`

This is low risk, but it does **not** cover the bare `png(...)` calls still present in `40_figures_smoke_fast.R`, so it should be treated as a companion hardening step rather than the primary fix.

### What not to do first

Do **not** start by rewriting the entire figure stack.

The narrow goal is to get the five publication-relevant `exAL-M-T1` reruns back onto the same successful path the original source campaigns already used, with one minimal headless-safe adjustment.

## Recommended execution order

### Step 1. Freeze the five-run execution contract

Use only the five runs listed above. Do not expand to the broader publication replay matrix.

### Step 2. Apply the minimal headless post fix

First attempt:
- `options(bitmapType = "cairo")` in `R/environmetrics/00_setup.R`

Fallback only if needed:
- harden `open_png()` with `type = "cairo"`

### Step 3. Rerun two canaries, not all five at once

Use one canary from each distinct exAL-M-T1 lineage:

1. standard cf1 lineage:
- `01/23/2021`
- `multimodel_20210123_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1`

2. exact override lineage:
- `12/25/2022`
- `multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep`

### Step 4. Canary acceptance checks

A canary passes only if all of the following are true:
- fit completes
- post completes
- reported CRPS matches the published table value
- keep-lane synthesis figures are present
- representative `2022-12-25` rerun emits `covariate_effects_summary.(csv,tex,rds)`
- no X11/PNG headless failure remains

### Step 5. Scale to the remaining three cf1 cutoffs

Only after both canaries pass:
- `11/12/2021`
- `12/21/2021`
- `05/11/2022`

### Step 6. Refresh the revised article from those reruns only

Refresh `Evironmetrics---REVISED-DOC-Corrected` from the newly verified rerun outputs, starting with:
- `fig:synth1`
- `tab:components_23_31`
- `fig:synth2` if retained

### Step 7. Revisit Phase B historical-summary objects

Only after Phase A is stable, decide whether to regenerate or relabel:
- `fig:dry_quantile`
- `fig:rainy_quantile`
- `fig:80_components`
- `tab:gamma_sigma_intervals1`
- `tab:gamma_sigma_intervals2`

## Deliverables from this plan

When the plan is executed successfully, we should have:
- five reproducible `exAL-M-T1` reruns aligned with the current CRPS table,
- a verified headless-safe post path for those reruns,
- refreshed Section 5 assets for `Evironmetrics---REVISED-DOC-Corrected`,
- and a clean boundary between the narrow exAL-M-T1 refresh and the broader HE2 replay scaffolding.

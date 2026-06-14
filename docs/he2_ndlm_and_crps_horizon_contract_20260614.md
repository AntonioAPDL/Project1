# HE2 NDLM And CRPS Horizon Contract

Date: 2026-06-14

This note records two corrections to the HE2 publication wiring:

1. `N-M-T1` is a normal multivariate dynamic linear model baseline, not a
   quantile-lane exDQLM fit.
2. Raw NWS CRPS must not be mixed into the 28-day benchmark table because the
   archived NWS products provide eight valid daily forecast leads for the
   rolling-origin cutoffs used here.

## NDLM Clarification

The `N-M-T1` manuscript label resolves through the publication manifest to
family `ndlm_main_keep` and likelihood mode `normal`:

- revised article artifact:
  `Evironmetrics---REVISED-DOC-Corrected-2/artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv`
- manifest builder:
  `scripts/build_he2_bayesian_publication_manifest.py`
- NDLM constants:
  `R/unified/families/ndlm_main/00_constants.R`
- NDLM exact update implementation:
  `R/unified/families/ndlm_main/08_vb_cavi_exact.R`

The active NDLM update is Gaussian/Kalman. In
`R/unified/families/ndlm_main/08_vb_cavi_exact.R`,
`ndlm_exact_hist_forward_pass()` builds historical observation rows for USGS,
GloFAS, and NWS and passes them to `ndlm_exact_sequential_update()` with
source-specific Gaussian observation variances. There is no fitted asymmetric
Laplace or extended asymmetric Laplace latent-scale update in this path, and
therefore no fitted `s_t` or `u_t` lane for `N-M-T1`.

The source of confusion is post-processing language: posterior predictive
samples from the normal NDLM are summarized by predictive quantiles and scored
by CRPS using the same exported CRPS machinery as the quantile-likelihood
families. Those predictive quantiles are scoring summaries, not fitted target
quantile levels.

## CRPS Horizon Split

Before this patch, the revised article's main HE2 CRPS table combined:

- 28-day CRPS averages for Bayesian models;
- 28-day CRPS averages for raw GloFAS;
- 8-day CRPS averages for raw NWS.

That was not a valid single-horizon comparison. The post-stage already exports
per-time CRPS rows through:

- `R/environmetrics/40_figures.R`
- `R/environmetrics/02_helpers_core.R`

The article-side refresh now freezes
`crps_forecast_per_time.csv` for each authoritative selected `exAL-M-T1`
cutoff under:

`Evironmetrics---REVISED-DOC-Corrected-2/artifacts/five_cutoff_crps_validation_sources/<cutoff>_exal_m_t1/`

The generated article tables now use two explicit contracts:

| Table | Horizon | Raw rows | Bayesian rows |
| --- | ---: | --- | --- |
| `tab:benchmark_crps_models` | 28 days | `RAW-GLOFAS` only | all nine Bayesian families |
| `tab:benchmark_crps_models_nws_horizon` | 8 days | `RAW-GLOFAS`, `RAW-NWS` | all nine Bayesian families restricted to leads 1--8 |

The cell-level audit file is:

`Evironmetrics---REVISED-DOC-Corrected-2/tables/generated_tex/benchmark_crps_horizon_summary.csv`

Each row records the table label, manuscript row label, cutoff, horizon length,
source path, selector used (`model_id` for raw rows, `model_variant` for
Bayesian rows), and exact mean CRPS before five-decimal rendering.

## Implementation Files

Revised article repo:

- `scripts/refresh_exal_m_t1_generated_assets.py`
  - now copies per-time CRPS files into the five-cutoff source bundle.
- `scripts/build_generated_table_includes.py`
  - generates the 28-day table and the NWS-horizon table.
  - uses leads 1--28 for `tab:benchmark_crps_models`.
  - uses leads 1--8 for `tab:benchmark_crps_models_nws_horizon`.
- `scripts/article_repo_layout.py`
  - declares the new generated TeX filenames.
- `MANUSCRIPT_ASSET_MANIFEST.json`
  - declares both table labels and their source contracts.
- `wileyNJD-APA.tex`
  - clarifies that the `N` rows are normal DLM baselines, not quantile-lane
    fits.
  - includes the new NWS-horizon table after the 28-day table.
- `tests/test_article_a1_and_table_contracts.py`
  - asserts that the 28-day table excludes `RAW-NWS`.
  - asserts that the NWS-horizon table includes both raw baselines and documents
    leads 1--8.

Workflow repo:

- `scripts/validate_revision_cross_repo_wiring.py`
  - now reconstructs the HE2 28-day and 8-day expected values from per-time CRPS
    sources.
  - compares the corrections HE2 table to the 28-day contract.
  - rejects stale prose claiming that raw NWS is best "overall" in the mixed
    28-day table.

Corrections repo:

- `/data/muscat_data/jaguir26/Corrections---Project-1/main.tex`
  - now describes the split horizon policy.
- `/data/muscat_data/jaguir26/Corrections---Project-1/tables/generated_tex/he2_benchmark_crps_response_table.tex`
  - synced from the revised article 28-day HE2 table body.

## Remaining Watch Item

The HE3 ablation response table still includes raw forecast rows as references.
The current patch fixes the primary HE2 benchmark table and the new NWS-horizon
companion table. A separate HE3 policy decision is still needed if we want the
ablation raw-reference rows to follow the exact same split-horizon treatment.

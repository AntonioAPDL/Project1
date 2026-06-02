# exDQLM Multivariate Keep Authoritative Refocus

Date: 2026-06-01 PDT / 2026-06-02 UTC

## Executive Decision

The apparent 20220511 failure is no longer treated as an algorithmic failure. The issue that triggered the latest
diagnostic loop was the plotting scale used for the cutoff-window synthesis figure. Once the synthesis plots were
rendered on a common `0` to `6.5` `log1p(cms)` scale, the current cutoff-window figures looked coherent.

The production-authoritative exDQLM multivariate `keep` specification set is therefore the completed canonical-input
grid winner set from:

```text
reports/exdqlm_multivar_keep_grid_eval_guard_promotion_final_20260530/combined_winners_by_cutoff.csv
```

The high-discount 20220511 experiment is diagnostic only. It confirms that the workflow can produce visually stable
figures under very high discounts, but its forecast-window CRPS is worse than the canonical-grid 20220511 winner.

The GDPC6 20221225 experiment is a strong off-grid candidate, not a silent replacement for the canonical all-cutoff
bundle. It improves 20221225 mean CRPS in one isolated covariate-bundle experiment, but it was not evaluated across all
cutoffs or all discount/epsilon cases. Promote it only after an explicit covariate-bundle comparison.

## Evidence Backbone

Tracked decision and workflow notes:

- `docs/exdqlm_multivar_keep_grid_guard_promotion_readout_20260530.md`
- `docs/exdqlm_multivar_keep_diagnostics_promotion_20260531.md`
- `docs/canonical_gdpc_subset6_noi_soi_espi_pna_whwp_amo_20260527.md`
- this note and `docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`

Untracked runtime/report evidence:

- `reports/exdqlm_multivar_keep_grid_eval_guard_promotion_final_20260530/combined_winners_by_cutoff.csv`
- `reports/exdqlm_multivar_keep_grid_eval_guard_promotion_final_20260530/combined_raw_controls_for_winners.csv`
- `reports/phase_b_20220511_c02_vs_c06_numerical_comparison_20260601/README.md`
- `reports/he2_exdqlm_multivar_keep_20220511_phaseb_vb_latent_audit_20260531/COMPONENT_DIAGNOSTIC_FINDINGS.md`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20220511_highdf_staticdiag_20260601`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_gdpc6_bestc04eps030_20260527`

Current plotting repair to commit:

- `config/post_publication_figures.yaml` now sets shared `y_limits: [0, 6.5]`.
- `R/unified/post_publication_figures.R` resolves shared y-limits before optional cutoff-specific overrides.
- `R/environmetrics/40_figures_smoke_fast.R` uses fixed synthesis y-limits, with
  `UNIFIED_POST_SYNTHESIS_Y_LIMITS` as an explicit override.
- `tests/testthat/test_post_publication_figures.R` covers shared limits and the fallback cutoff-specific path.

## Production-Authoritative Canonical Grid Winners

These are the winners from the completed 150-cell canonical grid after failed-row recovery. They use the canonical
20260510 shared input bundle and the operational `max_iter = 100` gamma/sigma contract.

| cutoff | authoritative spec | epsilon | c_factor | df_t | df_s1 | df_s2 | df_s67 | df_discrep | lambda | df_trans | df_covs | mean CRPS | median CRPS | runner-up diff |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 20210123 | `c04_eps365` | 365 | 1.0 | 0.9995 | 0.999 | 0.999 | 0.9995 | 0.999 | 0.97 | 0.9999999 | 0.99999 | 0.139709 | 0.083939 | 0.003311 |
| 20211112 | `c04_eps365` | 365 | 1.0 | 0.9995 | 0.999 | 0.999 | 0.9995 | 0.999 | 0.97 | 0.9999999 | 0.99999 | 0.047236 | 0.044288 | 0.001290 |
| 20211221 | `c03_eps030` | 30 | 1.0 | 0.99995 | 0.9995 | 0.9995 | 0.9995 | 0.999 | 0.97 | 0.9999999 | 0.99999 | 0.265372 | 0.137032 | 0.011581 |
| 20220511 | `c02_eps060` | 60 | 1.0 | 0.99995 | 0.9995 | 0.9995 | 0.9995 | 0.999 | 0.97 | 0.9999999 | 0.9999999 | 0.032325 | 0.026597 | 0.000566 |
| 20221225 | `c05_eps030` | 30 | 1.0 | 0.9999 | 0.9993 | 0.9993 | 0.9995 | 0.9988 | 0.97 | 0.9999999 | 0.99999 | 0.665460 | 0.576694 | 0.002168 |

Raw forecast controls for the same winner rows:

| cutoff | spec | synth mean CRPS | GloFAS mean CRPS | NWS/NWM mean CRPS | valid days note |
| --- | --- | ---: | ---: | ---: | --- |
| 20210123 | `c04_eps365` | 0.139709 | 0.403660 | 0.830366 | synthesis/GloFAS 28 days; NWS/NWM 8 days |
| 20211112 | `c04_eps365` | 0.047236 | 0.169575 | 1.371917 | synthesis/GloFAS 28 days; NWS/NWM 8 days |
| 20211221 | `c03_eps030` | 0.265372 | 0.682464 | 0.281176 | synthesis/GloFAS 28 days; NWS/NWM 8 days |
| 20220511 | `c02_eps060` | 0.032325 | 0.272268 | 0.283659 | synthesis/GloFAS 28 days; NWS/NWM 8 days |
| 20221225 | `c05_eps030` | 0.665460 | 1.560064 | 0.556802 | synthesis/GloFAS 28 days; NWS/NWM 8 days |

## Diagnostic Runs Not Promoted As Production Winners

| run family | cutoff | best run/spec in that family | mean CRPS | why it matters | promotion status |
| --- | --- | --- | ---: | --- | --- |
| Phase B health traces | 20220511 | `c02_eps060`, `max_iter = 1000` | 0.031349 | confirms the same discount/epsilon family remains strong when retained for deeper diagnostics | not production-authoritative because it changes the operational iteration contract |
| High-discount static diagnostic | 20220511 | `hidf_eps12000` | 0.055919 | confirms no visual algorithm collapse under common y-scale and extreme discounts | diagnostic only; worse than `c02_eps060` |
| GDPC6 candidate bundle | 20221225 | `c04_eps030_gdpc6` | 0.660578 | one isolated six-index GDPC substitution improves 20221225 CRPS slightly | candidate only; requires controlled all-cutoff covariate-bundle comparison |

## Interpretation Of The 20220511 Diagnostics

The Phase B component audit remains useful but should be interpreted with the corrected plotting context.

Confirmed:

- The saved state/component contracts are coherent: USGS/source locations reconstruct to machine precision in the
  retained diagnostic objects.
- The promoted latent/component audit produces actionable traces for `E[s_t]`, `E[s_t^2]`, `E[u_t]`, `E[1/u_t]`,
  pseudo-data summaries, ELBO, gamma, sigma, and `state_norm_sq / T`.
- The 20220511 `c02_eps060` canonical-grid row is still the best canonical-grid scorer, and the 1000-iteration Phase B
  rerun of the same spec family scores slightly better.
- The high-discount variants all passed fit/post/validate/report, which argues against a hard Kalman or latent-update
  implementation collapse.

Still visible as a diagnostic caution:

- Deterministic location/component quantile-ordering warnings exist for 20220511, especially for `c02_eps060`.
- These warnings do not imply the posterior predictive synthesis figure is broken, because the synthesis/rearrangement
  workflow and the corrected common y-scale produce coherent cutoff-window plots.
- Keep the ordering summaries in the report package so future users can see where deterministic VB locations are less
  coherent than posterior predictive synthesis.

## What Was On Hold While We Chased The Scale Artifact

1. Freezing the final canonical-grid winner set as the production-authoritative exDQLM multivariate `keep` spec set.
2. Committing the fixed y-axis plotting patch so future cutoff-window synthesis figures are comparable across cutoffs.
3. Updating the stale repair tracker, which still described the workflow as repair-gated from 2026-05-23.
4. Building an authoritative winner bundle for all five cutoffs with common y-limits and the current report workflow.
5. Keeping the GDPC6 path documented for a future controlled covariate-bundle comparison.
6. Moving back to publication/report workflow work instead of further latent-update debugging.

## Promotion Plan

1. Commit the fixed y-axis patch, this refocus note, the authoritative spec manifest, and the repair-tracker status
   update.
2. Regenerate or recopy the five authoritative winner cutoff-window synthesis figures under a single untracked review
   bundle using the common `0` to `6.5` y-axis. Do not refit models for this.
3. If the next launch needs per-cutoff optimal specs, drive it from
   `docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml` rather than retyping specs.
4. Keep GDPC6 as a separate experiment family until a controlled comparison is approved. The minimum fair comparison is
   canonical-vs-GDPC6 for the selected production spec at each cutoff; a stronger comparison repeats the relevant
   discount/epsilon grid under the GDPC6 bundle.
5. Keep the promoted latent/component audit enabled in post-processing, but stop treating 20220511 as an unresolved
   algorithmic failure unless new fixed-scale figures or health traces contradict this conclusion.

## Current Risks To Monitor

| risk | current status | action |
| --- | --- | --- |
| Small winner margins | 20220511 and 20221225 have close runner-ups | keep top-5 tables in final report; avoid overclaiming uniqueness |
| Deterministic quantile ordering | visible in 20220511 component diagnostics | monitor/report; do not block CRPS-based production promotion |
| 20221225 raw NWS comparison | NWS/NWM has lower mean CRPS than synthesis but only 8 valid days | report both raw controls and valid-day counts |
| GDPC6 possible improvement | one 20221225 off-grid run beats the canonical winner slightly | evaluate as a separate covariate-bundle study |
| Figure comparability | old winner figures were generated before the shared y-axis patch | regenerate fixed-scale review figures before final human review |

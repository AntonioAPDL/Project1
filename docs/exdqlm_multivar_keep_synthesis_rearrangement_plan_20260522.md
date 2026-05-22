# exDQLM Multivariate Keep Synthesis Rearrangement Plan - 2026-05-22

## Purpose

This note documents the prelaunch repair for the post-stage synthesis of the seven independently fitted
exDQLM quantile models. It is intentionally scoped to posterior predictive synthesis and diagnostics. It does
not change the VB fit, latent `s_t`/`u_t` updates, gamma/sigma optimization, Kalman filtering, or saved fit
objects.

## Theory Contract

The article synthesis section defines a per-time synthesized quantile function from independently fitted
quantile models. For quantile levels `tau_1 < ... < tau_L`, each fitted model supplies local posterior
predictive information at its own target quantile, and the synthesized distribution is built by piecewise
linear blending between adjacent quantile models:

- Source: `/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt:512`
- Synthesis equation: `/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt:519`

The same section explicitly warns that independent quantile fits can cross, and states the correction:

1. isotonic adjustment at the anchor quantile levels;
2. distributional alignment of each posterior predictive sample distribution to the adjusted anchor;
3. dense-grid monotone rearrangement of the synthesized quantile function.

Source anchors:

- crossing risk: `/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt:531`
- isotonic adjustment: `/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt:533`
- monotone rearrangement: `/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt:549`

The installed `exdqlm` package exports `quantileSynthesis()`, which implements the same contract. The local
development source has the newer name `exdqlm_synthesize_from_draws()`, while the installed version is
`exdqlm` 0.4.0 and exports `quantileSynthesis()`. The project wrapper
`post_exdqlm_synthesize_from_sample_cube()` supports both names.

## Active Implementation Before This Patch

The active smoke-fast multivariate post path builds posterior predictive sample cubes with shape:

```text
[quantile x sample x time]
```

Historical synthesis is built in:

- `R/environmetrics/40_figures_smoke_fast.R:1212`

Forecast synthesis is built in:

- `R/environmetrics/40_figures_smoke_fast.R:654`

Before this patch, both paths sorted samples within each quantile row and time slice, then called the legacy
`synthesize_samples()` helper. That produced per-time marginal synthesis but did not write explicit
before/after quantile-crossing diagnostics, did not method-tag the cache, and did not promote the formal
isotonic/rearranged synthesis helper to the active multivariate path.

## Implemented Repair

The patch adds `post_synthesize_rearranged_sample_cube()` in `R/environmetrics/02_helpers_core.R`. For a sample
cube `[quantile x sample x time]`, it:

1. validates quantile ordering, shape, finite values, sample count, and grid size;
2. computes raw sample-path crossing diagnostics with `post_quantile_crossing_summary()`;
3. computes raw anchor-curve crossing diagnostics with `post_quantile_curve_from_sample_cube()` and
   `post_quantile_curve_crossing_summary()`;
4. calls `post_exdqlm_synthesize_from_sample_cube(..., enforce_isotonic = TRUE, rearrange = TRUE)`;
5. optionally sorts synthesized draws within each time point for marginal display/sample-table stability;
6. returns synthesized samples, empirical quantiles, isotone anchor quantiles, and diagnostics.

The active smoke-fast multivariate paths now call this helper for both:

- historical posterior predictive synthesis;
- forecast-window posterior predictive synthesis.

The patch also adds method-tagged cache files. The canonical cache names are still written for downstream
compatibility, but the active builders read the method-tagged cache first. This prevents stale legacy synthesis
caches from silently bypassing the repaired synthesis method.

## Runtime Diagnostics

Each multivariate post run now writes CSV diagnostics under the post output directory:

```text
<model>_history_quantile_synthesis_summary.csv
<model>_history_quantile_synthesis_raw_sample_crossing_per_time.csv
<model>_history_quantile_synthesis_raw_curve_crossing_per_time.csv
<model>_history_quantile_synthesis_anchor_curve_crossing_per_time.csv
<model>_history_quantile_synthesis_empirical_curve_crossing_per_time.csv

<model>_forecast_quantile_synthesis_summary.csv
<model>_forecast_quantile_synthesis_raw_sample_crossing_per_time.csv
<model>_forecast_quantile_synthesis_raw_curve_crossing_per_time.csv
<model>_forecast_quantile_synthesis_anchor_curve_crossing_per_time.csv
<model>_forecast_quantile_synthesis_empirical_curve_crossing_per_time.csv
```

The corresponding RDS diagnostics are cached with the synthesis method tag.

## Important Interpretation

The final synthesized matrix is still a marginal posterior predictive sample matrix by time. Sorting the
sample column at each time stabilizes marginal plots, quantile tables, CRPS inputs, and deterministic sample
subsets. It should not be interpreted as preserving a physical posterior trajectory identity across time.
This is acceptable for the current CRPS and cutoff-window posterior predictive plots, which use per-time
marginal distributions.

The raw sample-index crossing rate is a diagnostic of the arbitrary coupling across independently sorted
quantile-model draw arrays. A high raw sample-index crossing rate is not, by itself, evidence that the fitted
anchor quantile curves are wrong. The more scientifically relevant checks are the raw anchor-curve crossing
rate and the repaired anchor/empirical crossing rates.

## Test Plan

Added focused tests in `tests/testthat/test_post_quantile_synthesis_rearrangement.R`:

1. a deterministic crossing cube is repaired to non-crossing isotone anchors and monotone empirical quantiles;
2. fixed seeds produce deterministic synthesized draws and quantiles;
3. method-tagged cache names include the synthesis method tag;
4. the smoke-fast multivariate path statically references the formal rearranged synthesis helper and writes
   diagnostics.

Before launch, run:

```bash
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_quantile_synthesis_rearrangement.R')"
python3 -m unittest tests.python.test_univar_post_quantile_synthesis_fallback -v
```

For a real-output post-only replay, run the unified post stage against an existing seven-quantile `.RData`
bundle and verify:

1. forecast/history synthesis diagnostics are written;
2. raw crossing summaries are finite and interpretable;
3. anchor and empirical curve crossing shares are zero;
4. cutoff-window quantile CSVs are non-crossing;
5. CRPS table generation still succeeds;
6. held-out USGS values are still present in forecast-window plots.

## Validation Completed

Commands run:

```bash
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_quantile_synthesis_rearrangement.R')"
python3 -m unittest tests.python.test_univar_post_quantile_synthesis_fallback -v
Rscript --vanilla -e "parse('R/environmetrics/02_helpers_core.R'); parse('R/environmetrics/40_figures_smoke_fast.R'); cat('parse ok\n')"
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_crps_tables.R')"
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_publication_figures.R')"
python3 -m unittest tests.python.test_he2_crps_table_readiness_audit tests.python.test_he2_publication_relaunch_template -v
```

Results:

| validation | result |
| --- | --- |
| synthesis helper behavior | pass, 21 expectations |
| exdqlm package fallback static contract | pass |
| touched R file parse check | pass |
| CRPS post table helpers | pass, 64 expectations |
| publication post helpers | pass, 27 expectations |
| Python CRPS/readiness and relaunch template tests | pass, 20 template tests plus readiness tests |

An isolated real-output post replay was also run under:

```text
reports/exdqlm_multivar_keep_synthesis_rearrangement_replay_20260522/run_root/post/outputs/synthesis_rearrangement_replay_20260522d
```

The replay used the available four-quantile promotion bundle (`q05`, `q35`, `q50`, `q95`) and explicitly set
`UNIFIED_MULTIVAR_FORECAST_TRANSFER_MODE=keep`. This was not a production launch and did not write into the
source run directory.

Replay evidence:

| check | evidence |
| --- | --- |
| method-tagged keep cache files written | `post/cache_d/*__exdqlm_iso1_rearr1_grid1001_v1.rds` |
| forecast diagnostics written | `exdqlm_multivar_synth_keep_forecast_quantile_synthesis_summary.csv` |
| history diagnostics written | `exdqlm_multivar_synth_keep_history_quantile_synthesis_summary.csv` |
| raw forecast sample-index crossing detected | mean crossing rate `1.0` |
| raw forecast anchor-curve crossing detected | crossing share `0.0714285714` |
| repaired forecast anchor crossing | crossing share `0` |
| repaired forecast empirical crossing | crossing share `0` |
| repaired history anchor/empirical crossing | crossing share `0` |
| emitted cutoff-window quantile CSV crossing rows | `0` crossing rows across 47 rows |

The replay emitted truth-availability warnings because this older copied input bundle had no held-out USGS rows
after `2022-12-25`; this does not affect the synthesis repair validation. The full all-cutoff launch inputs are
still expected to provide the held-out forecast-window observations through the current input bundle contract.

## Launch Decision

The targeted tests and an isolated real-output keep replay passed with the repaired synthesis method. The full
all-cutoff launch can proceed after the code is committed and pushed, subject to the existing launch approval
boundary.

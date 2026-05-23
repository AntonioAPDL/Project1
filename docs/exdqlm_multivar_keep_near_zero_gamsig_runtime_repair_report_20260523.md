# exDQLM Multivariate Keep Near-Zero Gamma/Sigma Runtime Repair Evidence

Date: 2026-05-23

Status: targeted runtime repair passed. The evidence supports promoting the near-zero gamma/sigma fallback and runtime
harness, with one remaining campaign-level decision: whether to accept the repaired three-cutoff evidence or run one
fresh homogeneous five-cutoff campaign.

## Scope

This document records the runtime gate after the near-zero gamma/sigma implementation repair for the active
multivariate `exdqlm keep` workflow. It is intentionally narrower than the full theory audit: it asks whether the
patch actually fixes the failed lanes observed in the 2026-05-22 all-cutoff launch.

Protected older production roots were not modified. The targeted repair used a new isolated runtime root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_multivar_keep_near_zero_gamsig_repair_20260523`

Large runtime evidence remains untracked under:

`/data/muscat_data/jaguir26/project1_ucsc_phd/reports/exdqlm_multivar_keep_near_zero_gamsig_repair_runtime_20260523`

## Active Patch Surface

The runtime evidence exercises the active workflow through the unified fit bridge into the legacy runner.

Primary code references:

- [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:238):
  near-zero fallback environment controls.
- [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2630):
  policy passed into the gamma/sigma update.
- [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2682):
  accepted status `near_zero_sigma_only_fallback`.
- [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2690):
  runtime log marker `[gamsig_near_zero_fallback]`.
- [R/disc_w/10_gamsig_laplace.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/10_gamsig_laplace.R:96):
  fallback policy normalization.
- [R/disc_w/10_gamsig_laplace.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/10_gamsig_laplace.R:126):
  near-zero fallback eligibility.
- [R/unified/config.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/config.R:2051):
  unified config validation.
- [R/unified/stages/stage_fit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/stages/stage_fit.R:1182):
  exported legacy environment variables.
- [scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py:161):
  monitor parsing for near-zero fallback counts.
- [scripts/build_exdqlm_near_zero_gamsig_runtime_report.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_exdqlm_near_zero_gamsig_runtime_report.py:163):
  runtime gate builder and cleanup-aware `.RData` contract.

## Runtime Specification

The targeted repair reran the three cutoff rows that had failed the gamma/sigma minimum-update gate:

- `20210123`
- `20211221`
- `20220511`

Each row ran all seven quantiles: `q05`, `q20`, `q35`, `q50`, `q65`, `q80`, `q95`.

Common scientific and operational settings:

- `data_start=1987-05-29`
- harmonics `1,2,3`
- transfer covariates `PPT, SOIL, PCA, PPT_sq, SOIL_sq, PPT_x_SOIL, PPT_lag1, PPT_lag2, PPT_lag3, SOIL_lag1, SOIL_lag2, SOIL_lag3`
- `df_t=0.99999`
- `df_s1=0.9999`
- `df_s2=0.9999`
- `df_s67=0.9999`
- `df_discrep=0.9999`
- `lambda=0.97`
- `df_trans=0.9999999`
- `df_covs=0.9999999`
- `c_factor=1`
- `epsilon=365`
- `max_iter=100`
- `DISC_GAMSIG_MIN_UPDATE_ITERS=50`
- near-zero fallback enabled with `mode=sigma_only` and `gamma_anchor=full_candidate`
- post-stage `.RData` cleanup enabled

## Runtime Gate

The final gate was generated with:

```bash
python3 scripts/build_exdqlm_near_zero_gamsig_runtime_report.py \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_multivar_keep_near_zero_gamsig_repair_20260523 \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_multivar_keep_near_zero_gamsig_repair_20260523/control/repair_matrix \
  --out-dir reports/exdqlm_multivar_keep_near_zero_gamsig_repair_runtime_20260523 \
  --allow-post-cleaned-rdata
```

The gate requires: runner pass, terminal gamma/sigma updates at or above the configured minimum, no pseudo-data guard
failures, no state guard events, no fatal log errors, and either lane `.RData` files or verified post-stage `.RData`
cleanup. The cleanup-aware contract is necessary because the repair run intentionally deletes large `.RData` objects
after post has completed.

## Result

The runtime repair passed `21/21` lanes.

Full lane evidence:

- `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/exdqlm_multivar_keep_near_zero_gamsig_repair_runtime_20260523/README.md`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/exdqlm_multivar_keep_near_zero_gamsig_repair_runtime_20260523/runtime_lane_summary.csv`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/exdqlm_multivar_keep_near_zero_gamsig_repair_runtime_20260523/monitor/LIVE_STATUS.md`

Compact evidence table:

| cutoff | lane summary | result |
| --- | --- | --- |
| `20210123` | 7/7 lanes passed; updates ranged `79/50` to `90/50`; pseudo failures `0`; state guards `0`; fatal errors `0`; post cleanup `7/7` | pass |
| `20211221` | 7/7 lanes passed; updates ranged `79/50` to `90/50`; pseudo failures `0`; state guards `0`; fatal errors `0`; post cleanup `7/7` | pass |
| `20220511` | 7/7 lanes passed; updates ranged `79/50` to `90/50`; pseudo failures `0`; state guards `0`; fatal errors `0`; post cleanup `7/7` | pass |

The three originally failed lanes are now repaired:

| cutoff | failed lane | before: gamma/sigma updates | after: gamma/sigma updates | near-zero fallback count | pseudo failures | final status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `20210123` | `q35` | `16/50` | `90/50` | `3` | `0` | pass |
| `20211221` | `q20` | `21/50` | `79/50` | `3` | `0` | pass |
| `20220511` | `q20` | `17/50` | `90/50` | `1` | `0` | pass |

The post stage also produced the expected publication evidence for each repaired row, including:

- `All_ELBOS_DISC.png`
- `SMOKE_OBSERVED_SERIES_DISC.png`
- `exdqlm_multivar_synth_keep_cutoff_window_posterior_samples_with_raw_ensembles.png`
- `tables/crps_forecast_summary.csv`
- `tables/crps_forecast_per_time.csv`
- `tables/crps_truth_availability.csv`
- `tables/gamma_summary.csv`
- `tables/sigma_summary.csv`
- `tables/covariate_effects_summary.csv`

After cleanup, the repair runtime root contains no `.RData` or `.tmp.*` files and is approximately `61M`.

## Interpretation

Confirmed:

- The failed lanes were reproducibly fixed by the near-zero gamma/sigma fallback without lowering
  `DISC_GAMSIG_MIN_UPDATE_ITERS`.
- The repaired lanes reached the posterior/post workflow and produced CRPS tables and diagnostic figures.
- The pseudo-data layer did not fail in the repaired rows.
- The state guard did not fire in the repaired rows.
- The `.RData` cleanup policy is compatible with the runtime gate when the cleanup marker reports
  `before=7 removed=7 remaining=0`.

Still worth monitoring:

- `q80` has high gamma/sigma guard counts in the repaired rows (`155` to `220`). These did not cause failures and did
  not trigger pseudo-data or state guards, but they remain the most sensitive successful lanes.
- Tail lanes have larger normalized state norms than central lanes, especially `20210123 q95`. This is bounded in the
  targeted repair but should stay on the launch monitor.
- The targeted repair is not a fresh homogeneous rerun of all five cutoffs. It repairs the failed rows from the
  previous campaign and validates the patch under the exact failed conditions.

## Promotion Decision

Recommendation: promote the near-zero fallback and runtime harness. The direct failure mechanism for the failed lanes
is no longer ambiguous: the failure was gamma/sigma update starvation when valid near-zero gamma candidates were
rejected by the split policy. The current evidence does not point to `s_t`, `u_t`, pseudo-data construction, or the
Kalman layer as the active cause of these specific operational failures.

Campaign-level next choice:

1. Use the repaired three-cutoff evidence together with the already successful rows from the 2026-05-22 campaign.
2. Or run one clean homogeneous five-cutoff campaign with the promoted patch and the same runtime gates.

For publication-grade reproducibility, the clean homogeneous five-cutoff campaign is the stronger option.

## Validation Commands

Additional deterministic validation for the new runtime harness:

```bash
python3 -m py_compile \
  scripts/prepare_exdqlm_near_zero_gamsig_repair_runs.py \
  scripts/run_exdqlm_near_zero_gamsig_matrix.py \
  scripts/build_exdqlm_near_zero_gamsig_runtime_report.py \
  tests/python/test_exdqlm_near_zero_gamsig_runtime_harness.py

python3 -m unittest tests.python.test_exdqlm_near_zero_gamsig_runtime_harness -v
```

# exDQLM Multivariate Keep Near-Zero Gamma/Sigma Repair Report

Date: 2026-05-23

Status: implementation and deterministic validation complete; targeted runtime fit smokes remain the next promotion
gate.

## Scope

This report closes the first implementation pass for the near-zero gamma/sigma defect identified after the 2026-05-22
all-cutoff full-history promotion launch. It covers the active multivariate `exdqlm keep` path only.

Protected older production roots were not modified. The existing 2026-05-22 all-cutoff root was parsed read-only for
evidence.

## Evidence Re-Freeze

Read-only evidence was regenerated under:

`/data/muscat_data/jaguir26/project1_ucsc_phd/reports/exdqlm_multivar_keep_near_zero_gamsig_failure_20260523`

Key files:

- `README.md`
- `lane_failure_summary.csv`
- `near_zero_event_table.csv`
- `terminal_preflight_table.csv`
- `monitor_once/LIVE_STATUS.md`

The failed lanes remain:

| cutoff | failed lane | terminal iter | gamma/sigma updates | near-zero no-candidate events | split-reject near-zero events | pseudo-data failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `20210123` | `q35` | 100 | 16 / 50 | 14 | 54 | 0 |
| `20211221` | `q20` | 100 | 21 / 50 | 12 | 32 | 0 |
| `20220511` | `q20` | 100 | 17 / 50 | 14 | 29 | 0 |

Interpretation is unchanged and now more precisely counted: the observed operational failure is a near-zero
gamma/sigma split/fallback policy defect, not a pseudo-data guard failure.

## Implemented Repair

### Active Runner

Updated:

- [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r)

The runner now has explicit near-zero fallback controls:

- `DISC_GAMSIG_NEAR_ZERO_FALLBACK_ENABLED`, default `TRUE`
- `DISC_GAMSIG_NEAR_ZERO_FALLBACK_MODE`, default `sigma_only`
- `DISC_GAMSIG_NEAR_ZERO_GAMMA_ANCHOR`, default `full_candidate`

The new behavior is intentionally narrow:

1. It only applies when the split decision reason is exactly `near_zero`.
2. It requires the full candidate to be finite and inside the configured near-zero gamma threshold.
3. It re-optimizes `theta_s` with fixed `theta_g`.
4. It rejects the fallback if the fallback objective or point moments are nonfinite.
5. If accepted, it returns `laplace_status="near_zero_sigma_only_fallback"` with `guard_triggered=FALSE`.
6. Non-near-zero failures still use the existing guard/refreeze path.

This means a valid near-zero gamma update now counts as a real finite gamma/sigma update instead of starving
`gamsig_update_iters`.

### Shared Helpers

Updated:

- [R/disc_w/10_gamsig_laplace.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/10_gamsig_laplace.R)

Added deterministic helper contracts for:

- normalizing near-zero fallback policy;
- checking near-zero fallback eligibility;
- requiring a finite near-zero full candidate.

### Config And Bridge

Updated:

- [R/unified/config.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/config.R)
- [R/unified/stages/stage_fit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/stages/stage_fit.R)

The unified config now validates:

- `fit.<family>.gamma_sigma.near_zero_fallback.enabled`
- `fit.<family>.gamma_sigma.near_zero_fallback.mode`
- `fit.<family>.gamma_sigma.near_zero_fallback.gamma_anchor`

The stage-fit bridge exports the three corresponding `DISC_GAMSIG_*` environment variables into the legacy worker.

### Monitoring And Evidence Tooling

Updated:

- [scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py)

Added:

- parsing for `[gamsig_near_zero_fallback]`;
- `near_zero_fallback_count`;
- `near_zero_fallback_log_count`;
- a `near0` column in the compact live monitor.

Added:

- [scripts/build_exdqlm_near_zero_gamsig_failure_report.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_exdqlm_near_zero_gamsig_failure_report.py)

This script regenerates the failure evidence report from read-only logs.

## Tests Run

All deterministic validation below passed on 2026-05-23:

```bash
Rscript --vanilla -e "invisible(parse('DISC_Optimal_Synth_Ranges_W_transfer_forecast.r')); cat('parse ok\n')"
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_disc_w_gamsig_laplace.R')"
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_unified_gamma_sigma_state_refresh_schedule_config.R')"
python3 -m unittest tests.python.test_he2_exdqlm_keep_allcutoff_monitor tests.python.test_stage_fit_quantile_gamma_sigma_overrides tests.python.test_disc_sampling_diagnostics_source_contract -v
python3 -m unittest tests.python.test_he2_publication_relaunch_builder_selection.HE2PublicationRelaunchBuilderSelectionTests.test_exdqlm_allcutoffs_fullhistory_promotion_batch_builds_guarded_configs -v
python3 -m py_compile scripts/build_exdqlm_near_zero_gamsig_failure_report.py scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py tests/python/test_he2_exdqlm_keep_allcutoff_monitor.py tests/python/test_stage_fit_quantile_gamma_sigma_overrides.py
python3 scripts/build_exdqlm_near_zero_gamsig_failure_report.py
python3 scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522 --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522/control/publication_relaunch_matrix --out-dir reports/exdqlm_multivar_keep_near_zero_gamsig_failure_20260523/monitor_once --once
git diff --check
```

Coverage added:

- near-zero split decision and fallback eligibility;
- invalid fallback policy normalization;
- active runner source contract for new env vars/status/counters;
- unified config validation for the new block;
- stage-fit quantile override resolution for `near_zero_fallback`;
- monitor parsing and `near0` output;
- all-cutoff promotion builder source-level compatibility.

## What Is Confirmed

Confirmed:

- The three observed failed lanes failed at the gamma/sigma minimum-update terminal guard.
- Each failed lane had repeated `reason=near_zero` split no-candidate events.
- The failed-lane logs show zero pseudo-data guard failures.
- The active runner now has a guarded, non-median near-zero sigma-only fallback.
- The fallback is finite-gated and does not weaken general guard behavior.
- The unified config and stage-fit bridge can carry the new fallback policy.
- The monitor can expose near-zero fallback usage.

## What Is Not Yet Confirmed

Not yet confirmed:

- The three failed lanes have not yet been rerun with the patch in isolated fit-only smokes.
- The repaired three cutoff rows have not yet been rerun through full fit/post/validate/report.
- Full campaign-level CRPS and plot quality after repair remain unverified.

This is important: the root defect is now implemented and deterministic tests pass, but runtime promotion still
requires the targeted smoke gates from the repair plan.

## Required Next Gates

Run these isolated fit-only smokes before any broad relaunch:

| smoke | role |
| --- | --- |
| `20210123 q35` | primary q35 failure reproduction |
| `20211221 q20` | first q20 failure reproduction |
| `20220511 q20` | second q20 failure reproduction |
| `20221225 q20` | healthy q20 control |
| `20211112 q35` | healthy q35 control |

Pass criteria:

1. fit reaches posterior sampling and writes `.RData`;
2. `near_zero_sigma_only_fallback` appears only where expected;
3. `gamsig_update_iters >= 50`;
4. no pseudo-data guard failures;
5. no terminal state guard;
6. ELBO, state norm, sigma, and gamma traces remain finite and comparable to neighboring successful lanes.

Only after those smokes pass should we rerun the three failed cutoff rows with all seven quantiles each:

- `20210123`
- `20211221`
- `20220511`

## Prioritized Remaining Work

| priority | work | status |
| ---: | --- | --- |
| 1 | Run the five isolated lane smokes in a new repair root | pending |
| 2 | Generate smoke report with near-zero fallback counts and ELBO/gamma/sigma/state traces | pending |
| 3 | Rerun the three failed cutoff rows with all seven quantiles each | pending |
| 4 | Run post/validate/report and regenerate CRPS/plots for repaired cutoffs | pending |
| 5 | Decide whether to publish mixed repaired evidence or run one clean homogeneous all-five-cutoff relaunch | pending |

## Recommendation

Proceed to isolated targeted smokes next. Do not lower `DISC_GAMSIG_MIN_UPDATE_ITERS`, do not disable pseudo-data or
state guards, and do not relaunch all 35 lanes until the three failed lanes pass with the new near-zero fallback.

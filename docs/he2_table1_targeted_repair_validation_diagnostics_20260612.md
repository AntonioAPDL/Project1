# HE2 Table 1 Targeted Repair Validation Diagnostics 2026-06-12

## Purpose

This note records the prelaunch validation result for the Table 1 targeted
repair package prepared on 2026-06-12. The goal was to apply the supplied
discount / epsilon table without relaunching broad production work until the
package passed wiring and health gates.

The rerun package is defined by:

- template: `config/he2_bayesian_publication_relaunch_table1_targeted_repair_20260612.template.yaml`
- batch selection: `config/he2_relaunch_batches/table1_targeted_repair_20260612.yaml`
- package overview: `docs/he2_table1_targeted_repair_relaunch_20260612.md`
- unit tests: `tests/python/test_he2_table1_targeted_repair_20260612.py`

## What Passed

The static wiring checks passed:

- the builder generated 24 selected Table 1 repair configs;
- generated run IDs matched the requested repair rows;
- patched specs matched the 2026-06-12 override table for the overridden rows;
- `N-U-T1` and `AL-U-T1` remained selected but preserved current publication
  specs because they were not included in the override table;
- the canonical HE2 shared input-bundle root remained
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`;
- the canonical bundle run id remained `20260510_publication_shared_r01`;
- `data_start` remained `1987-05-29`.

Focused tests passed with:

```bash
python3 -m unittest tests.python.test_he2_table1_targeted_repair_20260612
python3 -m py_compile \
  scripts/build_he2_bayesian_publication_relaunch_configs.py \
  scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  scripts/launch_he2_bayesian_publication_relaunch.py \
  scripts/run_multimodel_v8_queue.py
```

## Validation Blocker

Prelaunch validation blocked on one lane:

| cutoff | manuscript label | family | transfer | quantile | validation status |
|---|---|---|---|---:|---|
| `20210123` | `exAL-M-T0` | `exdqlm_multivar` | drop | `0.05` | warning escalated by fail-fast |

The validation-smoke health report is:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/prelaunch_validation_20260612_final/smoke_runs/fit_quantile/exdqlm_multivar_drop/20210123/fit_smoke_exdqlm_multivar_drop_20210123_qsubset/fit/q=05/outputs/multivar_forecast_health.txt`

The smoke was only 10 iterations, so a longer diagnostic was required before
declaring the supplied spec invalid.

## Targeted 100-Iteration Diagnostic

The diagnostic used the same generated config as the targeted repair package,
but with these diagnostic-only changes:

- `fit.quantiles = [0.05]`;
- one worker / one core;
- `max_iter = 100`;
- `min_total_iters = 100`;
- `n_samp = 512`;
- `forecast_health.fail_fast = false` so the run could write the full health
  report instead of aborting after the warning;
- post / validate / report stages disabled.

Diagnostic config:

`reports/he2_table1_targeted_repair_20260612_validation_diagnostics/diagnostic_20210123_exalm_t0_q05_user_spec_iter100.yaml`

Diagnostic run root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/diagnostic_runs/diagnostic_20210123_exalm_t0_q05_user_spec_iter100`

The diagnostic completed cleanly. Its `.RData` was removed after extracting the
health evidence; the log and health reports remain.

## Diagnostic Result

The longer diagnostic confirmed that the validation issue is real for this
lane. It is not a short-smoke artifact.

| metric | value | limit | status |
|---|---:|---:|---|
| `max_abs_history_exps` | 50.907968 | 25 | warning |
| `state_norm_sq_per_T` | 565.204510 | 10000 | ok |
| `transfer_level_max_abs` | 19.806443 | 25 | ok |
| `transfer_coef_max_abs` | 0.721408 | 100 | ok |
| `max_abs_forecast_exps` | 34.401296 | not hard-capped | large |
| `nonfinite_history_exps` | 0 | 0 | ok |
| `nonfinite_forecast_exps` | 48 | reported | present |
| `max_E_sigma` | 0.163913 | 100 | ok |

Full diagnostic health report:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/diagnostic_runs/diagnostic_20210123_exalm_t0_q05_user_spec_iter100/fit/q=05/outputs/multivar_forecast_health.txt`

Terminal state-health CSV:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/diagnostic_runs/diagnostic_20210123_exalm_t0_q05_user_spec_iter100/fit/q=05/outputs/multivar_terminal_state_health.csv`

## Interpretation

The 100-iteration trace was numerically smooth:

- gamma/sigma did not jump after warmup;
- no guard failures appeared;
- `state_norm_sq_per_T` remained far below the hard cap;
- transfer level and transfer coefficient magnitudes remained below hard caps;
- historical exps were finite.

Therefore this is not evidence of an immediate `s_t` / `u_t` numerical blow-up
or Kalman-state explosion. The blocked metric is the fitted historical location
range, with large forecast exps in the same lane.

The current HE2 source run for the same row shows the same behavior:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602/runs/multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_multivar_drop/fit/q=05/outputs/multivar_forecast_health.txt`

That source run used:

- `df_s1 = df_s2 = df_s67 = df_discrep = 0.99999`;
- `epsilon = 30`;
- `c_factor = 1`;
- `max_iter = 100`;
- `n_samp = 2000`.

The new diagnostic used the supplied 2026-06-12 override:

- `df_s1 = df_s2 = df_s67 = df_discrep = 0.99999999`;
- `epsilon = 365`;
- `c_factor = 1`;
- `max_iter = 100`;
- `n_samp = 512`.

Despite those differences, the final fit behavior is nearly identical:

| run | `max_abs_forecast_exps` | `max_E_sigma` | terminal fit behavior |
|---|---:|---:|---|
| current HE2 source row | 34.284226 | 0.163666 | smooth 100-iter fit |
| 2026-06-12 override diagnostic | 34.401296 | 0.163913 | smooth 100-iter fit, history warning |

Older April feature-covariate runs for this label were much smaller but used a
shorter history (`TT=1081`) rather than the current full-history HE2 bundle
(`TT=12294`). Example:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_all9_featurecov_20260415/runs/multimodel_20210123_v8_featurecov_v1_exdqlm_multivar_drop/fit/q=05/outputs/multivar_forecast_health.txt`

This points away from the new override table as the root cause. The leading
suspect is the interaction of full-history HE2 inputs, the multivariate exAL
drop state-space, and the extreme lower quantile, not a fresh numerical
instability introduced by the 2026-06-12 discount table.

## Recommendation

Do not launch the full targeted repair queue as-is.

The next robust move is to split the work:

1. Keep the prepared package as the reproducible specification freeze.
2. Do not suppress the `max_abs_history_exps` health warning by merely raising
   the threshold or disabling fail-fast for production.
3. Run a small candidate ladder for the `20210123` / `exAL-M-T0` / `q05` lane
   under the canonical full-history bundle:
   - current HE2 source spec as a formal control, with current terminal health
     metrics enabled;
   - the supplied 2026-06-12 spec, already completed here;
   - a less sticky seasonal/discrepancy alternative;
   - an AL-forced multivariate-drop control to verify whether the exAL latent
     layer is responsible for the large location range;
   - optionally a no-transfer or constrained-transfer control if the previous
     controls point to transfer/discrepancy identifiability.
4. If only `exAL-M-T0` remains problematic, launch the other selected repair
   rows separately and keep `exAL-M-T0` out of Table 1 promotion until its
   candidate ladder has a clean winner.
5. Promote Table 1 values only from runs whose frozen specs, input manifests,
   post outputs, and health reports are all linked in the article manifest.

## Decision Log

- The targeted repair package was built and tested.
- Full launch was not started.
- A validation-only process that was too slow under a 10-iteration NDLM smoke
  was stopped; it was isolated to this package and did not touch production
  campaigns.
- The final prelaunch validation failed on the q05 exAL multivariate-drop lane.
- A 100-iteration diagnostic confirmed the lane still violates the history
  location warning.
- The diagnostic `.RData` was removed after evidence capture.

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

## Warmup-40 Validation And Launch

The corrected warmup-40 validation passed after changing the univariate
full-pipeline smoke from `q05` only to `q05` plus `q50`:

- validation outdir:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/prelaunch_validation_20260613_warmup40_q05q50`
- validation summary:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/prelaunch_validation_20260613_warmup40_q05q50/prelaunch_validation_summary.md`
- result: `18 / 18` smoke runs passed, with `18` temporary `.RData` files
  removed by validation cleanup.

The key previously failing multivariate q05 lane passed the full-pipeline smoke
under `warmup_freeze_iters = 40`. It froze gamma/sigma through iteration `40`,
released at iteration `41` from a settled state, and remained bounded through
terminal iteration `43`:

| iter | frozen | sigma_exp | gamma_exp | state_norm_sq |
|---:|---|---:|---:|---:|
| 40 | true | 0.3987874 | 0 | 575738.6 |
| 41 | false | 0.1454220 | -0.002706019 | 574024.8 |
| 43 | false | 0.1833703 | -0.009039003 | 631142.2 |

The corresponding health report recorded `state_norm_sq_per_T = 51.33741267`,
`max_E_sigma = 0.2305429405`, and `max_abs_history_exps = 11.26204035`, all
within the production gate limits.

After this pass, the isolated 24-row Table 1 repair queue was launched with:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_table1_targeted_repair_20260612.template.yaml \
  --skip-validate \
  --reset-state \
  --start-monitor \
  --monitor-out-dir reports/he2_table1_targeted_repair_20260612_live_warmup40 \
  --monitor-interval 300 \
  --monitor-max-snapshots 288
```

Runtime root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612`

Queue controller PID at launch: `3897384`; monitor PID at launch: `3897526`.
The controller was launched with `.RData` cleanup after post enabled.

## Recommendation

Do not launch the original warmup-5 targeted repair queue as-is. The active
repair path is the warmup-40 queue documented above.

The 2026-06-13 relaunch attempt changes the quantile VB warmup policy to
`warmup_freeze_iters = 40` for all selected AL/exAL quantile families while
leaving the supplied discount factors, `lambda`, `epsilon`, and `c_factor`
unchanged. This specifically tests whether the blocked extreme lower-quantile
lane needs the longer stabilization window that had already helped other
multivariate AL/exAL repairs.

The next robust move after the warmup-40 relaunch is:

1. Monitor the isolated 24-row queue through `report` completion.
2. Confirm each selected run records `.RData` cleanup after post.
3. Build the repair-campaign compare outputs and Table 1 merge candidates.
4. If any lane fails, keep the prepared package as the reproducible
   specification freeze and split the work:
   - launch the non-problematic selected repair rows separately;
   - keep `20210123` / `exAL-M-T0` / `q05` in a candidate ladder rather than
     lowering health standards.
5. Do not suppress any `max_abs_history_exps` health warning by merely raising
   the threshold or disabling fail-fast for production.
6. If warmup 40 does not resolve the gate, run a small candidate ladder for the
   `20210123` / `exAL-M-T0` / `q05` lane
   under the canonical full-history bundle:
   - current HE2 source spec as a formal control, with current terminal health
     metrics enabled;
   - the supplied 2026-06-12 spec, already completed here;
   - a less sticky seasonal/discrepancy alternative;
   - an AL-forced multivariate-drop control to verify whether the exAL latent
     layer is responsible for the large location range;
   - optionally a no-transfer or constrained-transfer control if the previous
     controls point to transfer/discrepancy identifiability.
7. Promote Table 1 values only from runs whose frozen specs, input manifests,
   post outputs, and health reports are all linked in the article manifest.

## Decision Log

- The targeted repair package was built and tested.
- The original warmup-5 queue was not launched.
- A validation-only process that was too slow under a 10-iteration NDLM smoke
  was stopped; it was isolated to this package and did not touch production
  campaigns.
- The final prelaunch validation failed on the q05 exAL multivariate-drop lane.
- A 100-iteration diagnostic confirmed the lane still violates the history
  location warning.
- The diagnostic `.RData` was removed after evidence capture.
- On 2026-06-13, the batch-level common patch was updated so all selected
  AL/exAL quantile-family rows use `warmup_freeze_iters = 40`.
- The warmup-40 prelaunch run at
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/prelaunch_validation_20260613_warmup40`
  confirmed that the previously blocked multivariate `20210123` /
  `exAL-M-T0` / `q05` lane passes the health gate:
  `max_abs_history_exps = 11.26204035`, `state_norm_sq_per_T = 51.33741267`,
  and terminal status `ok`.
- The remaining failure in that validation run was a smoke configuration
  mismatch, not a fit instability: the univariate AL full-pipeline smoke used
  only `q05`, but the legacy univariate post repair requires at least two
  fitted quantiles. The Table 1 repair template now uses `q05` and `q50` for
  that smoke.
- The corrected warmup-40 validation at
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/prelaunch_validation_20260613_warmup40_q05q50`
  passed all `18` smoke runs.
- A duplicate dry-run validator started by the launch dry-run was stopped after
  it began re-running the already completed expensive validation. It was
  isolated to this package and had not launched the repair queue.
- The actual 24-row repair queue was launched with `--skip-validate` only after
  the dedicated warmup-40 validation passed. Queue state was reset into
  `control/restart_resets/20260613T045037Z` before launch.

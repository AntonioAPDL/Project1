# HE2 exDQLM Multivar Drop 20211112 q50 Repair

Date: 2026-06-02

Scope: isolated repair of the single failed `exdqlm_multivar_drop` row from the current HE2 relaunch, cutoff `20211112`, quantile `q50`.

## Frozen Evidence

Runtime evidence is frozen under:

`reports/he2_exdqlm_multivar_drop_20211112_q50_failure_audit_20260602/`

The failing source row was:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_20260602/runs/multimodel_20211112_v8_he2pubgdpc1r1_exdqlm_multivar_drop`

The row failed during fit-stage forecast-health validation:

`[FIT_FORECAST_HEALTH_FAIL] multivar drop q=50 violated forecast-health limits: max_abs_forecast_exps=667.492208 > 650.000000`

The frozen health comparison shows that `20211112 q50` is an isolated outlier, not a mild threshold issue. Its `max_abs_forecast_exps` is `667.492`, while the next-largest value in the 5-cutoff x 7-quantile drop matrix is about `34.614`.

## Diagnosis

This is a true q50 terminal VB/state pathology.

Evidence:

- `R/unified/stages/stage_fit.R` performs the active fit-stage health check on `theta$sm_ens`, forecast columns of `theta$exps`, and `gamsig$E.sigma`.
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` records median state guards, rolls back state/latent/gamma-sigma objects, and emits terminal sampling diagnostics.
- The failed q50 log shows repeated state guards near terminal iterations, oscillating `sigma_exp`/`gamma_exp`, and a terminal endpoint that was still frozen.
- The terminal guard diagnostic reported `frozen=true` with `lag_iters=3`, but the previous guard condition required `lag_iters <= max_guard_lag_iters` before it could stop sampling. With `max_guard_lag_iters=0`, the terminal guard did not trip even though the endpoint was frozen.

Conclusion: the failed output should not have reached sampling. The correct behavior is to block sampling whenever `require_frozen=true` and the terminal endpoint is still frozen due to a state guard.

## Code Repair

Patched files:

`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`

`DISC_Optimal_Synth_Ranges_W.r`

The unified legacy wrapper dispatches by transfer mode: `keep` uses `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`, while `drop` uses `DISC_Optimal_Synth_Ranges_W.r`. The repair therefore has to exist in both entrypoints.

The terminal guard now computes:

- `terminal_sampling_guard_recent_enough`
- `terminal_sampling_guard_blocked`

When `terminal_sampling_guard.require_frozen=true`, sampling is blocked if any of these are true:

- the terminal endpoint is still frozen;
- the guard is same-iteration/recent;
- the guard is within `max_guard_lag_iters`.

This preserves the old lag-window behavior for non-frozen endpoints while preventing a frozen terminal state from slipping through.

Regression coverage:

`tests/python/test_he2_exdqlm_multivar_drop_q50_repair.py`

## Isolated Relaunch Contract

Builder:

`scripts/build_he2_exdqlm_multivar_drop_20211112_q50_repair.py`

Runtime root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_20211112_q50repair_20260602`

The relaunch keeps the scientific contract unchanged:

- cutoff: `20211112`
- family: `exdqlm_multivar_drop`
- likelihood: `exal`
- transfer mode: `drop`
- input bundle: canonical HE2 publication shared bundle
- transform policy: `log1p_only`
- harmonics: `1,2,3` with trend included
- discount factors: unchanged from the current drop relaunch
- Wishart forecast covariance: `epsilon=30`, `c_factor=1`
- VB max iterations: `100`

Only q50 stabilization is changed:

| setting | repair value |
|---|---:|
| `median_state_hold_after_guard_iters` | `10` |
| `median_state_blend_alpha` | `1.0` |
| `median_cov_blend_alpha` | `1.0` |
| `median_max_abs_gamma_step` | `0.075` |
| `median_max_abs_log_sigma_step` | `0.15` |

## Execution Plan

1. Build the isolated repair package.
2. Run the q50-only diagnostic config.
3. If q50 passes fit health, run the full 7-quantile `20211112` repair row.
4. Validate post/report artifacts and forecast-health summaries.
5. Confirm `.RData/.rda` cleanup after diagnostic and final post.

The q50-only diagnostic explicitly deletes `.RData/.rda` after fit. The final row uses `scripts/run_unified_with_cleanup.sh`, which sets `CLEANUP_RDATA_AFTER_POST=1`.

## Decision Gate

Pass criteria:

- q50 diagnostic reaches fit-stage health without terminal sampling guard failure.
- full row reaches `fit/post/validate/report=pass`.
- q50 `max_abs_forecast_exps` is no longer an isolated order-of-magnitude outlier.
- no retained `.RData/.rda` remains under the repair root after final post.

If q50 still trips the terminal guard under the repair config, treat that as useful evidence: the active q50 path remains unstable under the same scientific spec, and the next move is a targeted q50 stabilization ladder, not a broader relaunch.

## Final Result

Status: passed end to end.

Final evidence:

`reports/he2_exdqlm_multivar_drop_20211112_q50_repair_final_20260602/`

Final repaired row:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_20211112_q50repair_20260602/runs/multimodel_20211112_v8_he2pubgdpc1r1_exdqlm_multivar_drop_q50repair_20260602`

Observed final row gates:

- `fit=pass`, `post=pass`, `validate=pass`, `report=pass`;
- post-stage cleanup removed all retained `.RData/.rda`, leaving `0`;
- all seven quantiles wrote forecast-health reports;
- q50 terminal guard emitted the patched fields `recent_enough=false blocked=false`, so sampling was allowed because the terminal endpoint was not frozen;
- q50 had only the early iteration-6 state rollback and did not reproduce the failed baseline late guards at iterations 75, 86, and 97.

Before/after q50 health:

| run | `max_abs_forecast_exps` | `max_abs_sm_ens` | `max_E_sigma` |
|---|---:|---:|---:|
| failed baseline | `667.492` | `134.199` | `4.219` |
| q50-only diagnostic repair | `2.002` | `1.512` | `0.01024` |
| final repaired row q50 | `2.002` | `1.512` | `0.01024` |

Final CRPS summary for this repaired row:

| model | valid days | mean CRPS |
|---|---:|---:|
| `exdqlm_multivar_synth_drop` | `28` | `1.798676` |
| `glofas_ensemble` | `28` | `0.169575` |
| `nws_nwm_ensemble` | `8` | `1.371917` |

Interpretation: the failed row was not a threshold artifact. It was a q50 median stabilization failure that allowed sampling from a bad terminal state in the original drop entrypoint. The repaired q50 stabilization plus the terminal-guard semantic fix removes the pathological q50 state/forecast scale while preserving the scientific spec and input bundle.

## Promotion

The repaired q50 policy is now promoted into the authoritative all-cutoff `exdqlm_multivar_drop` relaunch workflow.

Promotion doc:

`docs/he2_exdqlm_multivar_drop_q50_repair_promotion_20260602.md`

Shared policy module:

`scripts/he2_exdqlm_multivar_drop_q50_policy.py`

Fresh all-cutoff relaunch root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602`

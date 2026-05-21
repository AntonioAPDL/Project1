# exDQLM Multivariate Keep Guarded Reproduction 2026-05-21

## Purpose

This document records the isolated guarded q-lane reproduction run after the first repair sequence for the
multivariate `exdqlm keep` workflow. It is tracked because it is the first end-to-end runtime evidence after the
forecast `u_t` indexing fix, latent moment hardening, pseudo-data guard instrumentation, transform-regression tests,
and targeted guarded launcher were added.

The large run outputs and plots remain untracked under `reports/`.

## Run Contract

- Isolated runtime root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_guarded_log1p_q05_q35_q50_q95_20260521/`
- Isolated report root:
  `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/`
- Live monitor evidence:
  `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/live_monitor/LIVE_STATUS.md`
- Runtime stability audit evidence:
  `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/runtime_stability/`
- Guard event evidence:
  `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/pseudodata_guard_events/pseudodata_guard_events.csv`
- Post-stage log:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_guarded_log1p_q05_q35_q50_q95_20260521/runs/multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dfall999999_datastart2017_ready_exdqlm_multivar_keep__guarded_log1p_q05_q35_q50_q95_20260521/post/logs/post_runner.log`

The run was prepared by `repro/audits/prepare_exdqlm_keep_guarded_repro.py`, whose guarded-launch behavior is defined
at `repro/audits/prepare_exdqlm_keep_guarded_repro.py:42-155`. The launcher enabled pseudo-data guards in warning
mode and disabled the expensive post-save KL/JSD objective for this isolated audit run using
`DISC_W_POST_SAVE_OBJECTIVE_ENABLED=0`.

## Fit Outcome

All four targeted quantile lanes wrote `.RData` fit outputs.

| lane | status | iter | state norm sq | sigma exp | gamma exp | output bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| q05 | output written | 3000 | 1521.116 | 0.04159479 | 0.8357179 | 614403137 |
| q35 | output written | 3000 | 2233.589 | 0.1136433 | 0.1103588 | 615356651 |
| q50 | output written | 1079 | 2547.352 | 0.1227996 | -0.01111135 | 614988494 |
| q95 | output written | 3000 | 5082.421 | 0.07100852 | -1.762717 | 615690228 |

The wrapper exited nonzero only in the isolated post-processing stage. The post log reports:

`[crps.glofas.truth_TRUTH_MISSING] no USGS truth rows available at/after 2022-12-26.`

That is a post-stage truth-window/figure issue, not an exDQLM fit-output failure. The four `.RData` files were already
complete and were subsequently read by `repro/audits/exdqlm_keep_runtime_stability_audit.R`.

## Guard Events

The guard report contains 18 rows, all in q05 and all for historical `E_inv_uts`.

| lane | quantity | block | iterations | cap | peak max | peak iter | nonfinite | nonpositive |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| q05 | E_inv_uts | history | 1001-1018 | 5000 | 14397.595 | 1005 | 0 | 0 |

No guard rows were written for `FFF`, `QQQ_diag`, forecast pseudo-data, `E[s]`, `E[s^2]`, or `E[u]`.

Interpretation: the repaired path still has a transient q05 latent-tail episode, but it recovered without propagating
into a pseudo-data or state-norm explosion. The saved q05 `.RData` object has final/post-recovery `E[1/u]` maxima
below the warning cap, so the live guard CSV is essential evidence for this transient.

## Runtime Stability Audit

The read-only runtime audit wrote:

- `runtime_key_findings.csv`
- `state_norm_totals.csv`
- `object_summaries.csv`
- latent and pseudo-data trace PNGs

High-signal saved-output summaries from `runtime_key_findings.csv`:

| lane | max E[s] | max E[s^2] | max E[u] | max E[1/u] | historical FFF range | historical QQQ diag max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| q05 | 0.857360 | 1.12993 | 0.303452 | 2959.73 | [0.012569, 3.97928] | 0.325060 |
| q35 | 0.903181 | 1.23903 | 0.917347 | 1067.23 | [-0.0029885, 1.09207] | 0.979332 |
| q50 | 0.887234 | 1.20232 | 0.956068 | 457.015 | [-0.113456, 0.386141] | 1.01658 |
| q95 | 0.981712 | 1.38791 | 0.393845 | 539.212 | [-2.16174, -0.0462886] | 0.463255 |

State norm totals from `state_norm_totals.csv`:

| lane | block | finite frac | total state norm sq | max time state norm sq |
| --- | --- | ---: | ---: | ---: |
| q05 | history | 1 | 1521.116 | 7.14880 |
| q35 | history | 1 | 2233.589 | 13.1329 |
| q50 | history | 1 | 2547.352 | 15.2666 |
| q95 | history | 1 | 5082.421 | 23.8692 |

## Interpretation

This run materially changes the working diagnosis:

1. The previous q50 catastrophic state explosion was not reproduced. The prior q50 evidence had state norm squared
   `1.125e10`; this guarded run ended q50 at `2547.352`.
2. Saved outputs are finite and coherent enough for the read-only runtime audit across q05/q35/q50/q95.
3. The Kalman layer did not receive any guarded nonfinite or extreme `FFF`/`QQQ_diag` values in this run.
4. The result does not identify one sole causal fix, because the targeted run included multiple changes together:
   forecast `update_uts` indexing, `s_t` entropy/moment hardening, half-order `u_t` moment formulas, pseudo-data
   guard instrumentation, and the post-save objective disablement.
5. The remaining live q05 `E[1/u]` spike means latent-tail stability is improved but not fully closed. This is the
   strongest remaining runtime signal to investigate before a broad production relaunch.

## Promotion Status

This evidence is strong enough to continue with targeted ablations and guard-threshold tuning. It is not enough to
declare the algorithm fully solved or to broadly relaunch production.

Required next checks:

1. Run fixed/free `sigma/gamma` and fixed/free latent ablations on q05/q35/q50/q95 to isolate which repair mattered
   most.
2. Decide production guard thresholds and whether `E[1/u]` warning mode should become fail-fast or damped/refrozen
   behavior.
3. Add trend/transfer/discrepancy decomposition traces to confirm that stable state norms are not hiding
   identifiability drift.
4. Extend the compiled-vs-reference Kalman fixture to ragged forecast `keep` with `J=2` and retained transfer.
5. Fix or explicitly gate the post-stage truth-window figure path so isolated fit success is not reported as a full
   workflow failure when truth is unavailable after the target date.

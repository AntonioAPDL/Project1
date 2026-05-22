# exDQLM Multivariate Keep Patch Takeaways And Visual Review

Date: 2026-05-21

This note summarizes what the current patches actually changed, what the promotion-v2 evidence supports, and what
still needs careful improvement before treating the repaired `log1p_cms` path as broadly production-ready.

## Bottom Line

The current patch set is not just cosmetic. It fixes concrete failure modes in the active `exdqlm keep` workflow and
adds reproducible gates around the suspected feedback loop:

1. unstable latent-tail precision,
2. free `sigma/gamma` updates,
3. pseudo-data construction,
4. Kalman state absorption,
5. retained trend/transfer/discrepancy identifiability.

The isolated promotion-v2 run completed `fit`, `post`, `validate`, and `report` for q05/q35/q50/q95 with all `.RData`
outputs written and zero pseudo-data guard rows. The evidence supports this statement:

> The immediate `log1p_cms` algorithmic blow-up is controlled by the explicit capped/guarded promotion profile.

It does not yet support this stronger statement:

> The full scientific/statistical calibration problem is completely solved for every future spec and cutoff.

That distinction matters. The current patches solve the operational instability observed in the audited lanes, but the
tail lanes still deserve additional `sigma/gamma` damping/refreeze work and broader promotion tests before a broad
campaign relaunch.

## Main Patches

### 1. Forecast `u_t` Indexing Repair

Patch: forecast-member latent `update_uts(...)` calls now use the segment-local forecast column index `TT_sub`
consistently.

Why it matters: the previous indexing was a real implementation risk in the forecast-member latent update path. Bad
forecast indexing can feed the wrong retained-source member into `u_t`, then into pseudo-data precision and ultimately
the Kalman update.

Evidence:

- active fit-stage and sampling-stage latent loops:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4235-4333` and
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:5011-5043`;
- regression test: `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`;
- final findings entry: `docs/exdqlm_multivar_keep_final_findings.md`.

### 2. Stable Canonical `s_t` Moments And Entropy

Patch: `s_t` positive-truncated-normal moments and entropy were made numerically stable and aligned with the canonical
exAL conditional.

Why it matters: unstable or inconsistent `E[s_t]`, `E[s_t^2]`, or entropy can perturb the variational objective and
the pseudo-data terms. This patch removes one plausible formula-level explanation for the failure.

Evidence:

- canonical source: `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex`;
- active update path: `update_sts(...)` at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1855`;
- test coverage: `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`.

### 3. Closed-Form Half-Order `u_t` Moments

Patch: `u_t` moments use stable half-order GIG identities for `E[u_t]`, `E[1/u_t]`, `E[log u_t]`, and entropy-related
quantities.

Why it matters: the observed log1p failures were strongly tied to tail-lane precision. `E[1/u_t]` enters the
pseudo-data precision, so numeric spikes here directly affect `FFF`, `QQQ`, and the state update.

Evidence:

- canonical source: `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex`;
- active update path: `update_uts(...)` at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1903`;
- test coverage: `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`.

### 4. Pseudo-Data Guards

Patch: explicit finite/range guards were added around historical and forecast pseudo-data quantities, with promotion
mode configured to fail fast rather than silently continue.

Why it matters: this is the diagnostic tripwire for the root feedback loop. If latent moments or `sigma/gamma` drive
bad pseudo-data, the workflow now records or fails at the causal boundary instead of only showing a late state blow-up
or missing output.

Evidence:

- active pseudo-data shape checks and guards:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3055-3256`;
- seed and live forecast pseudo-data construction:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3671-3916`;
- runtime evidence: `reports/exdqlm_keep_runtime_stability_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`;
- promotion-v2 result: zero pseudo-data guard rows across q05/q35/q50/q95.

### 5. Explicit Promotion Profile With Latent Precision Cap

Patch: isolated promotion tooling can launch a named profile with:

- pseudo-data guard mode `fail`,
- latent `E[1/u_t]` cap `5000`,
- state guard enabled,
- terminal sampling guard enabled,
- delayed state guard start at iteration `1000`,
- post-save objective disabled unless explicitly requested.

Why it matters: this is the most sensitive current patch. The latent precision cap directly changes pseudo-observation
precision. That is why it must remain explicit and named, not silently hidden as the default.

Evidence:

- latent cap implementation: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1932-1998`;
- promotion tooling:
  `repro/audits/prepare_exdqlm_keep_guarded_repro.py:86-99`,
  `repro/audits/prepare_exdqlm_keep_guarded_repro.py:173-195`;
- tests: `tests/python/test_exdqlm_keep_ablation_tooling.py:97-179`;
- successful run root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/runs/multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dfall999999_datastart2017_ready_exdqlm_multivar_keep__promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u`;
- live monitor final:
  `reports/exdqlm_keep_guarded_repro_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/live_monitor_final/LIVE_STATUS.md`.

### 6. Delayed State Guard Start

Patch: `DISC_GAMSIG_STATE_GUARD_START_ITER` delays state-norm guard/refreeze behavior until after early recovery.

Why it matters: promotion v1 failed even with zero pseudo-data guard rows because the state guard was active from the
first refresh and trapped q05/q95 in repeated refreeze. Promotion v2 passed after delaying that guard.

Evidence:

- promotion v1 evidence:
  `reports/exdqlm_keep_guarded_repro_promotion_log1p_q05_q35_q50_q95_v1_20260521_latent_cap_e_inv_u/`;
- promotion v2 evidence:
  `reports/exdqlm_keep_guarded_repro_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`;
- active state guard config and use:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:338-353`,
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4538-4796`;
- test coverage: `tests/python/test_exdqlm_keep_ablation_tooling.py` and
  `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`.

### 7. Post-Stage Truth Availability Gate

Patch: missing future USGS truth no longer makes a successful fit look like a failed workflow. Missing truth is
reported and padded as `NA` for CRPS/figure paths.

Why it matters: this separates algorithmic fit failure from normal future-truth unavailability after the cutoff.

Evidence:

- helper: `R/environmetrics/02_helpers_core.R:1639`;
- figure callers:
  `R/environmetrics/40_figures_smoke_fast.R:2014-2456`,
  `R/environmetrics/40_figures.R:5367-5788`;
- test: `tests/testthat/test_post_crps_tables.R:29-46`;
- promotion-v2 post output:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/runs/multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dfall999999_datastart2017_ready_exdqlm_multivar_keep__promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/post/outputs/`.

### 8. Reproducible Visual Review Script

Patch: `repro/audits/exdqlm_keep_visual_review.R` now extracts ELBO traces, `new.theta.out$sm` state paths,
`new.theta.out$exps`, and decomposition-derived USGS/forecast panels from a completed run.

Why it matters: visual review is now reproducible from the `.RData` outputs and decomposition CSVs. The plots are no
longer ad hoc screenshots.

Evidence:

- script extraction and summaries: `repro/audits/exdqlm_keep_visual_review.R:95-196`;
- script plot generation: `repro/audits/exdqlm_keep_visual_review.R:223-298`;
- test: `tests/testthat/test_exdqlm_keep_visual_review.R:1-95`;
- visual report:
  `reports/exdqlm_keep_visual_review_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`.

## Promotion-v2 Numerical Takeaways

Promotion-v2 completed the full wrapper and wrote all q05/q35/q50/q95 outputs.

Terminal fit monitor:

| lane | terminal iter | state norm sq | sigma exp | gamma exp | output |
| --- | ---: | ---: | ---: | ---: | --- |
| q05 | 3000 | 1521.127 | 0.04159492 | 0.8357256 | written |
| q35 | 3000 | 2233.589 | 0.1136433 | 0.1103588 | written |
| q50 | 1079 | 2547.352 | 0.1227996 | -0.01111135 | written |
| q95 | 3000 | 5082.421 | 0.07100852 | -1.762717 | written |

Saved-output runtime summaries:

| lane | max saved historical `E[1/u_t]` | max historical `FFF` | max `QQQ_diag` |
| --- | ---: | ---: | ---: |
| q05 | 764.467843 | 3.979276 | 0.325061 |
| q35 | 923.202869 | 1.092066 | 0.979332 |
| q50 | 172.961606 | 0.386141 | 1.016580 |
| q95 | 110.044606 | -0.046289 | 0.463255 |

Important nuance: q95 `FFF` values are negative in the saved-output summary, so its "max" is the least-negative
value. The observed range was finite and far from guard limits.

Decomposition summaries:

- historical reconstruction error was numerical tolerance only, about `8.9e-16` or smaller;
- q05/q95 source-1 historical median absolute `mu_without_transfer`: `0.192401` / `0.651413`;
- q05/q95 source-1 historical median absolute discrepancy: `0.398565` / `0.595735`.

This is radically smaller than the latent-freeze failure scale, where q05/q95 state norms and components became
large even though output files were written.

## Visual Evidence To Review

Visual report directory:

`reports/exdqlm_keep_visual_review_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`

Main PNGs:

- `elbo_convergence_panel.png`
- `elbo_tail_step_panel.png`
- `thetaout_state_norm_panel.png`
- `thetaout_selected_states_panel.png`
- `usgs_history_target_exps_last730.png`
- `usgs_history_q05_q50_q95_band_last730.png`
- `forecast_source_exps_by_lane.png`

ELBO summary:

| lane | saved iters | final ELBO | max abs step last 100 | delta last 100 |
| --- | ---: | ---: | ---: | ---: |
| q05 | 3001 | -59.461997 | 5.245750e-07 | 0.000043 |
| q35 | 3001 | -59.121936 | 5.754627e-07 | -0.000054 |
| q50 | 1080 | -59.093052 | 8.428787e-05 | -0.000491 |
| q95 | 3001 | -59.214517 | 1.982782e-07 | -0.000018 |

Interpretation: there is no visual evidence of late ELBO divergence. q05/q35/q95 are essentially flat in the tail.
q50 stopped earlier and also has a small tail step.

`theta.out` state summary:

| lane | max `sum(sm^2)` | final `sum(sm^2)` | median `sum(sm^2)` |
| --- | ---: | ---: | ---: |
| q05 | 7.148848 | 0.852233 | 0.364555 |
| q35 | 13.132914 | 1.410930 | 0.400089 |
| q50 | 15.266613 | 1.609808 | 0.441781 |
| q95 | 23.869177 | 2.993857 | 1.220264 |

Interpretation: the saved `theta.out$sm` paths are bounded. q95 is the largest lane, as expected, but this is not a
runaway state path.

USGS target-exps summary:

| lane | median abs error, log1p | 95% abs error, log1p | max abs error, log1p |
| --- | ---: | ---: | ---: |
| q05 | 0.161837 | 1.164779 | 3.586249 |
| q35 | 0.123174 | 0.670850 | 3.176152 |
| q50 | 0.135384 | 0.650722 | 3.069332 |
| q95 | 0.452054 | 1.165322 | 2.486930 |

Interpretation: the q05/q50/q95 band generally tracks the observed USGS dynamics and preserves quantile ordering.
The median is smooth and misses some sharp observed peaks and fast recessions. That is a remaining scientific
calibration issue, not evidence of the old numerical explosion.

## Most Sensitive Areas Still To Improve

### P0: Treat Latent `E[1/u_t]` Capping As A Named Production Profile

The cap is effective, but it changes pseudo-data precision. Keep it visible in manifests, launch scripts, and report
metadata. Do not bury it as an invisible default.

Next tests:

1. rerun the same promotion profile on at least one nearby cutoff;
2. compare capped versus uncapped saved `E[1/u_t]`, `FFF`, `QQQ`, and decomposition;
3. verify no systematic q05/q95 bias is introduced.

### P1: Add A Damped Or Refrozen `sigma/gamma` Candidate

Promotion-v2 passed, but q95 still ends with a relatively large negative `gamma_exp` (`-1.762717`). The latent-freeze
ablation showed that free `sigma/gamma` can still drive very large q05/q95 state paths. This is the next most
important root-level hardening.

Next tests:

1. implement damping/refreeze as an explicit profile;
2. compare q05/q35/q50/q95 against promotion-v2;
3. require no pseudo-data guard rows, bounded state norms, coherent decomposition, and stable ELBO tails.

### P1: Keep Decomposition Monitoring Mandatory

A run can be numerically finite while trend/transfer/discrepancy are scientifically implausible. The decomposition
audit is the best current check that the retained blocks are not absorbing absurd signal.

Next tests:

1. make decomposition summary part of every promotion bundle;
2. add thresholds for reconstruction error, component magnitudes, and lane ordering;
3. review q95 retained-transfer/discrepancy magnitudes before broader launches.

### P1: Broaden Runtime Promotion Before Any Broad Campaign

The q05/q35/q50/q95 evidence is strong for the audited cutoff/spec. It is not enough to prove universal stability.

Next tests:

1. same profile on a second cutoff;
2. optionally include q01/q99 only after q05/q95 pass again;
3. keep fail-fast pseudo-data guard and delayed state guard active.

### P2: Improve ELBO And State Diagnostics For Routine Reports

The new visual-review script proves the needed data are present. The next step is integrating this into routine
promotion reporting so reviewers do not have to remember separate commands.

Next tests:

1. run `repro/audits/exdqlm_keep_visual_review.R` from the promotion wrapper or report stage;
2. include the seven main PNGs in the curated evidence bundle;
3. record the exact `.RData` path and decomposition directory in the report README.

## Readiness Assessment

Ready now:

- use promotion-v2 as the current isolated, evidence-backed `log1p_cms` candidate;
- review the ELBO, `theta.out`, and USGS exps plots from the generated report;
- keep the patch set as the current repaired baseline.

Not ready yet:

- broad production relaunch without at least one more cutoff/spec check;
- making latent precision capping invisible/default;
- declaring `sigma/gamma` fully solved without a damping/refreeze candidate.

The best current answer is: we now understand the failure mechanism well enough to control the observed blow-up, but
the robust long-term fix is still a layered promotion policy plus one more `sigma/gamma` hardening pass, not a single
magic one-line patch.

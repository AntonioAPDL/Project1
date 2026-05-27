# exDQLM Multivariate Keep Repair Tracker

Last updated: 2026-05-23

## Scope

This is the living execution tracker for the repaired `log1p_cms` multivariate `exdqlm keep` workflow. It tracks the
remaining work after the full audit, first repair sequence, and isolated guarded q05/q35/q50/q95 reproduction.

The current goal is not to produce every possible diagnostic artifact. The goal is to finish the remaining work in a
high-quality sequence:

1. preserve the successful guarded-run evidence,
2. add only the curated PNG/evidence bundle needed for review and communication,
3. isolate which repair mattered through targeted ablations,
4. make q05-like latent-tail behavior production-safe,
5. verify scientific component behavior and remaining Kalman contracts,
6. fix operational post-stage failure modes,
7. decide whether the repaired `log1p_cms` path is ready for broader production.

## Operating Rules

1. Do not stop, relaunch, or modify existing production campaigns unless explicitly requested.
2. Keep new runtime outputs under `reports/` and untracked by default.
3. Commit tracked docs, tests, scripts, and small reproducibility helpers intentionally.
4. After every phase, update this tracker with:
   - commands run,
   - evidence paths,
   - pass/fail status,
   - remaining risk,
   - next action.
5. Do not promote a broad production relaunch until the promotion gate at the end of this tracker is explicitly
   satisfied.

## Current Baseline

### Post-Launch Repair Status

The 2026-05-22 all-cutoff full-history promotion launch is no longer in a "ready, not launched" state. It partially
completed:

- `20211112` and `20221225` reached post/report pass.
- `20210123`, `20211221`, and `20220511` failed at fit because one quantile lane in each row stopped before the
  required gamma/sigma update count.
- The failure is now tracked as a near-zero gamma/sigma split/fallback defect, not as a pseudo-data or Kalman blow-up.

Authoritative repair plan:

- [near-zero gamma/sigma repair plan](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_near_zero_gamsig_repair_plan_20260523.md)
- [near-zero gamma/sigma repair report](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_near_zero_gamsig_repair_report_20260523.md)

Implementation status:

- Near-zero `sigma_only` fallback for non-median lanes is implemented in the active multivariate `keep` runner.
- Unified config/stage-fit propagation and monitor counters are implemented.
- Deterministic unit/source/config/monitor tests pass.
- Runtime promotion is still gated on isolated targeted fit smokes for the three failed lanes plus healthy controls.

Do not relaunch the broad all-cutoff campaign until the targeted near-zero repair gates in that plan pass.

Tracked summary docs:

- [final findings](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_final_findings.md)
- [patch takeaways and visual review](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_patch_takeaways_visual_review.md)
- [repair and transform regression plan](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_repair_and_transform_regression_plan.md)
- [guarded reproduction evidence](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_guarded_repro_20260521.md)
- [multi-cutoff promotion plan](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_multicutoff_promotion_plan_20260522.md)
- [all-cutoff full-history promotion readiness](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_allcutoffs_fullhistory_promotion_readiness_20260522.md)

Current promotion package:

| item | status | evidence |
| --- | --- | --- |
| All five HE2 cutoffs package | partially launched; repair-gated | `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522.template.yaml` |
| All-cutoff guarded batch | partially launched; repair-gated | `config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522.yaml` |
| `max_iter=100` retarget | locked | template/batch tests and generated-config test |
| Full-history 1987 input bundle | locked | generated `cutoff_bundle_audit.csv` under the all-cutoff preflight root |
| GDPC/PPT/SOIL covariates | locked | support manifest and generated-config tests |
| Blended PPT/SOIL deterministic forecasts | locked | generated-config test asserts GEFS q85 sources plus noisy/observed blends |
| Full transfer features | locked | generated-config test asserts PPT/SOIL/PCA plus squares, interaction, lags |
| Full harmonic basis | locked | `tests/testthat/test_exdqlm_multivar_structure_contract.R` |
| `.RData` policy | locked | current cleanup wrapper keeps `.RData` through post and removes it after post; no-cleanup queue patch intentionally skipped |

Completed first repair sequence:

| item | status | evidence |
| --- | --- | --- |
| Forecast `update_uts` `TT_sub` indexing fix | done | commit `eb22e6e` |
| Transform forensics and scale-contract tests | done | commit `be5cf55` |
| Stable `s_t` moments/entropy | done | commit `4bbb643` |
| Closed-form half-order `u_t` moments | done | commit `4bbb643` |
| Pseudo-data guards in warning mode | done | commit `4bbb643` |
| Guarded repro launcher and post-save objective switch | done | commit `5a83162` |
| Guarded run monitor | done | commit `869c9c2` |
| Guarded q05/q35/q50/q95 reproduction | done | `docs/exdqlm_multivar_keep_guarded_repro_20260521.md` |

Guarded reproduction result:

| lane | iter | terminal state norm sq | fit output |
| --- | ---: | ---: | --- |
| q05 | 3000 | 1521.116 | written |
| q35 | 3000 | 2233.589 | written |
| q50 | 1079 | 2547.352 | written |
| q95 | 3000 | 5082.421 | written |

Residual concern:

| issue | status | evidence | next action |
| --- | --- | --- | --- |
| q05 transient historical `E[1/u_t]` burst | open | 18 guard rows, iterations 1001-1018, peak `14397.595` | tune/decide guard response |
| Single causal layer not isolated | open | guarded run used multiple fixes together | run ablations |
| Post-stage no-truth failure | open | no USGS truth rows at/after `2022-12-26` | gate/fix post-stage figure path |

## Execution Checklist

### T0. Curated Evidence Bundle From Existing Guarded Outputs

Status: done

Purpose: create a compact review bundle, not a plot dump. This should help us inspect and communicate the repaired
run before spending time on causal ablations.

Inputs:

- existing guarded q05/q35/q50/q95 `.RData` outputs under the isolated guarded run root,
- existing runtime audit output under
  `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/runtime_stability/`.

Required outputs under a new or existing `reports/` subdirectory:

1. q05/q35/q50/q95 state norm panel.
2. `E[1/u_t]` panel, with q05 iterations 1001-1018 called out when possible.
3. `FFF` and `QQQ_diag` panels.
4. sigma/gamma trace or terminal-lane summary, depending on what is available without re-fitting.
5. selected state-coordinate panel.
6. short `README.md` explaining what the plots show and what they do not prove.

Acceptance criteria:

1. No new model fitting.
2. Bundle is small enough for review.
3. The q05 `E[1/u_t]` transient is visible or explicitly linked to the guard CSV.
4. The bundle supports, but does not replace, the ablation plan.

Evidence:

- script:
  `repro/audits/exdqlm_keep_curated_evidence_bundle.R`
- test:
  `tests/testthat/test_exdqlm_curated_evidence_bundle.R`
- report:
  `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/curated_evidence/`
- validation:
  `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_curated_evidence_bundle.R')"` passed
  with 6 expectations.

### T0b. Promotion-v2 ELBO, `theta.out`, And USGS Visual Review

Status: done

Purpose: make the requested ELBO convergence, saved state, and USGS `new.theta.out$exps` review reproducible from
the promotion-v2 `.RData` outputs and decomposition CSVs.

Required outputs:

1. ELBO convergence by q-lane.
2. Tail ELBO step size by q-lane.
3. `sum(new.theta.out$sm^2)` by history time and q-lane.
4. Selected `new.theta.out$sm` coordinates labelled by the state-coordinate map.
5. observed USGS against q05/q35/q50/q95 target `exps` for the final 730 history days.
6. q05/q50/q95 target-exps band against observed USGS.
7. retained-source forecast `exps` by lead.

Evidence:

- script:
  `repro/audits/exdqlm_keep_visual_review.R`
- test:
  `tests/testthat/test_exdqlm_keep_visual_review.R`
- report:
  `reports/exdqlm_keep_visual_review_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`
- summary:
  [patch takeaways and visual review](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_patch_takeaways_visual_review.md)
- validation:
  `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_keep_visual_review.R')"` passed with
  7 expectations.

Observed result:

- no late ELBO divergence; q05/q35/q95 tail steps were below `6e-7`, and q50 was below `8.5e-5`;
- saved `theta.out$sm` state norms were bounded, with max `sum(sm^2)` from `7.148848` in q05 to `23.869177` in q95;
- q05/q50/q95 USGS target-exps ordering is coherent;
- q50 is smooth and misses some sharp observed peaks/recessions, which remains a scientific calibration review item
  rather than evidence of numerical blow-up.

### T1. Ablation Harness Design

Status: done

Purpose: design the smallest safe harness for causal isolation.

Required design decisions:

1. How to freeze or replay `sigma/gamma`.
2. How to freeze or replay latent moments.
3. Which q-lanes are required for each ablation: default q05/q35/q50/q95, with permission to reduce only if justified.
4. Which existing guarded run values are used as seeds or reference values.
5. Which environment variables or config flags are added.

Acceptance criteria:

1. The harness is isolated from production roots.
2. It has explicit output/report paths.
3. It records all freeze/replay values in manifests.
4. It has at least smoke-level parse/test coverage before runtime use.

Evidence:

- design:
  [exdqlm_multivar_keep_ablation_harness_design.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_ablation_harness_design.md)
- single-run preparer:
  `repro/audits/prepare_exdqlm_keep_guarded_repro.py`
- matrix preparer:
  `repro/audits/prepare_exdqlm_keep_ablation_matrix.py`
- tests:
  `tests/python/test_exdqlm_keep_ablation_tooling.py`
  and `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`
- prepared matrix:
  `reports/exdqlm_keep_ablation_matrix_ablation_log1p_q05_q35_q50_q95_20260521/`
- validation:
  `python3 -m unittest tests.python.test_exdqlm_keep_ablation_tooling -v` passed with 3 tests;
  `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R')"`
  passed with 52 expectations.

### T2. Fixed/Free `sigma/gamma` Ablations

Status: fixed-gamsig v3 complete; compared against latent-freeze, latent-cap, and promotion-v2 evidence

Purpose: determine whether the `sigma/gamma` approximation or calibration is the decisive instability source under
the current `log1p_cms` scale.

Run matrix:

| condition | lanes | expected evidence |
| --- | --- | --- |
| free `sigma/gamma`, repaired latent path | q05/q35/q50/q95 | control against guarded run |
| fixed `sigma/gamma`, free latent path | q05/q35/q50/q95 | isolates gamsig dynamics |
| damped/refrozen `sigma/gamma`, free latent path | q05/q35/q50/q95 if needed | tests production control |

Required outputs:

1. `sigma_exp_vec`, `gamma_exp_vec`, objective values, optimizer convergence flags.
2. `E[s]`, `E[s^2]`, `E[u]`, `E[1/u]`, `E[log u]`.
3. `FFF`, `QQQ_diag`, `FFF_forecast`, `QQQ_forecast_diag`.
4. state norms and guard events.
5. runtime summary README.

Acceptance criteria:

1. If fixed `sigma/gamma` removes q05 `E[1/u]` bursts or materially changes stability, prioritize gamsig
   recalibration/damping.
2. If fixed `sigma/gamma` does not materially change the q05 burst, prioritize latent guard response and
   identifiability/decomposition.
3. Do not infer from terminal state norm alone; inspect latent and pseudo-data trajectories.

Prepared condition:

- `fixed-gamsig`
- invalid first launch:
  `reports/exdqlm_keep_ablation_matrix_ablation_log1p_q05_q35_q50_q95_20260521/launch_ablation_matrix_ablation_log1p_q05_q35_q50_q95_20260521.sh`
  was stopped during early fixed-gamsig fit initialization after logs showed `warmup_freeze_iters=10` instead of the
  intended `max_iter + 5`. Root cause: `R/unified/stages/stage_fit.R` rebuilds worker `DISC_GAMSIG_*` values from the
  generated YAML policy, overriding wrapper-level exports.
- fix:
  `repro/audits/prepare_exdqlm_keep_guarded_repro.py` now writes fixed-gamsig policy values into
  `fit.exdqlm_multivar.gamma_sigma` and existing quantile overrides.
- v2 prepared launch:
  `reports/exdqlm_keep_ablation_matrix_ablation_log1p_q05_q35_q50_q95_v2_20260521/launch_ablation_matrix_ablation_log1p_q05_q35_q50_q95_v2_20260521.sh`
- v2 launch result:
  failed before fitting because config validation requires `state_refresh_schedule.start_iter > warmup_freeze_iters`
  when the refresh schedule is enabled. Fixed-gamsig config generation now disables `state_refresh_schedule`.
- v3 prepared launch:
  `reports/exdqlm_keep_ablation_matrix_ablation_log1p_q05_q35_q50_q95_v3_20260521/launch_ablation_matrix_ablation_log1p_q05_q35_q50_q95_v3_20260521.sh`
- original launch, retained only as invalid/stopped evidence:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_ablation_log1p_q05_q35_q50_q95_20260521_fixed_gamsig/control/launch_multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dfall999999_datastart2017_ready_exdqlm_multivar_keep__ablation_log1p_q05_q35_q50_q95_20260521_fixed_gamsig.sh`

Valid fixed-gamsig v3 evidence:

- run root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_ablation_log1p_q05_q35_q50_q95_v3_20260521_fixed_gamsig/runs/multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dfall999999_datastart2017_ready_exdqlm_multivar_keep__ablation_log1p_q05_q35_q50_q95_v3_20260521_fixed_gamsig`
- fit status:
  `reports/exdqlm_keep_guarded_repro_ablation_log1p_q05_q35_q50_q95_v3_20260521_fixed_gamsig/live_monitor_final/LIVE_STATUS.md`
- runtime stability:
  `reports/exdqlm_keep_runtime_stability_ablation_log1p_q05_q35_q50_q95_v3_20260521_fixed_gamsig/`
- curated evidence:
  `reports/exdqlm_keep_curated_evidence_ablation_log1p_q05_q35_q50_q95_v3_20260521_fixed_gamsig/`
- decomposition evidence:
  `reports/exdqlm_keep_decomposition_ablation_log1p_q05_q35_q50_q95_v3_20260521_fixed_gamsig/`

Observed result:

- all four lanes wrote `.RData` with `gamsig_update_iters=0` and `frozen=true`;
- no pseudo-data guard rows were written;
- terminal history state norm squared was `962.241` for q05, `1956.977` for q35, `2320.214` for q50, and
  `8875.863` for q95;
- saved-output `E[1/u]` stayed under the current `5000` guard cap, with largest historical maxima around
  q95/source1 `4818.429` and q05/source1 `4401.679`.

Interpretation so far:

- Freezing `sigma/gamma` prevents the q05 live guard burst seen in the guarded control from appearing as a
  pseudo-data guard event, but saved-output latent tails are not uniformly smaller than the control. Treat this as
  evidence for `sigma/gamma`/latent interaction, not proof that the latent formulas are irrelevant.

### T3. Fixed/Free Latent Moment Ablations

Status: complete for v3 matrix

Purpose: determine whether the `s_t/u_t` updates remain the dominant source of instability after numerical
hardening.

Run matrix:

| condition | lanes | expected evidence |
| --- | --- | --- |
| free latent moments, free `sigma/gamma` | q05/q35/q50/q95 | repaired control |
| fixed/replayed latent moments, free `sigma/gamma` | q05/q35/q50/q95 | isolates latent dynamics |
| capped/damped `E[1/u]`, free `sigma/gamma` | q05 first, then q35/q50/q95 if promising | tests production guard policy |

Acceptance criteria:

1. If replayed/capped latent moments stabilize q05 without harming q50/q95, define a production policy.
2. If latent replay does not change behavior, shift emphasis to `sigma/gamma` and decomposition.
3. All latent interventions must be documented as diagnostics unless explicitly promoted later.

Prepared conditions:

- `latent-freeze`
- `latent-cap-e-inv-u`
- original matrix launch, stopped before latent conditions because fixed-gamsig v1 was invalid:
  `reports/exdqlm_keep_ablation_matrix_ablation_log1p_q05_q35_q50_q95_20260521/launch_ablation_matrix_ablation_log1p_q05_q35_q50_q95_20260521.sh`
- v2 matrix launch:
  `reports/exdqlm_keep_ablation_matrix_ablation_log1p_q05_q35_q50_q95_v2_20260521/launch_ablation_matrix_ablation_log1p_q05_q35_q50_q95_v2_20260521.sh`
- v3 matrix launch:
  `reports/exdqlm_keep_ablation_matrix_ablation_log1p_q05_q35_q50_q95_v3_20260521/launch_ablation_matrix_ablation_log1p_q05_q35_q50_q95_v3_20260521.sh`

Valid latent-freeze v3 evidence:

- run root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_freeze/runs/multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dfall999999_datastart2017_ready_exdqlm_multivar_keep__ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_freeze`
- fit status:
  `reports/exdqlm_keep_guarded_repro_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_freeze/live_monitor_final/LIVE_STATUS.md`
- runtime stability:
  `reports/exdqlm_keep_runtime_stability_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_freeze/`
- curated evidence:
  `reports/exdqlm_keep_curated_evidence_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_freeze/`
- decomposition evidence:
  `reports/exdqlm_keep_decomposition_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_freeze/`

Observed latent-freeze result:

- all four lanes wrote `.RData` and the full wrapper completed post/validate/report under the T7 truth-window gate;
- no pseudo-data guard rows were written;
- terminal history state norm squared was `8011171` for q05, `13652.71` for q35, `4803.106` for q50, and
  `8190166` for q95;
- q05/q95 sigma/gamma drifted into large asymmetric tail values even though the latent moments were fixed:
  q05 `sigma_exp=3.065681`, `gamma_exp=6.756436`; q95 `sigma_exp=3.075551`, `gamma_exp=-6.76794`;
- runtime audit shows frozen latent values, with historical `E[1/u]` constant at approximately `0.345762`
  for the target, `0.156208` for source 1, and `0.601143` for source 2;
- decomposition reconstructs fitted means to numerical tolerance, but q05/q95 component magnitudes are large:
  historical median absolute `mu_without_transfer` is about `55.16` for q05 and `55.84` for q95, and source-1
  discrepancy is about `23.19` for q05 and `23.07` for q95.

Valid latent-cap v3 evidence:

- run root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_cap_e_inv_u/runs/multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dfall999999_datastart2017_ready_exdqlm_multivar_keep__ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_cap_e_inv_u`
- fit status:
  `reports/exdqlm_keep_guarded_repro_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_cap_e_inv_u/live_monitor_final/LIVE_STATUS.md`
- runtime stability:
  `reports/exdqlm_keep_runtime_stability_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_cap_e_inv_u/`
- curated evidence:
  `reports/exdqlm_keep_curated_evidence_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_cap_e_inv_u/`
- decomposition evidence:
  `reports/exdqlm_keep_decomposition_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_cap_e_inv_u/`

Observed latent-cap result:

- all four lanes wrote `.RData`, and the full wrapper completed post/validate/report under the T7 truth-window gate;
- no pseudo-data guard rows were written;
- terminal history state norm squared was `1521.127` for q05, `2233.589` for q35, `2547.352` for q50, and
  `5082.421` for q95;
- saved-output historical `E[1/u]` maxima were below the `5000` cap in all lanes: q05 `764.468`,
  q35 `923.203`, q50 `172.962`, and q95 `110.045` for the target-source row summarized in the runtime report;
- historical `FFF` and `QQQ_diag` stayed small compared with the guard caps: q05 `FFF` max `3.97928`,
  q95 `FFF` max `-0.0462886`, q05 `QQQ_diag` max `0.325061`, and q95 `QQQ_diag` max `0.463255`;
- decomposition reconstructs fitted means to numerical tolerance, with q05/q95 component magnitudes far closer to
  the fixed-gamsig/control scale than to the latent-freeze failure scale.

Interpretation so far:

- Freezing latent moments is not sufficient to stabilize q05/q95 when `sigma/gamma` remains free. That makes a
  latent-formula-only explanation unlikely.
- Capping `E[1/u]` during the update loop produces finite q05/q95 outputs in this isolated diagnostic, but it
  does not by itself prove a scientifically safe production fix because it directly changes pseudo-observation
  precision.
- The current leading explanation is interactional: latent-tail precision, `sigma/gamma` dynamics, and retained
  state identifiability reinforce each other. The strongest causal evidence is that free `sigma/gamma` can still
  drive large q05/q95 states under fixed latent moments, while fixed `sigma/gamma` and capped latent precision both
  keep pseudo-data and state norms finite.

### T4. q05 Guard-Response Policy

Status: policy, isolated promotion tooling, and first capped promotion runtime complete

Purpose: turn the warning-mode q05 `E[1/u_t]` evidence into a production decision.

Candidate policies:

1. warn-only with documented thresholds,
2. fail-fast on cap exceedance,
3. temporary `sigma/gamma` refreeze after guard,
4. damp/cap `E[1/u_t]` before pseudo-data construction,
5. trigger snapshotting only.

Acceptance criteria:

1. The chosen policy prevents silent destructive pseudo-data.
2. The policy does not mask scientifically important tail behavior without reporting it.
3. The policy is tested with deterministic fixtures and at least one targeted q05 runtime check.

Policy document:

- `docs/exdqlm_multivar_keep_guard_response_policy.md`

Current decision:

- diagnostic ablations remain `warn` mode with guard CSVs;
- promotion candidates should use `DISC_PSEUDODATA_GUARD_MODE=fail`;
- latent `E[1/u]` capping remains diagnostic by default. The latent-cap run is clean enough to justify a separate
  capped promotion candidate, but not clean enough to silently make capping the default without a fail-fast
  production run and scientific review;
- `repro/audits/prepare_exdqlm_keep_guarded_repro.py --guard-profile promotion` now prepares isolated candidates
  with fail-fast pseudo-data guards, explicit state norm/refreeze controls, delayed state-guard start, and terminal
  sampling guard exports.

Promotion v1 evidence:

- run/report root:
  `reports/exdqlm_keep_guarded_repro_promotion_log1p_q05_q35_q50_q95_v1_20260521_latent_cap_e_inv_u/`
- all pseudo-data guard rows: `0`;
- q05 and q95 failed at iter `3000` with repeated state-guard events and terminal state norm squared around
  `1.50e6` and `1.56e6`;
- q35 was interrupted after the overall promotion decision was already failed;
- interpretation: state guarding was active too early and trapped q05/q95 before the latent-cap path could recover
  to the stable state scale seen in the diagnostic latent-cap v3 run.

Promotion v2 evidence:

- run root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/runs/multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dfall999999_datastart2017_ready_exdqlm_multivar_keep__promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u`
- final live status:
  `reports/exdqlm_keep_guarded_repro_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/live_monitor_final/LIVE_STATUS.md`
- runtime stability:
  `reports/exdqlm_keep_runtime_stability_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`
- curated evidence:
  `reports/exdqlm_keep_curated_evidence_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`
- decomposition evidence:
  `reports/exdqlm_keep_decomposition_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`
- all q05/q35/q50/q95 lanes wrote `.RData`, and the full wrapper completed post/validate/report;
- no pseudo-data guard rows were written;
- terminal state norm squared was q05 `1521.127`, q35 `2233.589`, q50 `2547.352`, q95 `5082.421`;
- post-stage truth-window handling exported missing future USGS truth rows as `NA`-padded CRPS inputs rather than
  failing the workflow.

### T5. Trend/Transfer/Discrepancy Decomposition

Status: implemented; fixed-gamsig, latent-freeze, and latent-cap runtime validation complete

Purpose: verify the stable outputs are scientifically interpretable, not merely finite.

Required outputs:

1. trend contribution traces,
2. retained transfer contribution traces,
3. discrepancy contribution traces by source/lead where available,
4. reconstruction checks against fitted means,
5. q-lane comparison table.

Acceptance criteria:

1. Contributions reconstruct fitted means within numerical tolerance.
2. No single weakly identified component silently absorbs implausible signal under the repaired run.
3. If identifiability is questionable, document whether it appears only under unstable inputs or also under healthy
   pseudo-data.

Implementation and evidence:

- script:
  `repro/audits/exdqlm_keep_decomposition_audit.R`
- deterministic test:
  `tests/testthat/test_exdqlm_keep_decomposition_audit.R`
- fixed-gamsig evidence:
  `reports/exdqlm_keep_decomposition_ablation_log1p_q05_q35_q50_q95_v3_20260521_fixed_gamsig/`
- latent-freeze evidence:
  `reports/exdqlm_keep_decomposition_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_freeze/`
- latent-cap evidence:
  `reports/exdqlm_keep_decomposition_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_cap_e_inv_u/`

Current result:

- history and forecast reconstructions match populated `new.theta.out$exps` rows to numerical tolerance
  (`<= 8.9e-16` in the fixed-gamsig report);
- retained transfer `zeta` is finite in history and both forecast segments;
- q95 has the largest median component magnitudes among fixed-gamsig lanes, especially forecast `zeta` and
  source-1 discrepancy, so identifiability remains a scientific monitoring concern even when pseudo-data are finite.
- latent-freeze q05/q95 is the strongest identifiability warning: source-1 historical median absolute
  `mu_without_transfer` is about `55` and discrepancy about `23`;
- latent-cap q05/q95 returns to a small-component scale, with source-1 historical median absolute
  `mu_without_transfer` q05 `0.192401` and q95 `0.651413`.

### T6. Ragged Forecast Kalman Fixture

Status: done

Purpose: close the remaining compiled Kalman/RTS contract gap for the active `keep` structure.

Fixture requirements:

1. `J=2`,
2. retained transfer block `ppx>0`,
3. true ragged forecast segment transition,
4. compiled-vs-reference checks for filtered and smoothed means/covariances,
5. symmetry and PSD/coherence checks.

Acceptance criteria:

1. Compiled and reference outputs agree within defined tolerance.
2. Forecast segment transition logic is explicitly exercised.
3. Failures are localized to a minimal fixture before any production run.

Evidence:

- script:
  `repro/audits/run_exdqlm_keep_kalman_fixture.R`
- deterministic test:
  `tests/testthat/test_exdqlm_keep_kalman_fixture.R`
- report:
  `reports/exdqlm_multivar_keep_kalman_fixture_20260521_ragged/`

Result:

- fixture uses `J=2`, retained `ppx=1`, and ragged horizons `k_ens=c(5,2)`;
- compiled-vs-reference max absolute differences are below `1e-8` for historical and forecast filtered and
  smoothed means/covariances;
- covariance symmetry checks are exact at reported precision and minimum eigenvalues are positive in the fixture.

### T7. Post-Stage Truth-Window Gate

Status: done

Purpose: prevent successful isolated fits from being reported as failed whole-workflow runs when post-stage figures
need truth rows that are unavailable after the cutoff.

Required behavior:

1. detect missing truth rows before CRPS/figure code errors,
2. write a clear skipped/partial diagnostic artifact,
3. preserve successful fit-stage status,
4. keep default behavior unchanged where truth is available.

Acceptance criteria:

1. Post-stage no-truth cases exit cleanly or with an explicitly classified partial status.
2. Existing successful post workflows are not regressed.

Implementation:

- `R/environmetrics/02_helpers_core.R` now provides `post_truth_from_start_or_na(...)`, which returns an all-`NA`
  truth vector and an explicit availability row instead of stopping when USGS truth is missing after the forecast
  start.
- `R/environmetrics/40_figures_smoke_fast.R` and `R/environmetrics/40_figures.R` export
  `crps_truth_availability` alongside CRPS tables.
- Fixed-gamsig v3 fit wrote all four `.RData` files, then post failed before this patch with
  `[crps.glofas.truth_TRUTH_MISSING] no USGS truth rows available at/after 2022-12-26`; this is the target runtime
  case for the patch.
- Latent-freeze v3 and latent-cap v3 both completed the full post/validate/report wrapper after this patch, while
  exporting truth availability instead of stopping on the missing future USGS truth window.

### T8. Promotion Decision

Status: isolated capped/guarded promotion candidate passed; broad production still requires explicit review/launch decision

Promotion requires:

1. curated evidence bundle complete,
2. ablations identify the most likely decisive repair or show that the stability gain is interactional,
3. q05 guard-response policy chosen and tested,
4. decomposition traces pass or identify an accepted limitation,
5. ragged forecast Kalman fixture passes or has a documented blocker,
6. post-stage truth-window handling is fixed or explicitly waived,
7. final findings and this tracker are updated with exact evidence paths.

Decision outcomes:

| outcome | meaning |
| --- | --- |
| promote repaired `log1p_cms` path | technically supportable only as the explicit promotion-v2 profile: latent `E[1/u]` cap `5000`, fail-fast pseudo-data guard, delayed state guard at iter `1000`, and terminal sampling guard |
| targeted additional ablations | still recommended for damped/refrozen `sigma/gamma`, because q05/q95 terminal gamma values remain asymmetric |
| hold production | default operational decision unless the user explicitly chooses to relaunch production with the named promotion-v2 profile |

### T9. Full-History Promotion Packaging

Status: implemented for no-launch validation; launch not executed

Purpose: move the audited promotion-v2 controls out of ad hoc wrapper environment exports and into the main HE2
publication relaunch config path, then freeze a reviewable 2022-12-25 full-history/full-spec package.

Target package:

- readiness doc:
  `docs/exdqlm_multivar_keep_fullhistory_promotion_readiness.md`
- template:
  `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20221225_fullhistory_promotion_20260522.template.yaml`
- batch:
  `config/he2_relaunch_batches/exdqlm_multivar_keep_20221225_fullhistory_promotion_20260522.yaml`

Frozen target contract:

- cutoff `2022-12-25`;
- data start `1987-05-29`;
- all seven quantiles: q05/q20/q35/q50/q65/q80/q95;
- canonical 20260510 shared input bundle;
- `log1p_cms` fit/post scale and `transform_policy: log1p_only`;
- full transfer covariates `PPT`, `SOIL`, `PCA` plus square, interaction, and lag terms;
- full harmonic indices `[1, 2, 3]`, which map to legacy harmonic values `c(1, 2, 1/6.8068493)`;
- requested prelaunch discounts: `df_t=0.99999`, `df_s1=df_s2=df_s67=df_discrep=0.9999`, `lambda=0.97`,
  `df_trans=df_covs=0.9999999`;
- requested Wishart prior `epsilon=365.0`, `c_factor=1.0`;
- `max_iter=200` for the requested prelaunch/dry-test package;
- promotion-v2 guards: latent `E[1/u]` cap `5000`, pseudo-data guard mode `fail`, state guard delayed to iter
  `1000`, and terminal sampling guard `fail_fast`.

Historical source-lock note:

- the older full-history `2022-12-25` source config before set09/debug-patching used
  `df_t=0.99999999`, `df_s1=df_s2=df_s67=0.9999`, `df_discrep=0.999`, `lambda=0.97`,
  `df_trans=0.9999999`, and `df_covs=0.99999`;
- the currently packaged no-launch representative still uses selected set09 values
  `df_s1=df_s2=0.9998`, `df_discrep=0.998`, and `df_covs=0.9999999` in commit `4bc0f52`;
- the 2026-05-18 discount-refresh retained legacy run used `df_t=0.99999`, `df_s1=df_s2=df_s67=df_discrep=0.9999`,
  `df_trans=0.9999999`, forecast `epsilon=365.0`, and `df_covs=0.99999`;
- the active package intentionally follows the user-requested `df_covs=0.9999999`, not the May 18 `df_covs=0.99999`;
- the old and current configs both represent the full seasonal basis through indices, not literal values.

Implementation:

- `R/unified/stages/stage_fit.R` maps YAML config to the guarded runner environment variables:
  `DISC_LATENT_ABLATION_MODE`, `DISC_LATENT_E_INV_U_CAP`, `DISC_PSEUDODATA_GUARD_*`, and
  `DISC_GAMSIG_STATE_GUARD_START_ITER`.
- `R/unified/config.R` adds defaults and validation for `fit.exdqlm_multivar.latent_ablation`,
  `fit.exdqlm_multivar.pseudodata_guard`, and delayed state-guard start.
- Python and testthat coverage now checks the source mapping, config validation, static batch contract, and builder
  output for the new no-launch package.

Launch boundary:

- no relaunch has been run from this package;
- next allowed step is no-launch builder/prelaunch validation in the new artifact root only;
- old live roots and the background verifier remain untouched.

### T10. Pre-Grid Component-Diagnostic Gate

Status: implemented and validated; no grid launch executed

Purpose: make the future epsilon/discount-factor grid produce the retained-state q50 diagnostics before `.RData`
cleanup while preserving the smoke-fast post route that produced the successful all-cutoff 2026-05-23 baseline.

Implementation:

- `R/environmetrics/02_helpers_core.R` adds `post_transform_usgs_log1p_truth_to_analysis_scale()` and
  `post_flow_scale_label()` so shared USGS `data0` truth stays on `log1p_cms` under `log1p_only` and converts to
  loglog only when that scale is explicitly requested.
- `R/environmetrics/40_figures_multivar_only.R` now uses the scale-aware truth helper, dynamic y-axis labels, and the
  configured component pre-window for q50 retained-state plots and summaries.
- `R/unified/config.R`, `R/unified/stages/stage_post.R`, `R/unified/post_module_plan.R`, and
  `scripts/run_environmetrics_figures.R` add the `post.multivar_component_diagnostics` gate. When enabled for an
  exDQLM multivar run, smoke-fast post remains active and `40_figures_multivar_only.R` is appended for q50 components.
- `R/unified/post_artifact_contract.R` now requires q50 component CSV/PNG outputs and verifies the retained-transfer
  `keep` contract from `multivar_transfer_contract_q50.csv`.
- The `fail_fast` switch is wired through for explicit debug runs, but production grid configs should keep the default
  `post.multivar_component_diagnostics.fail_fast=true` so `.RData` cleanup waits for component diagnostics to pass.

Operational contract:

- future grid configs should set `post.multivar_component_diagnostics.enabled=true`;
- component diagnostics must run while `.RData` is still present;
- `.RData` cleanup should occur only after post and the component artifact contract pass;
- the already-cleaned 2026-05-23 root remains a valid public-figure/CRPS freeze point, but cannot be retroactively
  upgraded into a component-diagnostics freeze point without rerunning fit output.

## Validation Log

| date | command/evidence | outcome |
| --- | --- | --- |
| 2026-05-24 | all-cutoff near-zero campaign root `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_fullhistory_nearzero_20260523` | pass; five cutoffs completed fit/post/validate/report with no retained `.RData` / `.rda` files remaining |
| 2026-05-24 | post artifact scan of the near-zero campaign | pass for smoke-fast contract: 5 `post_artifacts_summary.json`, 5 `crps_forecast_summary.csv`, 5 `crps_forecast_per_time.csv`, 5 `covariate_effects_summary.csv`; 0 retained-state `multivar_transfer_coefficients_window_q50.csv` because full component diagnostics were not run |
| 2026-05-24 | post-module wiring audit | current all-cutoff run used `POST_SMOKE_FAST=TRUE`; future epsilon/discount grids need a repaired log1p-safe component-diagnostic gate before `.RData` cleanup |
| 2026-05-24 | `docs/exdqlm_multivar_keep_freeze_and_epsilon_discount_grid_plan_20260524.md` | added freeze assessment, diagnostic gap, CRPS selection contract, cleanup contract, and implementation plan for epsilon/discount-factor exploration |
| 2026-05-24 | parse check for component-gate files: `R/environmetrics/02_helpers_core.R`, `R/environmetrics/40_figures_multivar_only.R`, `R/unified/config.R`, `R/unified/stages/stage_post.R`, `R/unified/post_artifact_contract.R`, `R/unified/post_module_plan.R`, `scripts/run_environmetrics_figures.R` | pass |
| 2026-05-24 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_module_plan.R')"` | pass, 22 expectations; verifies smoke-fast multivar lanes append q50 components only when the gate is enabled |
| 2026-05-24 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_artifact_contract.R')"` | pass, 46 expectations; verifies q50 component output requirements, fail-closed retained-transfer `keep` contract, and non-fatal debug behavior |
| 2026-05-24 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_config_mode_resolution.R')"` | pass, 64 expectations; verifies component-diagnostic defaults and validation |
| 2026-05-24 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_scale_contract_adapters.R')"` | pass, 18 expectations; verifies shared USGS truth remains log1p under `log1p_only` |
| 2026-05-24 | `python3 scripts/build_he2_exdqlm_multivar_keep_grid_configs.py --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_epsilon_discount_grid_20260524.template.yaml --reset-status` | pass; generated 30 specs, 150 spec-cutoff rows, and 1050 quantile fits under the isolated 2026-05-24 epsilon/discount grid runtime root |
| 2026-05-24 | `python3 scripts/validate_he2_exdqlm_multivar_keep_grid_prelaunch.py --matrix-dir ... --artifact-root ...` | pass, 8720 checks and 0 failures; verifies spec manifest, generated configs, canonical bundles, harmonics, transfer covariates, log1p scale, q50 component gate, cleanup wrapper, and original 56-worker queue contract |
| 2026-05-25 | live no-cleanup smoke row `c05_eps030`, cutoff `20211112` | pass through fit/post/validate/report; post artifact contract true, CRPS/input-health tables present, q50 retained-transfer contract errors at machine precision, retained `.RData` total about 51.5 GB |
| 2026-05-25 | memory-aware queue hardening | pass; `scripts/run_multimodel_v8_queue.py` now supports `--pause-mem-gb`, `--launch-mem-gb`, and `--heavy-mem-gb`; focused Python tests pass |
| 2026-05-25 | regenerated full epsilon/discount grid matrix from commit `c4b3f79` | pass; 30 specs, 150 rows, 1050 quantile fits; queue refreshed to 4 concurrent rows / 28 quantile workers with MemAvailable gates 120/170/190 GB |
| 2026-05-25 | `python3 scripts/validate_he2_exdqlm_multivar_keep_grid_prelaunch.py --matrix-dir ... --artifact-root ...` after memory refresh | pass, 8723 checks and 0 failures; adds memory-gated queue contract checks |
| 2026-05-24 | `python3 -m unittest tests.python.test_he2_exdqlm_keep_grid_tooling -v` | pass, 4 tests after memory-aware refresh; verifies frozen grid manifest, generated spec patches, and queue defaults |
| 2026-05-24 | `python3 -m unittest tests.python.test_he2_exdqlm_keep_allcutoff_monitor -v` | pass, 3 tests; verifies spec-aware monitor table and state-norm scaling |
| 2026-05-24 | `python3 -m unittest tests.python.test_multimodel_v8_tooling -v` | pass, 12 tests; verifies queue continue-on-fail terminal semantics and existing v8 tooling contracts |
| 2026-05-24 | `python3 scripts/build_he2_exdqlm_multivar_keep_grid_smoke_matrix.py --reset-status` and cleanup-root variant | pass; prepared no-cleanup and cleanup smoke matrices with 3 run rows / 21 quantile fits each |
| 2026-05-24 | `python3 -m unittest tests.python.test_he2_exdqlm_keep_grid_next_steps -v` | pass, 3 tests after memory-aware refresh; verifies smoke config rewriting, smoke memory defaults, and evaluator winner eligibility logic |
| 2026-05-24 | `python3 -m unittest tests.python.test_multimodel_v8_queue_contract -v` | pass, 7 tests after memory-aware refresh; verifies cleanup/no-cleanup wrappers and disk/RAM launch gates |
| 2026-05-25 | no-cleanup smoke root `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_smoke_nocleanup_20260524` | pass; three spec rows (`c01_eps365`, `c05_eps030`, `c06_eps030`) at cutoff `20211112` completed fit/post/validate/report; evaluator report `reports/exdqlm_multivar_keep_grid_eval_smoke_nocleanup_20260524/README.md` found 3 eligible rows and 0 failed/ineligible |
| 2026-05-25 | no-cleanup smoke evaluator CRPS | pass; winner `c01_eps365` mean CRPS `0.06742386511601428`, runner-up `c06_eps030` mean CRPS `0.06965513961065666`, third `c05_eps030` mean CRPS `0.07657749964241033`; repaired quantile-synthesis anchor/empirical crossing gate clean |
| 2026-05-25 | no-cleanup retained `.RData` cleanup after evidence capture | pass; 21 retained files totaling about 154.38 GiB removed after evaluator/post evidence was captured; no retained `.RData` / `.rda` files remained under the smoke root |
| 2026-05-25 | cleanup smoke root `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_smoke_cleanup_20260524` | pass; same three spec rows completed fit/post/validate/report; evaluator report `reports/exdqlm_multivar_keep_grid_eval_smoke_cleanup_20260524/README.md` found 3 eligible rows and 0 failed/ineligible |
| 2026-05-25 | cleanup smoke `.RData` contract | pass; final retained `.RData` / `.rda` count was `0`, confirming cleanup occurred after post artifact/report success |
| 2026-05-25 | full epsilon/discount grid launch | running; detached controller PID `3758588`, queue log `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524/control/publication_relaunch_matrix/queue.log`, four-row memory-gated policy active |
| 2026-05-27 | full grid queue recovery | patched after controller crash on transient manifest parse; 116 rows passed, 2 rows are legitimate q20 pseudo-data guard failures, 32 rows need relaunch; see `docs/exdqlm_multivar_keep_grid_recovery_20260527.md` |
| 2026-05-25 | full-grid live monitor snapshot | running; `reports/he2_exdqlm_multivar_keep_epsilon_discount_grid_live_20260524/LIVE_STATUS.md` shows first wave pending for `c01_eps365` on four cutoffs with normalized state norm reported per history day |
| 2026-05-21 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R')"` | pass, 45 expectations |
| 2026-05-21 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_transform_scale_sensitivity.R')"` | pass, 10 expectations |
| 2026-05-21 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_scale_contract_adapters.R')"` | pass, 13 expectations |
| 2026-05-21 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_runtime_stability_audit.R')"` | pass, 8 expectations |
| 2026-05-21 | `python3 -m unittest tests.python.test_log1p_transform_policy -v` | pass, 6 tests |
| 2026-05-21 | guarded q05/q35/q50/q95 reproduction | fit outputs written; post-stage no-truth failure after fit |
| 2026-05-21 | guarded runtime stability audit | pass; report written under `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/runtime_stability/` |
| 2026-05-21 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_curated_evidence_bundle.R')"` | pass, 6 expectations |
| 2026-05-21 | `python3 -m unittest tests.python.test_exdqlm_keep_ablation_tooling -v` | pass, 3 tests |
| 2026-05-21 | `python3 repro/audits/prepare_exdqlm_keep_ablation_matrix.py --tag ablation_log1p_q05_q35_q50_q95_20260521 --conditions fixed-gamsig,latent-freeze,latent-cap-e-inv-u --quantiles 0.05,0.35,0.5,0.95 --max-iter 3000 --workers 4 --guard-mode warn --post-save-objective off` | matrix prepared |
| 2026-05-21 | fixed-gamsig matrix launch v1 | stopped during early fixed-gamsig initialization; generated YAML still had `warmup_freeze_iters=10`, so the run was not a valid fixed-gamsig ablation |
| 2026-05-21 | `python3 -m unittest tests.python.test_exdqlm_keep_ablation_tooling -v` after YAML-policy fix | pass, 3 tests; fixed-gamsig test now checks generated YAML and quantile overrides |
| 2026-05-21 | `python3 repro/audits/prepare_exdqlm_keep_ablation_matrix.py --tag ablation_log1p_q05_q35_q50_q95_v2_20260521 --conditions fixed-gamsig,latent-freeze,latent-cap-e-inv-u --quantiles 0.05,0.35,0.5,0.95 --max-iter 3000 --workers 4 --guard-mode warn --post-save-objective off` | v2 matrix prepared; fixed-gamsig generated YAML verified with `warmup_freeze_iters=3005` and `min_update_iters=0` |
| 2026-05-21 | fixed-gamsig matrix launch v2 | failed before fit; validator rejected enabled `state_refresh_schedule` with `warmup_freeze_iters=3005` |
| 2026-05-21 | `python3 repro/audits/prepare_exdqlm_keep_ablation_matrix.py --tag ablation_log1p_q05_q35_q50_q95_v3_20260521 --conditions fixed-gamsig,latent-freeze,latent-cap-e-inv-u --quantiles 0.05,0.35,0.5,0.95 --max-iter 3000 --workers 4 --guard-mode warn --post-save-objective off` | v3 matrix prepared; fixed-gamsig generated YAML verified with refresh schedule disabled |
| 2026-05-21 | fixed-gamsig v3 runtime | fit wrote q05/q35/q50/q95 `.RData`; no pseudo-data guard rows; post failed on known no-truth CRPS path before T7 patch |
| 2026-05-21 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_crps_tables.R')"` after T7 patch | pass, 64 expectations |
| 2026-05-21 | `Rscript --vanilla repro/audits/run_exdqlm_keep_kalman_fixture.R reports/exdqlm_multivar_keep_kalman_fixture_20260521_ragged` | pass; ragged keep fixture with `J=2`, `ppx=1`, and compiled-vs-reference smoother checks |
| 2026-05-22 | q80 diagnostic stop | stopped by explicit user instruction; no matching `run_DISC_Optimal`/`DISC_Optimal` q80 process remained in the subsequent process scan |
| 2026-05-22 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_structure_contract.R')"` | pass, 6 expectations; verifies harmonic indices `[1, 2, 3]` map to values `c(1, 2, 1/6.8068493)` |
| 2026-05-22 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_config_mode_resolution.R')"` | pass, 49 expectations |
| 2026-05-22 | `python3 -m unittest tests.python.test_he2_publication_relaunch_template -v` | pass, 19 tests after retargeting the no-launch package to `max_iter=200` |
| 2026-05-22 | `python3 -m unittest tests.python.test_he2_publication_relaunch_builder_selection.HE2PublicationRelaunchBuilderSelectionTests.test_exdqlm_fullhistory_promotion_batch_builds_guarded_20221225_config -v` | pass, 1 test; temporary generated config carries full-history inputs, guarded controls, and `max_iter=200` |
| 2026-05-22 | `Rscript --vanilla -e "invisible(parse('R/unified/config.R')); invisible(parse('R/unified/stages/stage_fit.R'))"` | pass |
| 2026-05-22 | `git diff --check` | pass |
| 2026-05-22 | prelaunch source-lock retarget to requested `df99999`/`eps365` profile | package now uses `df_t=0.99999`, `df_s1=df_s2=df_s67=df_discrep=0.9999`, `df_trans=df_covs=0.9999999`, `epsilon=365.0`, `max_iter=200`; May 18 legacy run used the same profile except `df_covs=0.99999` |
| 2026-05-22 | reconstructed prior Codex conversation and multi-cutoff promotion plan | pass; plan added at `docs/exdqlm_multivar_keep_multicutoff_promotion_plan_20260522.md`, identifying `max_iter=100`, 35 single-threaded quantile fits, no-cleanup `.RData` retention, full USGS truth-source post behavior, and cleanup dry-run gates |
| 2026-05-22 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_config_mode_resolution.R')"` after `df99999`/`eps365` retarget | pass, 49 expectations |
| 2026-05-22 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_structure_contract.R')"` after `df99999`/`eps365` retarget | pass, 6 expectations |
| 2026-05-22 | `python3 -m unittest tests.python.test_he2_publication_relaunch_template -v` after `df99999`/`eps365` retarget | pass, 19 tests |
| 2026-05-22 | `python3 -m unittest tests.python.test_he2_publication_relaunch_builder_selection.HE2PublicationRelaunchBuilderSelectionTests.test_exdqlm_fullhistory_promotion_batch_builds_guarded_20221225_config -v` after `df99999`/`eps365` retarget | pass, 1 test; generated config and manifest `config_patch_json` carry requested active values |
| 2026-05-22 | `python3 -m unittest tests.python.test_disc_sampling_diagnostics_source_contract -v` after `df99999`/`eps365` retarget | pass, 6 tests |
| 2026-05-21 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_keep_kalman_fixture.R')"` | pass, 7 expectations |
| 2026-05-21 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_keep_decomposition_audit.R')"` | pass, 6 expectations |
| 2026-05-21 | fixed-gamsig v3 runtime stability and curated evidence bundle | pass; report paths recorded in T2 |
| 2026-05-21 | fixed-gamsig v3 decomposition audit | pass; history/forecast reconstructions match `new.theta.out$exps` to numerical tolerance |
| 2026-05-21 | `docs/exdqlm_multivar_keep_guard_response_policy.md` | drafted T4 guard-response policy; production promotion should fail-fast on pseudo-data guard breaches until latent-cap evidence is clean |
| 2026-05-21 | latent-freeze v3 runtime, runtime stability, curated evidence, and decomposition audit | pass mechanically, but diagnostic result is bad for q05/q95; fixed latents did not prevent large tail-lane states |
| 2026-05-21 | latent-cap v3 runtime, runtime stability, curated evidence, and decomposition audit | pass; all lanes wrote outputs, no pseudo-data guard rows, and q05/q95 state norms stayed finite |
| 2026-05-21 | `python3 -m unittest tests.python.test_exdqlm_keep_ablation_tooling -v` after promotion-profile tooling | pass, 4 tests |
| 2026-05-21 | focused closeout tests: runtime stability audit, decomposition audit, Kalman fixture, latent/pseudo-data audit, post-CRPS tables | pass: 9, 6, 7, 52, and 64 expectations respectively |
| 2026-05-21 | `git diff --check` | pass |
| 2026-05-21 | promotion v1 capped/guarded candidate | failed q05/q95 with early state-guard/refreeze trap; no pseudo-data guard rows |
| 2026-05-21 | added `DISC_GAMSIG_STATE_GUARD_START_ITER` and promotion tooling export/manifest support | validated by Python tooling test and latent/pseudo-data audit test |
| 2026-05-21 | promotion v2 capped/guarded candidate with state guard delayed to iter `1000` | pass; q05/q35/q50/q95 outputs written; fit/post/validate/report complete; zero pseudo-data guard rows |
| 2026-05-21 | v2 runtime stability, curated evidence, and decomposition audits | pass; report paths recorded in T4/T8 |
| 2026-05-21 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_curated_evidence_bundle.R')"` after no-guard README fix | pass, 9 expectations |
| 2026-05-22 | `Rscript --vanilla -e "invisible(parse('R/unified/config.R')); invisible(parse('R/unified/stages/stage_fit.R'))"` | pass |
| 2026-05-22 | `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_config_mode_resolution.R')"` | pass, 49 expectations |
| 2026-05-22 | `python3 -m unittest tests.python.test_disc_sampling_diagnostics_source_contract -v` | pass, 6 tests |
| 2026-05-22 | `python3 -m unittest tests.python.test_he2_publication_relaunch_template -v` | pass, 19 tests |
| 2026-05-22 | `python3 -m unittest tests.python.test_he2_publication_relaunch_builder_selection.HE2PublicationRelaunchBuilderSelectionTests.test_exdqlm_fullhistory_promotion_batch_builds_guarded_20221225_config -v` | pass |

## Change Log

| date | change | status |
| --- | --- | --- |
| 2026-05-21 | Created living repair tracker with curated evidence, ablation, guard-policy, decomposition, Kalman, post-stage, and promotion gates | done |
| 2026-05-21 | Completed `T0` curated evidence bundle and `T1` ablation harness design; prepared `T2/T3` ablation matrix | done |
| 2026-05-21 | Found and fixed fixed-gamsig ablation wiring so freeze policy is written into generated YAML, not only wrapper env | done |
| 2026-05-21 | Implemented post-stage missing-truth gate for CRPS exports | done |
| 2026-05-21 | Extended the keep Kalman fixture to retained-transfer ragged forecast smoothing and added a deterministic test | done |
| 2026-05-21 | Added a reusable decomposition audit for trend, transfer, discrepancy, and reconstruction checks | done |
| 2026-05-21 | Drafted guard-response policy for q05-like latent-tail events | done |
| 2026-05-21 | Completed latent-freeze and latent-cap v3 ablations, regenerated normalized runtime/curated evidence bundles, and added isolated promotion guard-profile tooling | done |
| 2026-05-21 | Added delayed promotion state-guard start, completed promotion v2, and recorded v1/v2 evidence | done |
| 2026-05-24 | Added log1p-safe q50 component diagnostics, smoke-fast append wiring, and fail-closed post artifact contract for retained-transfer `keep` semantics | done |
| 2026-05-24 | Prepared and validated the 30-spec all-cutoff epsilon/discount grid with continue-on-fail semantics | done |
| 2026-05-24 | Prepared no-cleanup and cleanup smoke matrices, grid evaluator scaffold, and next-step launch/evaluation runbook | done |
| 2026-05-25 | Hardened the queue around RAM gates after smoke evidence and relaunched the full grid at 4 concurrent rows / 28 quantile workers | running |
| 2026-05-25 | Completed no-cleanup and cleanup smoke gates, captured CRPS/evaluator evidence, and verified post-success `.RData` cleanup | done |

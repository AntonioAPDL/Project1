# exDQLM Multivariate Keep Final Findings

Date: 2026-05-21

## Executive Finding

The `log1p_cms` multivariate `exdqlm keep` instability is not explained by a single isolated formula bug. The best
current explanation is an interaction among latent-tail precision, free `sigma/gamma` updates, pseudo-data
construction, and weakly identified retained trend/transfer/discrepancy blocks.

The audit did find and patch concrete implementation risks, and the repaired guarded q05/q35/q50/q95 workflow now
writes all four `.RData` outputs in isolated reproductions. The decisive causal evidence is:

1. Fixed `sigma/gamma` keeps the v3 lanes finite with no pseudo-data guard rows.
2. Fixed latent moments do not keep q05/q95 scientifically stable when `sigma/gamma` remains free.
3. Capping `E[1/u_t]` keeps q05/q35/q50/q95 finite in an isolated diagnostic and avoids pseudo-data guard rows.
4. Therefore the failure is not "the `s_t/u_t` formulas alone". It is the feedback loop between latent precision,
   `sigma/gamma`, pseudo-data, and the retained state decomposition.

The first fail-fast promotion attempt showed that a state guard active from the first refresh can trap q05/q95 in
repeated refreeze. After adding an explicit delayed state-guard start, the second isolated promotion candidate
completed fit, post, validate, and report for q05/q35/q50/q95 with no pseudo-data guard rows. This is the strongest
runtime evidence so far for an explicitly capped/guarded `log1p_cms` candidate, but it still should be reviewed as a
named production profile rather than silently becoming the default algorithm.

## Source Lock

Canonical theory source:

- exAL stochastic representation and source-wise conditionals:
  `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:281-352`.
- Model C-T retained-transfer forecast contract:
  `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:161-237`.
- VB pseudo-data construction:
  `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex:944-959`.
- VB-Laplace/Delta motivation:
  `/data/muscat_data/jaguir26/project1_ucsc_phd/article.txt:208-212`.

Active implementation path:

- runner and latent updates:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1851-2011`;
- pseudo-data guards and construction:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3186-3254`,
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3649-3705`,
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3856-3911`;
- fit-stage latent update loops:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4230-4338`;
- sampling-stage forecast latent update loops:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:5005-5056`;
- state guard and terminal sampling guard:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:4530-4793`;
- isolated promotion tooling:
  `repro/audits/prepare_exdqlm_keep_guarded_repro.py:86-91`,
  `repro/audits/prepare_exdqlm_keep_guarded_repro.py:133-177`.
- main HE2 relaunch promotion path:
  `R/unified/stages/stage_fit.R`,
  `R/unified/config.R`,
  `config/he2_relaunch_batches/exdqlm_multivar_keep_20221225_fullhistory_promotion_20260522.yaml`.

## Confirmed Correct

- The retained-transfer `keep` state-space contract matches Model C-T: transfer is preserved in forecast rather
  than dropped.
- The active ensemble/member bookkeeping is coherent for source order, member axes, and ragged forecast horizons.
- `s_t` uses positive-truncated-normal moments and entropy, tested against numerical integration.
- `u_t` uses the half-order GIG moment identities, tested against Bessel identities and numerical integration.
- The pseudo-data algebra matches the information-form VB derivation.
- The compiled Kalman/RTS layer passes deterministic retained-transfer ragged forecast fixture checks with `J=2`,
  `ppx=1`, and unequal forecast horizons.
- Decomposition audits reconstruct populated `new.theta.out$exps` rows to numerical tolerance across the v3
  evidence runs.

## Found Wrong And Patched

1. Forecast-member `update_uts` used unsafe forecast column indexing at audit time.

   It now uses `TT_sub` consistently in the fit-stage and sampling-stage forecast loops. Regression coverage:
   `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`.

2. `s_t` entropy was not the canonical positive-truncated-normal entropy.

   The active runner now uses stable positive-truncated-normal moments/entropy. Regression coverage:
   `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`.

3. Missing future USGS truth could make a successful fit look like a failed workflow.

   `post_truth_from_start_or_na(...)` now gates CRPS/figure truth availability at
   `R/environmetrics/02_helpers_core.R:1639`; callers are wired at
   `R/environmetrics/40_figures_smoke_fast.R:2017` and `R/environmetrics/40_figures.R:5370`.

4. Diagnostic/prod guard separation was too implicit.

   The isolated launcher now has `--guard-profile promotion`, which exports fail-fast pseudo-data checks plus
   state/refreeze/terminal guards. Regression coverage:
   `tests/python/test_exdqlm_keep_ablation_tooling.py:135-184`.

5. Runtime audit lane labels could report `q5` instead of `q05`.

   `repro/audits/exdqlm_keep_runtime_stability_audit.R` now normalizes quantile lanes with two digits, with test
   coverage in `tests/testthat/test_exdqlm_runtime_stability_audit.R`.

6. Promotion state guarding was too aggressive when enabled from iteration 0.

   `DISC_GAMSIG_STATE_GUARD_START_ITER` now allows promotion candidates to delay the state-norm guard until after
   warmup/recovery. The promotion tooling records and exports the value, with regression coverage in
   `tests/python/test_exdqlm_keep_ablation_tooling.py` and
   `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`.

7. The successful promotion-v2 guard profile was not first-class in the main HE2 relaunch config path.

   `R/unified/stages/stage_fit.R` now maps `fit.exdqlm_multivar.latent_ablation`,
   `fit.exdqlm_multivar.pseudodata_guard`, and delayed state-guard config into the runner environment variables.
   `R/unified/config.R` validates those controls. The full-history no-launch package is documented in
   `docs/exdqlm_multivar_keep_fullhistory_promotion_readiness.md`.

## Runtime Evidence

Baseline guarded repaired control:

- evidence root:
  `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/`;
- all q05/q35/q50/q95 outputs wrote;
- q05 had 18 warning-mode `E[1/u_t]` guard rows at iterations `1001-1018`, peak `14397.595`;
- no `FFF`, `QQQ_diag`, forecast pseudo-data, `E[s]`, `E[s^2]`, or `E[u]` guard rows were written.

Fixed-gamsig v3:

- evidence roots:
  `reports/exdqlm_keep_guarded_repro_ablation_log1p_q05_q35_q50_q95_v3_20260521_fixed_gamsig/`,
  `reports/exdqlm_keep_runtime_stability_ablation_log1p_q05_q35_q50_q95_v3_20260521_fixed_gamsig/`,
  `reports/exdqlm_keep_decomposition_ablation_log1p_q05_q35_q50_q95_v3_20260521_fixed_gamsig/`;
- all lanes wrote outputs with `gamsig_update_iters=0`;
- no pseudo-data guard rows;
- terminal history state norms: q05 `962.241`, q35 `1956.977`, q50 `2320.214`, q95 `8875.863`.

Latent-freeze v3:

- evidence roots:
  `reports/exdqlm_keep_guarded_repro_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_freeze/`,
  `reports/exdqlm_keep_runtime_stability_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_freeze/`,
  `reports/exdqlm_keep_decomposition_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_freeze/`;
- all lanes wrote outputs and post/validate/report completed;
- no pseudo-data guard rows;
- terminal history state norms: q05 `8011171`, q35 `13652.71`, q50 `4803.106`, q95 `8190166`;
- q05/q95 `sigma/gamma` became large and asymmetric: q05 `sigma_exp=3.065681`, `gamma_exp=6.756436`; q95
  `sigma_exp=3.075551`, `gamma_exp=-6.76794`;
- decomposition shows q05/q95 source-1 historical median absolute `mu_without_transfer` around `55` and
  discrepancy around `23`.

Latent-cap v3:

- evidence roots:
  `reports/exdqlm_keep_guarded_repro_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_cap_e_inv_u/`,
  `reports/exdqlm_keep_runtime_stability_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_cap_e_inv_u/`,
  `reports/exdqlm_keep_decomposition_ablation_log1p_q05_q35_q50_q95_v3_20260521_latent_cap_e_inv_u/`;
- all lanes wrote outputs and the full wrapper completed;
- no pseudo-data guard rows;
- terminal history state norms: q05 `1521.127`, q35 `2233.589`, q50 `2547.352`, q95 `5082.421`;
- saved-output target historical `E[1/u]` maxima: q05 `764.468`, q35 `923.203`, q50 `172.962`, q95 `110.045`;
- q05/q95 decomposition returned to the small-component scale: source-1 historical median absolute
  `mu_without_transfer` q05 `0.192401`, q95 `0.651413`; discrepancy q05 `0.398565`, q95 `0.595735`.

Promotion v1:

- evidence root:
  `reports/exdqlm_keep_guarded_repro_promotion_log1p_q05_q35_q50_q95_v1_20260521_latent_cap_e_inv_u/`;
- fail-fast pseudo-data guard rows: `0`;
- q05 and q95 failed at iter `3000` with state norm squared around `1.50e6` and `1.56e6`;
- both lanes had repeated `[gamsig_state_guard]` events and stopped before the required gamma/sigma update count;
- interpretation: the guard profile was catching an unsafe state, but with `state_norm_abs_cap=1e6` active from
  the first refresh it also prevented the latent-cap path from reaching the stable state scale already observed in
  the v3 diagnostic.

Promotion v2:

- evidence roots:
  `reports/exdqlm_keep_guarded_repro_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`,
  `reports/exdqlm_keep_runtime_stability_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`,
  `reports/exdqlm_keep_curated_evidence_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`,
  `reports/exdqlm_keep_decomposition_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`,
  `reports/exdqlm_keep_visual_review_promotion_log1p_q05_q35_q50_q95_v2_20260521_latent_cap_e_inv_u/`;
- full unified wrapper completed fit, post, validate, and report;
- all four lanes wrote `.RData` with zero pseudo-data guard rows;
- terminal state norm squared: q05 `1521.127`, q35 `2233.589`, q50 `2547.352`, q95 `5082.421`;
- terminal `sigma_exp/gamma_exp`: q05 `0.04159492/0.8357256`, q35 `0.1136433/0.1103588`,
  q50 `0.1227996/-0.01111135`, q95 `0.07100852/-1.762717`;
- saved-output historical pseudo-data stayed far below promotion caps: q05 `FFF` max `3.979276`,
  q95 `FFF` min `-2.161739`, q05 `QQQ_diag` max `0.325061`, q95 `QQQ_diag` max `0.463255`;
- decomposition reconstructs populated fitted means to numerical tolerance and stays on the small-component scale:
  q05/q95 source-1 historical median absolute `mu_without_transfer` `0.192401`/`0.651413` and discrepancy
  `0.398565`/`0.595735`;
- post-stage truth availability correctly reports missing future USGS truth at/after `2022-12-26` and pads CRPS
  truth with `NA` instead of failing.
- visual review of `seq.elbo`, `new.theta.out$sm`, and `new.theta.out$exps` shows no late ELBO divergence, bounded
  saved state paths, coherent q05/q50/q95 USGS ordering, and a remaining calibration concern that q50 is smooth and
  misses some sharp observed peaks/recessions. See
  [patch takeaways and visual review](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_patch_takeaways_visual_review.md).

## Interpretation

The strongest negative result is latent-freeze: fixed latent moments did not stabilize q05/q95. That rules out a
latent-formula-only explanation and points at `sigma/gamma`/state feedback.

The strongest positive result is that both fixed-gamsig and latent-cap keep the pseudo-data and state norms finite.
Those two interventions act on different sides of the same feedback loop:

- fixed-gamsig prevents the skew/scale approximation from chasing tail-lane structure;
- latent-cap prevents extreme precision from entering pseudo-data construction;
- both reduce the forcing that the Kalman state update must absorb.

The Kalman layer appears to consume the pseudo-data according to contract. The remaining risk is not a known
compiled Kalman bug; it is that the current free VB updates can generate pseudo-data/state regimes where the
retained transfer/discrepancy/trend blocks are weakly identified and can absorb implausible signal.

The `loglog1p` to `log1p` transform change remains relevant as a scale amplifier. The evidence does not show that
`log1p` is impossible, but it does show the `log1p` path needs explicit guardrails and promotion gates because the
tail lanes are more exposed to near-zero/low-flow precision effects.

## Prioritized Fix List

P0. Do not broad-launch a new production campaign automatically from this audit. The explicit capped/guarded
promotion-v2 candidate passed, but production should use that named profile only after review of the promotion
evidence bundle.

P0. If promoting `log1p_cms`, use the explicit profile tested in promotion v2: pseudo-data guard mode `fail`,
latent `E[1/u]` cap `5000`, state guard enabled with delayed start at iter `1000`, terminal sampling guard, and
post-save objective disabled unless that expensive diagnostic is specifically needed.

P0. Keep latent `E[1/u]` capping diagnostic/explicit. It may be tested as a named capped candidate, but it should
not silently become the default because it changes pseudo-observation precision.

P0. Use the tracked full-history promotion package for the next no-launch prelaunch step:
`config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20221225_fullhistory_promotion_20260522.template.yaml`
plus `config/he2_relaunch_batches/exdqlm_multivar_keep_20221225_fullhistory_promotion_20260522.yaml`. Do not reuse
older reduced-spec roots for the representative full-history attempt. The package is currently set to the requested
prelaunch `max_iter=200`, and its `enabled_harmonic_indices: [1, 2, 3]` means the full legacy seasonal basis
`c(1, 2, 1/6.8068493)`, not literal harmonic values `[1, 2, 3]`.

P1. Add a damped/refrozen `sigma/gamma` candidate before broadening beyond q05/q35/q50/q95. Promotion v2 passed,
but q05/q95 still have asymmetric terminal gamma values, and latent-freeze shows free `sigma/gamma` can still drive
large tail-lane states.

P1. Keep decomposition monitoring in every candidate. q95 can be finite while still showing larger retained
transfer/discrepancy magnitudes.

P1. Keep the post-stage truth-window gate and CRPS truth availability exports in the production workflow.

P2. Revisit transform policy only after the guarded `log1p_cms` promotion candidate. The current evidence supports
making `log1p` work with guardrails before considering `log1plog1p` or reverting to `loglog1p`.

## Verification Completed

- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R')"`
  passed with 52 expectations.
- `Rscript --vanilla repro/audits/run_exdqlm_keep_kalman_fixture.R reports/exdqlm_multivar_keep_kalman_fixture_20260521_ragged`
  passed.
- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_keep_kalman_fixture.R')"` passed with
  7 expectations.
- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_keep_decomposition_audit.R')"` passed
  with 6 expectations.
- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_runtime_stability_audit.R')"` passed
  with 9 expectations after lane-label normalization.
- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_keep_visual_review.R')"` passed with
  7 expectations.
- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_curated_evidence_bundle.R')"` passed
  with 9 expectations after the no-guard README interpretation fix.
- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_crps_tables.R')"` passed with
  64 expectations.
- `python3 -m unittest tests.python.test_exdqlm_keep_ablation_tooling -v` passed with 4 tests after promotion
  profile tooling.
- Promotion v2 completed the full unified wrapper and generated live-monitor, runtime-stability, curated-evidence,
  and decomposition reports under `reports/`; generated reports remain untracked by default.
- Full-history promotion packaging checks passed on 2026-05-22: config/stage parse, config guard validation,
  source-contract mapping, template static contract, and builder-generated temporary config checks for the guarded
  2022-12-25 package.
- After retargeting the package to the requested prelaunch `max_iter=200`, the harmonic-structure contract test
  passed with 6 expectations, the template test passed with 19 tests, the builder-generated temporary config test
  passed, and `git diff --check` passed.

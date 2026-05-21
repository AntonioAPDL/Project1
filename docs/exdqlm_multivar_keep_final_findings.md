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

This is enough to prepare one fail-fast, guarded promotion candidate. It is not enough to launch broad production
without that gate.

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

P0. Do not broad-launch production yet.

P0. Prepare one isolated promotion candidate using `--guard-profile promotion`, pseudo-data guard mode `fail`,
state/refreeze guards, terminal sampling guard, and the current `log1p_cms` transform. Generate the same runtime,
curated, and decomposition evidence bundle.

P0. Keep latent `E[1/u]` capping diagnostic/explicit. It may be tested as a named capped candidate, but it should
not silently become the default because it changes pseudo-observation precision.

P1. Add a damped/refrozen `sigma/gamma` candidate if the promotion run trips state or pseudo-data guards. The
latent-freeze result makes this the most important remaining algorithmic control.

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
- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_crps_tables.R')"` passed with
  64 expectations.
- `python3 -m unittest tests.python.test_exdqlm_keep_ablation_tooling -v` passed with 4 tests after promotion
  profile tooling.
- Fixed-gamsig, latent-freeze, and latent-cap v3 runtime, runtime-stability, curated-evidence, and decomposition
  reports were generated under `reports/` and left untracked by default.

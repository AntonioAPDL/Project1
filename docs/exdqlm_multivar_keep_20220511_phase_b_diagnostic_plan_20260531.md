# 20220511 exDQLM Multivar Keep Phase B Diagnostic Plan

Status: ready to prepare, validate, and launch after explicit launch instruction.

Date: 2026-05-31

## Purpose

The 2022-05-11 cutoff is not resolved by the epsilon/discount grid winner alone. Phase A proved that the
`c02_eps060` CRPS winner can produce strong forecast CRPS while still showing severe raw quantile-posterior
crossing and visually poor synthesis. Phase B is the targeted follow-up that separates four competing
explanations:

1. short VB budget/convergence,
2. tail-lane gamma/sigma and latent `s_t`/`u_t` instability,
3. trend/state component excursions and identifiability,
4. cross-quantile coherence failure that is hidden by isotonic/rearranged postprocessing.

This plan intentionally does not relaunch the full grid. It runs only high-value retained and latent-diagnostic
cells for the problematic cutoff.

## Grounded Starting Point

Primary Phase A evidence is in:

- `reports/he2_exdqlm_multivar_keep_20220511_synthesis_diagnostic_plan_20260530/PHASE_A_READOUT.md`
- runtime root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20220511_synthesis_diag_nocleanup_20260530`

Phase A facts that drive Phase B:

| Evidence | Phase A result | Implication |
|---|---:|---|
| retained `.RData` | 7 files, 52.158 GB | the no-cleanup path works |
| all q lanes reached | iter 100 | this was a short run, not convergence-grade |
| forecast mean CRPS | 0.032325 | CRPS alone is not sufficient |
| forecast raw sample crossing | 1.000000 | raw posterior sample paths are incoherent |
| forecast raw curve crossing | 0.607143 | raw quantile curves cross on 17/28 forecast leads |
| post anchor/empirical crossing | 0 | postprocessing repairs order but masks raw incoherence |
| q95 gamma | strongly negative by source | tail/source behavior is central |
| latent update CSVs | absent | full-seven Phase A did not enable default-off latent diagnostics |
| `state_guard_start_iter` | 1000 | state guard was inactive during the 100-iteration run |

The 2022-05-11 grid contrast that matters most is:

| Cell | Mean CRPS | Raw forecast curve crossing | Worst raw gap | Why include |
|---|---:|---:|---:|---|
| `c02_eps060` | 0.032325 | 0.607143 | -0.091661 | CRPS winner, visually bad |
| `c06_eps090` | 0.037422 | 0.107143 | -0.037890 | cleaner raw-curve contrast |
| `c04_eps060` | 0.047680 | 1.000000 | -0.150808 | optional high-crossing failure contrast |
| `c05_eps030` | 0.147681 | 0.928571 | -1.035222 | optional clearly poor cell |

## Implementation Readiness

Two existing tooling paths are relevant.

1. Seven-quantile retained reruns use `scripts/build_he2_exdqlm_multivar_keep_grid_smoke_matrix.py`.
   This script selects existing grid configs and rewrites run roots/config paths in isolation. It now accepts
   explicit Phase B overrides:
   - `--gamma-sigma-max-iter`
   - `--gamma-sigma-min-update-iters`
   - `--state-guard-start-iter`

2. Narrow one-quantile latent diagnostics use `scripts/prepare_he2_exdqlm_multivar_keep_latent_diag_configs.py`
   and `scripts/run_he2_exdqlm_multivar_keep_latent_diag_ladder.py`. The config preparer already supports
   one-q rows, `--max-iter`, latent diagnostics, pseudo-data guard, and row-level `state_guard_start_iter`.
   The ladder removes `.RData` after each one-q row, so it is appropriate for latent evidence, not for retained
   full-seven synthesis/posterior-object inspection.

Focused test added/passed:

```bash
python3 -m unittest tests.python.test_he2_exdqlm_keep_grid_next_steps -v
```

The new test verifies that the seven-quantile smoke builder can reproducibly override:

- `fit.exdqlm_multivar.gamma_sigma.max_iter`
- `fit.exdqlm_multivar.gamma_sigma.min_update_iters`
- `fit.exdqlm_multivar.gamma_sigma.min_total_iters`
- `fit.exdqlm_multivar.gamma_sigma.stabilization.state_guard_start_iter`

## Core Phase B Design

Phase B should run two coupled tracks. The full-seven track tests cross-quantile synthesis and keeps the heavy
posterior objects. The one-q latent track tests the internal `s_t`/`u_t`/pseudo-data mechanism at manageable disk
cost.

### Track B1: Full-Seven Retained Runs

Run all seven quantiles for the same cutoff/specs, with cleanup disabled, so post output and `.RData` remain.

| Phase | Cutoff | Spec | q lanes | max_iter | State guard | Cleanup | Purpose |
|---|---|---|---:|---:|---:|---|---|
| B1a | `20220511` | `c02_eps060` | 7 | 1000 | 1000 | no | convergence-grade rerun of CRPS winner |
| B1b | `20220511` | `c06_eps090` | 7 | 1000 | 1000 | no | cleaner raw-crossing contrast |
| B1c | `20220511` | `c02_eps060` | 7 | 1000 | 50 | no | state-guard sensitivity if B1a still crosses badly |

B1c should be launched only after B1a/B1b are read. It is not the first move because it doubles down on disk and
changes the state trajectory control while B1a is the clean convergence comparison.

Recommended B1 artifact root:

```text
/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20220511_phase_b_retained_20260531
```

Recommended B1 report root:

```text
reports/he2_exdqlm_multivar_keep_20220511_phase_b_20260531
```

Prepare B1a/B1b:

```bash
python3 scripts/build_he2_exdqlm_multivar_keep_grid_smoke_matrix.py \
  --source-matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524/control/publication_relaunch_matrix \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20220511_phase_b_retained_20260531 \
  --tag phaseb1000_c02c06_nocleanup_20260531 \
  --cutoffs 20220511 \
  --grid-spec-ids c02_eps060,c06_eps090 \
  --gamma-sigma-max-iter 1000 \
  --gamma-sigma-min-update-iters 100 \
  --ordinary-max-concurrent 1 \
  --pause-free-gb 160 \
  --launch-free-gb 220 \
  --heavy-free-gb 220 \
  --pause-mem-gb 120 \
  --launch-mem-gb 170 \
  --heavy-mem-gb 190 \
  --heavy-cutoff-max-concurrent 1 \
  --poll-seconds 30 \
  --reset-status
```

Launch B1a/B1b only after config inspection:

```bash
MATRIX_DIR=/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20220511_phase_b_retained_20260531/control/publication_relaunch_matrix
ARTIFACT_ROOT=/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20220511_phase_b_retained_20260531

nohup python3 scripts/run_multimodel_v8_queue.py \
  --matrix-dir "$MATRIX_DIR" \
  --artifact-root "$ARTIFACT_ROOT" \
  --ordinary-max-concurrent 1 \
  --pause-free-gb 160 \
  --launch-free-gb 220 \
  --heavy-free-gb 220 \
  --pause-mem-gb 120 \
  --launch-mem-gb 170 \
  --heavy-mem-gb 190 \
  --heavy-cutoff-max-concurrent 1 \
  --poll-seconds 30 \
  --continue-on-fail \
  --skip-compares \
  --no-heavy-cutoff-blocks-ordinary \
  --no-cleanup \
  > "$MATRIX_DIR/controller_nohup.log" 2>&1 &
echo $! | tee "$MATRIX_DIR/controller.pid"
```

### Track B2: One-Quantile Latent/State Diagnostics

The B2 target is direct evidence for `s_t`, `u_t`, pseudo-data, and state behavior in the suspected tail lanes.
These runs should be one quantile per row, one worker per row, latent diagnostics enabled, and `.RData` cleaned
after reports.

Initial B2 target rows:

| Phase | Cutoff | Spec | q | State guard | Purpose |
|---|---|---|---:|---:|---|
| B2-main | `20220511` | `c02_eps060` | 0.05 | 1000 | lower-tail suspect |
| B2-main | `20220511` | `c02_eps060` | 0.20 | 1000 | connects to prior q20 failures |
| B2-main | `20220511` | `c02_eps060` | 0.50 | 1000 | median control |
| B2-main | `20220511` | `c02_eps060` | 0.80 | 1000 | upper-tail sentinel |
| B2-main | `20220511` | `c02_eps060` | 0.95 | 1000 | upper-tail suspect |
| B2-contrast | `20220511` | `c06_eps090` | 0.05 | 1000 | cleaner-spec lower tail |
| B2-contrast | `20220511` | `c06_eps090` | 0.50 | 1000 | cleaner-spec median |
| B2-contrast | `20220511` | `c06_eps090` | 0.95 | 1000 | cleaner-spec upper tail |
| B2-guard | `20220511` | `c02_eps060` | 0.05 | 50 | state-guard lower-tail sensitivity |
| B2-guard | `20220511` | `c02_eps060` | 0.95 | 50 | state-guard upper-tail sensitivity |

Do not launch B2-guard until B2-main shows whether the default delayed guard leaves state or latent excursions.

## Required Metrics And Acceptance Checks

Every Phase B readout must report these, by q and by source where applicable:

| Layer | Required metric | Why |
|---|---|---|
| Fit loop | iteration, ELBO, ELBO step, sigma, gamma, rollback/fallback counts | identifies convergence and gamma/sigma instability |
| State size | `sqrt(state_norm_sq) / TT_obs` | user-requested normalized state magnitude |
| Latent `s_t` | `E[s_t]`, `E[s_t^2]`, entropy, truncation/positivity status | checks truncated-normal latent behavior |
| Latent `u_t` | `E[u_t]`, `E[1/u_t]`, `E[log u_t]`, `lambda`, `psi`, `chi`, entropy | checks GIG latent behavior and near-zero pathology |
| Pseudo-data | `FFF`, `QQQ`, `FFF_forecast`, `QQQ_forecast` ranges | shows propagation from latent/gamma/sigma to Kalman inputs |
| State space | selected state coordinates, trend, seasonal, transfer, discrepancy paths | tests trend/transfer/discrepancy identifiability |
| Synthesis | raw sample crossing, raw curve crossing, worst gap, post anchor/empirical crossing | separates raw posterior coherence from post repair |
| Forecast skill | CRPS mean/median/max vs GloFAS and NWS/NWM | keeps predictive skill in view without overtrusting it |

For the normalized state size, use exactly:

```text
state_norm_sqrt_per_obs = sqrt(state_norm_sq) / TT_obs
```

For Phase A, `TT_obs = 12767` from the fit logs. The Phase A baseline is:

| q | state_norm_sq | sqrt(state_norm_sq) | sqrt/state obs |
|---:|---:|---:|---:|
| 05 | 23986.61 | 154.876 | 0.012131 |
| 20 | 20929.24 | 144.669 | 0.011332 |
| 35 | 22878.33 | 151.256 | 0.011847 |
| 50 | 23985.60 | 154.873 | 0.012131 |
| 65 | 27266.99 | 165.127 | 0.012934 |
| 80 | 28279.13 | 168.164 | 0.013172 |
| 95 | 34019.19 | 184.443 | 0.014447 |

Phase B should compare not just final values, but also the trajectory of this metric across iterations.

## Decision Rules

The key decisions after B1/B2 are:

| Result | Interpretation | Next action |
|---|---|---|
| B1a raw crossing drops strongly by 1000 iterations | short VB budget was a major driver | consider raising production budget or convergence rule |
| B1a remains bad, B1b remains comparatively cleaner | spec-specific tail/state interaction | prioritize c06-like settings or tail regularization |
| B1a and B1b both remain bad | broader 20220511 cross-quantile coherence issue | stop discount/epsilon-only sweeps; investigate joint/coherent quantile modeling |
| B2 shows `E[u_t]`, `E[1/u_t]`, `FFF`, or `QQQ` spikes in q05/q95 | latent/pseudo-data mechanism is still causal | tighten latent/gamma/pseudo-data acceptance before synthesis |
| B2 latents are clean but trend/state paths diverge by tail | trend/state identifiability is causal | add component-level tail constraints or earlier state guard |
| B2-guard improves state metric and crossing | delayed state guard is too late | move state guard inside the iteration budget |
| CRPS stays good while raw crossing stays high | postprocessing is producing skill but not coherent raw posterior | do not declare the model scientifically fixed |

## Readiness Gates Before Launch

Run these checks before starting any Phase B background controller:

1. `git status --short --branch` has only intentional tracked Phase B prep changes or is clean.
2. No old production run roots are targeted by the generated configs.
3. No existing live campaigns are stopped or modified.
4. `matrix_plan.csv` has only cutoff `20220511`, only intended specs, and one or two rows for B1.
5. Generated YAMLs have:
   - `run.run_root` under the new Phase B artifact root,
   - `fit.quantiles` equal to all seven q lanes for B1,
   - `fit.exdqlm_multivar.gamma_sigma.max_iter=1000`,
   - `fit.exdqlm_multivar.gamma_sigma.min_update_iters=100`,
   - `state_guard_start_iter=1000` for B1a/B1b,
   - `CLEANUP_RDATA_AFTER_POST=0` enforced by launching with `--no-cleanup`.
6. Free disk is sufficient for retained objects. Budget about 55 GB per full-seven retained row.
7. The first health check confirms seven quantile worker logs are active and controller PID is live.

## Current Recommendation

Yes, we are ready to move to Phase B in a controlled way. The first launch should be B1a/B1b only:

- `20220511 c02_eps060`, 1000 iterations, all seven quantiles, retained `.RData`;
- `20220511 c06_eps090`, 1000 iterations, all seven quantiles, retained `.RData`.

Then read those results before launching B1c or B2-guard. If B1a/B1b already show clear tail-state or latent
pathology, the narrow B2 diagnostics should be launched immediately to locate the mechanism.

## 2026-05-31 Diagnostic Promotion Addendum

The useful Phase B readouts have now been promoted into the active fit/post workflow; see
`docs/exdqlm_multivar_keep_diagnostics_promotion_20260531.md`.

Key promotion points:

- future fits write compact per-iteration health rows under
  `<fit output dir>/diagnostics/vb_iteration/fit_iteration_health_summary.csv`;
- future multivariate-only post stages run the tracked audit helper and write the component/latent report under
  `<post output dir>/vb_latent_component_audit/`;
- the default diagnostics are lightweight: the compact health CSV is enabled, while heavy per-source/member top-cell
  tables remain opt-in;
- this promotion is diagnostic only. It does not change the statistical update, warmup schedule, state guard, or
  latent update formulas.

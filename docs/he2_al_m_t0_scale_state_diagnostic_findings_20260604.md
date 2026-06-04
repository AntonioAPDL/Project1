# HE2 AL-M-T0 Scale/State Diagnostic Findings - 2026-06-04

## Scope

This note closes the targeted AL-M-T0 scale/state diagnostic ladder defined in
`docs/he2_al_m_t0_scale_state_diagnostic_plan_revision_20260604.md`.

The diagnostic target was the representative multivariate AL drop workflow with
transfer level only (`a1_transfer_level_only`), because that design removes the
transfer covariate rows and therefore tests whether the failures are caused by
the AL scale / latent `u_t` / pseudo-data / Kalman-state feedback itself.

## Tracked Implementation Under Audit

The active code path now has AL-compatible state guard semantics in both legacy
multivariate entrypoints:

| Surface | Evidence |
|---|---|
| Drop entrypoint reads `DISC_GAMSIG_STATE_GUARD_START_ITER` | `DISC_Optimal_Synth_Ranges_W.r:304` |
| Drop policy log reports likelihood, guard policy, disabled reason, start iter, and terminal guard mode | `DISC_Optimal_Synth_Ranges_W.r:2913`, `DISC_Optimal_Synth_Ranges_W.r:2921` |
| Drop state guard no longer has an AL bypass | `DISC_Optimal_Synth_Ranges_W.r:3781` |
| Transfer-forecast entrypoint uses the same AL-compatible guard condition | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:5869` |
| P3 diagnostic spec requires `max_iter=160`, `min_update_iters=50`, and q35/q65 guards | `config/he2_relaunch_batches/al_m_t0_scale_state_p3_force_gamma_sigma_iter160_highdf_eps365_cf1_20260604.yaml:1`, `:27`, `:39`, `:56` |
| Legacy fit-call contract is forced on in generated configs | `scripts/build_he2_dqlm_multivar_al_drop_diagnostic_plan.py:335`, `tests/python/test_he2_al_m_t0_diagnostic_plan.py:312` |
| Log-level two-cycle detector is tested | `scripts/audit_he2_al_m_t0_gamsig_cycles.py:14`, `tests/python/test_he2_al_m_t0_gamsig_cycle_audit.py:32` |
| Saved-state decomposition helper extracts state, latent, and pseudo-data summaries | `scripts/decompose_he2_al_m_t0_saved_state.R:115`, `:169`, `:270`, `:288` |

## Runtime Evidence Bundle

The new P3 diagnostic root is:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_scale_state_p3_a1_force_gammasigma_iter160_fitcontract_20260604`

The main untracked evidence artifacts are:

| Artifact | Path |
|---|---|
| P3 live/final health table | `reports/he2_al_m_t0_scale_state_diagnostic_20260604/minimal_matrix_p3_live/DIAGNOSTIC_LADDER_LIVE_STATUS.md` |
| P3 cycle audit | `reports/he2_al_m_t0_scale_state_diagnostic_20260604/minimal_matrix_p3_cycles/GAMSIG_CYCLE_AUDIT.md` |
| P3 cycle CSV | `reports/he2_al_m_t0_scale_state_diagnostic_20260604/minimal_matrix_p3_cycles/gamsig_cycle_summary.csv` |
| P3 saved-state decomposition manifest | `reports/he2_al_m_t0_scale_state_diagnostic_20260604/minimal_matrix_p3_decomposition/saved_state_decomposition_manifest.csv` |
| P0/P1/P2 comparison cycle audit | `reports/he2_al_m_t0_scale_state_diagnostic_20260604/minimal_matrix_fitcontract_cycles/GAMSIG_CYCLE_AUDIT.md` |
| P0/P1/P2 saved-state decomposition | `reports/he2_al_m_t0_scale_state_diagnostic_20260604/minimal_matrix_fitcontract_decomposition/` |

These files are intentionally under `reports/` and should remain untracked unless
we explicitly decide to archive a small subset.

## Pre-P3 Findings

The P0/P1/P2 comparison established the failure mechanism:

| Case | Result | Key evidence |
|---|---|---|
| P0 q65 baseline | Failed | two-cycle true, final `E[sigma] = 999.9559`, `state_norm_sq = 1.3467383e12` |
| P1 q65 terminal guard only | Failed | same terminal two-cycle as P0; terminal guard alone did not repair the fit trajectory |
| P2 q65 forced gamma/sigma + state guard, max_iter 100 | Stabilized but failed terminal preflight | no two-cycle, final `E[sigma] = 0.122976`, `state_norm_sq = 50317.57`, but only 35 gamma/sigma update iterations versus the required 50 |
| P2 q35 | Passed and healthier than P0 q35 | final `state_norm_sq/T = 2.0457` versus P0/P1 q35 around `23.5562` |
| q80 controls | Passed | no two-cycle and stable state norms under the same representative A1 setup |

The saved-state decomposition of the bad P0 q65 fit shows the terminal blow-up is
not a transfer-level-only defect. The largest state blocks were shared/discrepancy
states, while transfer level stayed small:

| Block in P0 q65 bad fit | Max abs | Norm sq |
|---|---:|---:|
| shared quantile | 10009.43 | `1.28166228397003e12` |
| GloFAS discrepancy | 1632.90 | `3.58641330065416e10` |
| NWS discrepancy | 1511.96 | `2.92118589970188e10` |
| transfer level | 2.35 | 93.67 |

The latent summaries also rule out `s_t` as the live AL culprit: `sts.E.sts` and
`sts.E.sts2` are exactly zero in the decomposed AL cases. The bad P0 q65 fit had
pathological AL `u_t` moments: `median E[u_t] = 2552.09`,
`median E[1/u_t] = 0.0003918`, and pseudo-data medians around
`FFF = -3365.56`, `QQQ = 22436099.17`.

## P3 Diagnostic Result

P3 uses the P2 stabilization policy but raises the iteration budget to 160 so
guarded lanes can still obtain at least 50 actual gamma/sigma updates.

Final P3 health:

| cutoff | q | fit | iter | ELBO | E[sigma] | E[gamma] | state norm sq | state/T | transfer level max abs | max abs exps |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 20211112 | q35 | pass | 160 | -880.7939 | 0.2064698 | 0 | 33469.7 | 2.6591 | 1.4780 | 2.4393 |
| 20211221 | q80 | pass | 135 | -898.5533 | 0.09840154 | 0 | 56639.67 | 4.4860 | 0.3517 | 3.6756 |
| 20220511 | q65 | pass | 160 | -862.6221 | 0.6641269 | 0 | 875189.2 | 68.5509 | 0.7286 | 17.4739 |
| 20221225 | q80 | pass | 160 | -872.4102 | 0.1013842 | 0 | 54794.69 | 4.2166 | 0.3460 | 3.5980 |

Cycle audit:

| cutoff | q | two-cycle suspect | guard count | final update iters | tail sigma ratio | tail state ratio |
|---:|---:|---|---:|---:|---:|---:|
| 20211112 | q35 | false | 7 | 78 | 2.4581 | 2.7414 |
| 20211221 | q80 | false | 0 | 130 | 1.0000 | 1.0000 |
| 20220511 | q65 | false | 9 | 57 | 1.0000 | 1.0000 |
| 20221225 | q80 | false | 0 | 155 | 1.0000 | 1.0001 |

The key correction versus P2 is q65: P3 ended with 57 gamma/sigma update
iterations, passed terminal preflight, and saved a valid RData. The q65 terminal
state is still larger than controls, but it is no longer catastrophic and does
not alternate between incompatible terminal regimes.

## P3 Saved-State Decomposition

P3 q65 state blocks are stable enough to avoid the old invalid posterior state:

| Block in P3 q65 | Max abs | Norm sq |
|---|---:|---:|
| shared quantile | 3.1534 | 175887.86 |
| GloFAS discrepancy | 2.1700 | 140621.45 |
| NWS discrepancy | 4.6315 | 558670.89 |
| transfer level | 0.7286 | 8.98 |

For all four P3 cases, `sts.E.sts`, `sts.E.sts2`, and `sts.tot.entrop` remain
zero in the decomposition summaries. That is consistent with AL mode and further
confirms that the observed AL-M-T0 failure was not an `s_t` update failure.

The q65 `u_t` moments also moved back into a plausible central range:

| Case | median E[u_t] | median E[1/u_t] | max E[u_t] |
|---|---:|---:|---:|
| P0 q65 bad | 2552.09 | 0.0003918 | 2971.42 |
| P3 q65 | 0.38745 | 0.64775 | 3.96676 |

However, the pseudo-data summaries still show floor-driven extreme tail cells in
P3. For P3 q65, `pseudodata.FFF_history` has median `-2.0358` but lower-quartile
cells at `-1.31868131868132e10`; `pseudodata.QQQ_history_diag` has median
`5.5660` but upper-quartile cells around `2.82085955639799e10`. This is no
longer creating an invalid terminal state under P3, but it remains a promotion
risk that should stay in the acceptance gate.

## Interpretation

Confirmed:

1. The old q65 catastrophic failure is not a raw input-bundle failure: q80 controls
   passed under the same representative A1 setup.
2. The old q65 failure is not a transfer-covariate-only problem: A1 removes driver
   rows and still reproduced the P0/P1 two-cycle.
3. The AL `s_t` layer is not the live culprit in these AL diagnostics: all
   decomposed AL `s_t` moments are zero.
4. The active failure mechanism is an interaction among the AL scale update,
   `u_t` moments, pseudo-data construction, and the Gaussian/Kalman state update.
5. P3 fixes the silent catastrophic terminal behavior for the representative
   suspect lanes by combining forced gamma/sigma updates, AL-compatible state
   guard, terminal guard, and enough iterations to satisfy update-count gates.

Questionable / not fully closed:

1. P3 q65 is valid but not as quiet as controls (`state_norm_sq/T = 68.55`).
2. P3 still has pseudo-data tail/floor extremes even when the saved state is
   acceptable.
3. We have proven the representative A1 matrix, not every full publication cutoff,
   quantile, and transfer design.

Wrong / fixed:

1. Treating terminal guard alone as sufficient was wrong. P1 reproduced the P0
   q65 failure.
2. Letting AL mode bypass the state guard was wrong for the active drop entrypoint.
3. Letting `max_iter=100` stand for guarded q65 was insufficient; P2 needed more
   actual gamma/sigma updates.

## Promotion Recommendation

Use P3 as the candidate stabilization policy for the AL-M-T0 suspect lanes, but
do not promote it blindly into final article tables without the gates below.

Priority fix list:

1. Promote the AL guard parity patch and policy logging as non-optional for both
   multivariate entrypoints.
2. For AL-M-T0 q35/q65 suspect lanes, use forced `freeze_target=gamma_sigma`,
   `state_guard_enabled=true`, terminal `fail_fast`, `min_update_iters=50`, and
   `max_iter >= 160`.
3. Keep q80 controls on the normal policy unless a future diagnostic shows a
   control-lane failure.
4. Require the live terminal health report and log-level two-cycle audit before a
   fit can enter CRPS or article-table selection.
5. Add or keep a latent/pseudo-data acceptance summary for `E[u_t]`,
   `E[1/u_t]`, `FFF`, and `QQQ`; P3 shows this layer can remain numerically
   extreme even when terminal states pass.
6. Before broad publication promotion, run a full AL-M-T0 cutoff/quantile smoke
   under the P3 policy with production cleanup enabled after post/report.
7. If the full smoke shows pseudo-data floor saturation in accepted fits, run a
   smaller P4 diagnostic focused on `u_t`/pseudo-data floors or caps before
   declaring the AL-M-T0 family final.

## Validation Commands

These commands were run as part of the implementation/audit chain:

```bash
python3 scripts/validate_he2_dqlm_multivar_al_drop_diagnostic_plan.py \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_scale_state_p3_a1_force_gammasigma_iter160_fitcontract_20260604 \
  --discount-spec-yaml config/he2_relaunch_batches/al_m_t0_scale_state_p3_force_gamma_sigma_iter160_highdf_eps365_cf1_20260604.yaml \
  --lane-scope representative \
  --experiment-scope a1

python3 scripts/launch_he2_al_m_t0_representative_diagnostics.py \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_scale_state_p3_a1_force_gammasigma_iter160_fitcontract_20260604 \
  --expected-spec-id scale_state_p3_force_gamma_sigma_iter160_highdf_eps365_cf1_20260604 \
  --expected-experiment-scope a1 \
  --confirm-launch \
  --max-concurrent 4

python3 scripts/monitor_he2_al_m_t0_diagnostic_ladder.py \
  --root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_scale_state_p3_a1_force_gammasigma_iter160_fitcontract_20260604 \
  --outdir reports/he2_al_m_t0_scale_state_diagnostic_20260604/minimal_matrix_p3_live

python3 scripts/audit_he2_al_m_t0_gamsig_cycles.py \
  --path /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_scale_state_p3_a1_force_gammasigma_iter160_fitcontract_20260604 \
  --report-dir reports/he2_al_m_t0_scale_state_diagnostic_20260604/minimal_matrix_p3_cycles

Rscript --vanilla scripts/decompose_he2_al_m_t0_saved_state.R \
  --outdir reports/he2_al_m_t0_scale_state_diagnostic_20260604/minimal_matrix_p3_decomposition \
  --case P3_20211112_q35=/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_scale_state_p3_a1_force_gammasigma_iter160_fitcontract_20260604/runs/diagnostic_20211112_dqlm_multivar_al_drop_q35_scale_state_p3_force_gamma_sigma_iter160_highdf_eps365_cf1_20260604_a1_transfer_level_only/fit/q=35/outputs/DISC_variables_35_exAL_synth_DISC.RData \
  --case P3_20211221_q80=/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_scale_state_p3_a1_force_gammasigma_iter160_fitcontract_20260604/runs/diagnostic_20211221_dqlm_multivar_al_drop_q80_scale_state_p3_force_gamma_sigma_iter160_highdf_eps365_cf1_20260604_a1_transfer_level_only/fit/q=80/outputs/DISC_variables_80_exAL_synth_DISC.RData \
  --case P3_20220511_q65=/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_scale_state_p3_a1_force_gammasigma_iter160_fitcontract_20260604/runs/diagnostic_20220511_dqlm_multivar_al_drop_q65_scale_state_p3_force_gamma_sigma_iter160_highdf_eps365_cf1_20260604_a1_transfer_level_only/fit/q=65/outputs/DISC_variables_65_exAL_synth_DISC.RData \
  --case P3_20221225_q80=/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_scale_state_p3_a1_force_gammasigma_iter160_fitcontract_20260604/runs/diagnostic_20221225_dqlm_multivar_al_drop_q80_scale_state_p3_force_gamma_sigma_iter160_highdf_eps365_cf1_20260604_a1_transfer_level_only/fit/q=80/outputs/DISC_variables_80_exAL_synth_DISC.RData
```


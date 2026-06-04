# HE2 AL-M-T0 Transfer Ladder Terminal Findings - 2026-06-04

## Scope

This note closes the targeted AL-M-T0 diagnostic ladder launched on 2026-06-04 after the
terminal-health guard and transfer-mode support patches.

The valid ladder rows are:

- `a0_full_sd`: full transfer feature design, SD scaling;
- `a1_transfer_level_only`: no transfer covariate driver rows, repaired in retry2;
- `a2_full_zscore`: full transfer feature design, z-score scaling;
- `a3_base_sd`: base transfer feature design, SD scaling;
- `a4_base_zscore`: base transfer feature design, z-score scaling.

The old pre-patch A1 rows from the first ladder root and the first A1 retry are implementation evidence only:
they failed before the zero-feature drop-runner fix and are not scientific model evidence.

## Evidence Paths

- Live/final status table:
  `reports/he2_al_m_t0_transfer_ladder_live_20260604/DIAGNOSTIC_LADDER_LIVE_STATUS.md`
- Machine-readable final status:
  `reports/he2_al_m_t0_transfer_ladder_live_20260604/diagnostic_ladder_live_status.csv`
- Replay helper output:
  `reports/he2_al_m_t0_transfer_ladder_live_20260604/terminal_health_replay/`
- Runtime roots:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_transfer_ladder_highdf_eps365_cf1_20260604`
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_a1_transfer_level_only_retry2_highdf_eps365_cf1_20260604`

## Terminal Result

Every valid ladder experiment has the same terminal-health pattern:

| experiment | q35 20211112 | q80 20211221 | q65 20220511 | q80 20221225 | takeaway |
|---|---:|---:|---:|---:|---|
| `a0_full_sd` | fail | pass | fail | pass | full raw-style design fails suspect lanes only |
| `a1_transfer_level_only` | fail | pass | fail | pass | removing transfer covariate drivers does not fix suspect lanes |
| `a2_full_zscore` | fail | pass | fail | pass | z-scoring full design does not fix suspect lanes |
| `a3_base_sd` | fail | pass | fail | pass | base-only SD design does not fix suspect lanes |
| `a4_base_zscore` | fail | pass* | fail | pass | terminal health still fails q35/q65 and passes q80 controls |

`a4_base_zscore` for q80/20211221 is a wrapper-level failure but a terminal-health pass. Its RData was saved and
the terminal replay showed zero health violations. The wrapper failure came from the old post-save objective path
before `DISC_Optimal_Synth_Ranges_W.r` was patched to honor `DISC_W_POST_SAVE_OBJECTIVE_ENABLED=FALSE`.

## Quantitative Signal

The q80 controls are healthy on terminal metrics:

- `state_norm_sq_per_T` is about 2.8 to 12.0;
- `transfer_level_max_abs` is about 0.35 to 6.48;
- `max_abs_history_exps` is about 3.60 to 8.45.

The q35/q65 suspect lanes fail by orders of magnitude:

- `state_norm_sq_per_T` ranges from about `2.05e5` to `3.78e8`;
- `max_abs_history_exps` ranges from about `560` to `30984`;
- full/base transfer variants also show huge `transfer_level_max_abs`, up to about `30954`;
- even `a1_transfer_level_only` keeps `transfer_level_max_abs` small but still has `max_abs_history_exps`
  around `1.31e4` and `state_norm_sq_per_T` around `1.05e8`.

This last point is crucial: the failure is not solely caused by the transfer covariate driver rows. The q35/q65
lanes can explode even when the transfer covariate block is removed.

## Confirmed Implementation Fixes

The following implementation issues were fixed and tested during this pass:

1. `DISC_Optimal_Synth_Ranges_W.r` now honors:
   - `DISC_W_POST_SAVE_OBJECTIVE_ENABLED`;
   - `DISC_W_POST_SAVE_JSD_ENABLED`;
   - `DISC_W_POST_SAVE_JSD_GRIDSIZE`.
2. Both legacy multivariate entrypoints now expose the post-save objective/JSD disabled log markers.
3. `scripts/monitor_he2_al_m_t0_diagnostic_ladder.py` now reports:
   - RData presence;
   - terminal violation count;
   - `state_norm_sq_per_T`;
   - `transfer_level_max_abs`;
   - `max_abs_history_exps`.
4. `scripts/replay_he2_al_m_t0_ladder_terminal_health.R` can replay terminal health for saved ladder RData
   artifacts that missed wrapper health because of pre-patch post-save diagnostic exits.

Validation commands:

```bash
Rscript --vanilla -e "invisible(parse('DISC_Optimal_Synth_Ranges_W.r')); invisible(parse('DISC_Optimal_Synth_Ranges_W_transfer_forecast.r')); cat('parse_ok\n')"
Rscript --vanilla -e "library(testthat); test_file('tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R')"
python3 -m py_compile scripts/monitor_he2_al_m_t0_diagnostic_ladder.py
Rscript --vanilla -e "invisible(parse('scripts/replay_he2_al_m_t0_ladder_terminal_health.R')); cat('parse_ok\n')"
```

## Interpretation

The AL-M-T0 instability is now localized more tightly:

1. It is not a generic workflow failure because q80 controls pass across the ladder.
2. It is not solely a transfer-feature scaling problem because full SD, full z-score, base SD, and base z-score
   all fail the same suspect lanes.
3. It is not solely the transfer covariate driver rows because `a1_transfer_level_only` still fails q35/q65.
4. The most likely remaining failure mode is interaction among AL sigma estimation, latent `u_t` behavior,
   and the state/Kalman layer under the q35/q65/cutoff data geometry.
5. The failing lanes often push `sigma` near the effective upper region and produce huge saved-state norms.

## Decision

Do not promote AL-M-T0 for publication tables or broad cutoff relaunches yet.

The right next move is not more transfer-feature tuning. The next diagnostic ladder should target the AL scale/state
interaction directly:

1. fixed or capped sigma experiments for q35/q65 with q80 controls;
2. stronger terminal sampling/fit guards for `sigma`, `E[u_t]`, and state norm;
3. state-block decomposition of the failing q35/q65 saved RData to identify which non-transfer block drives
   `max_abs_history_exps` in `a1_transfer_level_only`;
4. a one-lane deterministic replay that computes component contributions from `theta.out$sm` and `theta.out$exps`
   for q35/q65 versus q80 controls.

## Operational Notes

- The diagnostic RData files are intentionally retained for now because they are needed for component-level replay.
- The pre-patch post-save objective crash should not be counted as a model failure when the saved RData has a
  terminal-health pass.
- Future launches from commit `93009d6` or later should not hit the old post-save objective/JSD path when those
  switches are disabled.

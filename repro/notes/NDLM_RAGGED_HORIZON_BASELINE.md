# NDLM Ragged-Horizon Baseline (C0)

Date: 2026-02-20

Purpose:
- Freeze current NDLM horizon assumptions before refactor.
- Provide a "before" contract table for C1-C7.

## Shared-K Assumption Points (Current)

### Theory (NDLM---Ensemble)
- `NDLM---Ensemble/docs/derivations/sections/01_notation_and_model.tex:4`
  - Forecast period defined as `t=T+1,...,T+K` (single shared K).
- `NDLM---Ensemble/docs/derivations/sections/01_notation_and_model.tex:59`
  - Model C uses leads `k=1,...,K` for all active forecasters.
- `NDLM---Ensemble/docs/derivations/sections/02_joint_density.tex:30-33`
  - Joint factorization indexed on `t=T+1,...,T+K`.

### Unified NDLM implementation (project1)
- `R/unified/families/ndlm_main/01_inputs.R:117`
  - `K <- min(nws_len, glofas_len, horizon_cap)`.
- `R/unified/families/ndlm_main/01_inputs.R:124-132`
  - Forecast vectors truncated to `seq_len(K)` for both sources.
- `R/unified/families/ndlm_main/03_vb_updates.R:41`
  - VB loop forecast horizon read as scalar `K`.
- `R/unified/families/ndlm_main/03_vb_updates.R:145-166`
  - `sm_ens`/`sC_ens` built as two segments each with same width `K`.
- `R/unified/families/ndlm_main/03_vb_updates.R:174-177`
  - `standard_forecast_errors` computed only over shared `K`.
- `R/unified/families/ndlm_main/06_save_state.R:21-23`
  - Theory state stores scalar `K` and source lengths but no per-source horizons.

### Contracts/diagnostics currently enforcing shared K
- `R/unified/contract_checks.R:352`
  - `K_expected <- min(nws_len, glofas_len, K_cap)`.
- `R/unified/diagnostics.R:561`
  - Same shared-K expected rule.
- `R/unified/ndlm_post_diagnostics.R:197`
  - Horizon contract rule explicitly states shared-K `min(...)`.

## Before Contract Table

| Object / Formula | Current behavior | Expected ragged behavior | Status |
|---|---|---|---|
| Model C lead index (`k`) | Single shared `k=1..K` for all sources | Source-specific horizon `K_j`; active set `A_k={j: k<=K_j}` | mismatch |
| Forecast vectors in NDLM inputs | Both truncated to same `K=min(...)` | Keep full per-source lengths; no forced overlap truncation | mismatch |
| `sm_ens` segments | Both segments width `K` | Segment widths derived from active-set transitions (e.g., `K_(1)`, then `K_(2)-K_(1)` in 2-source case) | mismatch |
| `sC_ens` segments | Both segments depth `K` | Segment-specific depth following active-set transitions | mismatch |
| `standard_forecast_errors` | Shared horizon matrix over `K` | Ragged-aware structure consistent with per-lead active set | mismatch |
| Contract checks | Shared-K pass criterion (`min(...)`) | Per-lead/per-segment ragged consistency checks | mismatch |

## Frozen Baseline Notes
- This baseline intentionally records the current shared-K enforcement and should be treated as immutable C0 evidence.
- C1-C7 must replace these assumptions with ragged-horizon semantics without introducing silent clipping.

# Q-04 Root Cause Matrix

| Hypothesis | Evidence | Verdict |
|---|---|---|
| NDLM post path is truncating/mis-indexing valid fit outputs | `ndlm_plot_contract_check.csv` is pass in canonical and Q-04 run; stage `post=pass` | Rejected |
| NDLM Kalman backend wiring regression | `test_ndlm_kalman_backend.R` passes; NDLM-only run `kalman_backend=cpp` with contract pass | Rejected |
| NDLM fit loop under-iterates due implementation cap | `00_constants.R` had fixed `n_iter=16`; canonical summary had no configurable fit-loop controls and only 16 gamsig iterations | Supported (primary) |
| NDLM diagnostics false warning due wrong sign assumption on `delta` | Prior warning expected nonnegative delta; discrepancy deltas are signed | Supported (secondary) |

## Supported root causes
1. Hard-coded NDLM fit-loop iteration cap in implementation.
2. Diagnostics sign assumption mismatch (warning semantics), not model-state corruption.

## Implemented correction path
1. Configurable NDLM fit-loop controls (`max_iter`, `min_total_iters`, `elbo_tol`, `elbo_rel_tol`) wired from unified config and env.
2. NDLM summary now records convergence metadata (`converged`, `iterations_completed`, `convergence_reason`, criteria and final metrics).
3. NDLM diagnostics warning changed from nonnegativity to sign-balance informational warning.

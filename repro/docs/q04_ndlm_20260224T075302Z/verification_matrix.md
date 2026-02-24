# Q-04 Verification Matrix

| Check | Result | Evidence |
|---|---|---|
| NDLM fit-loop contract tests | pass | `tests/testthat/test_ndlm_fitloop_contract.R` |
| NDLM horizon diagnostics tests | pass | `tests/testthat/test_ndlm_horizon_contract.R` |
| NDLM backend consistency tests | pass | `tests/testthat/test_ndlm_kalman_backend.R` |
| NDLM-only lean run (fit/post/validate/report) | pass (all stages) | `repro/runs/diag_q04_ndlm_only_fitloop_20260224/run_manifest.yaml` |
| NDLM convergence metadata emitted | pass | `repro/runs/diag_q04_ndlm_only_fitloop_20260224/fit/ndlm_main/logs/ndlm_theory_summary.log` |
| NDLM post horizon contract | pass | `repro/runs/diag_q04_ndlm_only_fitloop_20260224/diagnostics/ndlm/ndlm_plot_contract_check.csv` |

## Key numeric evidence
- `iterations_completed=200`, `max_iter=200`, `convergence_reason=max_iter_reached`
- `crit_elbo_rel=0.000313793448884993`, `elbo_rel_tol=0.00025`

This confirms NDLM now obeys configured loop controls and exposes non-convergence explicitly instead of silently under-iterating.

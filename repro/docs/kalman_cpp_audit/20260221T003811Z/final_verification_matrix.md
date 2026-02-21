# Final Verification Matrix (A7/A8 Closure)

Date: 2026-02-21
Scope: NDLM + multiv exDQLM Kalman C++ audit/alignment thread.

| check | command/run | result | evidence |
|---|---|---|---|
| Targeted tests: C++ compile + NDLM backend config | `python3 -m pytest -q repro/tests/test_kalman_cpp_compile_smoke.py repro/tests/test_ndlm_kalman_backend_config.py` | PASS (`4 passed`) | `repro/docs/kalman_cpp_audit/20260221T003811Z/verification_logs/pytest_kalman.txt` |
| Targeted tests: R-vs-C++ NDLM smoother consistency | `Rscript --vanilla -e "library(testthat); test_file('tests/testthat/test_ndlm_kalman_backend.R')"` | PASS (`10 passed`) | `repro/docs/kalman_cpp_audit/20260221T003811Z/verification_logs/r_testthat_ndlm_backend.txt` |
| NDLM-only unified smoke run | `run_id=diag_ndlm_cpp_only_smoke_shared_20260221` | PASS (all stages pass; closed manifest) | `repro/runs/diag_ndlm_cpp_only_smoke_shared_20260221/run_manifest.yaml`; `repro/runs/diag_ndlm_cpp_only_smoke_shared_20260221/fit/ndlm_main/logs/ndlm_theory.log`; `repro/runs/diag_ndlm_cpp_only_smoke_shared_20260221/post/logs/post_runner.log` |
| multiv exDQLM median-only unified smoke run | `run_id=diag_multiv_cpp_ultrafast_smoke_shared_20260221`, `quantiles=[0.50]` | PASS (all stages pass; closed manifest) | `repro/runs/diag_multiv_cpp_ultrafast_smoke_shared_20260221/run_manifest.yaml`; `repro/runs/diag_multiv_cpp_ultrafast_smoke_shared_20260221/fit/q=50/logs/fit.log`; `repro/runs/diag_multiv_cpp_ultrafast_smoke_shared_20260221/post/logs/post_runner.log` |
| Stage-status snapshot for closure runs | manifests summarized from both run ids | PASS (all stage statuses `pass` and `finished_at_utc` non-null) | `repro/docs/kalman_cpp_audit/20260221T003811Z/verification_logs/run_status_summary.txt` |

## Closure Gate
- `A0` through `A8` are satisfied for the Kalman C++ audit/alignment scope.
- NDLM backend selector (`r|cpp`) is wired; `cpp` default is validated in unified workflow.
- Kalman contract/wiring baseline is now frozen for this thread.

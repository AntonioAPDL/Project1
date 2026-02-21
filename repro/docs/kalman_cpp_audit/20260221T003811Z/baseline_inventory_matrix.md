# Baseline Inventory Matrix (A0)

Date: 2026-02-21

| component | file | function/entrypoint | model | used_by_unified | callsite evidence | covariance input contract | ragged horizon status | ELBO ownership | status |
|---|---|---|---|---|---|---|---|---|---|
| `multiv_cpp` | `DISC_kalman_synth.cpp` | `DISC_update_theta_synth_cpp`, `DISC_update_theta_synth_cpp_W` | multiv exDQLM | yes | `R/unified/stages/stage_fit.R:376` -> `scripts/run_DISC_Optimal_Synth_Ranges_W.R` -> `DISC_Optimal_Synth_Ranges_W.r:61`, `DISC_Optimal_Synth_Ranges_W.r:2094` | `ex_q` / `ex_q_list_ens` provided externally (time-varying covariance inputs) | segmented via `k_ens` + transdim smoother blocks | C++ (historical + forecast segments) | baseline confirmed |
| `ndlm_cpp_legacy` | `DISC_kalman_synth_NDLM.cpp` | `update_theta_synth_cpp_ndlm` | NDLM | not currently | `DISC_Optimal_Synth_Ranges_NDLM.r:115`, `DISC_Optimal_Synth_Ranges_NDLM.r:1696` | `D` / `D_ens` provided externally (fixed per segment matrix in current implementation) | segmented via `k_ens` + transdim smoother blocks | C++ (historical + forecast segments) | baseline confirmed |
| `ndlm_cpp_exactv` | `kalman_NDLM.cpp` | `update_theta_cpp_ndlm_exactV` | NDLM | not currently | `kalman_NDLM.cpp:311` | `nu0,S0 -> V_obs` expected covariance (Wishart-like VB expectation) | fixed-dim (non-ragged legacy path) | C++ | baseline confirmed |
| `ndlm_unified_r` | `R/unified/families/ndlm_main/02_model_spec.R` | `ndlm_theory_kalman_smoother` | NDLM | yes | `R/unified/families/ndlm_main/03_vb_updates.R:122` | `R_vec` scalar obs variance + `q_diag` state noise in R | fixed-dim smoother (ragged handled outside smoother) | ELBO computed in R fit loop | baseline confirmed |

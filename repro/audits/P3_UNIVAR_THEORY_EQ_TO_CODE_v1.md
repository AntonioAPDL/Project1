# P3 Univariate Theory Equation-to-Code Audit (v1)

Date: 2026-02-11  
Family: `exdqlm_univar` (`implementation_mode=theory_aligned`)

## Theory Source of Truth

- `/data/muscat_data/jaguir26/univ-exDQLM---Ensemble/main.tex`

## Mapping Table

| Theory reference | Code implementation |
|---|---|
| `\section{Model A hierarchy and stacked DLM form}` (`\label{sec:modelA}`), observation/evolution blocks `\eqref{eq:obs}`, `\eqref{eq:theta_evol}`, `\eqref{eq:zeta_evol}`, `\eqref{eq:psi_evol}` | State definition and fixed dimensions in `R/unified/families/exdqlm_univar/00_constants.R` (`univar_theory_constants`); input assembly in `R/unified/families/exdqlm_univar/01_inputs.R` (`univar_theory_load_inputs`) |
| exAL augmentation and parameter map: `\label{sec:exal_aug}`, `\eqref{eq:g_gamma}`, `\eqref{eq:p_map}`, `\eqref{eq:ABC}` | `R/unified/families/exdqlm_univar/02_model_spec.R` (`univar_theory_exal_g`, `univar_theory_gamma_bounds`, `univar_theory_exal_map`) |
| Conditionally Gaussian pseudo-observation form: `\label{sec:cond_gauss_dlm}`, `\eqref{eq:ytilde_R}`, `\eqref{eq:pseudo_obs}` and FFBS recursions `\eqref{eq:ff_a}`-`\eqref{eq:ff_C}` | `R/unified/families/exdqlm_univar/02_model_spec.R` (`univar_theory_kalman_smoother`) and iterative use in `R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R` (`univar_theory_run_cavi`) |
| Mean-field VB/CAVI factorization and updates: `\label{sec:vb}`, `\eqref{eq:vb_factorization}`, `\eqref{eq:cavi_rule}`, `\label{sec:vb_alpha}`, `\label{sec:vb_v}`, `\label{sec:vb_s}` | Core update loop in `R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R` (`univar_theory_run_cavi`), including state update + latent moments |
| GIG and truncated-normal moments: `\eqref{eq:gig_moment}`-`\eqref{eq:gig_Elogv}`, `\eqref{eq:tn_Es}`-`\eqref{eq:tn_Es2}` | `R/unified/families/exdqlm_univar/02_model_spec.R` (`univar_theory_gig_moment`, `univar_theory_truncnorm_pos_moments`) |
| Laplace-Delta block for `(sigma,gamma)`: `\label{sec:laplace_delta}` | Numerical optimization of the joint block in `R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R` (`univar_theory_log_joint_sigma_gamma`, `univar_theory_run_cavi`) |
| ELBO monitoring: `\label{sec:elbo}`, `\eqref{eq:elbo_decomp}` | `R/unified/families/exdqlm_univar/04_elbo_optional.R` (`univar_theory_elbo_trace`) |
| Compatibility object contracts for downstream post | `R/unified/families/exdqlm_univar/05_save_state.R` (`univar_theory_pack_compat_outputs`) and runner `R/unified/families/exdqlm_univar/zz_run.R` (`unified_run_exdqlm_univar_theory`) |

## Known Intentional Deviations

- None documented for this v1 implementation.

## Open Verification Items

- Confirm full parity of the Laplace-Delta approximation details against all terms in `\label{sec:laplace_delta}` once P3 expands beyond smoke-scale diagnostics.
- Add deterministic ELBO trend checks (monotonicity tolerance) only after broader empirical validation; current diagnostics enforce finite-value safety only.

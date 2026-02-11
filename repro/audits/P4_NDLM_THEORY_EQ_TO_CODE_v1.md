# P4 NDLM Theory Equation-to-Code Audit (v1)

Date: 2026-02-11  
Family: `ndlm_main` (`implementation_mode=theory_aligned`)  
Scope: VB-only implementation (locked by D-002)

## Theory Source of Truth

- `/data/muscat_data/jaguir26/NDLM---Ensemble/docs/derivations/main.tex`
- Included derivation sections:
  - `sections/01_notation_and_model.tex`
  - `sections/03_state_posterior_ffbs.tex`
  - `sections/06_vb_cavi.tex`
  - `sections/07_elbo.tex`
  - `sections/09_predictive.tex`

## Mapping Table

| Theory reference | Code implementation |
|---|---|
| Model specification and observation/state equations (`\eqref{eq:A_obs}`, `\eqref{eq:A_theta}`, `\eqref{eq:A_zeta}`, `\eqref{eq:A_psi}`, `\eqref{eq:C_obs}`, `\eqref{eq:C_state}`) | `R/unified/families/ndlm_main/00_constants.R` (`ndlm_theory_constants`), `R/unified/families/ndlm_main/01_inputs.R` (`ndlm_theory_load_inputs`) |
| Kalman filtering/smoothing and FFBS conditionals (`\eqref{eq:lgssm_state}`, `\eqref{eq:lgssm_obs}`, `\eqref{eq:kf_f}`-`\eqref{eq:kf_C}`, `\eqref{eq:ffbs_B}`-`\eqref{eq:ffbs_cond}`) | `R/unified/families/ndlm_main/02_model_spec.R` (`ndlm_theory_kalman_smoother`) and calls from `R/unified/families/ndlm_main/03_vb_updates.R` |
| VB factorization and CAVI updates (`\eqref{eq:vb_factorization}`, `\eqref{eq:vb_cavi_rule}`, `\eqref{eq:vb_sigma}`, `\eqref{eq:vb_W}`, `\eqref{eq:vb_lambda}`, `\eqref{eq:vb_sigma_moments}`-`\eqref{eq:vb_state_moments}`) | `R/unified/families/ndlm_main/03_vb_updates.R` (`ndlm_theory_run_vb`) |
| ELBO decomposition and stopping criteria (`\eqref{eq:elbo_def}`, `\eqref{eq:elbo_blocks}`, `\eqref{eq:elbo_stop}`) | `R/unified/families/ndlm_main/04_elbo.R` (`ndlm_theory_elbo_trace`) and fit loop in `R/unified/families/ndlm_main/05_fitloop.R` |
| Predictive/ensemble moments (`\eqref{eq:one_step_pred}`, `\eqref{eq:mcmc_ppd}` context for output moments) | Ensemble state/covariance packing and draws in `R/unified/families/ndlm_main/03_vb_updates.R` (`sm_ens`, `sC_ens`, `samp_theta_ens`) |
| Legacy-compatible output aliases for downstream post | `R/unified/families/ndlm_main/06_save_state.R` (`ndlm_theory_pack_compat_outputs`), runner `R/unified/families/ndlm_main/zz_run.R` (`unified_run_ndlm_main_theory`) |

## Forecast-Window Stochastic W Treatment (Required by P4)

Theory anchor:
- Evolution covariance prior/updates are governed by `\eqref{eq:prior_W}` and VB covariance-factor block `\eqref{eq:vb_W}`.

Code implementation:
- `R/unified/families/ndlm_main/03_vb_updates.R` (`ndlm_theory_run_vb`) updates two stochastic covariance scales:
  - `w_hist` from historical state increments (`hist_diff`)
  - `w_fore` from forecast-window state increments (`fore_diff`)
- These scales are then propagated into:
  - state evolution diagonal process noise (`q_diag`)
  - forecast ensemble covariance slices `sC_ens` via `diag(w_fore * k + 1e-4, 7)`

Expected invariants:
- `w_hist >= 0`, `w_fore >= 0` and finite.
- Covariance slices (`sC`, `sC_ens`) remain symmetric and PSD (to tolerance).
- `sigma > 0` and finite.

## Known Intentional Deviations

- None documented for this v1 implementation.

## Open Verification Items

- Add direct ELBO component reconciliation against the full block decomposition in `sections/07_elbo.tex` after broader runtime coverage.
- Expand stochastic-W checks from sampled-slice diagnostics to full-scan diagnostics only when runtime budget permits.

# Family Post Object Contract Map (v1)

Date: 2026-02-11  
Scope: runtime object contracts loaded by current post modules from family model-state `.RData` files.

## exdqlm_univar (theory_aligned output, per quantile `q_num`)

Required object aliases:

- `new.theta.out_<q_num>_exAL_synth_DISC_uni`
- `samp.theta_<q_num>_exAL_synth_DISC_uni`
- `samp.sigma_<q_num>_exAL_synth_DISC_uni`
- `seq.elbo_<q_num>_exAL_synth_DISC_uni`

Minimum shape/type expectations used by post:

- `new.theta.out_*` is a list with:
  - `sm`: numeric matrix `[state_dim x T]`
  - `sC`: numeric array `[state_dim x state_dim x T]`
  - `exps`: numeric matrix with `ncol == T`
- `samp.theta_*`: numeric tensor with one dimension equal to `T`
- `samp.sigma_*`: numeric vector/matrix, finite values
- `seq.elbo_*`: numeric vector, finite values

## ndlm_main (theory_aligned output with legacy compatibility aliases)

Required object aliases:

- `new.theta.out_50_NDLM_synth_DISC`
- `samp.theta_50_NDLM_synth_DISC`
- `samp.sigma_50_NDLM_synth_DISC`
- `samp.theta_ens_50_NDLM_synth_DISC`
- `seq.elbo_50_NDLM_synth_DISC`
- `seq.sigma_50_NDLM_synth_DISC`
- `delta_50_NDLM_synth_DISC`

Minimum shape/type expectations used by post:

- `new.theta.out_*` is a list with:
  - `sm`: numeric matrix `[state_dim x T]`
  - `sC`: numeric array `[state_dim x state_dim x T]`
  - `sm_ens`: list of numeric matrices
  - `sC_ens`: list of numeric 3D arrays
  - `exps`: numeric matrix with `ncol == T`
- `samp.theta_*`: numeric tensor with one dimension equal to `T`
- `samp.sigma_*`: numeric vector/matrix, finite values
- `samp.theta_ens_*`: nested list/tensor containing numeric finite leaves (ensemble compatibility object)
- `seq.elbo_*`, `seq.sigma_*`, `delta_*`: numeric finite vectors

## Source references

- `R/environmetrics/30_univariate_and_misc.R`
- `R/environmetrics/40_figures.R`
- `R/unified/contract_checks.R`

## Validator-Minimal Artifact Schema (ndlm_main)

This section defines the validator-side minimum required artifacts for NDLM integration when
`models.run_ndlm_main=true` (run-scoped contract; no model semantics changes).

Required model-state output under run root:

- `fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`, or
- `fit/ndlm_main/outputs/ndlm_main_state.RData`, or
- `fit/ndlm_main/outputs/ndlm_main_*.RData`

Required when `fit.contract_checks.enabled=true`:

- `fit/contract_checks/ndlm_main/ndlm_main_contract_check.json` (or equivalent JSON report in that folder)

Required when `fit.diagnostics.enabled=true`:

- `fit/diagnostics/ndlm_main/ndlm_main_diagnostics.json` (or equivalent JSON report in that folder)

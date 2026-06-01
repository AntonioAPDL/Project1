# exDQLM Multivar Keep Diagnostics Promotion, 2026-05-31

## Purpose

This note closes the 20220511 Phase B diagnostic loop by promoting the useful audit outputs into the active multivariate `exdqlm keep` workflow. The goal is to make future runs self-auditing enough that we can diagnose extreme-quantile instability from the normal fit/post artifacts without rerunning a separate ad hoc investigation.

## Evidence Being Promoted

The retained Phase B audit showed that the problematic low-tail behavior is visible in deterministic VB state/location objects, not only in posterior predictive samples. The most useful checks were:

- component decomposition from `theta.out`: USGS location, baseline without transfer, trend, seasonal aggregate, transfer `zeta`, source discrepancy blocks, and state RMS norm;
- final variational latent moments: `E[s_t]`, `E[s_t^2]`, `E[u_t]`, `E[1/u_t]`;
- pseudo-data moments passed to the Kalman layer: `FFF` and diagonal `QQQ`;
- iteration-level traces: ELBO, gamma, sigma, and `state_norm_sq / T`;
- cross-quantile ordering and negative/low-tail forecast checks.

The one-off audit script is now tracked as `scripts/audit_exdqlm_multivar_keep_vb_latents.R` so it can be rerun reproducibly and called by post-processing.

## Fit-Stage Changes

Active file: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`.

The fit stage now enables compact latent diagnostics by default:

- `DISC_W_LATENT_DIAG_ENABLED=TRUE`
- `DISC_W_LATENT_DIAG_WRITE_HEALTH_SUMMARY=TRUE`
- `DISC_W_LATENT_DIAG_WRITE_ITERATION_SUMMARY=FALSE`
- `DISC_W_LATENT_DIAG_WRITE_TOP_CELLS=FALSE`

This means future fits write a lightweight CSV by default without emitting the heavier per-source/member top-cell tables unless explicitly requested.

Default diagnostic output path:

```text
<fit output dir>/diagnostics/vb_iteration/fit_iteration_health_summary.csv
```

The compact health CSV includes one row per VB iteration with:

- `elbo`, `crit_elbo`, `sigma_exp`, `gamma_exp`;
- `state_norm_sq`, `state_norm_sq_per_T`, `crit_state_norm_sq`, `state_growth_ratio`;
- maxima/minima for historical and forecast `E[s]`, `E[s^2]`, `E[u]`, `E[1/u]`, `FFF`, and diagonal `QQQ`;
- health flags for extreme `E[1/u]`, tiny/nonpositive `E[u]`, nonpositive/extreme `QQQ`, extreme `FFF`, state growth, and nonfinite state norms.

The `FFF`/`QQQ` columns summarize the Kalman pseudo-data inputs used by that iteration. They should be interpreted as iteration input diagnostics rather than post-update final pseudo-data.

## Post-Stage Changes

Active file: `R/environmetrics/40_figures_multivar_only.R`.

The multivariate-only post workflow now calls:

```text
scripts/audit_exdqlm_multivar_keep_vb_latents.R
```

when `UNIFIED_POST_MULTIVAR_VB_LATENT_AUDIT` is not disabled. The output is written under:

```text
<post output dir>/vb_latent_component_audit/
```

The post workflow also writes:

```text
<post output dir>/multivar_vb_latent_audit_status.csv
```

with the audit exit status and log paths.

The promoted audit report produces:

- `vb_fit_iteration_health_summary.csv` when fit-stage health CSVs exist;
- `vb_fit_progress_from_logs.csv`;
- `vb_latent_pseudodata_cutoff_window.csv`;
- `vb_forecast_latent_pseudodata_window.csv`;
- `vb_component_decomposition_window.csv`;
- `vb_component_decomposition_long.csv`;
- `vb_component_layout_contract.csv`;
- `vb_component_diagnostic_summary.csv`;
- `vb_component_quantile_order_summary.csv`;
- `vb_component_latent_overlay.csv`;
- PNG traces for ELBO, gamma, sigma, `state_norm_sq_per_T`, latent moments, pseudo-data, component decompositions, source locations, and q05/q95 component-latent overlays.

The audit is non-strict by default so a plotting/reporting failure does not abort an otherwise complete post stage. Set `UNIFIED_POST_MULTIVAR_VB_LATENT_AUDIT_STRICT=TRUE` to make failures fatal.

## Diagnostic Use

For the next 20220511-style investigation, inspect in this order:

1. `multivar_vb_usgs_location_quantiles_cutoff_window.png` for deterministic cross-quantile behavior.
2. `vb_latent_component_audit/plots/components_mu_usgs_all_quantiles_*.png` and `components_decomposition_facets_*.png` for trend/season/transfer/discrepancy attribution.
3. `vb_latent_component_audit/plots/forecast_window_E_inv_u_*.png` and `iter_health_max_E_inv_u.png` for latent-scale amplification.
4. `vb_latent_component_audit/plots/state_norm_sq_per_T_from_logs.png` and `iter_health_state_norm_sq_per_T.png` for state drift.
5. `vb_component_diagnostic_summary.csv` and `vb_component_quantile_order_summary.csv` for compact failure localization.

## Remaining Work

These changes improve evidence capture and reproducibility; they do not change the statistical update itself. The remaining model-side diagnostic/fix sequence is:

1. Compare q05/q95 component decomposition against the healthy cutoffs and the 20220511 winner.
2. If the extreme tails still fail while state norms remain stable, run targeted latent ablations (`freeze`, `cap_e_inv_u`, `cap_e_u_and_e_inv_u`) only for suspect lanes.
3. If ablations implicate `u_t`, promote a principled stability policy for the GIG/latent update rather than only post-hoc capping.
4. If ablations do not implicate `u_t`, isolate transfer identifiability by holding or simplifying the transfer block for q05/q95 at the suspect cutoff.
5. Keep posterior predictive synthesis changes separate from this investigation; the deterministic `theta.out` diagnostics should be clean first.

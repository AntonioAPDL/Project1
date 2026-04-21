# Phase 5 NDLM Forecast-Window Covariance Prior Audit

Status: complete

## Scope

- Audited `10` authoritative HE2 multivariate NDLM rows (`N-M-T0` and `N-M-T1`) using the resolved source runs identified in Phase 2 and Phase 3.
- `N-U-T1` is intentionally out of scope for this phase because `ndlm_univar` uses the scalar `n0/S0` prior, not the multivariate forecast-window covariance prior audited here.

## Static Code Trace

- `stage_fit` forwards all five forecast-IW env vars (`c_factor`, `epsilon0`, `dof_offset`, `scale_mult`, `jitter`): `R/unified/stages/stage_fit.R:1480,1483,1488,1491,1494`.
- `ndlm_theory_constants()` reads all five into runtime constants: `R/unified/families/ndlm_main/00_constants.R:93,127,94,128,95,129,96,130,97,131`.
- The active anchor builder `ndlm_exact_forecast_prior_anchor()` uses only `c_factor`, `epsilon0`, and `jitter`: `R/unified/families/ndlm_main/08_vb_cavi_exact.R:164,1098,166,1099,170`.
- The implemented anchor formula is `nu0 = d_k + 1 + epsilon0` and `S0 = epsilon0 * c_factor * W_T_k + diag(jitter)`: `R/unified/families/ndlm_main/08_vb_cavi_exact.R:190,192`.
- `dof_offset` and `scale_mult` are parsed but have no active use-site in the theory-aligned fit loop: `dof_offset` anchor refs `R/unified/families/ndlm_main/08_vb_cavi_exact.R`: not found; `scale_mult` anchor refs `R/unified/families/ndlm_main/08_vb_cavi_exact.R`: not found.
- Saved runtime state exposes `forecast_prior` and `forecast_cov_diagnostics`, but it does not preserve `dof_offset` or `scale_mult`: anchor/save refs `R/unified/families/ndlm_main/08_vb_cavi_exact.R:1102,879`; save-state pack refs `R/unified/families/ndlm_main/06_save_state.R:33,35`.

## Headline Findings

- All `10` audited multivariate NDLM HE2 rows run with `implementation_mode=theory_aligned`; runtime modes: `{'theory_aligned': 10}`.
- All `10` audited rows use `kalman_backend=cpp` and `anchor_mode=terminal_Q_hist`; anchor counts: `{'terminal_Q_hist': 10}`.
- Runtime `epsilon0` falls back to `T` for all `10` rows because the config-level `epsilon` field is blank in the authoritative HE2 source configs.
- Explicit `dof_offset` is present in `1` row configs, explicit `scale_mult` in `1`, and explicit `jitter` in `1`; however, only `jitter` is used in the active anchor builder.
- Covariance diagnostics exist for all `10` rows, and fit-level contract/diagnostic YAML also exists for all `10` rows (`contract=10`, `fit_diag=10`).
- Lineage mix remains the same as earlier phases: `{'baseline_20260402': 9, 'ndlm_relaunch_20260411': 1}`.

## Interpretation

- The authoritative manuscript NDLM main rows are already using the theory-aligned NDLM engine, not a separate legacy NDLM fit engine.
- The active forecast-window covariance prior is inverse-Wishart-like and anchored to the terminal historical discount covariance `Q_T`, not to a free-standing `dof_offset/scale_mult` parameterization.
- In the current implementation, the active prior knobs are effectively `epsilon0`, `c_factor`, and `jitter`. Because `epsilon0` is blank in the audited configs, the runtime uses `epsilon0 = T`.
- `dof_offset` and `scale_mult` are exposed by the config surface and forwarded through `stage_fit`, but they are inert in the current theory-aligned NDLM main fit path.
- This means the current NDLM forecast-window prior contract is only partially implemented relative to the public config surface. That is the main Phase 5 discrepancy.

## Outputs

- CSV: [wishart_runtime_trace.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/wishart_runtime_trace.csv)

# exDQLM Keep/Drop Clarification

Date: 2026-05-20

## Purpose

This document is the Stage 3 clarification note for the forecast-period `drop` and `keep`
variants used in the current exDQLM workflow.

This note does not assume that older project notes are correct. Every statement below was checked
against:

1. the canonical manuscript source `main.tex`, and
2. the current implementation in `R/environmetrics/20_model_setup.R`.

## Sources checked directly

Primary theory:
- `/data/muscat_data/jaguir26/exDQLM---Ensemble/main.tex`
  - Model C (`drop`): lines 139-141
  - Model C-T (`keep`): lines 161-223

Current implementation:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R`
  - forecast mode switch: lines 208-214
  - `keep` branch: lines 226-270
  - `drop` branch: lines 271-273

Secondary context only:
- `docs/exdqlm_theory_source_map.md`
- `docs/exdqlm_sigma_gamma_equation_sheet.md`

## 1. Theory: what `drop` means

In the manuscript, Model C is the forecast-stage specification in which the transfer block is
removed during the forecast period. The forecast state is

\[
\beta_t =
\begin{bmatrix}
\theta_t \\
\delta_t^f
\end{bmatrix},
\]

with no transfer state retained. Ensemble observations are conditionally exAL with loadings applied
only to the baseline state and the relevant discrepancy block.

Theory anchor:
- `main.tex` lines 139-141

Interpretation:
- baseline state is retained
- forecast discrepancy blocks are retained
- transfer coordinates are not part of the forecast state

This is the intended mathematical contract for `drop`.

## 2. Theory: what `keep` means

In the manuscript, Model C-T is the forecast-stage specification in which the transfer block
remains active:

\[
\beta_t^{(s)} =
\begin{bmatrix}
\theta_t \\
\delta_t^{1:a_s} \\
\tau_t
\end{bmatrix},
\qquad
\tau_t =
\begin{bmatrix}
\zeta_t \\
\psi_t
\end{bmatrix}.
\]

The transition matrix keeps a dedicated transfer block

\[
G_t^{\mathrm{trans}} =
\begin{bmatrix}
\lambda & x_t^\top \\
0 & I
\end{bmatrix},
\]

so the transfer state continues evolving during forecast. The manuscript states that forecast
loadings include:

1. the baseline state,
2. the relevant discrepancy block,
3. the transfer contribution.

Theory anchors:
- `main.tex` lines 161-223

Interpretation:
- baseline state is retained
- forecast discrepancy blocks are retained
- transfer coordinates are retained
- the forecast state is strictly larger than the `drop` state

This is the intended mathematical contract for `keep`.

## 3. Current code: how the switch is implemented

The current implementation takes the mode from:

```r
forecast_transfer_mode <- tolower(trimws(Sys.getenv("UNIFIED_MULTIVAR_FORECAST_TRANSFER_MODE", "drop")))
```

and then sets:

```r
keep_transfer_forecast <- isTRUE(use_covariates) && ppx > 0L && identical(forecast_transfer_mode, "keep")
```

Code anchor:
- `R/environmetrics/20_model_setup.R` lines 208-214

So the live behavior is:
- `drop` is the default if nothing is set
- `keep` is only active when transfer covariates are enabled and the transfer block dimension is
  positive

## 4. Current code: the `drop` branch

In the `drop` branch:

```r
GG_list[[j]] <- matrix(GG_tsc, nrow = core_dim, ncol = core_dim)
FF_list[[j]] <- matrix(FF_tsc, nrow = core_dim, ncol = jj)
```

Code anchor:
- `R/environmetrics/20_model_setup.R` lines 271-273

Meaning:
- forecast transition only contains the core baseline + discrepancy state
- forecast observation loadings only refer to that core state
- transfer coordinates are absent from both `GG_list[[j]]` and `FF_list[[j]]`

This matches Model C.

## 5. Current code: the `keep` branch

In the `keep` branch the code expands the forecast state:

```r
state_dim <- core_dim + ppx
G_transfer <- as.matrix(bdiag(lambda, diag(px)))
```

Code anchor:
- `R/environmetrics/20_model_setup.R` lines 226-231

This does two things:

1. it appends `ppx = 1 + px` transfer coordinates to the forecast state
2. it creates a transfer transition block with one persistent `zeta` coordinate and `px`
   coefficient coordinates

When future covariates are available, the transition is made time-varying:

```r
GG_tt[core_dim + 1L, (core_dim + 2L):state_dim] <- as.numeric(X_seg[tt, , drop = TRUE])
```

Code anchor:
- `R/environmetrics/20_model_setup.R` lines 243-260

Meaning:
- the first transfer coordinate evolves like `zeta_t`
- the remaining transfer coordinates act like retained regression coefficients
- future covariates drive `zeta_t` through those retained coefficients

For the forecast observation loadings, the code appends:

```r
transfer_load <- rbind(rep(1, jj), matrix(0, nrow = px, ncol = jj))
FF_list[[j]] <- rbind(FF_tsc, transfer_load)
```

Code anchor:
- `R/environmetrics/20_model_setup.R` lines 267-269

Meaning:
- each active forecast source loads the retained transfer intercept-like state `zeta_t`
- the retained coefficient states `psi_t` are not directly measurement-loaded
- instead, the coefficient states affect the forecast path through the transfer transition block

## 6. What is confirmed

### Confirmed C1
`drop` and `keep` are distinct forecast-state models in both theory and code.

Evidence:
- manuscript has separate Model C and Model C-T sections
- current code has explicit `drop` and `keep` branches

### Confirmed C2
The current `drop` code matches the theory of removing the transfer block during forecast.

Evidence:
- no transfer coordinates are added to `GG_list` or `FF_list` in the `drop` branch

### Confirmed C3
The current `keep` code retains the transfer state during forecast.

Evidence:
- transfer coordinates are appended to the state
- transfer transition block is retained
- future covariates drive that retained transfer block

### Confirmed C4
The current `keep` code gives direct forecast loading only to `zeta_t`, not to the coefficient
states.

Evidence:
- the appended `transfer_load` is `[1; 0; ...; 0]`

This is a concrete current-code specialization and should be treated as part of the active model
contract.

## 7. What is not taken for granted

Older notes sometimes talk about `keep` and `drop` loosely as if they were only convenience labels.
That is not safe enough for this audit.

The direct checks above show that:
- `drop` changes the state dimension
- `keep` changes the state dimension
- `keep` changes both the forecast transition and forecast observation maps

So these are not only naming conventions; they are distinct model specifications in the forecast
stage.

## 8. Important interpretation note

The manuscript wording says that Model C-T forecast loadings include the transfer contribution.
The current implementation realizes that contribution through:

1. direct measurement loading of the retained `zeta_t` coordinate, and
2. transition-driven evolution of the retained coefficient coordinates

It does not directly measurement-load the retained coefficient states themselves.

That is not a contradiction with the current code path; it is a concrete implementation
specialization of the more general Model C-T description.

## 9. Stage 3 conclusion

For the current repository and active workflow:

- `drop` = forecast transfer omitted
- `keep` = forecast transfer retained through an explicit transfer state block
- the current `keep` implementation retains `zeta_t` directly in forecast loadings
- retained coefficient states influence forecast evolution through the transfer transition, not
  through direct measurement loadings

This clarification is now locked to the current implementation path and should be used as the
reference when auditing any `keep`/`drop` behavior going forward.

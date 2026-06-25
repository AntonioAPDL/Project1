# N-M-T1 Static Algorithm Contract

Date: 2026-06-25

## Purpose

This document records the static implementation contract for the multivariate
NDLM keep model (`N-M-T1`, `ndlm_main_keep`) used in the current HE2 manuscript
tables. It is intentionally limited to input bundles, model specification, and
algorithmic wiring. It does not describe any launch, relaunch, runtime-health,
or tuning experiment.

## Scope

The relevant comparison target is the authoritative multivariate exDQLM keep
model (`exAL-M-T1`, `exdqlm_multivar_keep`). The comparison is meaningful only
for shared design elements:

- frozen input bundle,
- cutoff and scoring window,
- transfer-retained keep structure,
- harmonic interpretation,
- engineered covariates and forecast products,
- article CRPS source wiring.

It is not a strict likelihood-only comparison under the current manuscript
sources, because the selected `N-M-T1` and `exAL-M-T1` rows have different
discount/prior settings.

## Confirmed NDLM Route

The active NDLM main workflow is:

1. `R/unified/stages/stage_fit.R`
   - requires run-scoped shared inputs for `run_ndlm_main`;
   - chooses `scripts/run_ndlm_main.R` when
     `models.ndlm_main.implementation_mode = theory_aligned`;
   - exports the run-local retros, forecast products, engineered covariates,
     transfer mode, discount factors, harmonics, Kalman backend, and forecast
     inverse-Wishart settings through `NDLM_*` environment variables.
2. `scripts/run_ndlm_main.R`
   - sources only `R/unified/families/ndlm_main/*`;
   - calls `unified_run_ndlm_main_theory(...)`.
3. `R/unified/families/ndlm_main/01_inputs.R`
   - reads the shared retros, NWS forecast, GloFAS forecast, and engineered
     covariate feature table;
   - keeps the `log1p` internal scale;
   - builds historical and forecast covariate matrices from the frozen run
     bundle.
4. `R/unified/families/ndlm_main/07_state_registry.R`
   - defines the multivariate keep state blocks, measurement loadings, discount
     matrix, lead-specific forecast states, and ragged forecast source activity.
5. `R/unified/families/ndlm_main/08_vb_cavi_exact.R`
   - performs Gaussian/Kalman filtering and smoothing updates;
   - anchors forecast covariance priors to the terminal historical discount
     recursion.

## State Definition

For a base seasonal/trend dimension
`q = 1 + 2 * number_of_harmonics`, and `p` engineered covariates, the historical
state in keep mode is

```text
alpha_t = (theta_t, zeta_t, psi_t, delta_glofas,t, delta_nws,t)
```

with dimensions:

| block | dimension | meaning |
| --- | ---: | --- |
| `theta_t` | `q` | shared river state: level/trend plus seasonal harmonics |
| `zeta_t` | `1` | retained transfer intercept |
| `psi_t` | `p` | retained transfer covariate coefficients |
| `delta_glofas,t` | `q` | GloFAS discrepancy state |
| `delta_nws,t` | `q` | NWS discrepancy state |

The historical dimension is therefore `q + (1 + p) + 2q`.

For lead `k` in the forecast window, the keep-mode forecast state retains
`theta` and the transfer block and includes only discrepancy blocks for forecast
sources active at that lead. This is why the forecast state dimension can be
ragged by lead.

## Measurement Loading Contract

The state registry builds historical observation rows as follows:

| observation | loading |
| --- | --- |
| USGS | `F_base` on `theta_t`, `1` on `zeta_t` |
| GloFAS | USGS loading plus `F_base` on `delta_glofas,t` |
| NWS | USGS loading plus `F_base` on `delta_nws,t` |

In the forecast window, the USGS synthesis location is built from the retained
shared state and transfer block. GloFAS and NWS forecast observations add their
lead-active discrepancy blocks when those products exist for the lead.

## Harmonic Contract

The canonical harmonic vector used by the workflow is:

```text
c(1, 2, 1 / 6.8068493)
```

The NDLM configuration stores actual harmonic values under
`models.ndlm_main.seasonality.harmonics`. The exDQLM configuration can store
enabled harmonic indices under
`models.exdqlm_multivar.structure.enabled_harmonic_indices`. Therefore
`enabled_harmonic_indices = c(1, 2, 3)` means the third canonical value
`1 / 6.8068493`; it does not mean a literal harmonic value of `3`.

The static validator normalizes both representations to actual harmonic values
before comparing them.

## Likelihood And Latent-Layer Boundary

`N-M-T1` is a normal/Gaussian multivariate dynamic linear model. It is not a
quantile-lane model. Consequently, the following exDQLM quantities are not
available and should not be debugged as missing NDLM fields:

- `s_t`,
- `u_t` or `v_t`,
- exAL `gamma`,
- the exAL sigma/gamma Laplace approximation,
- cross-quantile synthesis internals.

The NDLM path has Gaussian observation variance updates and Kalman/RTS state
updates instead.

## Static Validation Gate

The tracked validator is:

```bash
python3 scripts/validate_nmt1_static_parity.py \
  --output-dir reports/nmt1_static_parity_audit_20260625
```

It produces:

- authority rows for the manuscript table and retained-current exDQLM figure
  sources;
- input bundle inventory and pairwise hash/numeric-equivalence comparisons;
- specification field matrix and parity classification;
- harmonic normalization table;
- covariate/forecast static profiles;
- article CRPS table wiring check;
- NDLM algorithm source map and state-space contract tables.

The intended passing state is:

- zero hard input/table failures,
- zero semantic failures for transfer mode and normalized harmonics,
- documented differences for likelihood family, quantile structure, latent
  layer, discounts, and forecast covariance prior settings.


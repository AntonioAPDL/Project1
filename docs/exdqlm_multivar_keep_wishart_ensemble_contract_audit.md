# exDQLM Multivariate Keep Wishart/Ensemble Contract Audit

Date: 2026-05-20

## Scope

This document audits the object-shape and ordering contract for the active
Wishart/ensemble path used by the multivariate `exdqlm keep` runner. It covers
ensemble object shapes, source ordering, ragged forecast segment construction,
forecast-member bookkeeping, evolution covariance lists, and the R-to-C++
contract.

## Source Status

Primary implementation anchors:

- [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r)
- [R/disc_w/04_ensemble_bookkeeping.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/04_ensemble_bookkeeping.R)
- [R/disc_w/06_ensemble_spec.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/disc_w/06_ensemble_spec.R)
- [DISC_kalman_synth_transfer_forecast.cpp](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_kalman_synth_transfer_forecast.cpp)

The older [DISC_W_WORKFLOW.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/DISC_W_WORKFLOW.md)
is useful context, but it is anchored to `DISC_Optimal_Synth_Ranges_W.r`, not
the transfer-forecast runner. For this audit, it is a workflow map only.

## Ensemble Object Contract

The canonical ensemble helper says:

- `E$type == "disc_w_ensemble"`
- `E$data` is a list of numeric matrix-like objects
- rows are time/lead index
- columns are member index
- `E$J == length(E$data)`
- `E$num_mem[j] == ncol(E$data[[j]])`
- `E$ranges[j] == nrow(E$data[[j]])`

Implementation anchors:

- contract metadata: `R/disc_w/06_ensemble_spec.R:13-27`
- validation: `R/disc_w/06_ensemble_spec.R:33-86`
- construction: `R/disc_w/06_ensemble_spec.R:88-135`

The active runner builds the concrete ensemble bundle with
`disc_w_build_ensembles(glofas_forecast, nws_forecast)` at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1314-1319`. That helper
removes the first forecast column, preserves source order, and returns
`ensembles`, `J`, `num_mem`, `ranges`, and `mean_forecast` at
`R/disc_w/04_ensemble_bookkeeping.R:18-38`.

Confirmed source ordering:

1. `ensembles[[1]]` is GloFAS forecast members.
2. `ensembles[[2]]` is NWS forecast members.
3. No helper reverses source order at construction.

Important nuance: forecast segments later reverse horizon differences, but the
source list itself remains in original source order.

## Forecast-Member Bookkeeping

The active runner converts the per-source ensemble matrices into ragged horizon
segments with `disc_w_concat_horizon_segments(...)` at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2829-2862`.

The helper requires non-increasing row counts (`ranges`) and then works from the
shortest horizon back to the longest. For each output segment it:

1. selects the rows belonging to the segment-specific horizon interval,
2. column-binds all sources still active at that interval,
3. returns segments in increasing forecast-time order after the reverse walk.

The member observation matrix passed to C++ is then transposed:
`ensembles_forecast <- lapply(ensembles_forecast, t)` at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2993-2994`. Therefore:

- pre-concat source matrices: rows = lead, columns = member
- C++ segment matrices: rows = member-expanded observations, columns = segment lead

The validator confirms `ensembles_forecast[[seg]]` has shape
`sum(num_mem[1:expected_series]) x expected_h` at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2976-2983`.

## Forecast State and Member Expansion

For forecast segment `seg`:

- `expected_series = J - seg + 1`
- `expected_obs = sum(num_mem[1:expected_series])`
- `expected_state = p*(J - seg + 2) + ppx`

The R validator enforces these at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2961-2984`.

The compiled core repeats the same member expansion logic:

- `sub_num_mem <- num_mem[1:j]` in C++ indexing terms
- `obs_dim = sum(sub_num_mem)`
- source-level forecast means are repeated by member count through
  `repeat_vector(...)`
- source-level loading columns are expanded through `expand_FF(...)`

Code anchors:

- member expansion utilities: `DISC_kalman_synth_transfer_forecast.cpp:250-304`
- forecast filter setup: `DISC_kalman_synth_transfer_forecast.cpp:1212-1283`
- later forecast steps: `DISC_kalman_synth_transfer_forecast.cpp:1300-1350`

This confirms that `FFF_forecast`, `QQQ_forecast`, and `ensembles_forecast`
must be member-expanded objects, not source-level objects.

## Evolution Covariance / Wishart Contract

The runner initializes forecast evolution covariance lists as one SPD diagonal
matrix per segment lead:

```r
new.covs_list <- mapply(function(n, r) {
  replicate(r, diag(0.0001, n), simplify = "array")
}, n = dim_theta, r = r_vec, SIMPLIFY = FALSE)
```

Code anchor: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3178-3195`.

The state update passes `cur.covs_list` to C++ as `W_list_ens` at
`DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3670-3679`. The C++ forecast
filter treats each slice as an additive evolution covariance:

\[
R = W_{\text{list},t} + G C_{t-1} G^\top.
\]

Code anchors:

- first forecast step: `DISC_kalman_synth_transfer_forecast.cpp:1235-1263`
- later forecast steps: `DISC_kalman_synth_transfer_forecast.cpp:1300-1315`

The C++ ELBO contribution uses an inverse-Wishart expectation from the stored
mean covariance matrix:

- precision helper: `DISC_kalman_synth_transfer_forecast.cpp:52-61`
- log determinant helper: `DISC_kalman_synth_transfer_forecast.cpp:63-80`
- smoothing/ELBO usage: `DISC_kalman_synth_transfer_forecast.cpp:1506-1523`,
  `1632-1648`

The R-side covariance update computes an innovation-based matrix `ww`, blends it
with a prior forecast covariance block, and forces SPD:

- update loop: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3795-3870`
- optional blending: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3873-3886`
- SPD projection helpers: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3071-3112`

The current contract is therefore:

1. `cur.covs_list[[seg]][,,lead]` is the forecast evolution covariance mean.
2. C++ uses it directly as additive process covariance in filtering.
3. C++ approximates inverse-Wishart precision/logdet terms from that mean and
   `forecast_cov_epsilon`.
4. R updates the mean covariance deterministically from smoothed forecast state
   moments and SPD projection.

## R-to-C++ Contract Table

| R object | C++ argument | Shape | Semantic role |
|---|---|---|---|
| `GG` | `GG` | `total_state x total_state x TT_sub` | historical transition |
| `FF` | `FF` | `total_state x (J+1) x TT_sub` | historical loading |
| `FFF` | `ex_f` | `(J+1) x TT_sub` | historical pseudo-data offset |
| `QQQ` | `ex_q` | `(J+1) x (J+1) x TT_sub` | historical pseudo-observation covariance |
| `GG_list[[seg]]` | `GG_list_ens[index]` | `state_dim x state_dim x h` | forecast transition, possibly time-varying |
| `FF_list[[seg]]` | `FF_list_ens[index]` | `state_dim x active_sources` | source-level forecast loading |
| `FFF_forecast[[seg]]` | `ex_f_list_ens[index]` | `obs_dim x h` | member-level forecast pseudo-data offset |
| `QQQ_forecast[[seg]]` | `ex_q_list_ens[index]` | `obs_dim x obs_dim x h` | member-level pseudo-observation covariance |
| `ensembles_forecast[[seg]]` | `y_list_ens[index]` | `obs_dim x h` | member-level forecast observations |
| `cur.covs_list[[seg]]` | `W_list_ens[index]` | `state_dim x state_dim x h` | forecast evolution covariance mean |
| `num_mem` | `num_mem` | length `J` | member counts per source |
| `ranges` | `k_ens` | length `J` | cumulative/ragged horizon endpoints |

## Confirmed

1. Ensemble rows/columns are explicit and validated: rows are time/lead, columns
   are members before ragged segmentation.
2. Source ordering is preserved at construction; ragged segmentation changes
   horizon grouping, not source identity.
3. Forecast member objects entering C++ are member-expanded and dimension-checked
   before the update.
4. The transfer forecast C++ path allocates forecast state arrays with `+ppx`,
   so the retained transfer tail is part of forecast filtering and smoothing.
5. Forecast covariance slices are treated as evolution covariance means in
   filtering and as inverse-Wishart means for ELBO terms.

## Questionable / To Audit Further

1. The name "Wishart" hides a mixed contract: R stores covariance means, C++ uses
   inverse-Wishart expected precision/logdet functions, and R applies deterministic
   SPD projection. This is not automatically wrong, but runtime evidence must
   check whether `cur.covs_list` eigenvalues become too small or too large.
2. `disc_w_force_spd(...)` can repair non-SPD matrices by jitter or eigenvalue
   flooring. That protects execution, but it can also mask unstable upstream
   pseudo-data or state updates. Runtime reports should count and quantify SPD
   repairs where possible.
3. The segment ordering is subtle. Any external diagnostic that reads
   `FFF_forecast`, `QQQ_forecast`, `sm_ens`, or `sC_ens` must use the same
   `ranges_per -> rev(...)` convention or it will compare the wrong lead block.

# NDLM Ragged-Horizon Contract (C1)

Date: 2026-02-20

## Goal
Define a theory-consistent forecast Model C contract when forecasters have unequal horizons `K_j`.

## Definitions
- Let active forecasters be `j=1,...,J_f`.
- Each source has horizon `K_j >= 0`.
- Forecast lead index domain is `k = 1,...,K_max`, where `K_max = max_j K_j`.
- Active set by lead:
  - `A_k = { j : k <= K_j }`.
- Active source count by lead:
  - `J_k = |A_k|`.

For state block size `q`:
- Transdimensional state dimension at lead `k`:
  - `p_k = q * (1 + J_k)`.

## Canonical formulation used in implementation
Use fixed-dimension internals with exact transdimensional equivalence.

### Full state
- Define full forecast state `\tilde\beta_k \in R^{p_full}` with
  - `p_full = q * (1 + J_f)`.
- Partition:
  - baseline block `\theta_k` (`q` dims),
  - discrepancy blocks `\delta_k^j` (`q` dims each, `j=1..J_f`).

### Selection/projection maps
- Define selector matrix `S_k \in R^{p_k x p_full}` that keeps baseline + active discrepancy blocks (`j \in A_k`).
- Active state is `\beta_k = S_k \tilde\beta_k`.
- Injection map is `E_k = S_k^T`.

### Dynamics
- Full transition and covariance are block-diagonal in forecast phase.
- Inactive blocks (`j \notin A_k`) are deterministic-zero in forecast likelihood calculations:
  - process innovation contribution masked to zero,
  - measurement loadings for inactive blocks are zero.

## Equivalence claim (fixed-dim vs true transdimensional)
A true transdimensional model evolves `\beta_k \in R^{p_k}`.
The fixed-dim embedding is equivalent when:
1. active blocks follow the same transition/innovation law,
2. inactive blocks are projected out of observation equations,
3. inactive-block innovations are zero-mass in the effective forecast recursion.

Under these conditions, filtering/smoothing marginals for all active components match the transdimensional model after applying `S_k`.

## Practical contract invariants
1. `K_vec = (K_1,...,K_{J_f})` stored in NDLM state metadata.
2. `K_max = max(K_vec)` and `A_k` computable for every lead.
3. Forecast segment outputs (`sm_ens`, `sC_ens`) are emitted by active-set segments, not forced shared-K copies.
4. `standard_forecast_errors` must be ragged-consistent with active-set structure (no forced min-horizon clipping).
5. Contract checks must validate per-segment/per-lead consistency rather than `K=min(...)`.

## Two-source expected shape (NWS vs GloFAS)
For `K_nws = 10`, `K_glofas = 28`:
- `K_vec = (28, 10)` after ordering by non-increasing horizon.
- Segment 1 (both active): leads `1..10`, width `10`.
- Segment 2 (only long-horizon source active): leads `11..28`, width `18`.
- `sm_ens` widths expected `[10, 18]` (not `[10,10]`).

# Q-02 Root Cause Analysis (Univar exDQLM)

- generated_at_utc: `2026-02-22T21:37:12Z`
- baseline_run: `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221`
- evidence_table: `repro/docs/q02_univar_20260222T212607Z/relative_convergence_counterfactual.csv`

## Hypotheses Tested

1. H1 (supported): convergence contract is absolute-only and scale-mismatched for extreme tails.
2. H2 (not supported as primary): numerical guard/refreeze instability causes stalls.
3. H3 (not supported as primary): data wiring defect specific to q=01/q=99.

## Evidence

- q=01/q=99 reach `max_iter=800` with monotone ELBO improvement and stable small per-step *relative* changes, while absolute deltas remain above fixed `1e-6` thresholds.
- Counterfactual check shows relative criteria are satisfiable early for tails under scale-aware thresholds; this indicates the contract (not data wiring) is the limiting factor.
- No guard-trigger signature appears as the dominant terminal cause in tail runs; both complete with valid outputs and pass stage-level checks.

## Supported Root Cause

The univar convergence policy used absolute delta thresholds only (`elbo/state/sigma/gamma`), which is not scale-aware for extreme quantiles where state norms and gamma magnitudes are large. This causes deterministic `max_iter_reached` despite stable relative progress.

## Fix Strategy (Q-02)

1. Add explicit relative tolerances to convergence policy resolution and stage-fit env wiring.
2. Evaluate each convergence metric via `(abs_delta < abs_tol) OR (rel_delta < rel_tol)`.
3. Preserve existing absolute thresholds and objective guard behavior for already-convergent quantiles.
4. Add deterministic tests for policy resolution and metric-delta behavior to prevent regression.

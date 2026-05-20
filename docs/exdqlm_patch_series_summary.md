# exDQLM Patch Series Summary

This note is the operator-facing summary for the `2026-05-20` sigma/gamma and
Laplace patch series. It is intentionally short and implementation-focused.

## Scope

The patch series changes the active sigma/gamma update path in:

- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- `R/disc_w/10_gamsig_laplace.R`

It does **not** redesign the base exDQLM likelihood or the `keep`/`drop`
forecast distinction.

## Main behavior changes

### 1. Near-zero gamma mode search

The active path now supports explicit split mode search near `gamma = 0`:

- search the negative branch,
- search the positive branch,
- compare the resulting transformed objectives,
- keep the better branch explicitly.

This aligns the active implementation more closely with the manuscript guidance
for the nonsmooth region around `gamma = 0`.

### 2. Exact pure-u moments

The active path now uses exact closed forms for:

- `E[sigma]`
- `E[1 / sigma]`
- `E[log(sigma)]`

These are no longer routed through the generic second-order Delta helper.

### 3. Canonical covariance naming

The active path now exposes the Laplace covariance as:

- `Sigma.LD`

For compatibility, it also still returns:

- `Hess.LD`

but `Hess.LD` should now be treated as a compatibility alias only.

### 4. Explicit fallback typing

The active path now distinguishes successful Laplace results from fallback
objects through explicit metadata.

Key fields:

- `laplace_status`
- `laplace_status_message`
- `laplace_covariance_type`
- `laplace_ridge`
- `laplace_ridge_regularized`
- `laplace_mode_search`
- `laplace_hessian_source`
- `laplace_is_fallback`

### 5. Ridge covariance diagnostics

The covariance builder now:

1. tries the exact precision inverse first,
2. only adds ridge regularization if needed,
3. records whether ridge regularization was actually used.

That means the active path now distinguishes:

- `laplace_precision_inverse`
- `ridge_regularized_precision_inverse`
- fallback covariance types such as `seed_diagonal`

## How to read the new fields

### `laplace_status`

Expected values in the active path:

- `ok`
- `al_sigma_only`
- `sigma_only_fallback`
- `guard_fallback`

Interpretation:

- `ok`: full Laplace path succeeded
- `al_sigma_only`: asymmetric-Laplace special case used the sigma-only path by design
- `sigma_only_fallback`: optimization stayed alive via the sigma-only rescue path
- `guard_fallback`: a non-Laplace guard fallback object was returned

### `laplace_covariance_type`

Expected values:

- `laplace_precision_inverse`
- `ridge_regularized_precision_inverse`
- `seed_diagonal`
- failure-type markers if covariance construction fails upstream

Interpretation:

- `laplace_precision_inverse`: clean Laplace covariance
- `ridge_regularized_precision_inverse`: stabilized covariance; usable, but not pure
- `seed_diagonal`: fallback-only covariance, not a true Laplace posterior covariance

### `laplace_mode_search`

Typical values:

- `full`
- `split_negative`
- `split_positive`
- `sigma_only:<reason>`
- `guard_fallback`
- `al_sigma_only`

This is intended as an audit trace of the path that produced the returned mode.

## Stale duplicate path

The older duplicate implementation in:

- `R/environmetrics/20_model_setup.R`

is retained as historical material only. It is now explicitly annotated as a
stale duplicate path and should not be treated as the source of truth for the
current workflow.

## Practical guidance

For ongoing or future audits:

- prefer `Sigma.LD` over `Hess.LD`,
- treat any `laplace_is_fallback = TRUE` result as a diagnostic event,
- treat `laplace_ridge_regularized = TRUE` as a stabilization event worth
  monitoring,
- use `laplace_mode_search` to understand whether near-zero branch splitting was
  engaged.

# N-M-T1 Broad Screen Runbook

This runbook freezes the preparation contract for the broad `N-M-T1`
(`ndlm_main_keep`) screen requested on 2026-06-25.

## Scope

The screen targets only the Gaussian multivariate NDLM keep model used for the
manuscript label `N-M-T1`. It is not a quantile model and therefore has no
`s_t`, `u_t`, `gamma`, or cross-quantile synthesis layer. Each matrix row is one
one-core Gaussian fit for one cutoff and one discount/forecast-covariance prior
specification.

The source inputs are the run-local shared snapshots audited by
`scripts/validate_nmt1_static_parity.py`:

`reports/nmt1_static_parity_audit_20260625/authority_rows.csv`

The broad-screen builder rewrites generated configs to those frozen source
snapshots for parameters, retrospectives, NWS, GloFAS, PPT, SOIL, and PCA
inputs. USGS has a deliberately different contract:

- the cutoff-truncated run-local `inputs/shared/usgs/usgs_daily.csv` is retained
  in the manifest as an audit snapshot only;
- `inputs.fit.usgs_cache_path` is preserved from the source resolved config and
  must point to the full recovered USGS daily cache used by post-stage truth and
  forecast-window CRPS.

This distinction is launch blocking. A previous first launch failed because the
screen builder incorrectly rewrote `inputs.fit.usgs_cache_path` to the
cutoff-truncated run-local snapshot. The fit stage was numerically healthy, but
`40_figures_ndlm_only.R` correctly stopped in post with
`no realized USGS rows at/after <cutoff + 1>`.

## Grid

The grid has 48 discount cases and 6 epsilon values:

- `df_t`: `0.99999`, `0.9999999`
- `df_s1`: `0.99999`, `0.9999`
- `df_s2`: `0.99999`, `0.9999`
- `df_s67`: `0.99999`
- `df_discrep`: `0.999`, `0.9999`, `0.99995`
- `lambda`: `0.97`
- `df_trans`: `0.9999999`, `0.99999`
- `df_covs`: `0.99999999`
- `c_factor`: `1`
- `epsilon`: `1`, `30`, `60`, `90`, `180`, `365`
- `max_iter`: `100`

This creates 288 specifications per cutoff and 1,440 total run rows across the
five cutoffs.

## Safety

The generated launch metadata is intentionally conservative:

- at most `3` active NDLM rows at once;
- at most `1` active `20221225` row at once;
- one computational core per row;
- continue on failed rows, because failed specifications are informative;
- skip compare-bundle construction during the queue;
- run through `scripts/run_unified_with_cleanup.sh`, so `.RData`/`.rda` files
  are removed after post and on failure.

## Preparation

```bash
python3 scripts/build_he2_ndlm_main_keep_broad_screen_configs.py --reset-status

python3 scripts/validate_he2_ndlm_main_keep_broad_screen_prelaunch.py
```

The validator checks the matrix size, one-core concurrency, harmonic convention,
discount/epsilon grid, frozen input hashes, and the post truth contract. For
each cutoff/spec it reads the configured GloFAS forecast dates and requires
finite USGS truth rows in `inputs.fit.usgs_cache_path` through the full forecast
window. This is intended to catch cutoff-truncated USGS truth wiring before any
model run is launched.

Default runtime root:

```text
/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_ndlm_main_keep_broad_screen_20260625
```

The builder writes the exact launch command to:

```text
/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_ndlm_main_keep_broad_screen_20260625/control/ndlm_main_keep_broad_screen/LAUNCH_READY.md
```

## Post-Run Evaluation

After the queue finishes or reaches a useful checkpoint:

```bash
python3 scripts/evaluate_he2_ndlm_main_keep_broad_screen.py
```

The evaluator ranks eligible rows by cutoff, compares mean forecast-window CRPS
against the current authoritative `N-M-T1` row, and flags any run that did not
clean its `.RData`/`.rda` files.

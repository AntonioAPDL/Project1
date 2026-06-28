# exDQLM Univariate Discount-Screening Plan

Date: 2026-06-28

## Purpose

Prepare a controlled screening campaign for the `exdqlm_univar` / `exAL-U-T1`
model across all five publication cutoffs. The current univariate exDQLM row is
valid and reproducible, but its forecast-window CRPS is not competitive enough
to treat its current discount-factor specification as final without a targeted
screen.

This plan is intentionally launch-ready but not a launch record. No production
campaigns should be stopped, overwritten, or relaunched from this document alone.

## Current Repository State

At the time of this plan, the three active repositories were clean and pushed:

| repo | branch state | HEAD |
|---|---:|---:|
| workflow repo | `main...origin/main` | `53bbaa4` |
| revised article repo | `main...origin/main` | `cc840cb` |
| corrections repo | `main...origin/main` | `85e17c7` |

## Current Univariate Baseline

Publication manifest:

`reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`

Article copy:

`Evironmetrics---REVISED-DOC-Corrected-2/artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv`

Current `exAL-U-T1` / `exdqlm_univar` baseline:

| cutoff | CRPS | horizon days | n valid | df_t | df_s1 | df_s2 | df_s67 | lambda | df_trans | df_covs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20210123 | 1.5937588394 | 28 | 28 | 0.99999999 | 0.99999 | 0.99999 | 0.99999 | 0.97 | 0.9999999 | 0.9999999 |
| 20211112 | 1.3720641646 | 28 | 28 | 0.99999999 | 0.99999 | 0.99999 | 0.99999 | 0.97 | 0.9999999 | 0.9999999 |
| 20211221 | 2.5629546886 | 28 | 28 | 0.99999999 | 0.99999 | 0.99999 | 0.99999 | 0.97 | 0.9999999 | 0.9999999 |
| 20220511 | 1.2667703182 | 28 | 28 | 0.99999999 | 0.99999 | 0.99999 | 0.99999 | 0.97 | 0.9999999 | 0.9999999 |
| 20221225 | 3.5952775390 | 28 | 28 | 0.99999999 | 0.99999 | 0.99999 | 0.99999 | 0.97 | 0.9999999 | 0.9999999 |

Current publication relaunch batch:

`config/he2_relaunch_batches/univar_al_exal_publication_relaunch_20260603.yaml`

Current publication relaunch template:

`config/he2_bayesian_publication_relaunch_univar_al_exal_20260603.template.yaml`

The older April univariate feature-covariate relaunch used:

| field | value |
|---|---:|
| `df_t` | 0.99999999 |
| `df_s1` | 0.9999 |
| `df_s2` | 0.9999 |
| `df_s67` | 0.9999 |
| `lambda` | 0.97 |
| `df_trans` | 0.9999999 |
| `df_covs` | 0.99999 |

That older setting is useful as a nearby comparison point because the June
publication relaunch tightened the seasonal and covariance discounts.

## Model-Specific Contract

The univariate exDQLM model is not the multivariate keep model.

For this screen:

- operative family: `exdqlm_univar`
- manuscript label: `exAL-U-T1`
- likelihood mode: `exal`
- implementation mode: `legacy_bridge`
- seven quantile fits per cutoff
- synthesis is performed from the seven fitted quantile lanes in the post stage

The univariate exDQLM screen should vary:

- `df_t`
- `df_s1`
- `df_s2`
- `df_s67`
- `lambda`, only if explicitly approved
- `df_trans`
- `df_covs`

The univariate exDQLM screen should not include:

- `df_discrep`, because there is no multivariate discrepancy block;
- `epsilon`, because the multivariate forecast inverse-Wishart prior is not the
  operative univariate tuning knob;
- `c_factor`, for the same reason.

If a future experiment introduces a univariate forecast-covariance prior knob,
it should be documented as a separate model/implementation experiment, not mixed
into this discount-factor screen.

## Input-Bundle Contract

The screen must use the same corrected shared input bundle lineage as the
current publication rows:

| field | required value |
|---|---|
| bundle root | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510` |
| bundle run id | `20260510_publication_shared_r01` |
| data start | `1987-05-29` |
| cutoffs | `20210123`, `20211112`, `20211221`, `20220511`, `20221225` |
| deterministic climate / covariates | inherit current publication bundle contract |
| post stage | same univariate-only post route used by the June 3 publication relaunch |

No candidate is promotable unless its resolved config and run-time shared-input
audit match this contract.

## Recommended Screening Design

Use a staged screen rather than a full Cartesian explosion.

### Stage A: Nearby Discount Screen

Goal: determine whether the current poor rows are mainly caused by the June
seasonal/covariance tightening.

Recommended candidates:

| spec id | df_t | df_s1 | df_s2 | df_s67 | lambda | df_trans | df_covs | reason |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| u01_current | 0.99999999 | 0.99999 | 0.99999 | 0.99999 | 0.97 | 0.9999999 | 0.9999999 | current publication baseline |
| u02_april | 0.99999999 | 0.9999 | 0.9999 | 0.9999 | 0.97 | 0.9999999 | 0.99999 | older featurecov relaunch neighborhood |
| u03_mid_season | 0.99999999 | 0.99995 | 0.99995 | 0.99995 | 0.97 | 0.9999999 | 0.999999 | middle between April and June |
| u04_adapt_season | 0.99999999 | 0.9995 | 0.9995 | 0.9999 | 0.97 | 0.9999999 | 0.99999 | more seasonal adaptation, keep long seasonal slower |
| u05_adapt_allseason | 0.99999999 | 0.9995 | 0.9995 | 0.9995 | 0.97 | 0.9999999 | 0.99999 | broad seasonal adaptation check |
| u06_adapt_trend | 0.999999 | 0.9999 | 0.9999 | 0.9999 | 0.97 | 0.9999999 | 0.99999 | trend adaptation plus April-like seasonal |
| u07_adapt_transfer | 0.99999999 | 0.9999 | 0.9999 | 0.9999 | 0.97 | 0.999999 | 0.99999 | transfer adaptation check |
| u08_adapt_covs | 0.99999999 | 0.9999 | 0.9999 | 0.9999 | 0.97 | 0.9999999 | 0.9999 | covariate-coefficient adaptation check |

Stage A total planned fits:

- `8 specs x 5 cutoffs x 7 quantiles = 280 quantile fits`

### Stage B: Expansion Only Where Stage A Improves

Only expand around cutoff/spec neighborhoods that beat the current publication
CRPS and remain visually/diagnostically healthy.

Candidate expansions:

- slightly lower `df_s1/df_s2` around the best Stage A seasonal pair;
- slightly lower `df_covs` if transfer-covariate adaptation helps;
- optional `lambda` screen around `0.95`, `0.97`, `0.99`, only after the
  discount screen shows that transfer memory is a plausible bottleneck.

Do not expand all cutoffs blindly. Expand by cutoff because the current CRPS
weakness is cutoff-dependent.

## Runtime and Cleanup Policy

Use a new isolated runtime root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_discount_screen_20260628`

Recommended launch policy:

- cleanup `.RData` after post by default;
- retain compact post outputs, CRPS tables, figures, logs, and matrix manifests;
- allow failed rows to remain failed and record them as information;
- use `ordinary_max_concurrent = 4` at most if the server is otherwise quiet;
- use `ordinary_max_concurrent = 3` if another heavy campaign is active;
- one row means one cutoff/spec with seven quantile workers;
- set `fit_parallel_workers = 7` and single-thread BLAS/OpenMP per quantile;
- set `max_iter = 100` unless a specific candidate needs a larger cap;
- keep current gamma/sigma robust initialization and objective guard defaults.

Before launch:

- confirm free disk space;
- confirm no stale queue controller is already attached to the new matrix dir;
- dry-run or prelaunch-validate generated configs;
- check all resolved configs have `run_exdqlm_univar = true` and all unrelated
  families disabled.

## Required Implementation Pieces

The current generic publication relaunch stack can run one spec per cutoff. A
screen needs explicit matrix generation for multiple specs. The cleanest
implementation is:

1. Add a small univariate grid builder, modeled on the existing multivariate
   grid builder but restricted to `models.exdqlm_univar.state_evolution`.
2. Add a focused prelaunch validator that checks:
   - matrix row count;
   - generated config count;
   - all five cutoffs;
   - seven active quantiles;
   - no `df_discrep`, `epsilon`, or `c_factor` in the univariate spec table;
   - same publication shared input bundle root and `1987-05-29` data start;
   - cleanup enabled;
   - one-thread runtime controls.
3. Add a compact health/CRPS summarizer that reports:
   - done/running/failed counts by cutoff and spec;
   - current iteration, ELBO, sigma, gamma, and state-norm information where
     available;
   - CRPS versus current publication baseline for finished specs.
4. Keep runtime evidence under `reports/` and the isolated runtime root.
5. Promote only after:
   - all seven quantile lanes for the winning cutoff/spec complete;
   - post-stage synthesis and CRPS are present;
   - forecast-window synthesis plots look coherent;
   - table-generation code is updated from a machine-readable winner manifest.

## Promotion Rules

A screened spec may replace the current authoritative `exAL-U-T1` row for a
cutoff only if:

1. it improves forecast-window CRPS against the current baseline for that cutoff;
2. the run uses the same corrected input bundle and post contract;
3. the synthesis figure is visually coherent;
4. quantile crossing is not materially worse than the current row;
5. logs do not show pathological gamma/sigma/state behavior;
6. the selected spec is frozen in a tracked manifest;
7. article and corrections tables are regenerated from that manifest rather than
   manually patched.

If only some cutoffs improve, promote only those cutoffs. The authoritative
manifest can be mixed by cutoff, as with the current multivariate keep winners.

## Validation Commands After Scaffolding

Expected prelaunch checks after the builder/validator are implemented:

```bash
python3 -m py_compile \
  scripts/build_he2_exdqlm_univar_discount_screen_configs.py \
  scripts/validate_he2_exdqlm_univar_discount_screen_prelaunch.py \
  scripts/summarize_he2_exdqlm_univar_discount_screen.py

python3 scripts/build_he2_exdqlm_univar_discount_screen_configs.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_univar_discount_screen_20260628.template.yaml

python3 scripts/validate_he2_exdqlm_univar_discount_screen_prelaunch.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_discount_screen_20260628/control/univar_discount_screen
```

Launch only after those checks pass and the user approves the actual grid.

## Immediate Recommendation

We are ready to prepare the screening scaffold, but we should not launch until
the grid is explicitly approved.

The recommended first grid is Stage A above. It is large enough to test the most
plausible reason the current univariate row is weak, but small enough to finish
and interpret without creating another unwieldy production campaign.

## Approved 2026-06-28 Screen

The user-approved screen replaces Stage A with five explicit state-evolution
specifications. It remains a univariate exDQLM screen: no `df_discrep`,
`epsilon`, or `c_factor` are introduced.

| spec | df_t | df_s1 | df_s2 | df_s67 | lambda | df_trans | df_covs |
|---|---:|---:|---:|---:|---:|---:|---:|
| `u01` | 0.99999 | 0.99999 | 0.99999 | 0.99999 | 0.97 | 0.9999999 | 0.9999999 |
| `u02` | 0.99999 | 0.99995 | 0.99995 | 0.99999 | 0.97 | 0.9999999 | 0.9999999 |
| `u03` | 0.99999 | 0.99995 | 0.99995 | 0.99995 | 0.97 | 0.9999999 | 0.9999999 |
| `u04` | 0.99999 | 0.9995 | 0.9995 | 0.9999 | 0.97 | 0.9999999 | 0.9999999 |
| `u05` | 0.99999 | 0.9995 | 0.9995 | 0.9999 | 0.97 | 0.99999 | 0.9999999 |

Planned run size:

- five specifications;
- five cutoffs;
- 25 row-level runs;
- seven quantile fits per row;
- 175 total quantile fits.

Concurrency:

- `ordinary_max_concurrent = 4`;
- `fit.parallel.workers = 7`;
- maximum active quantile workers: `28`.

Cleanup:

- clean `.RData`/`.rda`/`.rds` files under the isolated screen root before
  launch;
- run the queue with cleanup enabled so full posterior files are removed after
  post;
- keep compact CRPS, logs, figures, manifests, and status summaries.

Tracked implementation files:

- `config/he2_bayesian_publication_relaunch_exdqlm_univar_discount_screen_20260628.template.yaml`
- `scripts/build_he2_exdqlm_univar_discount_screen_configs.py`
- `scripts/validate_he2_exdqlm_univar_discount_screen_prelaunch.py`
- `scripts/summarize_he2_exdqlm_univar_discount_screen.py`


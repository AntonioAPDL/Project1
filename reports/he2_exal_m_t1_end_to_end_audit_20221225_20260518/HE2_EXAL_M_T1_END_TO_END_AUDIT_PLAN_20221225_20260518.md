# HE2 exAL-M-T1 End-to-End Audit Plan

## Scope
This audit is for the representative `exAL-M-T1` run at cutoff `2022-12-25`:

- family: `exAL-M-T1`
- model id: `exdqlm_multivar_keep`
- representative run root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep`

This audit assumes the core fitting algorithm is likely correct unless proven otherwise. The main objective is to locate where the object/scale/transform contract breaks between:

1. raw inputs
2. shared bundle ingress
3. fit-time state/parameter objects
4. post-stage reconstruction
5. exported quantiles/figures
6. human interpretation of those outputs

## Current Evidence
We already know the following:

1. A real post-stage scale bug existed in the active multivariate smoke-fast path.
2. That bug was fixed for this representative cutoff by making the active post path respect `analysis_scale_post_internal = log1p_cms` rather than a stale `log_log1p` contract.
3. After that fix, the bizarre explosion in forecast-window quantiles decreased sharply, which proves the earlier post transform bug was real.
4. Even after the scale fix, the row-level location diagnostics still look structurally wrong.
5. That structural issue appears not only in the forecast window but also in:
   - dry-period history
   - wet-period history
   - last 200 observations up to cutoff
6. This means the issue is likely upstream of synthesis and not merely a plotting problem in the forecast window.
7. The most likely failure classes are now:
   - wrong object being plotted/interpreted
   - pre-fit transformation mismatch
   - stage-to-stage scale contract mismatch
   - stale semantic assumption about how exAL location parameters relate to quantile dynamics

## Audit Question
The master question is:

> Where does the contract break between the mathematically intended USGS target quantity and the quantity actually exported/plotted in the current workflow?

## Working Hypotheses
### H1. Wrong object hypothesis
We are plotting an internal exAL location-like parameter, or a mean-corrected internal quantity, when what we actually want for interpretation is a predictive quantile curve or another target-level quantity.

Why this matters:
- it would explain why the history slices already look wrong
- it would explain why the curves remain distorted after fixing the extra post transform bug
- it would explain why the plotted rows do not visually behave like the quantile dynamics we expect to compare to observed USGS

### H2. Pre-fit transform hypothesis
The fit may be receiving data that is already transformed inconsistently, for example mixing:
- raw `cms`
- `log1p(cms)`
- `log(log1p(cms))`

Why this matters:
- a pre-fit issue would contaminate both historical and forecast diagnostics
- it would produce consistent distortion even if post is mathematically correct

### H3. Stage contract mismatch hypothesis
Different workflow stages may be using different assumptions for:
- analysis scale
- storage scale
- plotting scale
- inverse transform behavior

Why this matters:
- we already found one real example of this
- there may be additional remaining contract mismatches

### H4. Response/object comparability hypothesis
Observed USGS may be plotted directly on the target scale, while the model-side diagnostic object is not actually the same semantic quantity.

Why this matters:
- the curves could look bad even if both are numerically valid, simply because they are not supposed to be compared directly

### H5. Input bundle lineage mismatch hypothesis
A transformed or adapted bundle object may differ from the canonical expected lineage.

Why this matters:
- if one adapter writes the wrong transformed field or wrong date alignment, everything downstream can still run while remaining wrong

## Audit Design Principles
1. Audit one representative cutoff deeply before touching all cutoffs.
2. Separate mathematical object semantics from plotting concerns.
3. Record both intended and actual scale for every important object.
4. Do not collapse history and forecast logic unless we have proven they use the same semantic target.
5. Use small, explicit decomposition tables before large figure rewrites.
6. Preserve reproducibility: every diagnostic should have a script, explicit inputs, and a stable output path.
7. Treat local progress notes as scratch work and keep them out of Git.

## Audit Workstreams
### Workstream A. Canonical scale contract map
Goal:
- define the intended scale of each important object end to end

For each object record:
- path or environment object name
- stage
- intended scale
- actual scale observed
- transform applied to produce it
- transform assumed downstream
- whether that assumption is verified or inferred

Objects in scope:
- raw USGS source
- shared-bundle USGS input
- retros adapters
- `Y` response used in fit
- GloFAS/NWS retros
- GloFAS/NWS forecast adapters
- climate covariate adapters
- fit-state objects
- gamma/sigma objects
- multivariate history location summary
- multivariate forecast location summary
- predictive draw caches
- synthesized history/forecast samples
- exported quantile CSVs
- PNG/PDF review figures

Acceptance criteria:
- no object remains with “unknown scale” in the representative path
- every transform is explicitly justified or flagged

### Workstream B. Input and pre-fit lineage audit
Goal:
- verify the exact data contract before fitting

Checks:
- raw -> shared bundle transformation for USGS
- response vector values around a few reference dates
- exact scale of `Y`
- exact scale of GloFAS/NWS retros and forecasts used by the run
- blended `PPT` / `SOIL` contract
- updated GDPC/PCA contract
- date alignment from `1987-05-29` to cutoff
- historical/forecast split around `2022-12-25`

Acceptance criteria:
- one row-wise lineage sample exists for key dates
- input values can be reconciled across raw, adapter, bundle, and fit ingress

### Workstream C. Object semantics decomposition
Goal:
- determine what quantity is actually being plotted and what quantity should be plotted

For selected quantiles and dates, decompose:
- projected state mean `xb`
- discrepancy/transfer contribution
- any exAL shift term
- constructed `mu` passed toward predictive generation
- `sigma`, `gamma`, `p0`
- row-level predictive samples from `rexal()`
- row-level predictive empirical quantiles
- synthesized quantiles after `synthesize_samples()`

Reference quantiles:
- `q20`
- `q35`
- `q50`
- `q65`
- `q80`

Reference dates:
- a calm dry-period date
- a wet-period peak date
- a late-history date near cutoff
- one or two forecast dates after cutoff

Acceptance criteria:
- we can state precisely which object corresponds to:
  - latent location
  - exAL location parameter
  - row-level predictive quantile behavior
  - synthesized predictive quantile behavior
- we can say whether the current plot is semantically correct or not

### Workstream D. Historical-window sanity panels
Goal:
- localize whether the issue already exists in history and in which object family

Historical windows:
- dry: `2012-01-01` to `2016-12-31`
- wet: `2017-01-01` to `2019-12-31`
- last 200 observations to cutoff: `2022-06-09` to `2022-12-25`

For each window compare:
- observed USGS
- row-level location means
- central-only row-level location means
- if needed, row-level predictive quantiles
- if needed, synthesized historical quantiles

Acceptance criteria:
- we know whether the historical distortion is confined to tails or also affects the central rows
- we know whether the issue begins before synthesis

### Workstream E. Post-stage contract audit
Goal:
- prove the active post stage is mathematically consistent after the scale fix

Checks:
- active post runner path
- scale guard outputs
- cache naming and cache reuse behavior
- history vs forecast object builders
- quantile export builders
- figure builders
- no stale `log_log1p` assumptions remain in active code paths for this family

Acceptance criteria:
- every active multivariate keep post transformation used by the representative cutoff is accounted for
- any remaining stale assumptions are either patched or isolated

### Workstream F. Decision and relaunch gate
Goal:
- decide whether the next change should be:
  - post-only patch
  - input-prep patch and representative relaunch
  - broader rerun plan

Decision rules:
- if the issue is semantic-only: patch diagnostics/figures first
- if the issue is pre-fit transformation: patch data prep and relaunch representative cutoff
- if the issue is mixed-stage scale contract: patch stage contracts and rerun post first, then reassess fit
- if multiple failures are confirmed: fix in causal order, not all at once

## Required Deliverables
1. A scale-contract inventory for the representative run
2. A pre-fit lineage check for reference dates
3. An object-semantics decomposition report
4. Historical-slice panels for dry, wet, and last200 windows
5. A post-stage contract verification report
6. A final diagnosis memo with recommended next action

## Testing and Validation Matrix
### Required checks for every workstream
- file-existence checks
- date-alignment checks
- scale-consistency checks
- object-shape checks
- cache provenance checks
- compare-before/after checks where patches occur

### Hard validation gates
- no unexplained transform survives in the representative path
- no “semantic quantity” remains undefined
- no patch is accepted without a before/after numeric check and a figure-level check

## Progress Tracking
Versioned documents in this folder define the audit scope and status.
Live work logs, scratch notes, intermediate hypotheses, and iterative checklists live in:
- `repro/audit_local/exal_m_t1_end_to_end_audit_20221225_20260518/`

That local workspace is intentionally Git-ignored.

## Current Status
- representative cutoff chosen: done
- post-scale bug found: done
- post-scale bug fixed for representative cutoff: done
- history-slice review infrastructure: done
- history-only renderer bug fixed: done
- issue confirmed in history slices: done
- scale contract audit: pending
- pre-fit lineage audit: pending
- object semantics decomposition: pending
- final diagnosis memo: pending

## Immediate Next Steps
1. Build the representative scale-contract inventory
2. Build the pre-fit lineage table around a small set of dates
3. Build the one-date/one-quantile decomposition for `q20`, `q50`, and `q80`
4. Use that decomposition to decide whether the plotted location curves are semantically the right object

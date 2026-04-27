# exAL-M-T1 Discount Grid Exact-Input Fix

## Why the earlier discount probes were confounded

The earlier `exAL-M-T1` discount-factor probe batches were **not** pure discount-only variants of the current HE-table `exAL-M-T1` runs.

The main issue was in `data_prep_shared`:

- the builder preserved the selected source run's raw history and raw forecast paths
- but `data_prep_shared` then **re-materialized** forecast-window deterministic-climate PPT/SOIL futures and `covariate_features.csv`
- that changed the forecast-window transfer inputs relative to the HE-table source runs

So the earlier probe-vs-HE comparison changed:

- the discount-factor block
- forecast-window `PPT` / `SOIL`
- deterministic-climate future files
- `covariate_features.csv`

That is why the prior probe results could not be interpreted as a strict discount-factor sensitivity study against the HE-table `exAL-M-T1` baseline.

## What was changed

The exact-input relaunch fixes that by preserving the selected HE source run's `inputs/shared` tree directly.

Implementation changes:

- added `inputs.shared.exact_source_snapshot_root` to the unified config surface
- added an early exact-snapshot branch to `data_prep_shared`
- the new branch copies the selected HE source `inputs/shared` tree into the new run root before validation
- no deterministic-climate or engineered-feature regeneration occurs after that copy

One reproducibility exception is intentional:

- some selected HE source runs never preserved `inputs/shared/usgs/usgs_daily.csv`
- for those rows, `data_prep_shared` supplements **only** `inputs/shared/usgs/usgs_daily.csv` from `inputs.fit.usgs_cache_path`
- this keeps strict local post scoring reproducible without changing the HE source run's forecast-window covariate inputs

## New campaign

- Template:
  `config/multimodel_v8_exalm_t1_discount_grid_exact_20260424.template.yaml`
- Artifact root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_exalm_t1_discount_grid_exact_20260424`
- Matrix dir:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_exalm_t1_discount_grid_exact_20260424/control/exalm_t1_discount_grid_exact_v1`
- Generated configs:
  `config/unified_runs_exalm_t1_discount_grid_exact_20260424/`

## Validation outcome

Passed prelaunch validation:

- summary json:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_exalm_t1_discount_grid_exact_20260424/control/prelaunch_validation_20260424T225705Z/prelaunch_validation_summary.json`

What the validator proved:

- builder emitted `45` configs / `45` matrix rows
- every generated config stayed on the selected HE source scientific contract
- the only intended scientific change was the `state_evolution` discount block
- representative `data_prep_shared` smoke runs reproduced the selected source `inputs/shared` snapshot recursively
- when the source snapshot lacked a run-local USGS truth CSV, the only extra file was the supplemented `inputs/shared/usgs/usgs_daily.csv`

## Launch readiness

Scaffolding is built and ready.

Launch command:

```bash
bash scripts/run_multimodel_v8_exalm_t1_discount_grid.sh \
  --config /data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_exalm_t1_discount_grid_exact_20260424.template.yaml \
  --launch
```

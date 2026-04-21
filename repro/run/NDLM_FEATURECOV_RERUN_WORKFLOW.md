# NDLM Featurecov Rerun Workflow

Last updated: 2026-04-21

## Purpose

Launch the corrected NDLM-only rerun under the shared featurecov and deterministic-climate contract documented by the parity audit.

## Final Status

- complete
- authoritative campaign state:
  - [matrix_status.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/matrix_status.csv)
  - [queue.log](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/queue.log)
- final result:
  - `15 / 15` target rows passed
  - `0` failed
  - controller completed cleanly with `exit_code=0`

## Main Surfaces

- Template:
  [multimodel_v8_ndlm_featurecov_rerun.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_ndlm_featurecov_rerun.template.yaml)
- Builder:
  [build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py)
- Validator:
  [validate_ndlm_featurecov_rerun_prelaunch.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/validate_ndlm_featurecov_rerun_prelaunch.py)
- Launcher:
  [launch_multimodel_v8_ndlm_featurecov_rerun.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/launch_multimodel_v8_ndlm_featurecov_rerun.py)

## Current Corrected Scope

- `15` rows total
- families:
  - `ndlm_main_keep`
  - `ndlm_main_drop`
  - `ndlm_univar_keep`
- cutoffs:
  - `20210123`
  - `20211112`
  - `20211221`
  - `20220511`
  - `20221225`

## Build Only

```bash
python3 scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py \
  --config config/multimodel_v8_ndlm_featurecov_rerun.template.yaml
```

## Prelaunch Validation

```bash
python3 scripts/validate_ndlm_featurecov_rerun_prelaunch.py \
  --config config/multimodel_v8_ndlm_featurecov_rerun.template.yaml
```

Current validated evidence:

- [prelaunch_validation_summary.json](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/prelaunch_validation_20260421T045415Z/prelaunch_validation_summary.json)

## Launch

```bash
python3 scripts/launch_multimodel_v8_ndlm_featurecov_rerun.py \
  --template config/multimodel_v8_ndlm_featurecov_rerun.template.yaml
```

This launch path:

- rebuilds the matrix
- reruns prelaunch validation unless `--skip-validate` is used
- starts the queue controller as a detached background process
- records:
  - `controller_state/controller.pid`
  - `controller_state/last_launch.json`

## Monitor

```bash
tail -f /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/queue.log

python3 scripts/check_multimodel_v8_matrix_health.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1 \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420
```

## Notes

- The original pilot-rerun concept was superseded by a stronger prelaunch gate:
  - NDLM prior-path regression tests
  - builder regression tests
  - `data_prep_shared` + `fit` + `post` smoke runs for all three NDLM families
- A live post-stage contract bug was fixed in `R/unified/stages/stage_post.R` after the first queue replay:
  - `multivar_output_suffix` is now initialized unconditionally so NDLM-only post runs cannot reference an undefined exDQLM-only variable
- Both formerly failing live rows were replayed cleanly through `report` before the queue was resumed.
- The queue completed cleanly at `2026-04-21T11:09:10Z`; archived failed attempts remain in the run root for auditability but are not part of the authoritative `15`-row matrix state.

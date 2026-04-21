# NDLM Featurecov Rerun Launch Summary

Date: 2026-04-21  
Status: complete after two root-cause fixes

## Launch Result

- Matrix dir:
  [ndlm_featurecov_v1](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1)
- Launch metadata:
  [last_launch.json](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/controller_state/last_launch.json)
- Queue log:
  [queue.log](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/queue.log)

## Prelaunch Gate

The launch used the corrected prelaunch validation:

- [prelaunch_validation_summary.json](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/prelaunch_validation_20260421T045415Z/prelaunch_validation_summary.json)

That validation passed:

- matrix build (`15` configs)
- Python regression tests
- R regression tests
- `data_prep_shared` + `fit` + `post` smoke runs for all three NDLM families

## Launch-Time Root Fixes

The first live launch attempt revealed one builder bug:

- blank source `usgs_cache_path` values were being normalized to the repo root
- that caused a strict `data_prep_shared` failure for the first `20210123 / ndlm_main_keep` row

The fix was applied by:

- treating blank path strings as missing in the rerun builder
- freezing a campaign-level fallback `inputs.fit.usgs_cache_path`
- tightening the validator so the USGS cache path must be a real file

The failed pre-fix run directory was archived, not reused.

The second live launch attempt cleared `data_prep_shared`, but then exposed one shared post-stage contract bug:

- `stage_post.R` unconditionally exported `UNIFIED_EXDQLM_MULTIVAR_OUTPUT_SUFFIX`
- that variable had only been initialized inside the exDQLM-multivar branch
- NDLM-only post runs therefore failed with `object 'multivar_output_suffix' not found`

That second issue was fixed by initializing `multivar_output_suffix` unconditionally and by strengthening the validator to require full `post` smoke success for all three NDLM families.

## Replay Proof

The two formerly failing live rows were replayed from clean directories and both now pass end to end:

- [run_manifest.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/runs/multimodel_20210123_v8_ndlm_featurecov_v1_ndlm_main_keep/run_manifest.yaml)
- [run_manifest.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/runs/multimodel_20210123_v8_ndlm_featurecov_v1_ndlm_main_drop/run_manifest.yaml)
- [source_map.txt](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/runs/multimodel_20210123_v8_ndlm_featurecov_v1_ndlm_main_keep/inputs/shared/source_map.txt)

Current proof state:

- `data_prep_shared = pass`
- `fit = pass`
- `post = pass`
- `validate = pass`
- `report = pass`
- deterministic-climate artifacts materialized
- `covariate_features.csv` materialized
- local USGS truth CSV resolved and copied into the run-scoped shared inputs

## Final Completion Proof

The corrected rerun finished cleanly after those fixes:

- authoritative matrix status:
  [matrix_status.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/matrix_status.csv)
- final queue completion:
  [queue.log](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/queue.log)

Final campaign result:

- `15 / 15` target rows passed
- `0` failed
- all `5 / 5` cutoffs closed
- all `3 / 3` NDLM families closed
- controller completed with `exit_code=0`

# HE2 exdqlm_multivar_keep Shared Relaunch Validation Status

Date: 2026-05-16

## Decision

- status: `VALIDATED_NO_LAUNCH`
- launch posture: `READY_TO_SCHEDULE_RERUN`
- scope: all-cutoff `exdqlm_multivar_keep` shared relaunch preparation
- execution posture: no relaunch started in this step

## What passed

- shared relaunch contract was rebuilt and documented
- corrected shared bundle contract was rebuilt and documented
- shared-spec builder dry-run passed with `5` selected rows and `5` generated configs
- focused relaunch/manifest/contract unit suite passed: `45/45`
- shared-input validation passed for all `5` cutoff smoke runs and the family smoke run
- representative execution smoke passed for the hard case:
  - cutoff: `20210123`
  - quantile: `q50`
  - shared q50 stabilization layer active
  - `gamsig_update_iters=18`
  - `min_update_iters=6`
  - `frozen=false` at terminal preflight
  - `guard_count=0`
  - `Sampling finished: 34.689 seconds`

## Key evidence

Shared-spec validator root:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_20260516T220923Z`

Representative smoke logs:

- fit wrapper stdout:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_20260516T220923Z/fit_smoke_exdqlm_multivar_keep_20210123_qsubset.stdout.log`
- q50 fit log:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_20260516T220923Z/smoke_runs/fit_quantile/exdqlm_multivar_keep/20210123/fit_smoke_exdqlm_multivar_keep_20210123_qsubset/fit/exdqlm_multivar/keep/q=50/logs/fit.log`
- q50 sampling diagnostics:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_20260516T220923Z/smoke_runs/fit_quantile/exdqlm_multivar_keep/20210123/fit_smoke_exdqlm_multivar_keep_20210123_qsubset/fit/exdqlm_multivar/keep/q=50/logs/sampling_diagnostics.log`

## Important nuance

The Python prelaunch-validator wrapper did not write its final `prelaunch_validation_summary.json` during this session, even though the substantive validation steps completed successfully.

What we observed directly:

- all shared-input smoke checks completed cleanly
- the representative `20210123 q50` fit smoke completed the `fit` stage cleanly
- the terminal q50 preflight passed with `guard_count=0`, `frozen=false`, and `update_iters=18`
- sampling completed end to end

So the validation evidence is sufficient to treat this no-launch package as structurally validated and ready for scheduling, while still documenting the missing wrapper summary as a tooling issue rather than a model/input failure.

## Practical conclusion

We can now treat the shared rerun contract as the correct launch candidate for the next full `exdqlm_multivar_keep` relaunch:

1. shared corrected bundles
2. shared `epsilon=360.0`
3. shared `c_factor=1.0`
4. shared discount set `set08`
5. shared q50 stabilization layer

This package is prepared and validated, but it remains intentionally **not launched** in this step.

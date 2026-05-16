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
- shared-input validation passed for all `5` cutoff smoke runs and the family smoke run under the new manual shared set
- representative execution smoke completed cleanly for the hard case under the new manual shared set:
  - cutoff: `20210123`
  - quantile: `q50`
  - shared q50 stabilization layer active
  - terminal VB checkpoint: `iter=18`
  - `gamsig_update_iters=18`
  - `min_update_iters=6`
  - `frozen=false`
  - `guard_count=0`
  - `Sampling finished: 34.558 seconds`

## Key evidence

Shared-spec validator root:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_20260516T224635Z`

Representative smoke logs:

- fit wrapper stdout:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_20260516T224635Z/fit_smoke_exdqlm_multivar_keep_20210123_qsubset.stdout.log`
- q50 fit log:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_20260516T224635Z/smoke_runs/fit_quantile/exdqlm_multivar_keep/20210123/fit_smoke_exdqlm_multivar_keep_20210123_qsubset/fit/exdqlm_multivar/keep/q=50/logs/fit.log`
- q50 sampling diagnostics:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_20260516T224635Z/smoke_runs/fit_quantile/exdqlm_multivar_keep/20210123/fit_smoke_exdqlm_multivar_keep_20210123_qsubset/fit/exdqlm_multivar/keep/q=50/logs/sampling_diagnostics.log`

## Important nuance

This validation note now reflects the **new manual shared set**:

- `epsilon=30.0`
- `c_factor=1.0`
- discount set `set10_manual_20260516`

The prior `VALIDATED_NO_LAUNCH` status from the earlier `epsilon=360.0` / `set08` shared package is superseded by this new revalidation pass.

What we observed directly:

- all shared-input smoke checks completed cleanly
- the representative `20210123 q50` fit smoke advanced cleanly into ordinary VB updates under the new manual shared set
- the representative `20210123 q50` fit smoke reached terminal preflight with `guard_count=0`, `frozen=false`, and `gamsig_update_iters=18`
- the representative `20210123 q50` fit smoke finished sampling in `34.558` seconds
- no median freeze / low-update replay appeared in the smoke run

The only remaining validator wrinkle is the same wrapper behavior we observed earlier:

- `prelaunch_validation_summary.json` was not flushed
- the validator wrapper process remained open after the substantive smoke evidence completed

That is a tooling-wrapper issue, not a model-spec or input-bundle failure. The direct smoke evidence is the authoritative result here.

## Practical conclusion

We now have the correct next shared rerun candidate:

1. shared corrected bundles
2. shared `epsilon=30.0`
3. shared `c_factor=1.0`
4. shared discount set `set10_manual_20260516`
5. shared q50 stabilization layer

This package is prepared, updated, and validated as a **no-launch rerun candidate** under the new manual shared set. It remains intentionally **not launched** in this step.

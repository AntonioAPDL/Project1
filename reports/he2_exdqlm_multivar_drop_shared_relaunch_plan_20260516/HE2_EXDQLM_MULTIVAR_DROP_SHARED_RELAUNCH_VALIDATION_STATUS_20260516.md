# HE2 exdqlm_multivar_drop Shared Relaunch Validation Status

Date: 2026-05-16

## Decision

- status: `VALIDATED_NO_LAUNCH`
- launch posture: `READY_TO_LAUNCH_WHEN_SCHEDULED`
- scope: all-cutoff `exdqlm_multivar_drop` twin package prepared from the approved `keep` shared relaunch contract
- execution posture: no relaunch started in this step

## What passed

- shared relaunch contract was rebuilt and documented
- drop twin builder dry-run passed with `5` selected rows and `5` generated configs
- focused package/alignment tests passed: `6/6`
- keep-vs-drop alignment audit passed on the exact final package:
  - all bundle fields aligned: `true`
  - all shared spec fields aligned: `true`
- exact-final-batch prelaunch replay produced successful bundle/data-prep smokes for all five cutoffs:
  - `20210123.stdout.log`: `Unified run complete.`
  - `20211112.stdout.log`: `Unified run complete.`
  - `20211221.stdout.log`: `Unified run complete.`
  - `20220511.stdout.log`: `Unified run complete.`
  - `20221225.stdout.log`: `Unified run complete.`
- exact-final-batch family smoke completed:
  - `exdqlm_multivar_drop.stdout.log`: `Unified run complete.`
- exact-final-batch sensitive q50 replay completed under the shared state-freeze path:
  - cutoff: `20210123`
  - quantile: `q50`
  - terminal VB iter: `18`
  - `gamsig_update_iters=18`
  - `guard_count=0`
  - `frozen=false`
  - terminal preflight: `passed`
  - sampling: `finished`
  - sampling time: `33.828s`

## Important nuance

The exact-final-batch validator wrapper did not emit its top-level `prelaunch_validation_summary.json` before it was stopped. This is an orchestration/wrapper issue, not a scientific or input-lineage failure.

The direct evidence above is from the exact final validation root and confirms that:

1. the final batch used the corrected shared bundles
2. the final batch used the mirrored keep shared spec unchanged where intended
3. the hard-case q50 path cleared terminal VB and sampling on the final drop package

Because the substantive gates passed on the exact final batch, the package is treated as launch-ready in a no-launch posture.

## Remaining caveat

- automated wrapper summary artifact is absent for the final replay root
- no scientific, bundle, or spec blocker remains documented in the evidence set
- launch was intentionally not started in this step

## Key evidence

- alignment audit: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exdqlm_multivar_drop_shared_relaunch_plan_20260516/keep_drop_sharedspec_alignment.json`
- final validator root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_20260517T013216Z`
- q50 fit log: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_20260517T013216Z/smoke_runs/fit_quantile/exdqlm_multivar_drop/20210123/fit_smoke_exdqlm_multivar_drop_20210123_qsubset/fit/q=50/logs/fit.log`
- q50 sampling diagnostics: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_20260517T013216Z/smoke_runs/fit_quantile/exdqlm_multivar_drop/20210123/fit_smoke_exdqlm_multivar_drop_20210123_qsubset/fit/q=50/logs/sampling_diagnostics.log`

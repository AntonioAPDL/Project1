# HE2 exdqlm_multivar_keep Rerun Validation Status

Date: 2026-05-16

## Decision

- status: `BLOCKED`
- launch posture: `DO NOT LAUNCH`
- scope: all-cutoff `exdqlm_multivar_keep` rerun preparation

## What passed

- publication-winning exdqlm spec freeze was rebuilt and documented
- corrected shared bundle contract was rebuilt and documented
- no-launch builder dry-run passed with `5` selected rows and `5` generated configs
- focused relaunch/manifest/contract unit suite passed: `41/41`

## What blocked promotion

The representative execution smoke uncovered a real median-path instability before we launched anything.

Blocked case:

- cutoff: `20210123`
- quantile: `q50`
- validator root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_rerun_20260516/control/prelaunch_validation_20260516T214307Z`
- evidence log:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_rerun_20260516/control/prelaunch_validation_20260516T214307Z/smoke_runs/fit_quantile/exdqlm_multivar_keep/20210123/fit_smoke_exdqlm_multivar_keep_20210123_qsubset/fit/exdqlm_multivar/keep/q=50/logs/fit.log`

Observed execution shape at capture time:

- `state_guard_iter=8`
- `freeze_until_iter=18`
- `iter=15`
- `gamsig_update_iters=2`
- `min_update_iters=6`
- median state guard re-froze the run and prevented normal update accumulation

## Interpretation

This is the key result from the no-launch prep:

- the rerun package is correctly wired to the updated bundles and publication-winning exdqlm row specs
- but the publication-spec-only rerun contract is not yet safe to relaunch
- the `q50` stabilization problem is not limited to the already rerun cutoffs; it also appears in the representative `20210123` smoke when we remove the earlier recovery-layer adjustments

## Practical conclusion

We should **not** launch the all-cutoff `exdqlm_multivar_keep` rerun as currently specified.

The right next step is to design the exdqlm rerun spec as a two-layer contract:

1. publication-winning structural row spec
   - cutoff-specific `epsilon`
   - cutoff-specific discount factors
   - `c_factor=1.0`
2. explicit rerun stabilization layer for `q50` where needed
   - documented and tested, not implicit

Until that is done, this rerun package should be treated as prepared-but-blocked.

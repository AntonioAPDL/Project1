# HE2 exDQLM Multivar Drop q50 Repair Promotion

Date: 2026-06-02

Scope: promote the proven `20211112 q50` repair from an isolated diagnostic row into the authoritative all-cutoff `exdqlm_multivar_drop` / `exAL-M-T0` relaunch workflow.

## Decision

The active all-cutoff drop package must use the repaired q50 terminal-guard and stabilization policy. The older current-code package rooted at:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_20260602`

is retained only as failure context. Its `20211112 q50` row could pass ordinary finite-stage checks until terminal sampling produced pathological synthesis scale. The isolated repair documented in:

`docs/he2_exdqlm_multivar_drop_20211112_q50_repair_20260602.md`

passed fit, post, validate, and report with the same scientific spec and canonical input bundle.

## Promoted q50 Contract

Single source of truth:

`scripts/he2_exdqlm_multivar_drop_q50_policy.py`

Promoted values:

| setting | value |
|---|---:|
| `freeze_target` | `states` |
| `terminal_sampling_guard.mode` | `fail_fast` |
| `terminal_sampling_guard.min_guard_count` | `1` |
| `terminal_sampling_guard.max_guard_lag_iters` | `0` |
| `terminal_sampling_guard.require_frozen` | `true` |
| `median_state_hold_after_guard_iters` | `10` |
| `median_state_blend_alpha` | `1.0` |
| `median_cov_blend_alpha` | `1.0` |
| `median_max_abs_gamma_step` | `0.075` |
| `median_max_abs_log_sigma_step` | `0.15` |

This policy is now consumed by:

- `scripts/build_he2_exdqlm_multivar_drop_current_relaunch.py`
- `scripts/build_he2_exdqlm_multivar_drop_20211112_q50_repair.py`
- `scripts/build_he2_exdqlm_multivar_drop_shared_relaunch_plan.py`
- `scripts/validate_he2_exdqlm_multivar_drop_current_prelaunch.py`

The checked-in shared-spec batch also carries the same values:

`config/he2_relaunch_batches/exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.yaml`

## Authoritative Relaunch Root

Fresh clean all-cutoff root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602`

This root should be built from a clean working tree after the promotion commit is pushed. It should be the source for the final `exAL-M-T0` publication benchmark row unless a later validation failure supersedes it.

The package keeps the scientific contract unchanged:

- canonical input bundle: `20260510_publication_shared_r01`
- start date: `1987-05-29`
- transform policy: `log1p_only`
- likelihood: `exal`
- transfer mode: `drop`
- model structure: trend plus harmonics `1,2,3`
- transfer covariates: `PPT`, `SOIL`, `PCA` with lags `1,2,3`, squares, and `PPT_x_SOIL`
- forecast covariance prior: `epsilon=30`, `c_factor=1`
- discount factors: shared high-discount `exAL-M-T0` values from the checked-in batch
- VB maximum iterations: `100`
- resources: two cutoff rows at a time, seven quantile workers per row, maximum 14 active quantile workers
- cleanup: `scripts/run_unified_with_cleanup.sh` removes retained `.RData/.rda` after post

## Reproducibility

Build and validate:

```bash
python3 scripts/build_he2_exdqlm_multivar_drop_current_relaunch.py
python3 scripts/validate_he2_exdqlm_multivar_drop_current_prelaunch.py
python3 -m unittest \
  tests.python.test_he2_exdqlm_multivar_drop_current_relaunch \
  tests.python.test_he2_exdqlm_multivar_drop_sharedspec_package \
  tests.python.test_he2_exdqlm_multivar_drop_shared_relaunch_plan \
  tests.python.test_he2_exdqlm_multivar_drop_q50_repair \
  tests.python.test_launch_he2_exdqlm_drop_after_al_keep \
  -v
```

Launch directly from the generated matrix:

```bash
bash /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602/control/publication_relaunch_matrix/launch_current_drop.sh
```

Guarded launch after the AL keep queue:

```bash
python3 scripts/launch_he2_exdqlm_drop_after_al_keep.py --poll-seconds 300
```

The guarded launcher now targets tmux session:

`he2_exal_drop_q50repair_20260602`

and writes its handoff status under the repaired relaunch root.

## Validation Gate

Before publication promotion, require:

1. prelaunch validator reports zero failures;
2. all five cutoff rows reach `fit/post/validate/report=pass`;
3. `20211112 q50` health remains at the repaired scale, not the old failed scale;
4. all rows write CRPS tables, posterior trace/parameter figures, synthesis figures, and article-output manifests;
5. no `.RData/.rda` remains under the run root after post cleanup;
6. the publication manifest and parity gate are rebuilt from this repaired root.

If any row fails, treat that row as a targeted diagnostic problem. Do not revert to the old current-code root.

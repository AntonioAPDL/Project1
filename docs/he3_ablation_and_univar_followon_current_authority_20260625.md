# HE3 Ablation and Follow-On Figure/Univariate Current-Authority Plan

Timestamp: 2026-06-25.

This note freezes the implementation plan and launch evidence for the current-authority HE3
ablation refresh and the deferred figure/univariate follow-on work. It follows the user's
instruction to assume the recent article visual review is acceptable, skip any publication
archive DOI step unless a final DOI exists, remove retained multivariate keep `.RData`, run the
HE3 ablation with no `.RData` retention, and only after HE3 schedule any required follow-on
reruns. The requested fifth item is intentionally out of scope here.

## Completed Disk Cleanup

The retained multivariate keep `.RData` cleanup was scoped to:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_authoritative_rdata_retention_current_20260623`

Evidence is untracked under:

`reports/rdata_cleanup_20260625_retained_multivar_keep/`

The cleanup removed 35 `.RData`/`.rda` files totaling 278,009,074,839 bytes
(`258.92 GiB`). `/data` moved from `670G used / 200G available` to
`411G used / 459G available`. No active NDLM broad-screen runtime root was touched.

## Current HE3 Source Authority

HE3 now reads its source rows from the current HE2 publication manifest rather than the stale
June 8 source table. The generated source table is:

`config/he3_exdqlm_ablation_current_authority_20260625_best_by_cutoff_long.csv`

The five `exAL-M-T1` source rows are:

| Cutoff | Source label | Source run | Mean CRPS |
|---|---|---|---:|
| 2021-01-23 | `c04_eps365` | `multimodel_20210123_v8_he2grid_c04_eps365_exdqlm_multivar_keep` | 0.1397088548478634 |
| 2021-11-12 | `c04_eps365` | `multimodel_20211112_v8_he2grid_c04_eps365_exdqlm_multivar_keep` | 0.0472363501409808 |
| 2021-12-21 | `he2partial20260623` | `multimodel_20211221_v8_he2partial20260623_exdqlm_multivar_keep` | 0.2604466008954305 |
| 2022-05-11 | `he2partial20260623` | `multimodel_20220511_v8_he2partial20260623_exdqlm_multivar_keep` | 0.0227281783203013 |
| 2022-12-25 | `he2partial20260623` | `multimodel_20221225_v8_he2partial20260623_exdqlm_multivar_keep` | 0.5380554847458453 |

The current HE3 template is:

`config/multimodel_v8_he3_exdqlm_ablation_current_authority_20260625.template.yaml`

The matrix root is:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_current_authority_20260625/control/he3_exdqlm_ablation_current_authority_v1`

The runtime root is:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_current_authority_20260625`

The matrix has 30 rows: five reused full references and 25 launched ablation rows. The launched
rows are `noTrend`, `noTF`, `noH1`, `noH2`, and `noH3` for each cutoff.

## Guard and Retention Policy

The previous HE3 failure mode was tied to a generated config where
`state_guard_start_iter=1000` while the VB budget was only 100 iterations. The current template
explicitly overrides the generated HE3 gamma/sigma policy to:

- `state_guard_enabled: true`
- `state_guard_start_iter: 20`
- `state_guard_refreeze_iters: 20`
- `state_hold_after_guard_iters: 20`
- `state_norm_max_ratio: 25`
- `state_norm_abs_cap: 1.0e6`
- `state_norm_abs_cap_scale: per_time`
- `state_norm_ratio_ref_floor: 0.1`
- `median_state_blend_alpha: 0.5`
- `median_cov_blend_alpha: 0.5`

The reference floor is required because the relative state-growth guard is a
ratio diagnostic; when the previous accepted state norm is near zero, an
otherwise bounded long-history state can produce a meaningless ratio-only
failure. The median-only blend settings damp the q50 recovery path without
changing non-median quantile updates. The hard finite guard and absolute cap
remain unchanged. See
`docs/he3_current_authority_noTF_guard_loop_audit_20260626.md` for the 2021-12-21
noTF/q50 evidence that motivated this current-authority template repair.

The production queue uses `scripts/run_unified_with_cleanup.sh`, which sets
`CLEANUP_RDATA_AFTER_POST=1`. Generated HE3 launch configs also record
`he3_ablation.cleanup_rdata_after_post: true`; validation now fails if that metadata is absent.

## Validation Gates

The following checks passed before launch:

```bash
python3 -m py_compile \
  scripts/build_he3_exdqlm_ablation_matrix.py \
  scripts/build_he3_authoritative_source_table.py \
  scripts/validate_he3_exdqlm_ablation.py \
  scripts/audit_he3_exdqlm_ablation.py

python3 -m unittest tests.python.test_he3_exdqlm_ablation_tooling -v

python3 scripts/validate_he3_exdqlm_ablation.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_current_authority_20260625/control/he3_exdqlm_ablation_current_authority_v1 \
  --template config/multimodel_v8_he3_exdqlm_ablation_current_authority_20260625.template.yaml
```

The validation summary reports 30 total rows, 25 launch rows, five reused rows, and zero
findings.

## Launch Schedule

An active NDLM broad-screen campaign is running separately. To avoid crowding that work, the HE3
queue uses conservative concurrency:

- `ordinary_max_concurrent: 2`
- `heavy_cutoff_max_concurrent: 1`
- `fit_parallel.workers: 7`
- one cutoff order group at a time, with 2022-12-25 last

The queue is safe to resume/re-run because it reads `matrix_status.csv` from run manifests and
only launches `not_started` rows.

## Post-HE3 Steps

After all 30 HE3 rows pass:

1. Run the HE3 finish gate with cleanup enabled:
   `python3 scripts/finalize_he3_exdqlm_ablation.py --matrix-dir <matrix-dir> --cleanup-rdata`
2. Verify:
   - `he3_ablation_long.csv` has 30 pass rows;
   - `he3_ablation_audit.csv` has 25 all-OK launch rows;
   - runtime input detail has 200 OK rows;
   - article and corrections HE3 generated tables are synced.
3. Run article/corrections validation and compilation gates before promoting the HE3 table update.

## Deferred Follow-On Reruns

The current revised-article Figure A1 contract is **not** a univariate exDQLM contract. It is the
representative 2022-12-25 `exAL-M-T1` selected-output support figure, rendered from the
multivariate selected-model raw retained state component 6, as documented in
`docs/figure_a1_component_and_table_precision_contract_20260610.md`. Therefore, if Figure A1
requires another retained-state rebuild after HE3, the correct follow-on is a narrowly retained
representative multivariate selected-output support replay, not a univariate relaunch.

The univariate `exdqlm_univar` follow-on remains a separate publication-table/reference-synthesis
workflow refresh. It should be launched only after HE3 is complete and cleaned, and its
table-oriented all-cutoff relaunch should continue to clean `.RData` after post. Retain univariate
`.RData` only if a specific univariate diagnostic explicitly requires it, and remove it after the
diagnostic artifact is regenerated and validated.

The existing univariate tooling to inspect before any univariate follow-on is:

- `scripts/build_he2_exdqlm_univar_shared_relaunch_plan.py`
- `config/he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml`
- `config/he2_relaunch_batches/exdqlm_univar_all_cutoffs_sharedspec_20260516.yaml`
- `tests/python/test_he2_exdqlm_univar_shared_relaunch_plan.py`
- `tests/python/test_univar_post_quantile_synthesis_fallback.py`

No unsupported GDPC screening or GEFS-median claim expansion is part of this plan.

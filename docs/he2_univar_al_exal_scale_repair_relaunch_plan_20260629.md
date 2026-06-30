# HE2 Univariate AL/exAL Scale-Repair Relaunch Plan

Date: 2026-06-29

## Purpose

This plan prepares the repaired publication rerun for the two univariate
quantile families:

- `exdqlm_univar`, manuscript label `exAL-U-T1`, extended asymmetric Laplace
  likelihood.
- `dqlm_univar_al`, manuscript label `AL-U-T1`, asymmetric Laplace likelihood
  through the same legacy univariate bridge.

The immediate reason is the transform contamination found in
`docs/exdqlm_univar_transform_contamination_audit_20260629.md`: the legacy
runner was applying an additional `log()` to response and forecast-adapter
values that were already provided under the current publication `log1p(cms)`
contract. The resulting fitted states were on an unintended
`log(log(1 + flow))` scale, while publication figures and metrics are intended
to be on `log(1 + flow)`.

## Confirmed Current Repair

The active repair is source-level, not a plotting-only adjustment.

- `OptimalModelSLexAL.r` now sources
  `R/unified/univar_legacy_scale_contract.R` and transforms response, NWS, and
  GloFAS flow values through explicit scale-aware bridge functions.
- `R/unified/stages/stage_fit.R` exports
  `UNIFIED_LEGACY_FIT_INPUT_SCALE`, `UNIFIED_ANALYSIS_SCALE_FIT_INTERNAL`, and
  `UNIFIED_TRANSFORM_POLICY` to legacy subprocesses.
- `scripts/build_he2_bayesian_publication_relaunch_configs.py` force-locks the
  generated scale contract to `log1p_cms` with `transform_policy: log1p_only`,
  after row-level batch patches are merged.
- `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py` now checks
  both the source bridge and every generated config for the same contract.
- `R/unified/post_publication_figures.R` labels publication flow axes as
  `log(1 + x)` and rejects `log_log1p_cms`.
- `R/environmetrics/40_figures_smoke_fast.R` writes univariate fit diagnostics
  as `*_log1p.png`, labels quick diagnostic axes as `log(1 + flow)`, and keeps
  future USGS points on the same `log1p_cms` scale.

## Affected and Unaffected Models

Affected publication-facing models:

- `exAL-U-T1` (`exdqlm_univar`).
- `AL-U-T1` (`dqlm_univar_al`).

These need fresh fits for all five HE2 cutoffs and all seven quantile levels.

Not affected by this specific legacy-runner defect:

- Multivariate exDQLM keep/drop runners, which use the repaired multivariate
  data ingress path rather than `OptimalModelSLexAL.r`.
- NDLM models, which do not use the latent AL/exAL univariate bridge.

## Canonical Inputs

The repair relaunch must reuse the same publication shared input bundle used by
the authoritative multivariate synthesis:

- shared bundle root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
- bundle id: `20260510_publication_shared_r01`
- data start: `1987-05-29`
- cutoffs: `20210123`, `20211112`, `20211221`, `20220511`, `20221225`
- covariates: `PPT`, `SOIL`, and `PCA`/`GDPC1` aliases from the canonical
  bundle
- retrospective response storage scale: `log1p_cms`
- forecast adapter storage scale: raw cms, converted exactly once to
  `log1p_cms` inside the repaired bridge

## Dedicated Relaunch Package

New tracked launch package:

- template:
  `config/he2_bayesian_publication_relaunch_univar_al_exal_scale_repair_20260629.template.yaml`
- batch:
  `config/he2_relaunch_batches/univar_al_exal_scale_repair_20260629.yaml`

Runtime root:

```text
/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_univar_al_exal_scale_repair_20260629
```

Scope:

- 5 cutoffs x 2 families = 10 run rows.
- 7 quantile submodels per row = 70 quantile fits.
- Resource geometry: 4 run rows concurrently x 7 quantile workers per row =
  28 workers.
- One core per quantile worker, with BLAS/OpenMP thread env set to one per
  worker.
- Queue cleanup uses `scripts/run_unified_with_cleanup.sh`, so `.RData`,
  `.rdata`, and `.rda` artifacts are removed after post-stage completion.

The dedicated package intentionally does not overwrite the 2026-06-03
publication relaunch package, because the old package remains useful provenance
for what was invalidated.

## RData Cleanup Before Relaunch

Before launching repaired univariate fits, remove stale or contaminated
univariate R artifacts from known old univariate roots only. Do not remove
figures, metrics, logs, or manifests.

Target suffixes:

- `.RData`
- `.rdata`
- `.rda`

Known roots to clean:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_authoritative_retained_20260628`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_univar_al_exal_publication_relaunch_20260603`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_univar_al_all_cutoffs_sharedspec_20260517`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_discount_screen_20260628`

Cleanup must write an untracked manifest under `reports/` with file path,
bytes, and deletion status before removing files.

## Validation Gates

Run before launch:

```bash
python3 -m py_compile \
  scripts/build_he2_bayesian_publication_relaunch_configs.py \
  scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py

python3 -m unittest \
  tests.python.test_log1p_transform_policy \
  tests.python.test_environmetrics_scale_contract_source_contract \
  tests.python.test_he2_univar_scale_repair_relaunch -v

Rscript --vanilla -e "testthat::test_file('tests/testthat/test_univar_legacy_scale_contract.R')"

python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_univar_al_exal_scale_repair_20260629.template.yaml \
  --batch-file config/he2_relaunch_batches/univar_al_exal_scale_repair_20260629.yaml

python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_univar_al_exal_scale_repair_20260629.template.yaml \
  --batch-file config/he2_relaunch_batches/univar_al_exal_scale_repair_20260629.yaml
```

The prelaunch validator must confirm:

- source runner no longer contains direct `log()` bridge transforms;
- generated configs are `log1p_cms` and `log1p_only`;
- all selected rows share the canonical cutoff-specific bundle inputs;
- smoke fit and smoke full-pipeline checks complete;
- smoke `.RData` files are pruned.

Validation status on 2026-06-29/2026-06-30:

- source compile and unit tests passed after the final diagnostic-scale patch;
- the repair matrix built 10 rows and 70 quantile submodels;
- a full prelaunch validation pass completed before the final diagnostic-name
  and forecast-window truth-label patch, with 10 passed smoke scopes, 1 skipped
  NDLM-only smoke scope, and 25 temporary smoke R artifacts pruned;
- the final full prelaunch validation rerun passed after the diagnostic-label
  and forecast-window truth-scale patch, writing:
  `reports/he2_univar_al_exal_scale_repair_prelaunch_20260630_final/prelaunch_validation_summary.json`.

## Launch Command

After validation passes, launch the repair campaign with:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_univar_al_exal_scale_repair_20260629.template.yaml \
  --batch-file config/he2_relaunch_batches/univar_al_exal_scale_repair_20260629.yaml \
  --skip-validate \
  --reset-state \
  --start-monitor \
  --monitor-out-dir reports/he2_univar_al_exal_scale_repair_20260629_live
```

Use `--skip-validate` only when the standalone validation command above has
already passed for the same template and batch.

Launch status on 2026-06-30:

- queue launched with runtime root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_univar_al_exal_scale_repair_20260629`;
- queue command PID at launch: `65561`;
- live monitor PID at launch: `65703`;
- live monitor report directory:
  `reports/he2_univar_al_exal_scale_repair_20260629_live`;
- initial matrix state was 4 pending rows and 6 not-started rows, matching the
  intended 4-row concurrency geometry.

## Post-Run Promotion Checklist

- Confirm all 10 run rows finish `fit`, `post`, `validate`, and `report`.
- Confirm `.RData`, `.rdata`, and `.rda` do not remain under completed run
  roots.
- Rebuild publication manifest rows for `AL-U-T1` and `exAL-U-T1` from the
  repaired runtime root only.
- Regenerate CRPS tables, synthesis figures, univariate figure galleries, and
  article/poster support artifacts on the `log(1 + x)` scale.
- Re-run cross-repo publication freeze and article wiring validators.
- Update revised article and corrections response only after the repaired rows
  are confirmed complete.

## Checklist

- [x] Source-level bridge repair implemented.
- [x] Builder locks generated configs to `log1p_only`.
- [x] Prelaunch validator checks source and generated config scale contracts.
- [x] Dedicated repair template and batch created.
- [x] Regression tests added for the repair package.
- [x] Stale univariate `.RData` cleanup manifest written.
- [x] Stale univariate `.RData` files removed.
- [x] Repair package built in runtime root.
- [x] Repair package prelaunch validation passed for the repaired scale bridge.
- [x] Final quick diagnostic labels and future-truth scale fixed to `log1p_cms`.
- [x] Final full prelaunch validation rerun after diagnostic-label patch.
- [x] Repair queue launched.
- [ ] Repaired outputs promoted to publication artifacts.

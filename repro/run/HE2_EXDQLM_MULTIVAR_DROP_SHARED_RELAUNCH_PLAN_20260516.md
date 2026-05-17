# HE2 exdqlm_multivar_drop Shared Relaunch Plan

## Purpose

Prepare a clean, reproducible, no-launch relaunch package for `exdqlm_multivar_drop` using:

- the corrected shared-input bundle lineage,
- one shared exAL-M-T0 forecast-covariance prior,
- one shared discount-factor block,
- and the same proven q50 stabilization layer already approved for the current `exdqlm_multivar_keep` shared relaunch.

This stage does **not** launch the queue.

## Locked shared contract

- family: `exdqlm_multivar_drop`
- cutoffs: `20210123`, `20211112`, `20211221`, `20220511`, `20221225`
- shared bundle artifact root:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
- shared bundle run id:
  - `20260510_publication_shared_r01`
- retros and USGS window:
  - `1987-05-29 -> cutoff`
- deterministic blended covariates:
  - `PPT`, `SOIL`
- climate factor alias:
  - `PCA` backed by canonical `GDPC1`
- shared forecast covariance prior:
  - `epsilon=30.0`
  - `c_factor=1.0`
- shared discount set:
  - `set10_manual_20260516`
  - `df_t=0.99999999`
  - `df_s1=0.99999`
  - `df_s2=0.99999`
  - `df_s67=0.99999`
  - `df_discrep=0.99999`
  - `lambda=0.97`
  - `df_trans=0.9999999`
  - `df_covs=0.9999999`
- shared q50 stabilization:
  - `freeze_target=states`
  - `terminal_sampling_guard.mode=fail_fast`
  - `median_state_hold_after_guard_iters=0`
  - `median_state_blend_alpha=0.5`
  - `median_cov_blend_alpha=0.5`
  - `median_max_abs_gamma_step=0.15`
  - `median_max_abs_log_sigma_step=0.25`
- runtime / scheduler contract:
  - row scheduling: `ordinary_max_concurrent=1`
  - quantile-worker fanout: `fit_parallel_workers=7`
  - row process budget: `mc_cores=7`
  - thread caps per quantile worker: `OMP=OPENBLAS=MKL=VECLIB=NUMEXPR=1`
  - interpretation: one core per quantile model, seven quantile jobs in parallel within each row

## Why this spec

- this shared relaunch spec is a deliberate manual override recorded on `2026-05-16`
- it replaces the earlier family-wide `epsilon` / discount winner logic for the next `exdqlm_multivar_drop` rerun
- this twin package intentionally mirrors the approved `exdqlm_multivar_keep` shared relaunch contract so the drop family uses the same corrected bundles, prior scale, discount block, and q50 stabilization posture

## Approved tooling

- builder:
  - `scripts/build_he2_bayesian_publication_relaunch_configs.py`
- validator:
  - `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`
- report builder:
  - `scripts/build_he2_exdqlm_multivar_drop_shared_relaunch_plan.py`
- template:
  - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.template.yaml`
- batch:
  - `config/he2_relaunch_batches/exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.yaml`

## Commands

### 1. Rebuild the shared relaunch plan report

```bash
python3 scripts/build_he2_exdqlm_multivar_drop_shared_relaunch_plan.py
```

### 2. Build the no-launch relaunch configs

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.yaml
```

### 3. Run the prelaunch validator

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.yaml
```

## Validator focus

Representative execution smokes must cover:

- `20210123 q50`
- `20211221 q50`
- `20221225 q50`
- `20221225 q65`

The point is to prove that the shared spec is structurally valid **before** we schedule a real queue launch.

## Launch schedule after this stage

1. Canary relaunch: `20210123`, `20211221`, `20221225`
2. Review q50 / q65 fit-stage health and full row reports
3. Full 5-cutoff relaunch under the same shared spec
4. Article refresh from the new relaunch outputs
5. Commit and push updated article artifacts to `Evironmetrics---REVISED-DOC-2`

## Full-launch execution contract

When we move from validation to the real rerun, use:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516.yaml \
  --reset-state
```

Expected production behavior:

- the launch script rebuilds configs from the approved manifest-driven builder
- the launch script reruns the prelaunch validator before starting the queue
- only after validation passes does it reset stale matrix state and detach the queue controller
- `fit`, `post`, `validate`, and `report` all remain enabled, so the relaunch produces:
  - fit outputs
  - post outputs and post-side figures
  - validate compare metrics
  - report summaries and CRPS table source artifacts

## Do not do here

- do not start `launch_he2_bayesian_publication_relaunch.py`
- do not reset the old `20260512` root in this stage
- do not refresh the article figures from the planned shared-spec runtime root until the relaunch actually exists

# exDQLM Multivariate Keep Multi-Cutoff Promotion Plan

Date: 2026-05-22

Scope: plan the next guarded `log1p_cms` `exdqlm_multivar_keep` launch across all five HE2 publication cutoffs,
using the repaired workflow, `.RData` through post followed by cleanup, immediate post/CRPS/plots, and 35
single-threaded quantile fits in parallel. This document is a plan and source lock. It does not launch or clean
anything by itself.

## Current Decision

We prepared the multi-cutoff launch package, but this document still does not launch anything by itself.

The 2022-12-25 full-history guarded prelaunch proved the promoted path can run all seven quantiles at `max_iter=200`
without pseudo-data failures or fatal fit errors. The multi-cutoff package now retargets that repaired path to
`max_iter=100`, all five HE2 cutoffs, and the canonical full-history shared bundle.

The `.RData` decision changed after the first plan draft. We intentionally did **not** implement the no-cleanup queue
patch. The active queue still launches `scripts/run_unified_with_cleanup.sh`, which sets `CLEANUP_RDATA_AFTER_POST=1`.
That is now accepted for this launch: the fit-state `.RData` files are kept through the full post stage, then removed
after post finishes. Any diagnostic that needs `.RData` must therefore run inside the post/report stage or before
cleanup. The retained post outputs, CRPS tables, exported tables, ELBO plots, fit figures, and held-out USGS figures are
the durable artifacts for this campaign.

The held-out USGS truth-source issue is patched by commit `26d6f4e`, and the all-seven ELBO plotting issue is patched
by commit `9d30640`. Both are already on `origin/feature/export_posterior_tables`.

## Evidence Reconstructed

Primary conversation evidence:

- session index entry:
  `/home/jaguir26/.codex/session_index.jsonl:35`, id `019e4868-cbc6-7c11-9038-968884e474d1`,
  thread name `Audit exdqlm keep workflow`;
- conversation JSONL:
  `/home/jaguir26/.codex/sessions/2026/05/20/rollout-2026-05-20T19-41-28-019e4868-cbc6-7c11-9038-968884e474d1.jsonl`.

Key reconstructed milestones from that log:

| log line | evidence |
| ---: | --- |
| 703 | first full audit committed; found forecast `update_uts` `T` vs `TT_sub` bug and interactional failure diagnosis |
| 898, 943 | transform-regression repair plan committed and clarified that `log1p_cms` remains the target |
| 1541, 1553 | guarded q05/q35/q50/q95 reproduction launched with repaired monitoring |
| 2547 | guarded reproduction completed; q50 catastrophic failure did not reproduce, q05 transient `E[1/u]` remained |
| 7461 | patch takeaways and visual review committed; promotion-v2 profile identified as real but still explicit |
| 8227 | 2022-12-25 full-history promotion package source-locked and pushed at `737cb3c` |
| 8737 | guarded 200-iteration 2022-12-25 full-history prelaunch launched |
| 8795, 9129 | all seven lanes reached `iter=200`; all `.RData` files were produced, then post cleanup removed them |
| 9274 | all-seven ELBO plotting patch committed locally as `9d30640` |
| 9429 | held-out USGS truth-source patch committed locally as `26d6f4e` |

Current tracked evidence docs:

- `docs/exdqlm_multivar_keep_final_findings.md`
- `docs/exdqlm_multivar_keep_repair_tracker.md`
- `docs/exdqlm_multivar_keep_guard_response_policy.md`
- `docs/exdqlm_multivar_keep_patch_takeaways_visual_review.md`
- `docs/exdqlm_multivar_keep_fullhistory_promotion_readiness.md`
- `docs/exdqlm_multivar_keep_prelaunch_source_lock_20260522.md`

Current report evidence from the 2022-12-25 full-history prelaunch:

- `reports/he2_exdqlm_multivar_keep_fullhistory_promotion_live_20260522/`
- `reports/he2_exdqlm_multivar_keep_fullhistory_promotion_plots_20260522/`
- held-out USGS figures:
  `reports/he2_exdqlm_multivar_keep_fullhistory_promotion_plots_20260522/cutoff_synthesis_with_heldout_usgs/`

## Current Branch State

At the all-cutoff package update:

- branch: `feature/export_posterior_tables`;
- pushed baseline: `origin/feature/export_posterior_tables` at `b9b3ccf`;
- required post-stage patches already pushed:
  - `9d30640 Plot all multivar ELBO traces in smoke output`;
  - `26d6f4e Use full USGS truth source for post figures`;
- tracked runtime/audit outputs under `reports/` remain excluded locally and should not be committed by default.

## Launch Contract

The target launch is the HE2 publication `exAL-M-T1` `exdqlm_multivar_keep` family across these five cutoffs:

| cutoff token | cutoff date |
| --- | --- |
| `20210123` | 2021-01-23 |
| `20211112` | 2021-11-12 |
| `20211221` | 2021-12-21 |
| `20220511` | 2022-05-11 |
| `20221225` | 2022-12-25 |

These cutoffs come from
`config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516.yaml` and the canonical HE2
publication shared-bundle template.

Common contract for every cutoff:

| field | required value |
| --- | --- |
| family | `exdqlm_multivar_keep` |
| transfer mode | `keep` |
| history start | `1987-05-29` |
| input bundle | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510` |
| bundle run id | `20260510_publication_shared_r01` |
| quantiles | `0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95` |
| transform | `log1p_cms`, `transform_policy: log1p_only` |
| covariates | `PPT`, `SOIL`, `PCA` where `PCA` is the canonical GDPC/PCA alias |
| engineered terms | `PPT_sq`, `SOIL_sq`, `PPT_x_SOIL`, `PPT_lag1:3`, `SOIL_lag1:3` |
| harmonics | `enabled_harmonic_indices: [1, 2, 3]`, mapping to values `c(1, 2, 1/6.8068493)` |
| VB max iterations | `max_iter: 100` |
| runner mode | `fit.parallel.mode: global_models` |
| quantile workers per cutoff | `7` |
| per-process thread caps | `omp=openblas=mkl=veclib=numexpr=1` |
| simultaneous cutoffs | `5` |
| target concurrent quantile fits | `5 * 7 = 35` |
| post behavior | run post immediately after fit for each cutoff |
| RData behavior | keep `.RData` through the full post stage, then allow cleanup after post |

The final discount factors and Wishart prior values for the all-cutoff package are:

```text
df_t        0.99999
df_s1       0.9999
df_s2       0.9999
df_s67      0.9999
df_discrep  0.9999
lambda      0.97
df_trans    0.9999999
df_covs     0.9999999
epsilon     365.0
c_factor    1.0
```

These values are locked in
`config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_fullhistory_promotion_20260522.yaml`, generated
configs, and tests.

## Required Promotion Patches

### P0. Retarget Iterations To 100

The current 2022-12-25 promotion batch still has `max_iter: 200`. The multi-cutoff package must use `max_iter: 100`.

Implementation target:

- create a new all-cutoff template/batch rather than mutating the completed 2022-12-25 evidence package;
- assert the generated configs and frozen manifest `config_patch_json` contain `max_iter=100` for all five cutoffs.

### P0. Keep `.RData` Through Post, Then Cleanup

Observed code contract:

- `scripts/unified_run.R:193-196` reads `CLEANUP_RDATA_AFTER_POST`;
- `scripts/unified_run.R:296-305` deletes `.RData` after post when cleanup is enabled;
- `scripts/run_unified_with_cleanup.sh:12` sets cleanup on;
- `scripts/run_unified_without_cleanup.sh:27` sets cleanup off;
- `scripts/run_multimodel_v8_queue.py:324-329` currently hardcodes `scripts/run_unified_with_cleanup.sh`.

Implementation decision:

1. Do not add the no-cleanup queue setting in this launch package.
2. Keep the default queue runner as `scripts/run_unified_with_cleanup.sh`.
3. Treat `.RData` files as transient fit-state artifacts that must exist through post and may be deleted immediately
   after post completes.
4. Put durable evidence in post outputs, exported tables, smoke-fast figures, held-out USGS figures, and reports.

Acceptance criterion: post must finish before cleanup; after post, missing `.RData` is acceptable for this package.
If a later diagnostic requires `theta.out` or raw fit-state objects after post, that diagnostic must either be moved
into the post/report stage or the skipped no-cleanup queue patch must be implemented in a separate, explicit change.

### P0. Preserve Held-Out USGS Truth For Post/CRPS

Local commit `26d6f4e` changes `R/unified/stages/stage_post.R` so post figures can prefer a fuller configured/cached
USGS truth source when the run-scoped cutoff copy is truncated. This patch must be included in the launch branch.

Prelaunch check for every cutoff:

1. Resolve the post truth source from the generated config.
2. Confirm its max date is at least the forecast end date.
3. Confirm the run-scoped cutoff USGS copy may stop at cutoff without blocking held-out figures/CRPS.
4. Write a per-cutoff truth-source table under `reports/`.

### P0. Keep All-Seven ELBO Plotting

Local commit `9d30640` changes `R/environmetrics/40_figures_smoke_fast.R` so multivariate post output includes all
seven quantile ELBO traces when available. This patch must be included in the launch branch.

Acceptance criterion: every cutoff post bundle has an all-seven `All_ELBOS_DISC.png`, not only q50/q95.

### P1. Add Multi-Cutoff Monitor And Report Driver

The 2022-12-25 live monitor began as an untracked report helper. For five concurrent cutoffs, the monitor contract is
now promoted to tracked code at `scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py`:

- one compact status CSV per snapshot;
- one `live_status_latest.md`;
- fields: cutoff, q, iter, updates, ELBO, dELBO, `sigma_exp`, `gamma_exp`, state norm sq per history length,
  guard count, pseudo-data fail count, fatal error count, output state;
- stop condition: all five rows pass/fail, or bounded max snapshots.

The monitor is read-only. It parses `matrix_plan.csv`, `matrix_status.csv`, and per-quantile fit logs, then writes
untracked report artifacts under `reports/`. The launcher can start it automatically with `--start-monitor`.

## Cleanup Policy

Current runtime inventory found 64 `.RData`/`.rdata` files under
`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime`, totaling about 46.82 GiB. The new five-cutoff run may create
roughly 35 large `.RData` files transiently during fit/post. Because the accepted queue path cleans them after post,
they are not intended to be durable campaign artifacts.

Available space at plan time: about 471 GiB free on `/data`.

Cleanup must be explicit and reviewable:

1. Do not delete anything before the final multi-cutoff launch package and post-output path are ready.
2. Do not touch the older protected live roots named in the original audit request.
3. Use `scripts/cleanup_he2_runtime_artifacts.py` in dry-run mode first.
4. Protect all old live roots plus any report/evidence roots we choose to keep.
5. Copy compact evidence before deletion where needed.
6. Apply cleanup only after reviewing the dry-run report.
7. After the multi-cutoff run, retain only the new multi-cutoff `.RData` files until all diagnostics are complete.

Protected roots must include at least:

```text
/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reducedspec_defaultvb_iter3000_dft9995_datastart2010_ready_20260520/runs/multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dft9995_datastart2010_ready_exdqlm_multivar_keep
/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reducedspec_defaultvb_iter3000_dfall999999_datastart2017_ready_20260520/runs/multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dfall999999_datastart2017_ready_exdqlm_multivar_keep_rerun_20260520_160916
/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reducedspec_defaultvb_iter3000_dft9995_datastart2010_parallelpatchfix_20260520/runs/multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dft9995_datastart2010_parallelpatchfix_exdqlm_multivar_keep
/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reducedspec_defaultvb_iter3000_dfall999999_datastart2017_parallelpatchfix_20260520/runs/multimodel_20221225_v8_he2pubgdpc1r1_defaultvb_schedhold20refresh1_iter3000_dfall999999_datastart2017_parallelpatchfix_exdqlm_multivar_keep
```

## Implementation Sequence

### Step 1. Freeze Inputs And Specs

Actions:

1. Push or otherwise preserve local commits `9d30640` and `26d6f4e`.
2. Get final user-provided discount factors, `epsilon`, and `c_factor`.
3. Confirm the five cutoff list and canonical 20260510 input bundle.
4. Confirm no active protected production process would be affected.
5. Record disk space and current `.RData` inventory.

Tests/evidence:

- `git status --short --branch`;
- `df -h /data`;
- `.RData` inventory CSV under `reports/`;
- source-lock table under `docs/` if final specs differ from the previous `df99999`/`eps365` profile.

### Step 2. Build The New All-Cutoff Package

Actions:

1. Create a new template and batch, derived from:
   - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516.template.yaml`;
   - `config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516.yaml`;
   - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20221225_fullhistory_promotion_20260522.template.yaml`;
   - `config/he2_relaunch_batches/exdqlm_multivar_keep_20221225_fullhistory_promotion_20260522.yaml`.
2. Set artifact root to a new multi-cutoff promotion root.
3. Set all five cutoffs.
4. Set `fit_parallel_workers: 7`, `mc_cores: 7`, `fit.parallel.mode: global_models`.
5. Set queue concurrency to allow five run rows at once:
   `ordinary_max_concurrent: 5`, `heavy_cutoff_blocks_ordinary: false`, and `heavy_cutoff_max_concurrent: 1`.
6. Set `max_iter: 100`.
7. Apply final discount/Wishart spec.
8. Preserve all promotion-v2 guards.
9. Keep the current cleanup-wrapper behavior: `.RData` exists through post and is removed after post.

Acceptance criteria:

- generated `matrix_plan.csv` has exactly five rows, one per cutoff;
- every generated config has seven active quantiles;
- every generated config has thread caps of `1` and `mc_cores=7`;
- every generated config has `fit.parallel.mode=global_models`, `fit.parallel.workers=7`;
- every generated config has `max_iter=100`;
- every generated config points to the 20260510 shared bundle and `data_start=1987-05-29`.

### Step 3. Add Or Extend Tests

Required tests:

1. Template test for the new all-cutoff promotion package.
2. Builder-selection test that materializes the five generated configs in a temporary root and asserts:
   cutoffs, quantiles, `max_iter=100`, discounts/Wishart, input bundle, harmonics, transfer covariates, guards,
   `global_models`, and 7 workers.
3. Queue test that confirms the current cleanup wrapper is selected by default.
4. Stage-post truth-source test or preflight assertion for each cutoff.
5. Live-monitor unit test that verifies log parsing and `state_norm_sq / history_length`.
6. Existing tests from the 2022-12-25 source-lock pass.

Minimum validation command set:

```bash
Rscript --vanilla -e "invisible(parse('R/unified/config.R')); invisible(parse('R/unified/stages/stage_fit.R')); invisible(parse('R/unified/stages/stage_post.R'))"
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_config_mode_resolution.R')"
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_structure_contract.R')"
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_post_crps_tables.R')"
python3 -m unittest tests.python.test_he2_publication_relaunch_template -v
python3 -m unittest tests.python.test_he2_publication_relaunch_builder_selection -v
python3 -m unittest tests.python.test_he2_exdqlm_keep_allcutoff_monitor -v
python3 -m unittest tests.python.test_disc_sampling_diagnostics_source_contract -v
python3 -m unittest tests.python.test_cleanup_he2_runtime_artifacts -v
git diff --check
```

### Step 4. Dry-Run And Prelaunch Report

Actions:

1. Build generated configs into the new artifact root.
2. Run launch dry-run and capture the queue command.
3. Run cleanup dry-run only, not apply.
4. Write a prelaunch report under `reports/` and a tracked source-lock summary under `docs/` if specs changed.
5. Confirm disk/free-space gate can tolerate transient `.RData` while each post stage runs.

Required report tables:

- five generated configs and run ids;
- cutoff/date/start/forecast window;
- final discounts/Wishart;
- quantile/worker/thread contract;
- truth source and truth max date per cutoff;
- cleanup dry-run planned deletions and protected roots;
- expected transient `.RData` behavior and durable post-output paths.

### Step 5. Launch Only After Explicit Approval

Actions after approval:

1. Start queue with the current cleanup wrapper and five-row concurrency.
2. Start live monitor immediately.
3. Do not stop old live roots or unrelated diagnostics.
4. If any cutoff fails, do not relaunch automatically; classify the failure first.

Launch command shape to verify before use:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template <new-all-cutoff-template> \
  --batch-file <new-all-cutoff-batch> \
  --skip-validate \
  --start-monitor \
  --monitor-out-dir reports/he2_exdqlm_multivar_keep_allcutoffs_fullhistory_promotion_live_20260522
```

The exact final command belongs in the prelaunch report, not only in chat.

### Step 6. Post-Run Evidence Bundle

For every cutoff:

1. Verify post, validate, and report stages completed.
2. Verify `.RData` cleanup happened only after post completion.
3. Export all-seven ELBO plots.
4. Export fit-log traces: ELBO, ELBO step, `sigma_exp`, `gamma_exp`, state norm sq divided by history length, guard
   counts.
5. Run any `.RData`-dependent runtime stability audit before cleanup or from post-integrated outputs.
6. Run decomposition audit from post-integrated outputs.
7. Run visual review from post-integrated outputs: selected states, retained exps, USGS target exps.
8. Build cutoff and forecast-window synthesis plots with held-out USGS truth when available.
9. Export CRPS tables and truth-availability tables.
10. Write one cutoff README plus one campaign README.

Acceptance criteria:

- all expected figures/tables exist for all five cutoffs;
- all retained `.RData` paths are listed in a manifest;
- any quantile crossing is reported, not hidden;
- q20/q80 sigma/gamma guard activity and q95 gamma magnitude are summarized;
- failed or missing held-out truth is classified in truth-availability tables.

## Known Risks

| risk | why it matters | mitigation |
| --- | --- | --- |
| root cause is interactional, not a single isolated fix | broadening to 35 fits can expose new tail/cutoff behavior | keep promotion-v2 guards and runtime stability mandatory |
| latent `E[1/u]` cap changes pseudo-observation precision | it is a real numerical intervention | keep it explicit, named, and reported |
| q95 terminal gamma remains sensitive | prior evidence shows tail gamma asymmetry | monitor gamma by cutoff/lane; consider damped/refrozen candidate later |
| q20/q80 guard activity appeared in 2022-12-25 run | those lanes were less tested in the earliest q05/q35/q50/q95 reproductions | five-cutoff monitor must include guard counts by lane |
| `.RData` retention is heavy | 35 outputs may be hundreds of GiB while fit/post is active | dry-run disk check; keep `.RData` through post only; rely on durable post outputs after cleanup |
| queue cleanup is currently hardcoded on | raw `.RData` fit-state objects will not be durable artifacts | integrate needed diagnostics into post/report outputs and monitor logs before cleanup |
| held-out truth source can be cutoff-truncated | post figures/CRPS can silently miss truth | include commit `26d6f4e` and truth-source preflight |
| five concurrent cutoff runs may stress I/O/R memory | 35 processes are feasible only if each stays single-threaded | enforce thread caps and monitor RSS/free space |

## Readiness Gates

The multi-cutoff launch is not ready until every gate below is green:

| gate | status now | required closeout |
| --- | --- | --- |
| branch contains all post/plot patches | partial | push or intentionally preserve `9d30640` and `26d6f4e` |
| final discounts/Wishart supplied | open | user provides final values or confirms previous `df99999`/`eps365` |
| `max_iter=100` package exists | open | create new all-cutoff package and tests |
| `.RData` through-post cleanup policy | locked | default cleanup wrapper keeps `.RData` through post, then removes it |
| all-cutoff generated configs validated | open | builder tests and direct generated-config assertions |
| old `.RData` cleanup plan reviewed | open | dry-run cleanup report, protected roots checked |
| disk and process preflight passed | open | `df -h`, process scan, expected RData size estimate |
| live monitor ready for five cutoffs | closed | tracked monitor and unit tests added |
| explicit user launch approval | open | launch only after approval |

## Bottom Line

The algorithmic issue is no longer a mystery in the operational sense: the repaired, capped, guarded `log1p_cms`
profile controlled the observed blow-up in targeted lanes and in the 2022-12-25 all-seven prelaunch. The scientific
root cause remains interactional: latent-tail precision, `sigma/gamma`, pseudo-data, and retained state
identifiability reinforce each other.

The right next move is the explicit, monitored multi-cutoff promotion launch with `max_iter=100`, `.RData` retained
through post and then cleaned, full truth-source post behavior, 35 single-threaded quantile fits, and a strict
post-launch reporting gate.

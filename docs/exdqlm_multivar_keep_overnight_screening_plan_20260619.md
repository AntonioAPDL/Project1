# exDQLM Multivariate Keep Overnight Screening Plan

Date: 2026-06-19

Status: user supplied the concrete 2026-06-19 screening grid; launch only after
the matrix build and prelaunch gates pass.

## Goal

Run a new non-authoritative screening campaign for the multivariate
`exdqlm keep` (`exAL-M-T1`) workflow to search for potentially better
forecast-window CRPS specifications across discount factors and Wishart prior
epsilon values.

The screening campaign must not modify the current authoritative runs or article
assets. It should write into a new isolated runtime root, keep post/report
artifacts and diagnostics, and remove large `.RData` objects after successful
post-stage completion.

## Current Reference State

- Workflow repo status at planning time: clean on `main`.
- Host resources observed at planning time:
  - CPU cores: `64`.
  - Memory available: about `494 GiB`.
  - Disk available on `/data`: about `224 GiB`.
- Existing authoritative retained `.RData` cache:
  - root:
    `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_authoritative_rdata_retention_20260610`
  - retained files: `35`.
  - retained size: about `258.92 GiB`.
- New screening spec manifest:
  `config/he2_grid_specs/exdqlm_multivar_keep_overnight_screen_20260619.csv`.
- New screening campaign template:
  `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_overnight_screen_20260619.template.yaml`.
- Current authoritative per-cutoff winners are frozen in:
  `reports/exdqlm_multivar_keep_grid_eval_guard_promotion_final_20260530/combined_winners_by_cutoff.csv`.

The old May 2026 grid runbook remains the closest operational template:

- `docs/exdqlm_multivar_keep_grid_next_steps_runbook_20260524.md`
- `docs/exdqlm_multivar_keep_grid_evaluation_plan_20260524.md`
- `scripts/build_he2_exdqlm_multivar_keep_grid_configs.py`
- `scripts/validate_he2_exdqlm_multivar_keep_grid_prelaunch.py`
- `scripts/run_multimodel_v8_queue.py`
- `scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py`
- `scripts/evaluate_he2_exdqlm_multivar_keep_grid.py`

## Non-Disruption Contract

1. Use a new artifact root, for example:

   ```text
   /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619
   ```

2. Do not write into any authoritative grid root, retained-support root, or
   article asset directory.

3. Use the current canonical shared input bundle:

   ```text
   /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510
   ```

   with bundle run id:

   ```text
   20260510_publication_shared_r01
   ```

4. Keep the same five cutoffs:

   ```text
   20210123, 20211112, 20211221, 20220511, 20221225
   ```

5. Keep the same seven quantile models per cutoff:

   ```text
   0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95
   ```

6. Keep the same full-history data start:

   ```text
   1987-05-29
   ```

7. Keep the same transfer-covariate contract:

   ```text
   base covariates: PPT, SOIL, PCA
   engineered terms: PPT_sq, SOIL_sq, PPT_x_SOIL,
                     PPT_lag1, PPT_lag2, PPT_lag3,
                     SOIL_lag1, SOIL_lag2, SOIL_lag3
   ```

8. Keep the same harmonic-index contract:

   ```text
   enabled_harmonic_indices: [1, 2, 3]
   ```

   In this workflow, index `3` means the third configured harmonic, i.e. the
   internally configured `1 / 6.8068493` harmonic, not a literal frequency of
   `3`.

9. Keep cleanup enabled through:

   ```text
   scripts/run_unified_with_cleanup.sh
   ```

   which exports:

   ```text
   CLEANUP_RDATA_AFTER_POST=1
   ```

10. Do not pass `--no-cleanup` to `scripts/run_multimodel_v8_queue.py`.

## Recommended Concurrency

Use `7 x 4 = 28` active fit workers:

```text
fit_parallel_workers: 7
mc_cores: 7
ordinary_max_concurrent: 4
heavy_cutoff_max_concurrent: 4
```

The older grid smoke showed that a single seven-quantile row could use roughly
`68 GiB` resident memory during fit and `55+ GiB` during post. The safe default
therefore remains four concurrent rows with memory gates, even though the
machine has 64 cores.

Recommended queue gates:

```text
pause_free_gb: 25
launch_free_gb: 35
heavy_free_gb: 35
pause_mem_gb: 120
launch_mem_gb: 170
heavy_mem_gb: 190
poll_seconds: 30
continue_on_fail: true
skip_compares: true
heavy_cutoff_blocks_ordinary: false
```

Do not increase to five concurrent rows until the first wave completes with
comfortable memory and disk headroom.

## Spec Manifest

The concrete manifest for this screen is:

```text
config/he2_grid_specs/exdqlm_multivar_keep_overnight_screen_20260619.csv
```

It contains:

```text
9 discount cases x 7 epsilon values = 63 specs
63 specs x 5 cutoffs = 315 run rows
315 run rows x 7 quantile lanes = 2205 quantile fits
```

Epsilon values:

```text
1, 30, 60, 90, 180, 360, 1450
```

Discount cases:

```csv
discount_case_id,df_t,df_s1,df_s2,df_s67,df_discrep,lambda,df_trans,df_covs
s01,0.999999,0.9995,0.9995,0.9999,0.999,0.97,0.9999999,0.9999999
s02,0.999999,0.9995,0.9995,0.9995,0.999,0.97,0.9999999,0.9999999
s03,0.999999,0.9995,0.9995,0.9999,0.998,0.97,0.9999999,0.9999999
s04,0.999999,0.9995,0.9995,0.9999,0.996,0.97,0.9999999,0.9999999
s05,0.999999,0.9995,0.9995,0.9999,0.999,0.97,0.999999,0.999999
s06,0.9999999,0.9995,0.9995,0.9995,0.999,0.97,0.999999,0.999999
s07,0.9999999,0.9995,0.9995,0.9999,0.998,0.97,0.999999,0.999999
s08,0.9999999,0.9995,0.9995,0.9999,0.996,0.97,0.999999,0.999999
s09,0.9999999,0.99995,0.99995,0.9999,0.999,0.97,0.999999,0.999999
```

All rows use:

```text
c_factor = 1
max_iter = 120
min_update_iters = 50
```

Required columns for future edits:

```csv
grid_spec_id,discount_case_id,epsilon,c_factor,df_t,df_s1,df_s2,df_s67,df_discrep,lambda,df_trans,df_covs,max_iter,min_update_iters,notes
screen01_eps365,screen01,365,1,0.9999,0.9995,0.9995,0.9999,0.9990,0.97,0.9999999,0.9999999,100,50,short_description
screen01_eps180,screen01,180,1,0.9999,0.9995,0.9995,0.9999,0.9990,0.97,0.9999999,0.9999999,100,50,short_description
screen01_eps090,screen01,90,1,0.9999,0.9995,0.9995,0.9999,0.9990,0.97,0.9999999,0.9999999,100,50,short_description
screen01_eps060,screen01,60,1,0.9999,0.9995,0.9995,0.9999,0.9990,0.97,0.9999999,0.9999999,100,50,short_description
screen01_eps030,screen01,30,1,0.9999,0.9995,0.9995,0.9999,0.9990,0.97,0.9999999,0.9999999,100,50,short_description
```

Rules:

- `grid_spec_id` must be unique.
- Use a short stable prefix such as `s01_eps365`, `s02_eps090`, etc. Avoid
  changing the meaning of a reused id.
- `discount_case_id` groups rows that differ only by epsilon.
- `epsilon` must be positive.
- `c_factor` should usually remain `1` unless the screen is deliberately testing
  ensemble covariance inflation/deflation.
- All discount factors must be in `(0, 1]`.
- Keep `lambda = 0.97` unless the screen explicitly targets the Wishart
  discount.
- Use `max_iter = 100` and `min_update_iters = 50` for overnight screening, to
  match the canonical grid screening contract.

Recommended anchors to include unless runtime budget is tight:

| anchor | reason |
| --- | --- |
| old `c02_eps060` equivalent | current winner for cutoff `20220511` |
| old `c03_eps030` equivalent | current winner for cutoff `20211221` |
| old `c04_eps365` equivalent | current winner for cutoffs `20210123`, `20211112` |
| old `c05_eps030` equivalent | current winner for cutoff `20221225` |

Including anchors lets the new campaign detect drift from the existing
authoritative grid under the current code and runtime environment.

## Campaign Template

The concrete campaign template is:

```text
config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_overnight_screen_20260619.template.yaml
```

It is based on:

```text
config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_epsilon_discount_grid_20260524.template.yaml
```

with these campaign-specific fields changed:

```yaml
campaign:
  campaign_id: he2_bayesian_publication_exdqlm_multivar_keep_overnight_screen_20260619
  campaign_spec_id: he2screen
  artifact_root: /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619
  matrix_dir: /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619/control/publication_relaunch_matrix
  config_output_dir: /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619/control/generated_configs

grid:
  spec_manifest: config/he2_grid_specs/exdqlm_multivar_keep_overnight_screen_20260619.csv
```

Everything else should remain aligned with the old grid template unless there is
a deliberate reason to change it.

## Current Tooling Note

`scripts/build_he2_exdqlm_multivar_keep_grid_configs.py` already supports an
arbitrary spec manifest via `--config` / `grid.spec_manifest`.

The prelaunch validator must support dynamic spec counts. The old hard-coded
checks assumed:

```text
30 specs
150 run rows
1050 quantile fits
```

For this screen it should infer:

```text
63 specs
315 run rows
2205 quantile fits
```

The validator has been updated to infer the expected row count from the resolved
spec manifest and cutoff set, with a reduced synthetic-matrix regression test.

## Prelaunch Procedure

1. Confirm no production campaigns are actively using the target runtime root.
2. Optionally free disk by deleting only the retained authoritative `.RData`
   cache after explicit confirmation:

   ```text
   /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_authoritative_rdata_retention_20260610
   ```

   Record file count and size before deletion. Do not remove post outputs,
   figures, CSV manifests, or article-side artifacts.

3. Build the matrix:

   ```bash
   python3 scripts/build_he2_exdqlm_multivar_keep_grid_configs.py \
     --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_overnight_screen_20260619.template.yaml \
     --reset-status
   ```

4. Run static prelaunch validation:

   ```bash
   python3 scripts/validate_he2_exdqlm_multivar_keep_grid_prelaunch.py \
     --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619/control/publication_relaunch_matrix \
     --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619
   ```

5. Confirm the validation output shows zero failures and the expected number of
   rows/specs/quantile fits.

6. Optional but recommended: run one cleanup-enabled smoke row before the full
   overnight screen if the manifest includes new extremes such as very small
   epsilon or notably lower discount factors.

## Launch Command

Launch from a detached shell with cleanup enabled:

```bash
setsid bash -lc 'cd /data/muscat_data/jaguir26/project1_ucsc_phd && exec python3 scripts/run_multimodel_v8_queue.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619/control/publication_relaunch_matrix \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619 \
  --ordinary-max-concurrent 4 \
  --pause-free-gb 25 \
  --launch-free-gb 35 \
  --heavy-free-gb 35 \
  --pause-mem-gb 120 \
  --launch-mem-gb 170 \
  --heavy-mem-gb 190 \
  --heavy-cutoff-max-concurrent 4 \
  --poll-seconds 30 \
  --continue-on-fail \
  --skip-compares \
  --no-heavy-cutoff-blocks-ordinary' \
  > /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619/control/publication_relaunch_matrix/overnight_screen_queue_20260619.stdout.log 2>&1 &
```

Do not include `--no-cleanup`.

## Monitoring

Use:

```bash
python3 scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619 \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619/control/publication_relaunch_matrix \
  --out-dir reports/he2_exdqlm_multivar_keep_overnight_screen_live_20260619 \
  --once
```

Health checks should report:

- cutoff,
- spec,
- quantile,
- stage/status,
- iteration,
- ELBO,
- gamma and sigma,
- state norm per observational day,
- guard events,
- pseudo-data failures,
- cleanup state and retained `.RData` count.

## Evaluation

After completion:

```bash
python3 scripts/evaluate_he2_exdqlm_multivar_keep_grid.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619/control/publication_relaunch_matrix \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619 \
  --tag overnight_screen_20260619
```

Selection should remain per cutoff:

1. Exclude failed or unstable rows from promotion.
2. Rank eligible rows by forecast-window mean CRPS on `log_cms_plus1`.
3. Use median CRPS, worst-lead CRPS, stability status, and simpler priors as
   tie-breakers.
4. Compare each new winner against the current authoritative winner for the same
   cutoff.
5. Promote nothing automatically. Treat this as candidate discovery until the
   candidate figures, CRPS-by-lead behavior, and trace health are reviewed.

## Acceptance Criteria

A screening campaign is successful if:

- every planned row is terminal (`report/pass` or documented failure),
- cleanup leaves `0` retained `.RData` / `.rda` files under the screening root,
- the evaluator produces CRPS summaries, gate summaries, trace-health summaries,
  and failure logs,
- any new candidate winner has clean stability diagnostics,
- any candidate improvement is compared against the current authoritative
  per-cutoff winner,
- all evidence remains under the isolated screening runtime root and untracked
  `reports/` outputs until intentionally promoted.

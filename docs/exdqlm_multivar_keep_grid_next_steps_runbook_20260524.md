# exDQLM Multivar Keep Grid Next Steps Runbook

Date: 2026-05-24

Status: prepared; no-cleanup smoke launch in progress as of 2026-05-25 UTC.

2026-05-25 live hardening note: the first no-cleanup smoke row (`c05_eps030`, cutoff `20211112`)
showed that one seven-quantile fit row can use roughly 68 GB resident memory during fit and that
post can reach 55+ GB while loading retained posterior objects. The queue now supports explicit
`MemAvailable` gates. The full grid should start memory-aware rather than using the originally
planned 8 concurrent rows by default.

## Current Prepared State

The full epsilon/discount grid is frozen and statically validated:

- full grid root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524`
- full grid matrix: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524/control/publication_relaunch_matrix`
- specs: `30`
- cutoffs: `5`
- run rows: `150`
- quantile fits: `1050`
- static prelaunch validation: `8720` checks, `0` failures

No model fit was launched while preparing this runbook.

## Step 1. No-Cleanup Smoke

Purpose: verify the q50 component diagnostics and post artifact contract while retaining `.RData` for direct inspection.

Prepared root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_smoke_nocleanup_20260524`

Scope:

| item | value |
| --- | --- |
| cutoff | `20211112` |
| grid specs | `c01_eps365`, `c05_eps030`, `c06_eps030` |
| run rows | `3` |
| quantile fits | `21` |
| concurrent rows | `1` |
| cleanup | disabled |

Launch command, only after explicit approval:

```bash
python3 scripts/run_multimodel_v8_queue.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_smoke_nocleanup_20260524/control/publication_relaunch_matrix \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_smoke_nocleanup_20260524 \
  --ordinary-max-concurrent 1 \
  --pause-free-gb 25 \
  --launch-free-gb 35 \
  --heavy-free-gb 35 \
  --pause-mem-gb 80 \
  --launch-mem-gb 120 \
  --heavy-mem-gb 120 \
  --heavy-cutoff-max-concurrent 1 \
  --poll-seconds 30 \
  --continue-on-fail \
  --skip-compares \
  --no-heavy-cutoff-blocks-ordinary \
  --no-cleanup
```

After it completes, run:

```bash
python3 scripts/evaluate_he2_exdqlm_multivar_keep_grid.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_smoke_nocleanup_20260524/control/publication_relaunch_matrix \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_smoke_nocleanup_20260524 \
  --tag smoke_nocleanup_20260524
```

Required pass criteria:

- all three rows complete fit/post/validate/report or any failure is clearly understood;
- q50 component contract is present and passes for successful rows;
- forecast CRPS tables are present for `exdqlm_multivar_synth_keep`;
- quantile synthesis repaired anchor/empirical crossing shares are zero or numerical tolerance only;
- retained `.RData` remains available for inspection.

## Step 2. Cleanup-Enabled Smoke

Purpose: verify that production cleanup removes `.RData` only after the post artifact contract passes.

Prepared root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_smoke_cleanup_20260524`

Scope is the same three spec rows as the no-cleanup smoke.

Launch command, only after the no-cleanup smoke is inspected:

```bash
python3 scripts/run_multimodel_v8_queue.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_smoke_cleanup_20260524/control/publication_relaunch_matrix \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_smoke_cleanup_20260524 \
  --ordinary-max-concurrent 1 \
  --pause-free-gb 25 \
  --launch-free-gb 35 \
  --heavy-free-gb 35 \
  --pause-mem-gb 80 \
  --launch-mem-gb 120 \
  --heavy-mem-gb 120 \
  --heavy-cutoff-max-concurrent 1 \
  --poll-seconds 30 \
  --continue-on-fail \
  --skip-compares \
  --no-heavy-cutoff-blocks-ordinary
```

After it completes, run the evaluator on the cleanup smoke root and confirm successful rows have no retained `.RData`
under their run roots.

## Step 3. Full Grid Launch

Purpose: run the complete 30-spec, five-cutoff grid.

The original CPU-oriented target was 8 concurrent rows (`8 x 7 = 56` quantile workers). Live smoke
evidence shows this is not the safe first full-grid setting because RAM, not CPU, is the limiting
resource. Start at 4 concurrent rows with memory gates; consider increasing to 5 only after the
first full-grid fit/post cycle shows stable RAM and disk headroom.

Launch command, only after both smokes pass:

```bash
python3 scripts/run_multimodel_v8_queue.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524/control/publication_relaunch_matrix \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524 \
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
  --no-heavy-cutoff-blocks-ordinary
```

This uses production cleanup through `scripts/run_unified_with_cleanup.sh`.

If the first full-grid wave leaves more than 220 GB `MemAvailable` during both fit and post, a second
controller launch may use `--ordinary-max-concurrent 5 --heavy-cutoff-max-concurrent 5`. Do not use
8-way concurrency unless a new smoke or pilot demonstrates a much lower per-row memory footprint.

## Step 4. Live Monitoring

Use the spec-aware monitor:

```bash
python3 scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524 \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524/control/publication_relaunch_matrix \
  --out-dir reports/he2_exdqlm_multivar_keep_epsilon_discount_grid_live_20260524 \
  --once
```

The monitor table includes cutoff, grid spec, quantile, stage/status, iteration, ELBO, gamma, sigma, state norm per
history day, guard counts, near-zero fallback counts, pseudo-data failures, fatal errors, and output state.

## Step 5. Grid Evaluation

After the full grid completes:

```bash
python3 scripts/evaluate_he2_exdqlm_multivar_keep_grid.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524/control/publication_relaunch_matrix \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524 \
  --tag epsilon_discount_grid_20260524_final
```

The evaluator writes:

- `grid_artifact_gate_summary.csv`
- `grid_crps_per_time.csv`
- `grid_crps_summary_by_spec_cutoff.csv`
- `grid_crps_winners_by_cutoff.csv`
- `grid_crps_summary_by_spec_pooled.csv`
- `grid_input_health_summary.csv`
- `grid_quantile_synthesis_summary.csv`
- `grid_component_contract_summary.csv`
- `grid_trace_health_summary.csv`
- `grid_failure_log.csv`
- `README.md`

Primary selection is per cutoff using eligible `exdqlm_multivar_synth_keep` rows on `score_scale=log_cms_plus1`.
Failures remain in the report and are not silently dropped.

## Step 6. Freeze Winners

Once the evaluator report is reviewed:

1. freeze the per-cutoff winners and runner-ups in a final tracked doc;
2. record failed specs and failure reasons;
3. copy or symlink winner figures into a compact review folder under `reports/`;
4. decide whether to use per-cutoff winners or a single global spec;
5. only then prepare any publication rerun or final model-output promotion.

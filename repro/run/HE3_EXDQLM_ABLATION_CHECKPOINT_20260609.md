# HE3 exDQLM Ablation Checkpoint

Timestamp: 2026-06-09 00:29 UTC / 2026-06-08 17:29 PDT

This checkpoint documents the live state of the authoritative HE3 ablation campaign
anchored to `docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`.
It is intentionally a checkpoint, not a final sign-off: the queue was still running.

## Live Health

Runtime root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608`

Control directory:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608/control/he3_exdqlm_ablation_authoritative_winners_v1`

Observed state:

| Item | Value |
|---|---:|
| queue pass rows | 12 |
| queue pending rows | 1 |
| queue not-started rows | 17 |
| active row | `multimodel_20221225_v8_c05_eps030_exdqlm_multivar_keep_he3_noH1` |
| active stage | post-stage, `scripts/run_environmetrics_figures.R` |
| active post module | `40_figures_multivar_only.R` |
| `/data` free space | about 401 GB |
| runtime-root size | about 46 GB |
| project git state | clean, branch ahead of origin by 7 commits |

The active row had all seven fit `.RData` outputs saved successfully before entering
post-stage:

| quantile | active-row fit state |
|---:|---|
| 0.05 | saved |
| 0.20 | saved |
| 0.35 | saved |
| 0.50 | saved |
| 0.65 | saved |
| 0.80 | saved |
| 0.95 | saved |

The live process tree showed the controller, the row-level unified runner, and the
post-stage `Rscript` process alive. The post log advanced through
`30_univariate_and_misc.R` and `40_figures_smoke_fast.R` into
`40_figures_multivar_only.R`, so the row was not classified as stalled. The active row
had already written smoke figures, CRPS tables, posterior table export metadata, and
the cutoff-window posterior-sample figure before this checkpoint was finalized.

## Completed Evidence So Far

The completed launched rows with local post reports at this checkpoint were:

- `20211112`: `noH1`, `noH2`, `noH3`, `noTF`, `noTrend`
- `20221225`: `noTF`, `noTrend`

The active `20221225/noH1` row had written local post tables but had not yet returned a
completed row report to the controller.

The five `full` rows are reused authoritative references, not relaunched rows. Their
CRPS values are resolved from their source run directories by
`scripts/build_he3_exdqlm_ablation_summary.py` after all rows pass.

Completed local post-stage target-model CRPS values:

| cutoff | variant | target model | mean CRPS | median CRPS |
|---|---|---|---:|---:|
| 20211112 | `noTrend` | `exdqlm_multivar_synth_keep` | 0.723427 | 0.711027 |
| 20211112 | `noH3` | `exdqlm_multivar_synth_keep` | 1.035625 | 1.022196 |
| 20211112 | `noH2` | `exdqlm_multivar_synth_keep` | 1.047240 | 1.047060 |
| 20211112 | `noH1` | `exdqlm_multivar_synth_keep` | 1.601420 | 1.598778 |
| 20211112 | `noTF` | `exdqlm_multivar_synth_drop` | 1.912852 | 1.925870 |
| 20221225 | `noTF` | `exdqlm_multivar_synth_drop` | 2.367420 | 2.309404 |
| 20221225 | `noTrend` | `exdqlm_multivar_synth_keep` | 3.866177 | 3.802873 |

Active-row post CRPS already present, pending final row completion:

| cutoff | variant | target model | mean CRPS | median CRPS | row state |
|---|---|---|---:|---:|---|
| 20221225 | `noH1` | `exdqlm_multivar_synth_keep` | 4.812205 | 4.754373 | post in progress |

Partial interpretation:

1. For `20211112`, every ablation is much worse than the selected full winner
   (`mean CRPS = 0.0472363501` in the authoritative manifest). This is strong
   partial evidence that the retained trend, harmonics, and transfer structure are all
   contributing materially for that cutoff.
2. For `20211112`, among completed ablations, `noTrend` is the least damaging, while
   `noTF` is the most damaging. This should not be over-read as a global ranking until
   all cutoffs finish.
3. For `20221225`, the two completed ablations already show large degradation relative
   to the selected full winner (`mean CRPS = 0.6654596601`). The trend removal is worse
   than transfer removal in the current partial evidence.
4. The `20221225/noH1` row already had a high mean CRPS in its post table, but it was
   still in post-stage. Treat the number as useful live evidence, not final table input,
   until the row report and controller status mark it `pass`.

## Remaining Queue Work

Rows still not started at this checkpoint:

| cutoff | variants |
|---|---|
| 20221225 | `noH2`, `noH3` |
| 20210123 | `noH1`, `noH2`, `noH3`, `noTF`, `noTrend` |
| 20211221 | `noH1`, `noH2`, `noH3`, `noTF`, `noTrend` |
| 20220511 | `noH1`, `noH2`, `noH3`, `noTF`, `noTrend` |

The queue is configured to advance only after the current group passes. The heavy
cutoff `20221225` is intentionally limited to one active row at a time.

## Reproducibility Contract

The current campaign remains wired to the authoritative workflow in:

- `repro/run/HE3_EXDQLM_ABLATION_AUTHORITATIVE_WINNERS_20260608.md`
- `config/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608.template.yaml`
- `scripts/build_he3_exdqlm_ablation_matrix.py`
- `scripts/validate_he3_exdqlm_ablation.py`
- `scripts/run_he3_exdqlm_ablation_queue.py`
- `scripts/build_he3_exdqlm_ablation_summary.py`
- `scripts/audit_he3_exdqlm_ablation.py`
- `scripts/sync_he3_ablation_article_tables.py`

Post-stage is run-scoped and strict:

- `UNIFIED_REQUIRE_RUNSCOPED_POST=TRUE`
- `UNIFIED_ALLOW_LEGACY_POST_FALLBACK=FALSE`
- `UNIFIED_TRANSFORM_POLICY=log1p_only`
- `UNIFIED_POST_PUBLICATION_FIGURES=TRUE`
- `UNIFIED_POST_PUBLICATION_REWRITE_CANONICAL=TRUE`
- `UNIFIED_POST_PUBLICATION_EXPORT_PDF=TRUE`
- `UNIFIED_POST_PUBLICATION_FAIL_FAST=TRUE`

Article-side sync targets are:

- `Evironmetrics---REVISED-DOC-2/tables/generated_tex/he3_ablation_crps_main_table.tex`
- `Evironmetrics---REVISED-DOC-2/tables/generated_tex/he3_ablation_crps_body.tex`
- `Evironmetrics---REVISED-DOC-2/artifacts/he3_exdqlm_ablation_authoritative/`
- `Evironmetrics---REVISED-DOC-2/MANUSCRIPT_ASSET_MANIFEST.json`
- `Evironmetrics---REVISED-DOC-2/wileyNJD-APA.tex`
- `/data/muscat_data/jaguir26/Corrections---Project-1/main.tex`

Repository state observed at this checkpoint:

| repo | state |
|---|---|
| `project1_ucsc_phd` | clean, ahead of origin by 7 commits |
| `Evironmetrics---REVISED-DOC-2` | clean, ahead of origin by 4 commits |
| `Corrections---Project-1` | clean |

## Execution Plan From Here

1. Continue monitoring the existing controller. Do not stop or relaunch while rows are
   active and progressing.
2. Treat `matrix_status.csv` as the authoritative live status source. The queue is not
   complete until all 30 rows are `pass`.
3. If a row fails, preserve the failed run directory, inspect row-local fit/post logs,
   and fix root-cause wiring or contract failures before relaunching only that row. Do
   not patch manuscript tables around a failed row.
4. After all rows pass, let the queue completion hooks run. If they do not run
   automatically, run:

```bash
python3 scripts/build_he3_exdqlm_ablation_summary.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608/control/he3_exdqlm_ablation_authoritative_winners_v1

python3 scripts/audit_he3_exdqlm_ablation.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608/control/he3_exdqlm_ablation_authoritative_winners_v1

python3 scripts/sync_he3_ablation_article_tables.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608/control/he3_exdqlm_ablation_authoritative_winners_v1
```

5. Validate the generated HE3 reports:

- `reports/he3_exdqlm_ablation/he3_ablation_long.csv`
- `reports/he3_exdqlm_ablation/he3_ablation_wide.csv`
- `reports/he3_exdqlm_ablation/he3_ablation_summary.md`
- `reports/he3_exdqlm_ablation/he3_table_rows.tex`
- `reports/he3_exdqlm_ablation/audit/he3_ablation_audit.csv`
- `reports/he3_exdqlm_ablation/audit/he3_ablation_lead_buckets.csv`
- `reports/he3_exdqlm_ablation/audit/he3_ablation_audit.md`

6. Verify article and corrections sync by checking the generated TeX table, artifact
   manifest, and the patched manuscript sections in both external repos.
7. Only after post reports, CRPS tables, audits, article sync, and manifests are
   verified should large `.RData` files be removed by cleanup or manual cleanup.
8. Commit the final workflow/docs changes in `project1_ucsc_phd`; commit article-table
   sync in `Evironmetrics---REVISED-DOC-2`; commit corrections-table sync in
   `Corrections---Project-1`. Keep those commits separate so the scientific workflow,
   revised article, and corrections article remain reviewable.

## Current Recommendation

Do not intervene. The active `20221225/noH1` row is in a normal post-stage path and
the controller remains alive. The correct next action is continued monitoring until the
heavy `20221225` group finishes, followed by the final summary/audit/article-sync gate
once all 30 rows pass.

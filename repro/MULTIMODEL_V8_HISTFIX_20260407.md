# Multimodel v8 Hist-Fix Campaign (2026-04-07)

## Purpose

Rebuild the `20211221` and `20220511` v8 surfaces with true long-history retrospective support and rerun the affected matrices in an isolated runtime root.

## Why this exists

The finished `multimodel_v8_20260402` campaign used stable `forecats` bundles whose retrospective component collapsed to an `~1081` day synthetic-history window. The most visible symptom was that `20211221` and `20220511` were configured with `dates.data_start = 2010-01-01`, but the deeper issue is that the shared retrospective bundle itself effectively started near `2019`.

## Scope

Affected cutoffs:

- `20211221`
- `20220511`

Affected rerun surface:

- TT full baselines: `4` runs
- c100 multivariate epsilon reruns: `16` runs
- cf1 multivariate reruns: `20` runs
- total: `40` run roots
- compare bundles rebuilt downstream: `20`

## Artifact layout

Runtime root:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_histfix_20260407`

Stable long-history bundles:

- `stable_inputs/site=11160500/cutoff_date=<YYYY-MM-DD>/run_id=20260407_long_history_r01/`

Campaign phases:

- `source refill (GloFAS v3.1 historical only)`
- `control/histfix_tt_20260407`
- `control/histfix_c100_20260407`
- `control/histfix_cf1_20260407`

Generated configs:

- `config/unified_runs_histfix_20260407/`

## Input policy

### Retrospective inputs

For both cutoffs, the hist-fix bundles use:

- USGS daily flow: recovered daily archive
- GloFAS historical: `glofas_hist_v31_lisflood_cons`
- NWS retrospective: `nws_retro_v21` through its natural coverage end, then `nws_retro_v30` tail-fill for later cutoff-era dates

The campaign now includes a strict source-preflight stage before bundle creation:

- refill any missing monthly `hist_v31_lisflood_cons` shards under the existing recovery root
- extract the point series again
- refuse to build hist-fix bundles unless the extracted point series reaches `2022-05-11`

This keeps the scientific policy intact for the affected cutoffs instead of silently falling back to a different GloFAS history product.

The retrospective table stored in each stable bundle remains on the same scale expected by the current v8 workflow:

- `retros.csv` columns: `Date`, `USGS`, `GloFAS`, `NWS3.0`
- value scale: `log1p(cms)`

### Forecast inputs

The forecast-member tables are reused from the already successful `multimodel_v8_20260402` TT snapshots for the same cutoff:

- `nws_forecast.csv`
- `glofas_forecast.csv`

This preserves the forecast window exactly while replacing only the retrospective/history support.

### Covariates and parameters

The campaign uses copied long-history shared inputs from the successful `20210123` TT run root so the rerun does not depend on deleted repo-local caches:

- `parameters.txt`
- `cov_01_ELI.csv`
- `cov_02_ONI.csv`
- `cov_03_PPT.csv`
- `cov_04_SOIL.csv`
- `cov_05_PCA.csv`

## Scheduler policy

The rerun keeps the current one-core-per-job intent by using the existing `global_models` scheduler with explicit lane worker counts:

- TT `l1`: `23` workers
- TT `l2`: `22` workers
- multivar-only lanes: `14` workers

Queue concurrency:

- TT phase: `1` lane at a time
- c100 phase: `2` lanes at a time
- cf1 phase: `2` lanes at a time

## Launch command

```bash
nohup bash scripts/run_multimodel_v8_histfix_campaign.sh \
  > /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_histfix_20260407/control/histfix_campaign_launcher.log \
  2>&1 &
```

The wrapper now runs phases in this order:

1. source refill / readiness check for `hist_v31_lisflood_cons`
2. isolated stable-bundle build
3. TT queue
4. c100 multivariate queue
5. cf1 multivariate queue

## Monitoring

Queue logs:

- `.../data_recovery/.../family=glofas_historical/.../status/hist_v31_histfix_ready.json`
- `control/histfix_tt_20260407/queue.log`
- `control/histfix_c100_20260407/queue.log`
- `control/histfix_cf1_20260407/queue.log`

Health refresh:

```bash
python3 scripts/check_multimodel_v8_matrix_health.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_histfix_20260407/control/histfix_tt_20260407 \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_histfix_20260407
```

## Acceptance checks

Before trusting the rerun, confirm for at least one TT run that:

1. `inputs/shared/data_start_filter_summary.txt` reports a common start at `1987-05-29`
2. `inputs/shared/retros/retros.csv` starts at `1987-05-29`
3. covariate snapshots in `inputs/shared/covariates/` also start at `1987-05-29`
4. the run reaches `fit` cleanly under `global_models`

## Reproducibility notes

- The current canonical `multimodel_v8_20260402` tree is left untouched.
- Hist-fix configs are written to a dedicated config directory.
- Hist-fix bundles are stored in runtime, not under the repo root.
- Queue/control/report artifacts are phase-scoped and resumable.

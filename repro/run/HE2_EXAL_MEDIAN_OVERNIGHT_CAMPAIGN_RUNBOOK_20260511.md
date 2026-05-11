# HE2 exAL Median Overnight Campaign Runbook (2026-05-11)

## Purpose
Run a comprehensive, sidecar-only overnight stabilization campaign for the sensitive median case:
- cutoff: `2021-01-23`
- family: `exdqlm_multivar_keep`
- quantile: `q=0.50`

This campaign is intentionally isolated from the production 45-row relaunch workflow.
It is designed to leave us with a ranked morning summary of median stabilization ideas without contaminating the main campaign machinery.

## Canonical campaign config
- [median_overnight_campaign_exdqlm_multivar_keep_20210123_q50_20260511.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/median_overnight_campaign_exdqlm_multivar_keep_20210123_q50_20260511.yaml)

## Core implementation surfaces
- Sidecar overnight driver:
  - [run_exdqlm_median_overnight_campaign.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_exdqlm_median_overnight_campaign.py)
- Single-probe harness reused by the campaign:
  - [run_exdqlm_median_warmup_probes.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_exdqlm_median_warmup_probes.py)
- Median runtime stabilization env wiring:
  - [stage_fit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/stages/stage_fit.R)
  - [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r)
  - [DISC_Optimal_Synth_Ranges_W.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W.r)

## New sidecar-only knobs
These remain inert unless explicitly set in the sidecar config:
- `median_state_hold_after_guard_iters`
- `median_state_blend_alpha`
- `median_cov_blend_alpha`

## Runtime root
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_median_overnight_campaign_20260511`

## Standard commands
Dry run:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/median_overnight_campaign_exdqlm_multivar_keep_20210123_q50_20260511.yaml \
  --dry-run
```

Small smoke run:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/median_overnight_campaign_exdqlm_multivar_keep_20210123_q50_20260511.yaml \
  --max-probes 2 \
  --concurrency 2
```

Full overnight run:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/median_overnight_campaign_exdqlm_multivar_keep_20210123_q50_20260511.yaml \
  --concurrency 24
```

## Key outputs
Campaign-level:
- `reports/campaign_plan.csv`
- `reports/campaign_results.csv`
- `reports/campaign_results.json`
- `reports/campaign_progress.json`
- `reports/MORNING_SUMMARY.md`

Per-probe:
- `probes/<wave>/<probe>/reports/probe_results.csv`
- `probes/<wave>/<probe>/reports/winner_summary.json`
- `probes/<wave>/<probe>/reports/MEDIAN_WARMUP_PROBE_REPORT.md`
- `probes/<wave>/<probe>/control/launch_logs/...`
- `control/worker_logs/<wave>__<probe>.log`

## Morning review order
1. open `reports/MORNING_SUMMARY.md`
2. inspect the top ranked healthy or near-healthy probes
3. compare the best probe rows against their per-probe `winner_summary.json`
4. inspect the worker log and quantile fit log for the most promising 1-3 candidates
5. only then decide whether to promote one policy into the production relaunch path

# HE2 exdqlm Multivar Keep q35 State-Path Campaign Runbook (2026-05-12)

## Purpose
Run a second-generation, sidecar-only stabilization campaign for the unresolved
`q=0.35` case:
- cutoff: `2021-01-23`
- family: `exdqlm_multivar_keep`
- quantile: `q=0.35`

This campaign exists because the first parallel q35 search failed `15/15` and
showed that q35 is exploding during the freeze window before meaningful
`gamma/sigma` updates begin.

## What changed from the first q35 campaign
The first q35 campaign taught us two important things:
1. `q35` is failing on the early state path, often by `iter=2`, with
   `last_updates=0`.
2. Many of the previously varied `median_*` stabilization knobs are genuinely
   median-only in the DISC runtime, so they do not change `q35` behavior.

This second-generation campaign only varies knobs that actually apply to `q35`:
- `freeze_target`
- `warmup_freeze_iters`
- `init.sigma_floor`
- `init.sigma_scale`
- global `theta_sigma_upper`
- global Hessian ridge settings

## Canonical campaign config
- [q35_statepath_campaign_exdqlm_multivar_keep_20210123_20260512.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/q35_statepath_campaign_exdqlm_multivar_keep_20210123_20260512.yaml)

## Runtime root
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_q35_statepath_campaign_20260512`

## Campaign structure
- `wave1_state_freeze`
  - freeze latent states early and let `gamma/sigma` adapt first
- `wave2_short_gamma_freeze`
  - shorten or remove the default `gamma/sigma` freeze
- `wave3_state_freeze_bounds`
  - combine state-freeze with tighter global sigma bounds and stronger Hessian ridge
- `wave4_short_gamma_bounds`
  - combine short gamma-freeze with tighter global sigma bounds and stronger Hessian ridge

## Automatic confirmation
If any screening probe is healthy, the campaign automatically reruns the
selected winner with a stricter fit-only confirmation contract:
- `min_update_iters = 10`
- `min_total_iters = 15`
- `max_iter = 25`

That keeps the campaign unattended but still gives us stronger evidence than a
single cheap screening pass.

## Standard commands
Dry run:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/q35_statepath_campaign_exdqlm_multivar_keep_20210123_20260512.yaml \
  --dry-run
```

Small smoke run:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/q35_statepath_campaign_exdqlm_multivar_keep_20210123_20260512.yaml \
  --max-probes 2 \
  --concurrency 2
```

Full campaign:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/q35_statepath_campaign_exdqlm_multivar_keep_20210123_20260512.yaml \
  --concurrency 6
```

## Key outputs
Campaign-level:
- `reports/campaign_plan.csv`
- `reports/campaign_plan.json`
- `reports/campaign_results.csv`
- `reports/campaign_results.json`
- `reports/campaign_progress.json`
- `reports/campaign_warnings.md`
- `reports/MORNING_SUMMARY.md`

Per-probe:
- `probes/<wave>/<probe>/reports/probe_results.csv`
- `probes/<wave>/<probe>/reports/winner_summary.json`
- `probes/<wave>/<probe>/reports/MEDIAN_WARMUP_PROBE_REPORT.md`
- `control/worker_logs/<wave>__<probe>.log`
- `probes/<wave>/<probe>/runs/.../fit/exdqlm_multivar/keep/q=35/logs/fit.log`

## Review order
1. open `reports/campaign_warnings.md`
2. open `reports/MORNING_SUMMARY.md`
3. check whether any probe reached `last_updates >= 5`
4. if a winner exists, inspect its `winner_summary.json`
5. inspect the winning `q=35` fit log before promoting anything upstream

## Promotion rule
Do not promote a q35 policy into the family map unless it:
- is healthy in screening
- is healthy in automatic confirmation
- reaches meaningful `gamma/sigma` updates
- avoids the early freeze-window state explosion pattern

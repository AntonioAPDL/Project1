# HE2 exdqlm Multivar Keep q35 Parallel Campaign Runbook (2026-05-12)

## Purpose
Run a sidecar-only, parallel stabilization campaign for the unresolved `q=0.35`
case:
- cutoff: `2021-01-23`
- family: `exdqlm_multivar_keep`
- quantile: `q=0.35`

This campaign is intentionally isolated from the production relaunch workflow.
It keeps the shared bundle, discounts, epsilon, covariates, and canonical GDPC
lineage fixed while screening q35-specific initialization and stabilization
ideas in parallel.

## Canonical campaign config
- [q35_parallel_campaign_exdqlm_multivar_keep_20210123_20260512.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/q35_parallel_campaign_exdqlm_multivar_keep_20210123_20260512.yaml)

## Core implementation surfaces
- Parallel sidecar driver:
  - [run_exdqlm_median_overnight_campaign.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_exdqlm_median_overnight_campaign.py)
- Single-probe harness reused by the campaign:
  - [run_exdqlm_median_warmup_probes.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_exdqlm_median_warmup_probes.py)
- q35-specific template and prior one-off probes:
  - [he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_q35_probe_20260511.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20210123_q35_probe_20260511.template.yaml)
  - [20210123_exdqlm_multivar_keep_q35_lighter_probe_20260511.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_q35_lighter_probe_20260511.yaml)
  - [20210123_exdqlm_multivar_keep_q35_midscale_probe_20260511.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_relaunch_batches/20210123_exdqlm_multivar_keep_q35_midscale_probe_20260511.yaml)

## Runtime root
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_q35_parallel_campaign_20260512`

## Probe families
- `wave1_anchors_and_scales`
  - current q35 anchors and sigma scale / sigma floor variants
- `wave2_damping`
  - tighter gamma / log-sigma step damping
- `wave3_bounds_and_holds`
  - longer hold windows and tighter transformed sigma bounds

## Standard commands
Dry run:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/q35_parallel_campaign_exdqlm_multivar_keep_20210123_20260512.yaml \
  --dry-run
```

Small smoke run:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/q35_parallel_campaign_exdqlm_multivar_keep_20210123_20260512.yaml \
  --max-probes 2 \
  --concurrency 2
```

Full q35 campaign:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/q35_parallel_campaign_exdqlm_multivar_keep_20210123_20260512.yaml \
  --concurrency 4
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

## Review order
1. open `reports/MORNING_SUMMARY.md`
2. compare the best healthy rows against the current q35 anchors
3. inspect the best 1-3 probe `winner_summary.json` files
4. inspect the worker log and `q=35` fit log for those candidates
5. only then decide whether to promote one q35 policy into the next family-level relaunch map

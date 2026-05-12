# HE2 exdqlm Multivar Keep q35 Final Background Campaign Runbook (2026-05-12)

## Purpose
Run the final q35-only sidecar stabilization program for the last unresolved
quantile in `exdqlm_multivar_keep` at cutoff `2021-01-23`.

Target:
- family: `exdqlm_multivar_keep`
- cutoff: `2021-01-23`
- quantile: `q=0.35`

This campaign is the clean endgame for q35:
- fully sidecar
- reproducible
- safe to leave unattended in the background
- one core per case
- `12` cases in parallel by default
- focused only on q35-relevant controls

## Canonical config
- [q35_final_background_campaign_exdqlm_multivar_keep_20210123_20260512.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/q35_final_background_campaign_exdqlm_multivar_keep_20210123_20260512.yaml)

## Runtime root
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_q35_final_background_campaign_20260512`

## Why this campaign is different
This final program deliberately stops spending q35 compute on directions that
already failed cleanly:
- no median-only stabilization knobs pretending to affect q35
- no family-wide reuse assumptions
- no short gamma-freeze branch as a main search direction
- no pure sigma floor/scale scanning without a state-freeze backbone

Instead it focuses on the only levers that materially helped q35 so far:
- state-freeze backbone
- post-thaw state guard / hold / blend for non-median quantiles
- tighter transformed sigma bounds
- stronger Hessian ridge
- stricter confirmation on screening winners

## Resource policy
Every case runs with:
- `fit_parallel_workers = 1`
- `mc_cores = 1`

The launcher also clamps library threading for each case:
- `OMP_NUM_THREADS=1`
- `OPENBLAS_NUM_THREADS=1`
- `MKL_NUM_THREADS=1`
- `VECLIB_MAXIMUM_THREADS=1`
- `NUMEXPR_NUM_THREADS=1`

This avoids hidden BLAS/OpenMP oversubscription and makes the `12`-way
background concurrency real.

## Campaign structure
### Wave 0: Anchors
Four fixed reference probes inside the same runtime root:
1. current best q35 backbone by updates
2. best low-sigma q35 backbone
3. best bounded q35 candidate so far
4. one known-bad short gamma-freeze anchor

### Wave 1: State-Freeze Backbone
Eight probes:
- `freeze_target = states`
- `warmup_freeze_iters = 6, 8, 10, 12`
- init family A: `sigma_floor = 0.01`, `sigma_scale = 0.50`
- init family B: `sigma_floor = 0.0005`, `sigma_scale = 0.60`

### Wave 2: Post-Thaw State Control
Eight probes built around the two strongest q35 backbones from the prior state-path campaign:
- hold after guard: `5, 10`
- state blend alpha: `1.0, 0.85`
- generic non-median state guard enabled

### Wave 3: Bounds and Ridge
Eight probes built around the same two strongest backbones:
- `theta_sigma_upper = 3.5, 3.0`
- `hessian_ridge_init = 1e-4, 1e-3`

### Wave 4: Combined Rescue
Four integrated rescue probes:
- 2 strongest backbones
- 2 combined hold/blend/bounds/ridge profiles

### Confirmation
Automatic fit-only confirmation for the top `4` healthy screening winners max:
- `min_update_iters = 12`
- `min_total_iters = 20`
- `max_iter = 40`

If no screening probes are healthy, the controller writes:
- `reports/campaign_stop_reason.json`

## Standard commands
Dry run:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/q35_final_background_campaign_exdqlm_multivar_keep_20210123_20260512.yaml \
  --dry-run
```

Two-probe smoke:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/q35_final_background_campaign_exdqlm_multivar_keep_20210123_20260512.yaml \
  --max-probes 2 \
  --concurrency 2
```

Full unattended campaign:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/q35_final_background_campaign_exdqlm_multivar_keep_20210123_20260512.yaml \
  --concurrency 12
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
- `reports/campaign_stop_reason.json`

Per-screening-probe:
- `probes/<wave>/<probe>/reports/probe_results.csv`
- `probes/<wave>/<probe>/reports/winner_summary.json`
- `probes/<wave>/<probe>/reports/MEDIAN_WARMUP_PROBE_REPORT.md`
- `control/worker_logs/<wave>__<probe>.log`

Per-confirmation-probe:
- `confirmations/<wave>/<probe>/reports/probe_results.csv`
- `control/confirmation_worker_logs/<wave>__<probe>.log`

## Review order
1. open `reports/campaign_warnings.md`
2. open `reports/MORNING_SUMMARY.md`
3. open `reports/campaign_stop_reason.json` if present
4. inspect the top current screening candidates section
5. inspect confirmation rows if any exist
6. inspect the top q35 fit log before promoting anything upstream

## Promotion rule
A q35 policy is not promotable into the family map unless it:
- is healthy in screening
- is healthy in confirmation
- reaches meaningful q35 updates
- avoids the early state-path blow-up pattern
- is reproducible from the pinned base generated config and committed code

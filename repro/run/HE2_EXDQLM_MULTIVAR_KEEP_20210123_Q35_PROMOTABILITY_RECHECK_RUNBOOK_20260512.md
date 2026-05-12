# HE2 exdqlm Multivar Keep q35 Promotability Recheck Runbook (2026-05-12)

## Purpose
Turn the fixed q35 fit-path rerun into a clean, reproducible promotability decision.

Target:
- family: `exdqlm_multivar_keep`
- cutoff: `2021-01-23`
- quantile: `q=0.35`
- commit: `9baab1b`

This runbook exists because the old q35 blocker is now fixed in code, and the
remaining question is whether the resulting q35 fit is promotable into the full
family relaunch map.

## Canonical config
- [q35_final_background_campaign_recheck_exdqlm_multivar_keep_20210123_20260512.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/q35_final_background_campaign_recheck_exdqlm_multivar_keep_20210123_20260512.yaml)

## Runtime root
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_q35_final_background_recheck_20260512`

## Promotability gate
The q35 candidate is considered promotable when all of the following hold:
- fit reaches meaningful q35 updates
- VB completes
- sampling completes
- `.RData` artifact is written
- `multivar_forecast_health.txt` is written
- `max_abs_sm_ens <= 1000`
- `max_abs_forecast_exps <= 650`
- `max_E_sigma <= 100`
- `nonfinite_sm_ens == 0`
- `nonfinite_forecast_exps <= 48`

Note:
- `nonfinite_forecast_exps=48` is currently tolerated because the accepted q20,
  q50, q65, and q80 sidecars show the same pattern under `transfer_mode=keep`.

## Why `harvest-existing` matters
The q35 fit can complete successfully while the outer sidecar controller is still
in bookkeeping or while a prior monitoring interruption prevents the report files
from being written. The harvest mode rebuilds the probe summaries directly from the
completed artifact tree without rerunning the expensive fit.

## Standard commands
Dry run:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/q35_final_background_campaign_recheck_exdqlm_multivar_keep_20210123_20260512.yaml \
  --dry-run
```

Clean rerun:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/q35_final_background_campaign_recheck_exdqlm_multivar_keep_20210123_20260512.yaml \
  --concurrency 1
```

Harvest an already-finished recheck root without rerunning fit:
```bash
python3 scripts/run_exdqlm_median_overnight_campaign.py \
  --config config/q35_final_background_campaign_recheck_exdqlm_multivar_keep_20210123_20260512.yaml \
  --harvest-existing \
  --assume-exit-code 0 \
  --concurrency 1
```

Single-probe harvest directly:
```bash
python3 scripts/run_exdqlm_median_warmup_probes.py \
  --config /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_q35_final_background_recheck_20260512/control/generated_single_probe_configs/wave2_post_thaw_state_control__w2_a_hold10_blend100.yaml \
  --harvest-existing \
  --assume-exit-code 0
```

## Review order
1. open `reports/campaign_progress.json`
2. open `reports/campaign_results.csv`
3. open `probes/.../reports/probe_results.csv`
4. open `probes/.../reports/winner_summary.json`
5. confirm the q35 fit log shows:
   - `theta_seed_check ... ready=true`
   - `VB converged`
   - `Sampling finished`
6. confirm `multivar_forecast_health.txt` matches the promotability gate

## Promotion target
If the promotability gate passes, the next step is to wire q35 into the full
`2021-01-23 exdqlm_multivar_keep` row map and relaunch the full row.

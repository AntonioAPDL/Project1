# P2B No-Root-Writes Smoke Report

- Config: `config/unified_runs/smoke_p2b_no_root_writes.yaml`
- Run ID: `20260210_212458`
- Run root: `repro/runs/20260210_212458`

## Closure Evidence

- Manifest: `repro/runs/20260210_212458/run_manifest.yaml`
- `finished_at_utc`: `2026-02-11T05:56:49Z`
- Write-audit (fit stage): `repro/runs/20260210_212458/validate/write_audit/fit/fs_diff.patch`
- Write-audit result: `fs_diff.patch` size is `0` bytes (no outside-run-root writes detected during fit stage)

## Run-Scoped Legacy Outputs

- Univariate output:
  - `repro/runs/20260210_212458/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
- NDLM output:
  - `repro/runs/20260210_212458/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`

## Repo-Root Write Check

- Existing legacy root files are present but unchanged in this run:
  - `variables_50_exAL_synth_DISC_uni.RData` (pre-existing timestamp: `Sep 14 21:37`)
  - `DISC_variables_50_NDLM_synth_DISC.RData` (pre-existing timestamp: `May 21 2025`)
- Fit-stage write audit enforced at stage 2 with empty allowlist and passed.

## Manifest Artifact Entries (legacy bridges)

- `fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
- `fit/exdqlm_univar/q=50/logs/univar_legacy.log`
- `fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
- `fit/ndlm_main/logs/ndlm_legacy.log`

## Notes

- First run attempt (`20260210_212008`) failed due non-finite values in `weighted_time_series.csv`.
- Second run attempt (`20260210_212059`) failed because `glofas_forecast.csv` (10-row `Date` format) was incompatible with univariate `objective_deltas` expectations.
- Final passing smoke used run-scoped shared GloFAS input sourced from:
  - `data/forecats_cache/site=11160500/run_id=20260206_paper_default_latest/forecast_cache/glofas/issue_date=2022-12-25/glofas_members.csv`

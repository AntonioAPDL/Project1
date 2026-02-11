# P6 Combined Orchestration Smoke

- Config: `config/unified_runs/smoke_p6_combined_theory_orchestration.yaml`
- Run ID: `20260211_120855`
- Run root: `repro/runs/20260211_120855`
- Command:
  - `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/smoke_p6_combined_theory_orchestration.yaml`

## Manifest Closure

- Manifest: `repro/runs/20260211_120855/run_manifest.yaml`
- `timestamps.finished_at_utc`: `2026-02-11T20:36:55Z`
- `validation.status`: `pass`
- Compare report: `repro/runs/20260211_120855/validate/compare_report.json`
- Report summary: `repro/runs/20260211_120855/report/summary.md`, `repro/runs/20260211_120855/report/summary.json`

## Fit Family Artifacts

- Multivar DISC-W:
  - `repro/runs/20260211_120855/fit/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData`
- Univar theory:
  - `repro/runs/20260211_120855/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
  - `repro/runs/20260211_120855/fit/exdqlm_univar/q=50/logs/univar_theory.log`
- NDLM theory:
  - `repro/runs/20260211_120855/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
  - `repro/runs/20260211_120855/fit/ndlm_main/logs/ndlm_theory.log`

## Contract Checks + Diagnostics

- Contract checks:
  - `repro/runs/20260211_120855/fit/contract_checks/exdqlm_univar/q=50/q50_exdqlm_univar_contract_check.json`
  - `repro/runs/20260211_120855/fit/contract_checks/ndlm_main/ndlm_main_contract_check.json`
- Diagnostics:
  - `repro/runs/20260211_120855/fit/diagnostics/exdqlm_univar/q=50/q50_exdqlm_univar_diagnostics.json`
  - `repro/runs/20260211_120855/fit/diagnostics/ndlm_main/ndlm_main_diagnostics.json`

## Write-Audit

- `repro/runs/20260211_120855/validate/write_audit/fit/fs_diff.patch` size = `0`
- `repro/runs/20260211_120855/validate/write_audit/post/fs_diff.patch` size = `0`
- `repro/runs/20260211_120855/validate/write_audit/validate/fs_diff.patch` size = `0`
- `repro/runs/20260211_120855/validate/write_audit/report/fs_diff.patch` size = `0`

## Post Run-Scoped Proof

- Post runner log:
  - `repro/runs/20260211_120855/post/logs/post_runner.log`
- Root-load grep (`/data/muscat_data/jaguir26/project1_ucsc_phd/(variables_|DISC_variables_)`) over post logs:
  - no matches
- Run-scoped model-state paths logged for DISC-W, univar, NDLM under `repro/runs/20260211_120855/fit/...`.

## Note

- `repro/tools/validate_run.sh` reports `FAIL` for this smoke because it enforces 7 quantiles for DISC-W. This P6 smoke intentionally runs only `q=0.50` for bounded runtime.

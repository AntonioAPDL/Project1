# P3 Univariate Theory Contract-Check Smoke

- Config: `config/unified_runs/smoke_p3_univar_theory_contracts.yaml`
- Command:
  - `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/smoke_p3_univar_theory_contracts.yaml`
- Run ID: `20260211_094533`
- Run root: `repro/runs/20260211_094533`

## Closure Evidence

- Manifest: `repro/runs/20260211_094533/run_manifest.yaml`
- `finished_at_utc`: `2026-02-11T17:47:34Z`
- Model-state artifact:
  - `repro/runs/20260211_094533/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`

## Contract Check Evidence

- Report directory:
  - `repro/runs/20260211_094533/fit/contract_checks/exdqlm_univar/q=50/`
- Reports:
  - `repro/runs/20260211_094533/fit/contract_checks/exdqlm_univar/q=50/q50_exdqlm_univar_contract_check.json`
  - `repro/runs/20260211_094533/fit/contract_checks/exdqlm_univar/q=50/q50_exdqlm_univar_contract_check.yaml`
- Report status: `pass`

## Write-Audit Evidence

- Diff file: `repro/runs/20260211_094533/validate/write_audit/fit/fs_diff.patch`
- Size: `0` bytes
- Enforcement settings:
  - `write_audit.enforce_from_stage: 2`
  - `write_audit.allowlist_outside_run_root: []`

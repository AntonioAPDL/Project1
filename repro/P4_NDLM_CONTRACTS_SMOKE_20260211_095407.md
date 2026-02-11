# P4 NDLM Theory Contract-Check Smoke

- Config: `config/unified_runs/smoke_p4_ndlm_theory_contracts.yaml`
- Command:
  - `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/smoke_p4_ndlm_theory_contracts.yaml`
- Run ID: `20260211_095407`
- Run root: `repro/runs/20260211_095407`

## Closure Evidence

- Manifest: `repro/runs/20260211_095407/run_manifest.yaml`
- `finished_at_utc`: `2026-02-11T17:57:06Z`
- Model-state artifact:
  - `repro/runs/20260211_095407/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`

## Contract Check Evidence

- Report directory:
  - `repro/runs/20260211_095407/fit/contract_checks/ndlm_main/`
- Reports:
  - `repro/runs/20260211_095407/fit/contract_checks/ndlm_main/ndlm_main_contract_check.json`
  - `repro/runs/20260211_095407/fit/contract_checks/ndlm_main/ndlm_main_contract_check.yaml`
- Report status: `pass`
- Theory summary log checked by contract validator:
  - `repro/runs/20260211_095407/fit/ndlm_main/logs/ndlm_theory_summary.log`

## Write-Audit Evidence

- Diff file: `repro/runs/20260211_095407/validate/write_audit/fit/fs_diff.patch`
- Size: `0` bytes
- Enforcement settings:
  - `write_audit.enforce_from_stage: 2`
  - `write_audit.allowlist_outside_run_root: []`

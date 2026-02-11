# PD Theory Diagnostics Smoke

- Config: `config/unified_runs/smoke_pD_theory_diagnostics.yaml`
- Command:
  - `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/smoke_pD_theory_diagnostics.yaml`
- Run ID: `20260211_101249`
- Run root: `repro/runs/20260211_101249`

## Closure Evidence

- Manifest: `repro/runs/20260211_101249/run_manifest.yaml`
- `finished_at_utc`: `2026-02-11T18:16:50Z`

## Fit Artifacts

- Univariate theory model state:
  - `repro/runs/20260211_101249/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
- NDLM theory model state:
  - `repro/runs/20260211_101249/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`

## Contract Check Reports

- Univariate:
  - `repro/runs/20260211_101249/fit/contract_checks/exdqlm_univar/q=50/q50_exdqlm_univar_contract_check.yaml`
  - `repro/runs/20260211_101249/fit/contract_checks/exdqlm_univar/q=50/q50_exdqlm_univar_contract_check.json`
  - status: `pass`
- NDLM:
  - `repro/runs/20260211_101249/fit/contract_checks/ndlm_main/ndlm_main_contract_check.yaml`
  - `repro/runs/20260211_101249/fit/contract_checks/ndlm_main/ndlm_main_contract_check.json`
  - status: `pass`

## Diagnostics Reports

- Univariate diagnostics:
  - `repro/runs/20260211_101249/fit/diagnostics/exdqlm_univar/q=50/q50_exdqlm_univar_diagnostics.yaml`
  - `repro/runs/20260211_101249/fit/diagnostics/exdqlm_univar/q=50/q50_exdqlm_univar_diagnostics.json`
  - status: `pass`
- NDLM diagnostics:
  - `repro/runs/20260211_101249/fit/diagnostics/ndlm_main/ndlm_main_diagnostics.yaml`
  - `repro/runs/20260211_101249/fit/diagnostics/ndlm_main/ndlm_main_diagnostics.json`
  - status: `pass`

## Write-Audit Evidence

- Diff file: `repro/runs/20260211_101249/validate/write_audit/fit/fs_diff.patch`
- Size: `0` bytes
- Enforcement settings:
  - `write_audit.enforce_from_stage: 2`
  - `write_audit.allowlist_outside_run_root: []`

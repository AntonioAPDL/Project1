# P4 NDLM Theory Smoke Report

- Config: `config/unified_runs/smoke_p4_ndlm_theory.yaml`
- Command:
  - `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/smoke_p4_ndlm_theory.yaml`
- Run ID: `20260210_235222`
- Run root: `repro/runs/20260210_235222`

## Closure Evidence

- Manifest: `repro/runs/20260210_235222/run_manifest.yaml`
- `finished_at_utc`: `2026-02-11T07:55:22Z`
- NDLM output:
  - `repro/runs/20260210_235222/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
- NDLM logs:
  - `repro/runs/20260210_235222/fit/ndlm_main/logs/ndlm_theory.log`
  - `repro/runs/20260210_235222/fit/ndlm_main/logs/ndlm_theory_summary.log`

## Write-Audit Evidence

- Diff file: `repro/runs/20260210_235222/validate/write_audit/fit/fs_diff.patch`
- Size: `0` bytes
- Enforcement settings in config:
  - `write_audit.enforce_from_stage: 2`
  - `write_audit.allowlist_outside_run_root: []`

## Compatibility + Schema Notes

- Saved NDLM model-state contains legacy-compatible aliases required by post:
  - `new.theta.out_50_NDLM_synth_DISC`
  - `samp.theta_50_NDLM_synth_DISC`
  - `samp.sigma_50_NDLM_synth_DISC`
  - `samp.theta_ens_50_NDLM_synth_DISC`
  - `seq.elbo_50_NDLM_synth_DISC`
  - `seq.sigma_50_NDLM_synth_DISC`
  - `delta_50_NDLM_synth_DISC`
- Run-scoped NDLM summary confirms theory mode output and stochastic variance terms:
  - `implementation_mode=theory_aligned`
  - `sigma=0.73826759`
  - `w_hist=0.00000357`
  - `w_fore=0.00000356`
  - `T=16034`, `K=10`

## Root-Path Safety

- Output produced under run root only for this smoke path.
- Existing historical root file (`DISC_variables_50_NDLM_synth_DISC.RData`, timestamp `2025-05-21`) was not used as output target for this run.

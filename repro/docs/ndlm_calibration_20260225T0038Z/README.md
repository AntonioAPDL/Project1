# NDLM Calibration Lane r01 (2026-02-25)

Run ID: `diag_ndlm_only_calib_r01_20260225_003151`

## Stage closure

- Manifest: `repro/runs/diag_ndlm_only_calib_r01_20260225_003151/run_manifest.yaml`
- Status: `forecats=skip`, `data_prep_shared=pass`, `fit=pass`, `post=pass`, `validate=pass`, `report=pass`
- `finished_at_utc`: `2026-02-25T00:35:43Z`

## NDLM fit diagnostics

- Theory log: `repro/runs/diag_ndlm_only_calib_r01_20260225_003151/fit/ndlm_main/logs/ndlm_theory.log`
- Theory summary: `repro/runs/diag_ndlm_only_calib_r01_20260225_003151/fit/ndlm_main/logs/ndlm_theory_summary.log`
- Key summary values:
  - `iterations_completed=800`
  - `converged=false`
  - `convergence_reason=max_iter_reached`
  - `sigma=1.11738804`
  - `K_overlap=10`, `K_max=28`, `segment_lengths=[10,18]`

## NDLM post/diagnostic figures for visual review

Folder: `repro/runs/diag_ndlm_only_calib_r01_20260225_003151/diagnostics/ndlm/`

- `ndlm_elbo_trace.png`
- `ndlm_sigma_trace.png`
- `ndlm_state_norm_trace.png`
- `ndlm_dynamic_fit_full.png`
- `ndlm_dynamic_fit_2012_2016.png`
- `ndlm_dynamic_fit_2017_2019.png`
- `ndlm_dynamic_fit_2018_2020.png`

## Supporting tables

- `ndlm_iter_trace.csv`
- `ndlm_fit_series.csv`
- `ndlm_fit_vs_observed_coverage.csv`
- `ndlm_plot_contract_check.csv`
- `ndlm_object_shapes.csv`
- `ndlm_time_coverage.csv`
- `horizon_contract_check.csv`


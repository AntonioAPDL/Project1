# NDLM baseline note

Context:
- Checklist: `repro/MODEL_FIT_REFACTOR_TRACKER.md` section 7 (active NDLM calibration debug).
- No model refit executed for this checklist execution.
- Baseline run used: `repro/runs/diag_p10_ndlm_only_specalign_r05_20260225_073723`.

Run facts (from `ndlm_theory_summary.log`):
- `iterations_completed=2000`
- `convergence_reason=max_iter_reached`
- `sigma=0.56936055`
- `w_hist=1.0e-7`
- `w_fore=1.25e-7`
- `df_t=df_s1=df_s2=df_s67=df_discrep=df_trans=df_covs=0.9999999`
- `lambda=0.97`

Observed quality signal (from `ndlm_fit_vs_observed_coverage.csv`):
- `rmse=1.51326207785375e-4`
- `mae=4.71414285113565e-5`
- `corr=0.999999982284536`
- Potential symptom: apparent overfitting in retrospective fit diagnostics.

Evidence anchors:
- `repro/runs/diag_p10_ndlm_only_specalign_r05_20260225_073723/run_manifest.yaml`
- `repro/runs/diag_p10_ndlm_only_specalign_r05_20260225_073723/fit/ndlm_main/logs/ndlm_theory_summary.log`
- `repro/runs/diag_p10_ndlm_only_specalign_r05_20260225_073723/diagnostics/ndlm/ndlm_iter_trace.csv`
- `repro/runs/diag_p10_ndlm_only_specalign_r05_20260225_073723/diagnostics/ndlm/ndlm_fit_vs_observed_coverage.csv`

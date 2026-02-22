# Q-02 Verification Ladder

Generated at: 2026-02-22T22:42:00Z

## 1) Targeted tests

- Command:
  - `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_univar_convergence_contract.R'); testthat::test_file('tests/testthat/test_post_module_plan.R')"`
- Result: `pass`
- Evidence:
  - `tests/testthat/test_univar_convergence_contract.R`
  - `tests/testthat/test_post_module_plan.R`

## 2) Univar-only rerun (fit-focused)

- Run id: `diag_q02_univar_only_full7_relfix_20260222_225800`
- Status snapshot:
  - `forecats=pass`
  - `data_prep_shared=pass`
  - `fit=pass`
  - `post=fail` (pre-family-aware-post fix)
- Root-cause of post failure in this run:
  - NDLM bundle load attempted with empty path in univar-only mode.
- Evidence:
  - `repro/runs/diag_q02_univar_only_full7_relfix_20260222_225800/run_manifest.yaml`
  - `repro/runs/diag_q02_univar_only_full7_relfix_20260222_225800/post/logs/post_runner.log`

## 3) Post check for univar outputs (after post family-aware fix)

- Run id: `diag_q02_univar_full7_postonly_sourcerun_r05_20260222_223657`
- Source fit outputs:
  - `diag_q02_univar_only_full7_relfix_20260222_225800`
- Status snapshot:
  - `post=pass`
  - `finished_at_utc` non-null
- Output artifact contract summary:
  - `total_artifact_files=4`
  - `has_figure=true`
  - `table_exports_present=true`
  - `synthesis_core_shapes_ok=true`
- Evidence:
  - `repro/runs/diag_q02_univar_full7_postonly_sourcerun_r05_20260222_223657/run_manifest.yaml`
  - `repro/runs/diag_q02_univar_full7_postonly_sourcerun_r05_20260222_223657/post/logs/post_runner.log`
  - `repro/runs/diag_q02_univar_full7_postonly_sourcerun_r05_20260222_223657/post/outputs/diag_q02_univar_full7_postonly_sourcerun_r05_20260222_223657/post_artifacts_manifest.csv`
  - `repro/runs/diag_q02_univar_full7_postonly_sourcerun_r05_20260222_223657/post/outputs/diag_q02_univar_full7_postonly_sourcerun_r05_20260222_223657/post_artifacts_summary.json`

## 4) Convergence impact summary

- Baseline q01/q99 were `max_iter_reached` at 800 iterations.
- In rel-contract univar full-7 fit run:
  - q01 converged at 179
  - q99 converged at 70
- Evidence:
  - `repro/docs/q02_univar_20260222T212607Z/univar_symptom_table.csv`
  - `repro/docs/q02_univar_20260222T212607Z/univar_relfix_full7_symptom_table.csv`
  - `repro/docs/q02_univar_20260222T212607Z/univar_relfix_full7_vs_baseline.csv`

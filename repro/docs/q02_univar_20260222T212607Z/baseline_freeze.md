# Q-02 Univar Baseline Freeze

- generated_at_utc: `2026-02-22T21:26:07Z`
- canonical_run_id: `prod_canonical_full_e2e_parallel_onecore_refresh_20260221`
- canonical_manifest: `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/run_manifest.yaml`
- finished_at_utc: `2026-02-22T01:26:59Z`
- stage_status: `{'forecats': 'pass', 'data_prep_shared': 'pass', 'fit': 'pass', 'post': 'pass', 'validate': 'pass', 'report': 'pass'}`

## Baseline artifacts (univar-focused)

- Univar fit logs/summaries:
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=01/logs/univar_theory.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=01/logs/univar_theory_summary.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=05/logs/univar_theory.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=05/logs/univar_theory_summary.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=10/logs/univar_theory.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=10/logs/univar_theory_summary.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=50/logs/univar_theory.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=50/logs/univar_theory_summary.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=90/logs/univar_theory.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=90/logs/univar_theory_summary.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=95/logs/univar_theory.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=95/logs/univar_theory_summary.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=99/logs/univar_theory.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/exdqlm_univar/q=99/logs/univar_theory_summary.log`
- Univar symptom table:
  - `repro/docs/q02_univar_20260222T212607Z/univar_symptom_table.csv`
- Post outputs (relevant):
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/post/outputs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/All_exal_DISC.png` (exists=False)
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/post/outputs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/Allth_exal_DISC.png` (exists=True)
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/post/outputs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/plot_all_quantiles_combined_DISC.png` (exists=True)
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/post/outputs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/plot_combined_matrix_DISC.png` (exists=True)
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/post/outputs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/plot_3_row_matrix_DISC.png` (exists=True)
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/post/outputs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/All_ELBOS_DISC.png` (exists=True)
- Post manifest/summary:
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/post/outputs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/post_artifacts_manifest.csv`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/post/outputs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/post_artifacts_summary.json`

## Initial interpretation (pre-fix)

- Expected extreme-quantile difficulty signal:
  - q=01 converged=false reason=max_iter_reached iter=800 elbo_trend=increasing_last3
  - q=99 converged=false reason=max_iter_reached iter=800 elbo_trend=increasing_last3
- Mid-quantile control:
  - q=50 converged=true reason=all_convergence_criteria_met iter=70 elbo_trend=mixed_last3
- Potential implementation/wiring defect evidence: none obvious at baseline (all stages pass; only selected tails hit max_iter).

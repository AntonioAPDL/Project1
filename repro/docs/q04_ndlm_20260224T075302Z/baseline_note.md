# Q-04 NDLM Root-Cause Baseline (2026-02-24T07:53:02Z)

## Scope
- Focused on NDLM quality lane (`Q-04`) only.
- No multiv/univar post-contract rewrites in this step.

## Baseline evidence reviewed
- Canonical all-family pass run:
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/run_manifest.yaml`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/ndlm_main/logs/ndlm_theory.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/ndlm_main/logs/ndlm_theory_summary.log`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/fit/diagnostics/ndlm_main/ndlm_main_diagnostics.json`
  - `repro/runs/prod_canonical_full_e2e_parallel_onecore_refresh_20260221/diagnostics/ndlm/ndlm_plot_contract_check.csv`
- Prior NDLM isolation run:
  - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/run_manifest.yaml`
  - `repro/runs/diag_q01a_ndlm_only_sharedseed_fitpost_resume_sharedfix_20260220_215704/fit/ndlm_main/logs/ndlm_theory_summary.log`

## Baseline finding
- NDLM fit loop was hard-capped by code constant (`n_iter=16`) in `R/unified/families/ndlm_main/00_constants.R`, with no config-driven convergence schedule.
- This was inconsistent with unified fit policy used in exDQLM families and made NDLM quality behavior insensitive to run config.

## Root-cause classification
- Primary root cause: **implementation/wiring defect** (fit-loop control not wired into config/env), not post plotting.
- Secondary noise source: diagnostics warning assumed `delta >= 0`, but NDLM discrepancy deltas are signed by construction.

## Fix intent
- Wire NDLM fit-loop controls through unified config -> stage env -> NDLM constants.
- Add explicit convergence metadata in NDLM summary logs.
- Replace invalid nonnegativity warning with sign-balance warning (informational).

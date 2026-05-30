# exDQLM Multivar Keep Grid Guard Promotion - 2026-05-30

## Purpose

This note records the promotion of the validated gamma/sigma coherence repair into the active epsilon/discount grid
tooling. It is the implementation follow-up to:

- `docs/exdqlm_multivar_keep_gamma_sigma_coherence_guard_20260529.md`
- `reports/he2_exdqlm_multivar_keep_gamsig_coherence_full7_validation_20260529/DIAGNOSTIC_20260530.md`
- `docs/exdqlm_multivar_keep_grid_evaluation_plan_20260524.md`

The goal is to make the grid robust and auditable without hiding model failures. A failed aggressive
discount/epsilon row is still valid information, but it must fail at the correct layer with enough diagnostics to
select or reject the specification reproducibly.

## Validation Evidence Being Promoted

The full-seven validation row
`multimodel_20221225_v8_he2grid_c03_eps060_exdqlm_multivar_keep_gamsigcoh_full7` completed
`data_prep_shared`, `fit`, `post`, `validate`, and `report` under commit `e5133b2`.

Key evidence from the untracked runtime diagnostic:

| check | result |
| --- | --- |
| known pathological lane | `20221225 c03_eps060 q20` |
| old failure signature | accepted negative `E[a^2/(b sigma)] = -108.90929` before pseudo-data blow-up |
| new behavior | `[gamsig_rollback]` at q20 iter 46 rejects that candidate |
| q20 final status | reaches iter 100 and sampling finalization |
| pseudo-data failures | 0 |
| post/validate/report | pass |
| `.RData` cleanup | before 7, removed 7, remaining 0 |

This is strong evidence for the known gamma/sigma-to-latent-to-pseudo-data failure chain, but it is not a proof that
every future grid row is clean. The grid evaluator now distinguishes `clean`, `guarded_pass`, and `failed` rows so this
caveat remains visible during CRPS selection. Near-zero gamma/sigma fallback is recorded as a warning, not as a
selection penalty by itself, because it is common in stable completed grid rows and is not the same as a rollback,
latent-boundary event, pseudo-data guard event, or fatal failure.

## Promoted Runtime Policy

The active default pseudo-data guard mode is now fail-fast instead of warning:

| file | contract |
| --- | --- |
| `R/unified/config.R:373-375` | default `fit.exdqlm_multivar.pseudodata_guard.mode = "fail"` |
| `R/unified/config.R:2249-2254` | config validation falls back to `"fail"` and only accepts `warn` or `fail` |
| `R/unified/stages/stage_fit.R:1091-1096` | fit-stage environment export defaults `DISC_PSEUDODATA_GUARD_MODE` to `"fail"` |

The grid config builder now explicitly writes the guard block into every generated spec/cutoff config:

| file | contract |
| --- | --- |
| `scripts/build_he2_exdqlm_multivar_keep_grid_configs.py:150-166` | enables gamma/sigma coherence rollback and terminal sampling guard |
| `scripts/build_he2_exdqlm_multivar_keep_grid_configs.py:167-170` | enables pseudo-data guard in `fail` mode |

Required generated-config defaults for the grid:

```yaml
fit:
  exdqlm_multivar:
    gamma_sigma:
      coherence_guard:
        enabled: true
        rollback_on_guard: true
        min_uts_psi: 1.0e-8
        nonnegative_tol: 1.0e-10
      terminal_sampling_guard:
        mode: fail_fast
        min_guard_count: 1
        max_guard_lag_iters: 20
        require_frozen: true
    pseudodata_guard:
      enabled: true
      mode: fail
```

## Report Discovery After `.RData` Cleanup

The validation row exposed a report-only problem: after successful post cleanup, `report/summary.md` could show blank
`families.exdqlm_multivar.quantiles_found` even when all seven lane directories were present and complete. That made
cleaned successful runs look incomplete.

The report stage now merges artifact-based discovery with filesystem discovery:

| file | contract |
| --- | --- |
| `R/unified/stages/stage_report.R:133-185` | adds mode-aware q-directory discovery from `fit/exdqlm_multivar/<mode>/q=XX` plus legacy `fit/q=XX` |
| `R/unified/stages/stage_report.R:303-314` | merges artifact and filesystem quantile evidence before family summary construction |
| `R/unified/stages/stage_report.R:389-407` | writes `rdata_cleanup` into `report/summary.json` |
| `R/unified/stages/stage_report.R:454-467` | writes cleanup remaining count into `report/summary.md` |

The new test `tests/testthat/test_unified_stage_report_quantiles.R` creates q directories with no `.RData` and verifies
that the report still finds the multivariate keep quantiles and records cleanup remaining as zero.

## Monitor And Evaluator Stability Taxonomy

The live monitor now surfaces the layer implicated by each lane:

| file | contract |
| --- | --- |
| `scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py:137-205` | scans fit logs for gamma/sigma rollbacks, latent guards, pseudo-data guards, near-zero fallbacks, and fatal errors |
| `scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py:217-309` | adds cleanup fields, remaining `.RData` count, output state, and failure layer |
| `scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py:342-368` | writes a compact live table with rollback, latent, pseudo-data, fatal, output, and layer columns |

The grid evaluator now writes stability diagnostics and uses them in eligibility and selection:

| file | contract |
| --- | --- |
| `scripts/evaluate_he2_exdqlm_multivar_keep_grid.py:60-175` | collects run-level stability diagnostics from q-lane logs and cleanup manifest |
| `scripts/evaluate_he2_exdqlm_multivar_keep_grid.py:270-339` | adds stability diagnostics to artifact gates and marks hard failures ineligible |
| `scripts/evaluate_he2_exdqlm_multivar_keep_grid.py:384-411` | ranks eligible rows by stability tier before CRPS |
| `scripts/evaluate_he2_exdqlm_multivar_keep_grid.py:478-516` | reports stability-status counts and new output tables |
| `scripts/evaluate_he2_exdqlm_multivar_keep_grid.py:551-558` | writes `grid_stability_diagnostics.csv` and `grid_guarded_candidate_log.csv` |

Stability statuses:

| status | meaning | ranking behavior |
| --- | --- | --- |
| `clean` | no rollback, latent guard, pseudo-data event, fatal error, or cleanup anomaly found; may still carry a near-zero fallback warning | preferred tier |
| `guarded_pass` | run passed, but used a rollback or guard that should remain visible | eligible, but lower priority than clean rows |
| `failed` | fatal error, pseudo-data guard failure, or `.RData` cleanup anomaly | ineligible |

This policy avoids two bad outcomes: it does not hide instability behind CRPS, and it does not automatically discard a
known recovered row like the q20 validation case when no clean alternative exists.

The first full-grid evaluator pass after this promotion showed that most warnings were benign near-zero fallback
events, with no gamma/sigma rollbacks and no latent-parameter guards in completed rows. Therefore near-zero fallback is
kept in `stability_warning` but no longer moves a run from `clean` to `guarded_pass`.

## CRPS Selection Rule After Promotion

Per-cutoff model selection remains based on forecast-window CRPS for `exdqlm_multivar_synth_keep` on
`log_cms_plus1`, but eligibility now includes stability and cleanup:

1. Exclude rows with failed fit/post/validate/report, missing post contract, missing CRPS, bad input health, bad
   quantile synthesis, missing q50 component contract, or missing q50 trace.
2. Exclude rows with hard stability failures: fatal log errors, pseudo-data guard failures, or retained `.RData` after
   successful cleanup.
3. Rank eligible rows by `selection_tier` first: `clean` before `guarded_pass`, where near-zero-only rows remain
   `clean`.
4. Within the same tier, rank by mean CRPS, median CRPS, worst-lead CRPS, then grid spec id.
5. Preserve all failed and guarded rows in CSV outputs so the final selection doc can explain why a low-CRPS run was
   rejected or demoted.

## Tests Run

Commands:

```bash
Rscript --vanilla -e "parse('R/unified/config.R'); parse('R/unified/stages/stage_fit.R'); parse('R/unified/stages/stage_report.R')"
python3 -m py_compile scripts/monitor_he2_exdqlm_multivar_keep_allcutoffs.py scripts/evaluate_he2_exdqlm_multivar_keep_grid.py scripts/build_he2_exdqlm_multivar_keep_grid_configs.py
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_config_mode_resolution.R')"
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_unified_stage_report_quantiles.R')"
python3 -m unittest tests.python.test_he2_exdqlm_keep_allcutoff_monitor tests.python.test_he2_exdqlm_keep_grid_tooling tests.python.test_he2_exdqlm_keep_grid_next_steps -v
```

Results:

| check | result |
| --- | --- |
| R parse for config/fit/report | pass |
| Python py_compile for builder/monitor/evaluator | pass |
| unified config tests | pass, 82 expectations |
| report quantile cleanup test | pass, 5 expectations |
| Python monitor/grid/evaluator tests | pass, 10 tests |

## Remaining Work Before Final Grid Selection

1. Re-run the grid evaluator on the current grid root after all active/relaunched rows finish.
2. Review `grid_stability_diagnostics.csv` before accepting winners; a `guarded_pass` winner is acceptable only if no
   clean row has comparable CRPS for that cutoff. Near-zero-only warnings should be interpreted separately from
   rollback/latent/pseudo-data guards.
3. Inspect `grid_guarded_candidate_log.csv` for repeated q20-style rollbacks or frequent latent boundary events.
4. Treat any `pseudodata_guard_fail` row as a real failed spec/cutoff unless a separate source-lock investigation finds
   an input or wiring error.
5. Freeze final winners in a tracked grid-selection document with CRPS, raw forecast controls, stability tier, cleanup
   proof, and winner figure paths.

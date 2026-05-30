# exDQLM Multivar Keep Guard-Promotion Grid Readout - 2026-05-30

## Scope

This is the first guard-aware readout of the 2026-05-24 epsilon/discount grid after promoting the gamma/sigma
coherence repair and pseudo-data fail-fast policy. It is based on the read-only evaluator output:

`reports/exdqlm_multivar_keep_grid_eval_guard_promotion_20260530_nearzero_warning`

The report directory is intentionally untracked. This tracked note freezes the key results and the immediate recovery
plan.

## Evaluation Policy

The corrected evaluator policy is:

1. fatal errors, pseudo-data guard failures, and `.RData` cleanup anomalies are hard failures;
2. gamma/sigma rollbacks, latent-parameter guards, and pseudo-data guard events are visible stability events;
3. near-zero gamma/sigma fallback remains visible in `stability_warning`, but is not a selection penalty by itself;
4. eligible rows are ranked by stability tier and then forecast-window mean CRPS for
   `exdqlm_multivar_synth_keep` on `log_cms_plus1`.

This distinction matters. A first pass that treated near-zero-only fallback as `guarded_pass` selected overly
conservative, worse-CRPS rows. The corrected pass keeps near-zero-only rows eligible as `clean` with warnings.

## Grid Health

| item | count |
| --- | ---: |
| spec-cutoff rows evaluated | 150 |
| eligible rows | 147 |
| failed/ineligible rows | 3 |
| clean rows | 147 |
| failed rows | 3 |

Per-cutoff stability counts:

| cutoff | clean | failed |
| --- | ---: | ---: |
| 20210123 | 29 | 1 |
| 20211112 | 30 | 0 |
| 20211221 | 30 | 0 |
| 20220511 | 29 | 1 |
| 20221225 | 29 | 1 |

Across the old grid root, completed rows had no gamma/sigma rollbacks and no latent-parameter guards. The only
warnings in completed rows were near-zero fallback events.

## Current Winners

| cutoff | winner | mean CRPS | median CRPS | max CRPS | warning | runner-up | runner-up mean CRPS | diff |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: |
| 20210123 | `c04_eps365` | 0.139709 | 0.083939 | 0.519274 | near-zero fallback 1 | `c05_eps365` | 0.143020 | 0.003311 |
| 20211112 | `c04_eps365` | 0.047236 | 0.044288 | 0.080426 | near-zero fallback 5 | `c04_eps180` | 0.048527 | 0.001290 |
| 20211221 | `c03_eps030` | 0.265372 | 0.137032 | 1.136538 | near-zero fallback 1 | `c02_eps030` | 0.276953 | 0.011581 |
| 20220511 | `c02_eps060` | 0.032325 | 0.026597 | 0.094507 | near-zero fallback 2 | `c03_eps090` | 0.032891 | 0.000566 |
| 20221225 | `c05_eps030` | 0.665460 | 0.576694 | 2.223163 | near-zero fallback 1 | `c04_eps030` | 0.667628 | 0.002168 |

These are provisional winners because three grid rows failed before producing CRPS. Two of the current winner margins
are very small, so the failed rows should be recovered before declaring final winners.

## Raw Forecast Controls For Current Winners

| cutoff | winner | synth mean CRPS | GloFAS mean CRPS | NWS/NWM mean CRPS | note |
| --- | --- | ---: | ---: | ---: | --- |
| 20210123 | `c04_eps365` | 0.139709 | 0.403660 | 0.830366 | NWS/NWM has 8 valid days |
| 20211112 | `c04_eps365` | 0.047236 | 0.169575 | 1.371917 | NWS/NWM has 8 valid days |
| 20211221 | `c03_eps030` | 0.265372 | 0.682464 | 0.281176 | NWS/NWM has 8 valid days |
| 20220511 | `c02_eps060` | 0.032325 | 0.272268 | 0.283659 | NWS/NWM has 8 valid days |
| 20221225 | `c05_eps030` | 0.665460 | 1.560064 | 0.556802 | NWS/NWM has 8 valid days |

## Failed Rows To Recover

| cutoff | spec | failure layer | observed failure | why recover |
| --- | --- | --- | --- | --- |
| 20220511 | `c02_eps090` | pseudo-data/fatal | q20 pseudo-data `FFF` cap exceeded at iter 32 | same old failure family as the gamma/sigma guard repair; winner margin for this cutoff is only 0.000566 |
| 20221225 | `c03_eps060` | pseudo-data/fatal | q20 pseudo-data `FFF` cap exceeded at iter 47 | same known failure signature; a separate full-seven validation row already passed under the guard patch |
| 20210123 | `c06_eps365` | sampling walltime/fatal | q05 sampling walltime exceeded at `sampling_retro_synth_done` | completes the grid; may or may not affect winner selection |

## Recovery Execution

The three failed cells were recovered in an isolated runtime root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_guard_promotion_failed_rows_recovery_20260530`

The recovery launch copied the original grid specifications and input wiring, then used the current promoted guard
policy:

- gamma/sigma coherence guard enabled with rollback;
- terminal sampling fail-fast enabled;
- pseudo-data guard set to fail;
- `.RData/.rda` cleanup enabled after successful post;
- sampling walltime allowance raised for the recovery cells so the old q05 terminal-sampling timeout could finish.

Recovery execution plan:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_guard_promotion_failed_rows_recovery_20260530/control/recovery_exec_plan.csv`

Recovery evaluator output:

`reports/exdqlm_multivar_keep_grid_eval_guard_promotion_failed_rows_recovery_20260530`

All three recovery rows completed `fit`, `post`, `validate`, and `report`. Cleanup removed seven q-output
`.RData/.rda` files per recovered row, leaving zero retained q-output `.RData/.rda` files in the recovery root.

| cutoff | recovered spec | old failure | recovery status | mean CRPS | warning | retained q-output `.RData/.rda` |
| --- | --- | --- | --- | ---: | --- | ---: |
| 20210123 | `c06_eps365` | q05 terminal-sampling walltime at `sampling_retro_synth_done` | `guarded_pass` | 0.190805 | gamma/sigma rollback 1; near-zero fallback 2 | 0 |
| 20220511 | `c02_eps090` | q20 pseudo-data `FFF` cap exceeded at iter 32 | `guarded_pass` | 0.032553 | gamma/sigma rollback 3; near-zero fallback 2 | 0 |
| 20221225 | `c03_eps060` | q20 pseudo-data `FFF` cap exceeded at iter 47 | `guarded_pass` | 0.786710 | gamma/sigma rollback 3; latent-parameter guard 2 | 0 |

Interpretation: the promoted guard stack recovered the old pseudo-data explosion signatures without suppressing the
diagnostic evidence. The recovered rows are not silent clean passes; they remain visible as `guarded_pass` rows because
real gamma/sigma rollbacks and latent guards occurred.

## Final Combined Readout

The final combined untracked report is:

`reports/exdqlm_multivar_keep_grid_eval_guard_promotion_final_20260530`

It combines:

- the corrected original evaluator output in
  `reports/exdqlm_multivar_keep_grid_eval_guard_promotion_20260530_nearzero_warning`;
- the isolated recovery evaluator output in
  `reports/exdqlm_multivar_keep_grid_eval_guard_promotion_failed_rows_recovery_20260530`.

Final grid completion:

| item | count |
| --- | ---: |
| original eligible rows | 147 |
| recovered rows added | 3 |
| final eligible rows | 150 |
| final spec-cutoff cells represented | 150 |
| failed/ineligible cells after recovery | 0 |

Final winners are unchanged after recovery:

| cutoff | final winner | mean CRPS | median CRPS | max CRPS | warning | runner-up by policy | runner-up mean CRPS | diff |
| --- | --- | ---: | ---: | ---: | --- | --- | ---: | ---: |
| 20210123 | `c04_eps365` | 0.139709 | 0.083939 | 0.519274 | near-zero fallback 1 | `c05_eps365` | 0.143020 | 0.003311 |
| 20211112 | `c04_eps365` | 0.047236 | 0.044288 | 0.080426 | near-zero fallback 5 | `c04_eps180` | 0.048527 | 0.001290 |
| 20211221 | `c03_eps030` | 0.265372 | 0.137032 | 1.136538 | near-zero fallback 1 | `c02_eps030` | 0.276953 | 0.011581 |
| 20220511 | `c02_eps060` | 0.032325 | 0.026597 | 0.094507 | near-zero fallback 2 | `c03_eps090` | 0.032891 | 0.000566 |
| 20221225 | `c05_eps030` | 0.665460 | 0.576694 | 2.223163 | near-zero fallback 1 | `c04_eps030` | 0.667628 | 0.002168 |

Raw forecast controls for the final winners:

| cutoff | final winner | synth mean CRPS | GloFAS mean CRPS | NWS/NWM mean CRPS | note |
| --- | --- | ---: | ---: | ---: | --- |
| 20210123 | `c04_eps365` | 0.139709 | 0.403660 | 0.830366 | NWS/NWM has 8 valid days |
| 20211112 | `c04_eps365` | 0.047236 | 0.169575 | 1.371917 | NWS/NWM has 8 valid days |
| 20211221 | `c03_eps030` | 0.265372 | 0.682464 | 0.281176 | NWS/NWM has 8 valid days |
| 20220511 | `c02_eps060` | 0.032325 | 0.272268 | 0.283659 | NWS/NWM has 8 valid days |
| 20221225 | `c05_eps030` | 0.665460 | 1.560064 | 0.556802 | NWS/NWM has 8 valid days |

The main final CSV artifacts are:

- `reports/exdqlm_multivar_keep_grid_eval_guard_promotion_final_20260530/combined_crps_summary_by_spec_cutoff.csv`;
- `reports/exdqlm_multivar_keep_grid_eval_guard_promotion_final_20260530/combined_winners_by_cutoff.csv`;
- `reports/exdqlm_multivar_keep_grid_eval_guard_promotion_final_20260530/combined_top5_by_cutoff_policy_rank.csv`;
- `reports/exdqlm_multivar_keep_grid_eval_guard_promotion_final_20260530/combined_top5_by_cutoff_crps_only.csv`;
- `reports/exdqlm_multivar_keep_grid_eval_guard_promotion_final_20260530/combined_raw_controls_for_winners.csv`;
- `reports/exdqlm_multivar_keep_grid_eval_guard_promotion_final_20260530/recovered_failed_rows_summary.csv`.

## Final Decision

The guard-promotion work is now strong enough to close this grid readout:

1. The old pseudo-data explosion cells were recovered under the promoted gamma/sigma rollback and fail-fast policy.
2. The terminal-sampling walltime cell completed when given a recovery walltime allowance; this did not require a model
   specification change.
3. All 150 spec-cutoff cells now have eligible CRPS rows.
4. The final best-CRPS policy winners are unchanged from the corrected near-zero-warning readout.
5. The remaining scientific caution is that 20220511 has a very small winner margin. The selected row is still the best
   under both policy ranking and mean CRPS, but close alternatives should be retained in the model-comparison table.

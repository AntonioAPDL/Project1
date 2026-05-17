# HE2 exAL Revised-Doc Audit (2026-05-17)

## Scope
This audit checks the three exAL families against the revised-doc integration layer:
- `exdqlm_multivar_keep` (`exAL-M-T1`)
- `exdqlm_multivar_drop` (`exAL-M-T0`)
- `exdqlm_univar` (`exAL-U-T1`)

It certifies four separate things:
1. Did all five cutoff reruns complete through `report`?
2. Did the reruns emit fit/post metrics and synthesis artifacts?
3. Are the revised-doc figure and representative-table sources wired to the completed rerun roots?
4. Is the benchmark CRPS table already authoritative from those completed reruns?

## Executive Summary
- All three exAL rerun families completed through `report` for all five cutoffs.
- All three families emitted the core post-stage metrics tables and synthesis artifacts needed for reproduction.
- `exAL-M-T1` figure wiring is now fully closed, including the historical-support/current-model lane via the retained-support replay contract.
- The representative appendix/source tables (`components`, `gamma`, `sigma`) are wired to the corrected representative `2022-12-25 exAL-M-T1` rerun bundle.
- The benchmark CRPS table is still sourced from the frozen HE2 publication manifest, and the completed shared-spec exAL rerun-local synthesis CRPS values do **not** match those frozen benchmark rows.
- Because of that benchmark mismatch, the exAL family set is **not yet fully certified** as an end-to-end authoritative manuscript table workflow.

## Family Verdicts
| Label | Family | Rerun completion | Post metrics + synthesis | Figure wiring | Benchmark table authoritative? | Overall |
|---|---|---|---|---|---|---|
| `exAL-M-T1` | `exdqlm_multivar_keep` | `complete_5_of_5` | `yes` | `fully_closed_for_figures` | `no` | `figures_closed_benchmark_blocked` |
| `exAL-M-T0` | `exdqlm_multivar_drop` | `complete_5_of_5` | `yes` | `limited_direct_figure_usage` | `no` | `run_complete_benchmark_blocked` |
| `exAL-U-T1` | `exdqlm_univar` | `complete_5_of_5` | `yes` | `reference_synthesis_family_refreshed` | `no` | `run_complete_reference_figure_benchmark_blocked` |

## Revised-Doc Wiring That Is Confirmed Current
- Article figure status counts: `{"unchanged_intentionally": 8, "updated_now": 39}`
- Representative selected-model table sources current: `True`
- Historical-support repaired: `True`
- `tab:components_23_31`, `tab:gamma_sigma_intervals1`, and `tab:gamma_sigma_intervals2` are sourced from `artifacts/representative_selected_model_2022_12_25`, which points at the corrected `20260516` `exAL-M-T1` rerun root.
- The keep-side historical-support/current-model figures now render from the corrected retained-support replay rooted in the completed `20220511 exAL-M-T1` run.

## Benchmark Table Certification Status
- Current benchmark Bayesian source: `artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv`
- This is still the frozen HE2 publication manifest, not a rerun-local exAL source layer.
- The completed shared-spec exAL rerun-local synthesis CRPS values diverge from those frozen benchmark values for all three exAL manuscript labels.

Representative mismatch examples:
| Cutoff | Label | Frozen CRPS | Shared-spec rerun local CRPS | Status |
|---|---:|---:|---:|---|
| `12/25/2022` | `exAL-M-T1` | `0.4375` | `162225957192096.5000` | `mismatch` |
| `12/25/2022` | `exAL-M-T0` | `2.3365` | `287742.7068` | `mismatch` |
| `12/25/2022` | `exAL-U-T1` | `1.1189` | `2.0664` | `mismatch` |

## Key Conclusion
The three exAL run families themselves are reproducible and strong on the rerun/figure side, and `exAL-M-T1` is fully closed for revised-doc figures. The exAL family set is **not yet fully done end to end** because the benchmark CRPS table has not been reconciled to the completed shared-spec rerun outputs. Until that reconciliation is explicit, the exAL runs are figure-authoritative and representative-table-authoritative, but not yet benchmark-table-authoritative.


# NDLM Post-Correction Reaudit Workflow

Last updated: 2026-04-21  
Status: complete

## Objective

Reaudit the **current corrected NDLM implementation** after the successful featurecov rerun, with the goal of determining whether the remaining poor NDLM CRPS values are:

- a genuine modeling result, or
- evidence of a remaining implementation/theory bug

This workflow starts **after** the earlier parity audit has already fixed:

- mixed provenance
- stale input contract
- missing engineered feature activation
- missing deterministic-climate blending
- inactive multivariate prior knobs
- launch-time USGS and post-stage bugs

## Current Trigger

The corrected rerun completed successfully, but some NDLM values remain unexpectedly poor:

| Label | 01/23/2021 | 11/12/2021 | 12/21/2021 | 05/11/2022 | 12/25/2022 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `N-U-T1` | `0.3520` | `0.2486` | `1.1768` | `0.1572` | `2.1451` |
| `N-M-T0` | `0.5257` | `0.7126` | `3.5474` | `2.0727` | `4.2233` |
| `N-M-T1` | `0.5930` | `0.8524` | `13.9269` | `2.2880` | `8.9743` |

These are now the right numbers to investigate.

## Starting Evidence

- Corrected rerun summary:
  [ndlm_final_audit_summary.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/ndlm_final_audit_summary.md)
- Corrected rerun workflow:
  [NDLM_FEATURECOV_RERUN_WORKFLOW.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/NDLM_FEATURECOV_RERUN_WORKFLOW.md)
- Corrected rerun root:
  [/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420)

## Phase Structure

### Phase 0. Scope freeze

Deliverables:

- [TRACKER_NDLM_REAUDIT_POSTCORRECTION.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/TRACKER_NDLM_REAUDIT_POSTCORRECTION.md)
- [NDLM_REAUDIT_SCOPE_20260421.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/NDLM_REAUDIT_SCOPE_20260421.md)

Purpose:

- freeze the post-correction objective
- distinguish this reaudit from the earlier provenance/fairness audit
- define the anomaly priorities

### Phase 1. Corrected rerun anomaly characterization

Deliverables:

- `ndlm_reaudit_anomaly_digest.csv`
- `ndlm_reaudit_anomaly_digest.md`

Purpose:

- characterize the remaining NDLM failures by cutoff and family
- identify whether the main pathology is centered in:
  - multivariate vs univariate
  - `keep` vs `drop`
  - specific cutoffs
  - specific forecast leads

Must answer:

- where exactly is the NDLM behavior implausible?
- is the main problem mean bias, variance inflation, or lead-specific collapse?

Status:

- complete
- outputs:
  - [ndlm_reaudit_anomaly_digest.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_reaudit_anomaly_digest.csv)
  - [ndlm_reaudit_anomaly_digest.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_reaudit_anomaly_digest.md)

### Phase 2. Corrected runtime inventory and contract freeze

Deliverables:

- `ndlm_reaudit_runtime_inventory.csv`
- `ndlm_reaudit_runtime_inventory.md`

Purpose:

- freeze the exact corrected rerun artifacts
- capture the runtime objects we will inspect in later phases

Must record:

- run manifests
- resolved configs
- key fit/post outputs
- diagnostic folders
- predictive tables and caches

Status:

- complete
- outputs:
  - [ndlm_reaudit_runtime_inventory.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_reaudit_runtime_inventory.csv)
  - [ndlm_reaudit_runtime_inventory.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_reaudit_runtime_inventory.md)

### Phase 3. Forecast scoring and post-processing audit

Deliverables:

- `ndlm_scoring_audit.md`
- optional scoring trace tables/scripts

Purpose:

- verify that NDLM CRPS and forecast-window summaries are computed correctly

Must answer:

- are NDLM outputs scored on the intended transformed scale?
- are the correct predictive objects used?
- are the forecast-window quantiles and CRPS inputs internally consistent?

Status:

- complete
- output:
  - [ndlm_scoring_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_scoring_audit.md)

### Phase 4. Posterior predictive generation audit

Deliverables:

- `ndlm_predictive_generation_audit.md`

Purpose:

- inspect the generated predictive samples and quantiles directly

Must answer:

- do predictive draws look numerically stable?
- do quantiles and means behave sensibly?
- is there evidence of transformation or back-transformation distortion?

Status:

- complete
- outputs:
  - [ndlm_predictive_generation_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_predictive_generation_audit.md)
  - [ndlm_predictive_cache_summaries.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_predictive_cache_summaries.csv)
  - [ndlm_vs_quantile_predictive_scale.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_vs_quantile_predictive_scale.csv)
  - [ndlm_sigma_mixing_replay.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_sigma_mixing_replay.csv)

### Phase 5. Multivariate state/measurement/transfer audit

Deliverables:

- `ndlm_multivar_contract_audit.md`

Purpose:

- inspect the multivariate NDLM path where the worst anomalies occur

Must answer:

- is `keep` really doing what we think it does?
- are transfer and discrepancy states entering forecast mode correctly?
- are measurement loads, state dimensions, and active-set-by-lead structures sensible?

Status:

- complete
- output:
  - [ndlm_multivar_contract_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_multivar_contract_audit.md)

### Phase 6. Forecast covariance, prior, and discount-dynamics audit

Deliverables:

- `ndlm_covariance_dynamics_audit.md`

Purpose:

- inspect whether the current multivariate NDLM dynamics are stable under the corrected contract

Must answer:

- is variance exploding?
- are state/covariance updates sensible through the forecast window?
- do the worst cutoffs show obvious instability signatures?

Status:

- complete
- output:
  - [ndlm_covariance_dynamics_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_covariance_dynamics_audit.md)

### Phase 7. Synthetic numerical harness

Deliverables:

- `ndlm_synthetic_harness_report.md`

Purpose:

- test the NDLM implementation in a controlled setting where expected Gaussian behavior is known

Must answer:

- does the implementation behave correctly in simple reference cases?
- if not, where does it diverge from theory?

Status:

- complete
- outputs:
  - [ndlm_synthetic_harness_report.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_synthetic_harness_report.md)
  - [ndlm_kalman_congruence_checks.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_kalman_congruence_checks.csv)

### Phase 8. Instrumented replay of worst cutoffs

Deliverables:

- replay logs and a short replay report

Priority rows:

- `20211221 / ndlm_main_keep`
- `20221225 / ndlm_main_keep`
- at least one `ndlm_main_drop` anomaly row

Purpose:

- observe the worst cases with targeted instrumentation instead of relying only on aggregate outputs

Status:

- complete
- output:
  - [ndlm_instrumented_replay_report.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_instrumented_replay_report.md)

### Phase 9. Final discrepancy report and remediation decision

Deliverables:

- `ndlm_reaudit_final_summary.md`

Decision outcomes:

- `A`: implementation is sound; remaining poor NDLM performance is a genuine modeling result
- `B`: implementation is mostly sound, but one or more correctable issues materially worsen NDLM performance
- `C`: implementation is materially wrong and must be fixed before the NDLM comparison can be trusted

Status:

- complete
- decision:
  - `C`
- output:
  - [ndlm_reaudit_final_summary.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_reaudit_postcorrection/ndlm_reaudit_final_summary.md)

## Reproducibility Rules

- use the corrected rerun root as the source of truth
- preserve all intermediate audit outputs under `reports/ndlm_reaudit_postcorrection/`
- prefer reusable scripts over ad hoc shell notes
- keep runtime evidence paths in every phase note

## Initial Priorities

Tier 1:

- `20211221 / ndlm_main_keep`
- `20221225 / ndlm_main_keep`

Tier 2:

- `20211221 / ndlm_main_drop`
- `20221225 / ndlm_main_drop`
- `20220511 / ndlm_main_drop`

Tier 3:

- `20221225 / ndlm_univar_keep`

## First Concrete Step

Completed.

## Final Read

The post-correction reaudit showed that the remaining NDLM anomaly is not best explained by the Normal likelihood itself and not by a Kalman-core failure. The decisive issue is a multivariate post-stage predictive-sampling bug that mixed non-USGS sigma draws into the USGS predictive sampler. The fix is in place, but the manuscript-facing NDLM values should be refreshed from a new rerun before they are treated as final.

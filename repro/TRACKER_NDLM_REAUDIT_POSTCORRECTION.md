# NDLM Post-Correction Reaudit Tracker

Date opened: 2026-04-21  
Status: complete

## Purpose

This tracker opens a second NDLM audit after the corrected featurecov rerun.

The first NDLM parity audit established that the older manuscript-facing NDLM rows were not on the intended shared featurecov / blended-forecast contract. That problem has now been fixed, and the corrected rerun completed successfully (`15 / 15` pass).

The remaining concern is different and more specific:

- even under the corrected input contract, several NDLM CRPS values still look implausibly poor
- this raises the possibility that the remaining gap is no longer a provenance/fairness issue, but an implementation or theory-to-code issue inside the current NDLM path

This tracker is therefore **not** a rerun of the earlier fairness audit. It is a focused reaudit of the **current corrected NDLM implementation**.

## Why This Reaudit Is Needed

The corrected rerun values are:

| Label | 01/23/2021 | 11/12/2021 | 12/21/2021 | 05/11/2022 | 12/25/2022 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `N-U-T1` | `0.3520` | `0.2486` | `1.1768` | `0.1572` | `2.1451` |
| `N-M-T0` | `0.5257` | `0.7126` | `3.5474` | `2.0727` | `4.2233` |
| `N-M-T1` | `0.5930` | `0.8524` | `13.9269` | `2.2880` | `8.9743` |

These values already incorporate the major contract fixes from the first audit:

- corrected featurecov inputs
- engineered covariate feature matrix
- deterministic-climate blending
- activated multivariate NDLM prior knobs
- fixed launch-time USGS and post-stage bugs

So the remaining anomalies are no longer easy to explain as stale inputs or mixed provenance.

## Main Questions

1. Are the corrected NDLM CRPS values genuinely reflecting poor Normal-likelihood model performance?
2. Or is there still an implementation problem in one of these areas?
   - forecast scoring / post-processing
   - posterior predictive generation
   - multivariate state-space construction
   - transfer-function activation in forecast mode
   - covariance / variance propagation
   - lead indexing / active-set handling
   - transformation between latent Gaussian outputs and scored predictive draws

## Working Hypotheses

### H1. Forecast scoring / post-processing bug

The NDLM fit may be fine, but the scored predictive samples or forecast-window summaries may be built incorrectly in `post`.

### H2. Predictive transform or sampling bug

The multivariate NDLM may be generating unstable or mis-transformed predictive draws, especially on the `log(1+Q)` or related back-transformed scale.

### H3. Multivariate transfer/discrepancy implementation bug

The biggest anomalies are in `N-M-T0` and especially `N-M-T1`, which points suspicion toward the multivariate discrepancy / transfer-function path rather than the univariate Normal model.

### H4. Forecast covariance / state-evolution instability

The NDLM may be numerically coherent but dynamically unstable under the current multivariate setup, for example through variance blow-up or overly persistent discrepancy states.

### H5. Genuine model weakness

This remains possible, but it should be treated as the final fallback explanation only after the implementation-sensitive hypotheses above are checked carefully.

## Priority Cases

### Tier 1

- `N-M-T1` at `20211221` (`13.9269`)
- `N-M-T1` at `20221225` (`8.9743`)

### Tier 2

- `N-M-T0` at `20211221` (`3.5474`)
- `N-M-T0` at `20221225` (`4.2233`)
- `N-M-T0` at `20220511` (`2.0727`)

### Tier 3

- `N-U-T1` at `20221225` (`2.1451`)

## Phase Structure

| Phase | Goal | Status |
| --- | --- | --- |
| Phase 0 | Kickoff, anomaly framing, and scope freeze | complete |
| Phase 1 | Corrected rerun anomaly characterization | complete |
| Phase 2 | Corrected runtime inventory and contract freeze | complete |
| Phase 3 | Forecast scoring and post-processing audit | complete |
| Phase 4 | Posterior predictive generation audit | complete |
| Phase 5 | Multivariate state/measurement/transfer audit | complete |
| Phase 6 | Forecast covariance, prior, and discount-dynamics audit | complete |
| Phase 7 | Synthetic numerical harness and theory sanity checks | complete |
| Phase 8 | Instrumented replay of worst cutoffs | complete |
| Phase 9 | Final discrepancy report and remediation decision | complete |

## Expected Outputs

- `repro/run/NDLM_REAUDIT_POSTCORRECTION_WORKFLOW.md`
- `reports/ndlm_reaudit_postcorrection/NDLM_REAUDIT_SCOPE_20260421.md`
- `reports/ndlm_reaudit_postcorrection/ndlm_reaudit_anomaly_digest.csv`
- `reports/ndlm_reaudit_postcorrection/ndlm_reaudit_runtime_inventory.csv`
- `reports/ndlm_reaudit_postcorrection/ndlm_scoring_audit.md`
- `reports/ndlm_reaudit_postcorrection/ndlm_predictive_generation_audit.md`
- `reports/ndlm_reaudit_postcorrection/ndlm_multivar_contract_audit.md`
- `reports/ndlm_reaudit_postcorrection/ndlm_covariance_dynamics_audit.md`
- `reports/ndlm_reaudit_postcorrection/ndlm_synthetic_harness_report.md`
- `reports/ndlm_reaudit_postcorrection/ndlm_instrumented_replay_report.md`
- `reports/ndlm_reaudit_postcorrection/ndlm_reaudit_final_summary.md`

## Success Criteria

The reaudit is successful when we can do all of the following:

1. Explain the remaining NDLM anomalies with evidence, not guesswork.
2. Show whether the current corrected NDLM results are credible outputs of the intended model.
3. If a bug exists, isolate it to a concrete code path, artifact, or theory-to-code mismatch.
4. If the implementation is sound, document that clearly enough to defend the remaining gap as a genuine modeling result.
5. Leave behind a reproducible workflow that can be rerun after future NDLM changes.

## Final Outcome

Outcome: `C`

The post-correction reaudit found a concrete implementation bug in the multivariate NDLM predictive-sampling path. The current corrected rerun is therefore not trustworthy for manuscript-facing NDLM comparison values until the NDLM rerun is repeated from the fixed post sampler.

## Final Key Findings

- The anomaly is concentrated in the multivariate NDLM rows, especially `ndlm_main_keep`.
- The NDLM Kalman smoother core is numerically congruent with both the C++ backend and the Gaussian backbone used by the quantile-family theory path.
- The score tables are internally consistent; they are faithfully scoring the predictive matrices they are given.
- The predictive matrices themselves are contaminated by a multivariate sigma-mixing bug in the old `post_ndlm_predictive_draws(...)` path.
- The covariance diagnostics do not support a gross PSD/stability failure explanation.

## Follow-On Action

- Relaunch the `15`-row NDLM featurecov rerun from the fixed predictive-sampling code.
- Replace the provisional NDLM values now present in the handling-editor table after the post-fix rerun completes.

## Working Checklist

### Phase 1. Anomaly characterization

- [x] Build a per-cutoff, per-family anomaly digest from the corrected rerun
- [x] Add lead-wise CRPS summaries where available
- [x] Compare NDLM spread, center, and forecast-window behavior across cutoffs
- [x] Flag the worst rows for deep replay

### Phase 2. Runtime inventory and freeze

- [x] Freeze the exact corrected rerun configs, manifests, and key outputs
- [x] Record the authoritative runtime artifacts for all 15 rows
- [x] Verify which artifacts differ between univariate and multivariate NDLM paths

### Phase 3. Scoring / post audit

- [x] Trace NDLM forecast-window CRPS from runtime outputs to the final score tables
- [x] Verify that NDLM predictive objects are being scored on the intended scale
- [x] Check that NDLM scoring uses the intended predictive samples / quantiles

### Phase 4. Predictive-generation audit

- [x] Inspect `y_reps`, posterior summaries, and quantile exports for NDLM rows
- [x] Check for variance explosion, heavy skew from transformation, or degenerate quantiles
- [x] Compare multivariate vs univariate NDLM predictive behavior under the same cutoff

### Phase 5. Multivariate contract audit

- [x] Verify transfer/discrepancy state activation in `keep` and `drop`
- [x] Verify measurement-load and state-dimension structure by lead
- [x] Confirm active-set and forecast-family support behavior is sensible

### Phase 6. Covariance / dynamics audit

- [x] Trace forecast covariance updates through the multivariate NDLM path
- [x] Audit state discounting and stability behavior under the corrected contract
- [x] Check whether the worst rows show obvious variance blow-up or unstable state propagation

### Phase 7. Synthetic harness

- [x] Build a small controlled NDLM sanity harness
- [x] Verify that simple Gaussian cases behave as expected
- [x] Compare theory expectation vs current implementation outputs

### Phase 8. Instrumented replay

- [x] Replay `20211221 / ndlm_main_keep` with detailed instrumentation
- [x] Replay `20221225 / ndlm_main_keep` with detailed instrumentation
- [x] Replay at least one `ndlm_main_drop` anomaly case

### Phase 9. Final synthesis

- [x] Decide whether the remaining problem is implementation, modeling, or both
- [x] If needed, define a concrete remediation patch set
- [x] If a fix is required, define the follow-on rerun scope

## Guardrails

- Do not reopen the old provenance/fairness question unless new evidence forces it.
- Treat the corrected rerun artifacts as the current source of truth.
- Keep univariate and multivariate NDLM paths separate in the analysis.
- Prefer runtime artifact evidence over config intent whenever they disagree.

# NDLM Post-Correction Reaudit Scope

Date: 2026-04-21  
Status: kickoff complete

## Scope

This note opens the second NDLM audit after the corrected featurecov rerun.

The first audit answered a fairness question:

- were the manuscript-facing NDLM rows using the intended shared contract?

The answer was no, so we fixed the contract and reran NDLM properly.

The current audit answers a different question:

- after those fixes, do the remaining NDLM CRPS anomalies indicate a genuine modeling weakness, or is something still wrong in the implementation?

## Why The Reaudit Is Justified

The corrected rerun is complete and valid as a campaign:

- `15 / 15` rows passed
- `0` failed
- corrected featurecov inputs and deterministic-climate artifacts were present
- multivariate prior knobs were active

But the resulting NDLM CRPS values still contain anomalies that are hard to accept without deeper inspection.

## Current Anomaly Table

| Label | 01/23/2021 | 11/12/2021 | 12/21/2021 | 05/11/2022 | 12/25/2022 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `N-U-T1` | `0.3520` | `0.2486` | `1.1768` | `0.1572` | `2.1451` |
| `N-M-T0` | `0.5257` | `0.7126` | `3.5474` | `2.0727` | `4.2233` |
| `N-M-T1` | `0.5930` | `0.8524` | `13.9269` | `2.2880` | `8.9743` |

Most suspicious patterns:

- the worst anomalies are concentrated in the **multivariate NDLM** path
- the strongest outlier is **`N-M-T1` at `20211221`**
- `N-M-T1` is also very poor at `20221225`
- `N-M-T0` is consistently poor in the harder later cutoffs
- the univariate NDLM is much less pathological, though still weak in `20221225`

This pattern suggests that the most likely remaining issue is not “Normal likelihood in general,” but the **multivariate NDLM forecast path**, especially in the transfer-enabled case.

## Main Suspicion Areas

1. **Forecast scoring / post**
   - wrong predictive object
   - wrong scale
   - wrong forecast-window slice

2. **Predictive generation**
   - unstable predictive draws
   - bad transformation or back-transformation
   - variance blow-up

3. **Multivariate transfer/discrepancy path**
   - incorrect forecast-mode state activation
   - bad measurement-load structure
   - bad active-set handling by lead

4. **Covariance dynamics**
   - unstable state discounting
   - overly diffuse forecast covariance
   - forecast-window prior still not behaving as intended in practice

## Non-Goals

This reaudit does **not** reopen:

- the old provenance issue
- the old input-contract mismatch
- the earlier launch-time USGS bug
- the earlier NDLM-only post-stage bug

Those were already resolved.

## Immediate Direction

The first evidence-building step should be:

- a corrected-rerun anomaly digest
- followed by a runtime inventory of the exact NDLM predictive artifacts we need to inspect

That should happen before any new theoretical conclusion is drawn.

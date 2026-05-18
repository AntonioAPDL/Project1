# HE2 exAL-M-T1 Current Findings

## Strongest Findings So Far
1. The representative run is consistently configured for `log1p_cms` at the active fit and post internal scales.
2. Raw/shared USGS and shared/post retrospective adapters reconcile exactly under `log1p(cms)` on the sampled reference dates.
3. Shared forecast members and post forecast adapters for both GloFAS and NWS reconcile exactly under member-wise `log1p(cms)` on the sampled reference forecast dates.
4. The exported fit-ingress matrix `data_cbind_tY_X.csv` does **not** match the direct `log1p(cms)` retrospective USGS series on the same dates.
5. Therefore, the first concrete divergence point we have identified is **between the already-correct adapters and the exported fit-ingress matrix**, not between the raw source data and the adapters.
6. Separately, the codepath audit confirms that the workflow contains at least two distinct model-side object families:
   - row-level location summaries
   - predictive/synthesized quantile objects
   These should not be treated as interchangeable.

## Why This Matters
If the fit-ingress `USGS` column is not the direct `log1p` response, then one of the following must be true:
- it is a transformed/derived response object used by the fitting workflow
- it is centered, differenced, or otherwise reparameterized before export
- it is not the raw model response object we think it is

That means a plot built from model-side diagnostics can look “wrong” even when the raw-to-adapter transform contract is perfectly correct.

## Most Important Current Lead
The audit now points most strongly at:
- response/object semantics at or after fit ingress
- not the raw USGS transform itself
- and not the member-wise forecast adapter transforms

## Immediate Next Investigation Target
The next best question is:

> What exactly is the `USGS` column in `data_cbind_tY_X.csv`, and how is it derived from the retrospective `USGS` series before fitting?

That should be resolved before assuming the core model fit is the issue.

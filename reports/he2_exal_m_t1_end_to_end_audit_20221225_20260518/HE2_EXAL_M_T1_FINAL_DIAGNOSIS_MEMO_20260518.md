# HE2 exAL-M-T1 Final Diagnosis Memo

## Main Conclusion

The strongest current evidence says the representative run still mixes legacy transform logic into the active fit input path, even though the run-level contract and the repaired post stage are both declared as `log1p_cms`.

In plain terms:

- the raw/shared/post adapters are mostly doing the right thing
- the active fit input script is not
- and that alone is enough to explain why the diagnostic objects look deeply wrong before we even ask whether the model implementation is bad

## Highest-Confidence Findings

- run contract says `analysis_scale_fit_internal = log1p_cms` and `analysis_scale_post_internal = log1p_cms`
- sampled history lineage exact match for raw -> shared/post retros under log1p: `True` means adapters are correct but fit ingress is not the same object
- fit ingress matches `log(log1p(raw))` on sampled USGS dates: `True`
- all three retrospective response series match `log(shared_retros)` exactly across the full run: `True`
- fit forecast code path uses `log(raw)` members: `True`

## What This Means

1. The representative fit is not currently aligned with the intended `log1p_only` data contract.
2. The remaining weirdness is not well explained by post-processing alone.
3. Some of the plotting confusion is semantic, but there is also a genuine fit-ingress transform mismatch that needs to be repaired.

## Recommended Fix Order

1. Patch the active fit input path in `R/environmetrics/10_data_inputs.R`.
2. Rebuild the representative cutoff from fit onward under the corrected transform contract.
3. Keep the repaired post-stage scale guard in place.
4. After the representative rerun, repeat the same audits before scaling to other cutoffs.

## Suggested Immediate Patch Targets

- Replace `Y <- log(Y)` with direct use of the already-log1p retrospective response matrix.
- Replace `log()` on raw NWS/GloFAS forecast members with `log1p()` or use a single canonical transformed adapter contract consistently.
- Audit whether any companion fit-side history/forecast helpers still assume legacy log/log-log semantics.

## Outputs

- findings table: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_end_to_end_audit_20221225_20260518/final_diagnosis_findings.csv`

# HE2 exAL-M-T1 Pre-Fit Lineage Audit

- run root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_reference_relaunch_20260518/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep`

## What This Checks

- Raw USGS -> shared USGS -> shared retros -> post retros -> fit ingress for a small set of reference dates.
- Shared forecast members -> post forecast adapters for GloFAS and NWS on the first three forecast days after cutoff.

## Main Read

- history lineage exact-match flag: `False`
- forecast member transform exact-match flag: `False`
- fit ingress matches `log(log1p(raw USGS))` on sampled history dates: `True`
- all three retrospective response series match `log(shared_retros)` exactly across the full run: `True`
- active fit input code path applies `log(raw)` to forecast members and `log(log1p(raw))` to retrospective response series
- last-200 historical window starts at `2022-06-09`

## Outputs

- history table: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_end_to_end_audit_20221225_20260518/prefit_history_lineage_reference_dates.csv`
- forecast transform table: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_end_to_end_audit_20221225_20260518/prefit_forecast_member_transform_checks.csv`
- response contract table: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_end_to_end_audit_20221225_20260518/prefit_response_contract_checks.csv`

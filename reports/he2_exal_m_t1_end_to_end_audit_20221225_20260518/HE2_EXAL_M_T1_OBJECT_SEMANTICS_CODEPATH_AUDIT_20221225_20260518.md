# HE2 exAL-M-T1 Object Semantics Codepath Audit

## Main Takeaway

- The workflow contains at least two distinct object families that can look superficially similar on the same scale:
  - row-level location summaries
  - row-level predictive draws / synthesized predictive quantiles
- This distinction is likely central to the current confusion.

## Outputs

- codepath table: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_exal_m_t1_end_to_end_audit_20221225_20260518/object_semantics_codepath.csv`

## Most Important Interpretation Risk

- Plotting `multivar_*_usgs_location_summary_log1p.rds` as though it were the predictive quantile dynamic may be semantically wrong even if the scale is correct.

# HE2 Bayesian Input Sanity Audit

This audit checks the authoritative current HE2 Bayesian rows (9 models x 5 cutoffs) and verifies whether, within each cutoff, they use the same shared historical inputs, forecast inputs, forecast-window covariate products, and blended-feature files.

## Headline

- artifact checks passed: `50 / 50`
- cutoffs audited: `5`
- Bayesian HE2 rows audited: `45`

## By Cutoff

| Cutoff | Artifact Checks Passing | Result |
|---|---:|---|
| `20210123` | `10 / 10` | All shared inputs/covariate products aligned |
| `20211112` | `10 / 10` | All shared inputs/covariate products aligned |
| `20211221` | `10 / 10` | All shared inputs/covariate products aligned |
| `20220511` | `10 / 10` | All shared inputs/covariate products aligned |
| `20221225` | `10 / 10` | All shared inputs/covariate products aligned |

## Contract Check

- covariate name sets observed: `['PPT|SOIL|PCA']`
- deterministic-climate enabled flags observed: `['True']`
- covariate-features enabled flags observed: `['True']`

## Outputs

- detail: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_bayesian_input_sanity_audit/he2_bayesian_input_sanity_detail.csv`
- summary: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_bayesian_input_sanity_audit/he2_bayesian_input_sanity_summary.csv`
- contracts: `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_bayesian_input_sanity_audit/he2_bayesian_input_sanity_contracts.csv`

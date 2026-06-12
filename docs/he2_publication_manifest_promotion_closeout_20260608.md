# HE2 Publication Manifest Promotion Closeout - 2026-06-08

## Decision

The HE2 Bayesian publication benchmark is promoted for the current manuscript
snapshot. All `9 x 5 = 45` Bayesian table cells now resolve to canonical
20260510 shared-input-bundle roots, including the three NDLM families completed
in the June 7 promotion batch.

Primary evidence:

- workflow manifest:
  `reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
- workflow parity gate:
  `reports/he2_publication_manifest/he2_publication_parity_gate_summary.json`
- CRPS readiness audit:
  `reports/he2_crps_table_readiness_20260517/crps_table_readiness.json`
- article freeze:
  `Evironmetrics---REVISED-DOC-Corrected-2/artifacts/he2_publication_freeze/`
- generated article table:
  `Evironmetrics---REVISED-DOC-Corrected-2/tables/generated_tex/benchmark_crps_main_table.tex`

## Final Gates

| Gate | Result |
|---|---:|
| Bayesian cells documented | 45 |
| cutoffs | 5 |
| promoted rows | 45 |
| pending rows | 0 |
| blocked rows | 0 |
| within-cutoff congruence checks | 50 / 50 |
| final 9-model benchmark ready | true |

The retrospective input alignment uses semantic CSV equality against the
canonical bundle; all other required fit/forecast/covariate artifacts use
content hashes. This is explicit in
`reports/he2_publication_manifest/he2_bayesian_publication_alignment.csv` via
the `comparison_basis` column.

## Promoted Family Roots

| Label | Family | Source |
|---|---|---|
| `N-U-T1` | `ndlm_univar_keep` | June 7 NDLM promotion root |
| `N-M-T0` | `ndlm_main_drop` | June 7 NDLM promotion root |
| `N-M-T1` | `ndlm_main_keep` | June 7 NDLM promotion root |
| `AL-U-T1` | `dqlm_univar_al` | June 3 univariate AL/exAL relaunch root |
| `AL-M-T0` | `dqlm_multivar_al_drop` | June 6 P5 AL-M-T0 production root |
| `AL-M-T1` | `dqlm_multivar_al_keep` | June 2 AL keep clone of exAL winners |
| `exAL-U-T1` | `exdqlm_univar` | June 3 univariate AL/exAL relaunch root |
| `exAL-M-T0` | `exdqlm_multivar_drop` | June 2 current-code drop relaunch root |
| `exAL-M-T1` | `exdqlm_multivar_keep` | May 24 canonical grid winners |

The NDLM promotion root is:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_bayesian_publication_relaunch_wave_a_ndlm_promotion_20260607`

## Table Interpretation

The regenerated table no longer supports the older sentence that exAL-M-T1 wins
all five rolling-origin cutoffs. The current article text has been updated to
match the table:

- `exAL-M-T1` is best overall in the first four cutoffs.
- `RAW-NWS` is best overall at `2022-12-25`.
- `AL-M-T1` is the best corrected Bayesian row at `2022-12-25`.
- `exAL-M-T1` remains the reference specification because it is the selected
  extended-likelihood multivariate model and has the strongest broad corrected
  performance over the first four cutoffs.

Raw baseline rows in the manuscript table continue to come from the existing
five-run exAL-M-T1 CRPS validation freeze in
`Evironmetrics---REVISED-DOC-Corrected-2/artifacts/five_cutoff_crps_validation_sources/`.
The June 7 NDLM compare bundles are retained as merged all-model provenance
evidence for the relaunched NDLM rows, not as the article raw-baseline source.

## Reproducible Refresh Commands

Workflow side:

```bash
python3 scripts/build_he2_bayesian_publication_manifest.py
python3 scripts/build_he2_publication_parity_gate.py
python3 scripts/build_he2_master_workflow_audit_tracker.py
python3 scripts/build_he2_crps_table_readiness_audit.py
```

Article side:

```bash
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_he2_manifest_snapshot.py \
  --article-root Evironmetrics---REVISED-DOC-Corrected-2 \
  --workflow-root .

python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/build_generated_table_includes.py \
  --article-root Evironmetrics---REVISED-DOC-Corrected-2

python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/build_article_asset_review_report.py \
  --article-root Evironmetrics---REVISED-DOC-Corrected-2
```

Regression tests:

```bash
python3 -m unittest \
  tests.python.test_he2_bayesian_publication_manifest \
  tests.python.test_he2_crps_table_readiness_audit \
  tests.python.test_revised_article_stage1_refresh_contract \
  -v

python3 -m pytest -q tests/python/test_article_asset_review_benchmark_source.py
```

## Remaining Work

1. Compile or otherwise check the revised article after the text/table update.
2. Decide whether the raw-baseline source should remain the five-run exAL-M-T1
   freeze or be replaced by a future all-model compare-bundle freeze. The
   current implementation keeps the existing article source contract.
3. Treat any future epsilon/discount-factor or model-family exploration as a new
   comparison campaign, not as an edit to this frozen publication snapshot.

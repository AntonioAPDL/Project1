# Publication Replay Workflow

This note defines the practical replay workflow for the current manuscript-facing
Bayesian HE2 table and the linked HE3 `12/25/2022` full-reference row.

## Purpose

The goal is to keep one operational contract for:

- what the current published rows are,
- which runtime lineage each row belongs to,
- which artifacts must exist before figures/tables are refreshed,
- and which representative rows should be verified before any broader rerun.

## Source of truth

Use these in this order:

1. [he2_bayesian_publication_manifest.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/he2_bayesian_publication_manifest.md)
2. [publication_replay_matrix.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/publication_replay/publication_replay_matrix.csv)
3. [representative_replay_verification.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/publication_replay/representative_replay_verification.md)
4. [exalm_t1_discount_grid_exact_vs_he2.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/quantile_discount_probe_analysis/exalm_t1_discount_grid_exact_vs_he2.md)

Do not use the older parity-audit lineage as the current publication source of
truth. Those documents remain useful diagnostics, but the publication manifest
and replay matrix are the current freeze.

## Publication lineages

### NDLM HE2 rows

- campaign:
  `multimodel_v8_ndlm_featurecov_rerun_postfix_20260421`
- rows:
  `N-U-T1`, `N-M-T0`, `N-M-T1`

### Univariate AL/exAL HE2 rows

- campaign:
  `multimodel_v8_univar_featurecov_he2_rerun_20260422`
- rows:
  `AL-U-T1`, `exAL-U-T1`

### Multivariate AL/exAL HE2 rows

- campaign:
  `multimodel_v8_featurecov_cf1_eps_sweep_20260416`
- rows:
  `AL-M-T0`, `AL-M-T1`, `exAL-M-T0`, and four of the five `exAL-M-T1` cells

### Publication override

- campaign:
  `multimodel_v8_exalm_t1_discount_grid_exact_20260424`
- row:
  `12/25/2022 / exAL-M-T1`
- winning set:
  `set09`

## Representative rows to verify first

These are locked in the replay matrix:

1. `01/23/2021 / N-M-T1`
2. `01/23/2021 / exAL-U-T1`
3. `01/23/2021 / exAL-M-T1`
4. `12/25/2022 / exAL-M-T1`

The fourth row is the fragile one and should be treated as the replay canary.

## Lineage root vs artifact root

Most rows use the same run directory for both lineage and retained outputs. A
small number of publication rows reuse a validated external pass. For those
rows:

- the replay matrix `run_root` identifies the publication lineage that selected
  the cell,
- the replay matrix `artifact_run_root` identifies the run that owns the saved
  post outputs and score files,
- and the compare bundle still follows the publication lineage because that is
  where row selection and provenance were recorded.

When refreshing tables or figures, follow the artifact-root paths rather than
assuming every publication row owns its outputs locally under `run_root`.

## Artifact contract

Before using any row to refresh manuscript assets, confirm these exist:

- `artifact_resolved_config_path`
- `artifact_run_manifest_path`
- `artifact_report_summary_path`
- `artifact_inputs_shared_path`
- compare bundle directory
- `source_provenance.csv`
- `tables/crps_forecast_summary.csv`
- `tables/crps_forecast_per_time.csv`
- `tables/posterior_table_exports_manifest.csv`
- `tables/posterior_table_exports_README.md`

`publication_figure_manifest.csv` should also exist when the lane emits
publication figures.

## Exact-row environment note

The `12/25/2022 / exAL-M-T1` publication override is the only row that already
has a recovered authoritative replay path documented in:

- [AUTHORITATIVE_R440_ENV_RECREATION.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/AUTHORITATIVE_R440_ENV_RECREATION.md)

The representative verified replay run is:

- [/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/paper_exalm_t1_r440_q20_keep_20221225_20260506](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/paper_exalm_t1_r440_q20_keep_20221225_20260506)

That run is not a full publication rerun. It is the fit-stability proof that
the authoritative `R 4.4.0` path can reproduce the sensitive keep-lane fit.

## Operational order

When we resume reruns or manuscript refreshes, use this order:

1. verify the four representative rows
2. replay or reuse the full publication lineage only after those pass
3. refresh figures/tables only from rows in the replay matrix
4. synchronize the corrections letter after the asset refresh is stable

## Regeneration commands

Rebuild the matrix:

```bash
python3 scripts/build_publication_replay_matrix.py
```

Re-run representative verification:

```bash
python3 scripts/verify_publication_replay_representatives.py
```

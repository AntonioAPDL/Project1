# HE4 Quantile Check-Loss Workflow

`HE4` is built from the finalized HE-2 model selections rather than from a separate ad hoc spreadsheet.

## Inputs

- Final HE-2 cutoff selections:
  - `project1_ucsc_phd_runtime/multimodel_v8_featurecov_cf1_eps_sweep_20260416/reports/final_featurecov_cf1_eps_analysis/best_by_cutoff_long.csv`
- Compare-bundle provenance for carried-forward baseline rows:
  - `project1_ucsc_phd_runtime/multimodel_v8_featurecov_cf1_eps_sweep_20260416/reports/multimodel_*_compare/source_provenance.csv`
- Run-level forecast quantile artifacts:
  - `*_cutoff_window_quantiles.csv`
- Run-level CRPS summaries used to validate the resolved source run:
  - `tables/crps_forecast_summary.csv`

## Builder

Run:

```bash
python3 scripts/build_he4_quantile_check_loss_tables.py
```

The builder:

1. Reads the finalized HE-2 selections for the four HE4 models.
2. Resolves the exact run directory behind each selected row.
3. Uses `mean_crps` from the run-level summary to disambiguate duplicate baseline `epsTT` runs.
4. Loads the forecast quantile artifact, keeps only `segment == "forecast"`, checks quantile monotonicity, and computes the mean quantile check loss for `tau ∈ {0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95}`.

## Outputs

Default output directory:

- `project1_ucsc_phd_runtime/multimodel_v8_featurecov_cf1_eps_sweep_20260416/reports/final_featurecov_cf1_eps_analysis/he4_quantile_check_loss/`

Files written:

- `he4_selection_audit.csv`
- `he4_quantile_check_loss_per_day.csv`
- `he4_quantile_check_loss_long.csv`
- `he4_quantile_check_loss_wide.csv`
- `he4_quantile_check_loss_summary.md`
- `he4_table_rows.tex`

## Score Convention

- Verification target: the observed USGS series stored in the selected run artifact.
- Scale: `log_cms_plus1`, matching the CRPS summaries used in HE-2.
- Loss: standard quantile check loss / pinball loss

```text
rho_tau(y - q_tau) = (y - q_tau) * (tau - 1[y < q_tau])
```

Lower values indicate better forecast calibration at that quantile level.

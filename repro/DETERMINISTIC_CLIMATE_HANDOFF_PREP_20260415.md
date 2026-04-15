# Deterministic Climate Handoff Prep (2026-04-15)

## Purpose

Prepare the GEFS + NWM handoff cache consumed by the all-9 feature-covariate relaunch in a reproducible way.

This workflow is intentionally separate from the model launch:

- it resumes from the existing GEFS+NWM manifest run
- it reuses the reconciled GEFS extract if present
- it fills the missing NWM full extract if needed
- it runs a combined health check
- it builds the handoff cache expected by `inputs.deterministic_climate.handoff_root`

## Config

- [deterministic_climate_handoff.site11160500.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/deterministic_climate_handoff.site11160500.yaml)

Key settings:

- manifest run dir:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=gefs_forecasts/full_runs/source_native_tranche1_20260406T194500Z/gefs_nwm_forecast_manifest_source_native_tranche1_20260406T194500Z`
- preferred GEFS extract:
  - `extract_gefs_full_reconciled_gefs_retry_20260406T224500Z`
- fallback GEFS extract:
  - `extract_gefs_full`
- NWM extract target:
  - `extract_full`
- combined health JSON:
  - `health_checks/forecast_extract_health_detclim_ready.json`
- handoff output root:
  - `handoff_forecasts/site=11160500/run_id=<manifest_run_id>/`

## Entry Point

- [prepare_deterministic_climate_handoff.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/prepare_deterministic_climate_handoff.py)

## Dry-Run

```bash
python3 scripts/prepare_deterministic_climate_handoff.py --dry-run
```

This writes a summary under:

- `<manifest_run_dir>/handoff_prep/detclim_handoff_prepare_summary.json`

## Live Run

```bash
python3 scripts/prepare_deterministic_climate_handoff.py
```

What it does:

1. selects the best available GEFS extract subdir
2. runs the NWM full extract if `extract_full/nwm/nwm_point_series.csv` is missing
3. runs the combined GEFS+NWM health check
4. builds the final handoff cache
5. patches [multimodel_v8_all9_featurecov.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_all9_featurecov.template.yaml) with the resolved `handoff_root`

## Validation

Targeted Python tests:

- [test_deterministic_climate_handoff_workflow.py](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/python/test_deterministic_climate_handoff_workflow.py)

Run:

```bash
python3 -m unittest tests.python.test_deterministic_climate_handoff_workflow
```

## Expected Next Step After Success

Once the handoff cache exists and the campaign template is patched, regenerate the all-9 configs in build-only mode before launching models:

```bash
bash scripts/run_multimodel_v8_all9_feature_campaign.sh \
  --config config/multimodel_v8_all9_featurecov.template.yaml
```

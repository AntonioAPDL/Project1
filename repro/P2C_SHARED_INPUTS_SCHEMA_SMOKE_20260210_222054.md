# P2C Shared-Inputs Schema Smoke

- Config: `config/unified_runs/smoke_p2c_shared_inputs_schema.yaml`
- Command: `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/smoke_p2c_shared_inputs_schema.yaml`
- Run ID: `20260210_222054`
- Run root: `repro/runs/20260210_222054`

## Closure

- Manifest: `repro/runs/20260210_222054/run_manifest.yaml`
- `timestamps.finished_at_utc`: `2026-02-11T06:53:15Z`

## Bridge Artifacts (Run-Scoped)

- `repro/runs/20260210_222054/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
- `repro/runs/20260210_222054/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
- `repro/runs/20260210_222054/fit/exdqlm_univar/q=50/logs/univar_legacy.log`
- `repro/runs/20260210_222054/fit/ndlm_main/logs/ndlm_legacy.log`

## Write-Audit (Fit Stage)

- Diff path: `repro/runs/20260210_222054/validate/write_audit/fit/fs_diff.patch`
- Result: `0` bytes (no outside-run-root writes detected with `enforce_from_stage=2`, empty allowlist).

## Shared Input Schema Evidence

- Canonical shared bundle root:
  - `repro/runs/20260210_222054/inputs/shared/`
- Snapshot bundle root:
  - `repro/runs/20260210_222054/inputs/shared/forecats_bundle/`
- Canonical source mapping:
  - `repro/runs/20260210_222054/inputs/shared/source_map.txt`
  - `source_mode=forecats_snapshot_mixed`
  - `source.retros_origin=configured`
  - `source.nws_origin=snapshot`
  - `source.glofas_origin=snapshot`
- Snapshot provenance mapping:
  - `repro/runs/20260210_222054/inputs/shared/forecats_bundle/snapshot_source_map.txt`
  - `glofas_members_source=.../forecast_cache/glofas/.../glofas_members.csv`

## Manifest Artifact Hashing

`run_manifest.yaml` includes hashed artifact entries for:

- `role: input_snapshot` files under `inputs/shared/forecats_bundle/...`
- `role: shared_input` canonical files under `inputs/shared/{parameters,retros,forecasts,covariates}/...`

This confirms schema-validated, run-scoped canonicalization and snapshot provenance recording without relying on a special cached-file override in config.

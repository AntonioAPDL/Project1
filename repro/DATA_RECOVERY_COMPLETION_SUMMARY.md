# Data Recovery Completion Summary

Last updated: 2026-04-16  
Primary run root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z`

## Final State

The prioritized recovery queue is complete.

| lane | completed | expected | percent |
|---|---:|---:|---:|
| `GLOFAS historical v3.1` | `433` | `433` | `100.0%` |
| `GLOFAS operational forecasts` | `1176` | `1176` | `100.0%` |
| `NWM retrospective v1.2` | `25` | `25` | `100.0%` |
| `GLOFAS historical v4.0` | `433` | `433` | `100.0%` |

Also complete:

| lane | artifact |
|---|---|
| `USGS daily flow` | `17,262` rows |
| `NWM retrospective v2.0` | `9,496` rows |
| `GEFS forecasts` | `56,110 / 56,110` files; `140,120 / 140,120` rows |
| `GLOFAS historical v2.1` | `423 / 423` shards; `12,848` point rows |

## Final Checkpoint

Fresh final checkpoint bundle:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/status/checkpoint_20260416T174311Z`

Key files:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/status/checkpoint_20260416T174311Z/checkpoint_summary.json`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/status/checkpoint_20260416T174311Z/checkpoint_summary.md`

Final safety bundle:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/status/final_safety_bundle_20260416T174522Z`

Safety bundle contents:

- `artifact_inventory.json`: final artifact roots, existence, file counts, and byte totals
- `artifact_checksums.sha256`: SHA-256 checksums for the core completion metadata files
- `README.md`: explains scope and limits of the bundle

The priority queue status is complete:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/status/priority_queue_20260409T010357Z/status/queue_status.json`

## Durable Artifact Roots

Final operational and historical outputs remain under the original campaign roots:

- `GLOFAS operational`: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=glofas_operational_forecasts/full_runs/glofas_operational_parallel_20260407T023100Z`
- `GLOFAS historical`: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=glofas_historical/full_runs/source_native_tranche1_20260406T194500Z`
- `NWM retrospective`: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z/family=nwm_retrospective/full_runs/source_native_tranche1_20260406T194500Z`

## Safety Notes

- The recovered outputs are durable on disk and no longer depend on active worker processes.
- The recovery queue has no remaining active target sessions or refill worker PIDs.
- The operational-tail repair has been committed into the repo so the recovery path itself is reproducible.
- The final safety bundle captures the current on-disk footprint of the key artifact roots plus checksums for the core completion metadata.

Important honesty note:

- The data are safe against accidental rerun loss and process interruption on the current host.
- They are **not** automatically protected against underlying disk failure unless they are copied to another storage location or backed up elsewhere.

If stronger protection is needed, the next step is an explicit backup or replication of the runtime output roots above.

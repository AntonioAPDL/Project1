# Debug-Small Workflow

## Purpose
Provide a fast, low-risk workflow to validate IO plumbing, shared-input filtering, and write-audit wiring without launching a long production fit.

## Config
- `config/unified_runs/debug_p7b_small.yaml`

Key properties:
- `run.io.enabled: true` with low thresholds (`1 GB`, `1%` inodes) for quick preflight behavior checks.
- `dates.data_start: "2010-01-01"` to filter shared inputs.
- `fit.quantiles: [0.5]`.
- `write_audit.enforce_from_stage: 2` with empty allowlist.
- Family runs are disabled in this debug wiring profile to keep runtime short.

## Command
```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
Rscript --vanilla scripts/unified_run.R --config config/unified_runs/debug_p7b_small.yaml
```

## What It Checks
1. Optional storage preflight check path.
2. Forecats snapshot -> shared-input canonical copy.
3. Shared input schema validation + optional `dates.data_start` filtering.
4. Fit-stage adapter generation and write-audit snapshots.

## What It Does Not Check
- Full production runtime for all families/quantiles.
- Post/validate/report contracts.
- Scientific convergence behavior.

## Returning to Production
Use your production config (for example `config/unified_runs/production_p7b_family_run.yaml`) and disable debug-only constraints unless specifically required.

## Safe Run Cleanup
Use dry-run first:
```bash
repro/tools/cleanup_runs.sh --dry-run --keep-last 10 --older-than-days 30
```
Apply only after review:
```bash
repro/tools/cleanup_runs.sh --apply --keep-last 10 --older-than-days 30
```

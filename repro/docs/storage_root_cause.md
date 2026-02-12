# Storage Root-Cause Note (2026-02-12)

## Summary
- Failure observed during production run `prod_p7b_20260212_013645` at fit quantile `q=05`.
- Error signature in `repro/runs/prod_p7b_20260212_013645/fit/q=05/logs/fit.log`:
  - `Error in save(list = var_names, file = file_path, envir = env) : error writing to connection`
- Manifest did not close:
  - `repro/runs/prod_p7b_20260212_013645/run_manifest.yaml`
  - `timestamps.finished_at_utc: null`
  - `validation.status: pending`

## Filesystem Evidence
- `df -h`:
  - `/data` (`/dev/md124`) -> `916G total`, `863G used`, `7.0G avail`, `Use% 100%`
  - `/` (`/dev/md127`) -> `280G total`, `276G used`, `4.4G avail`, `Use% 99%`
- `df -i`:
  - `/data` inode use ~`4%` (free inode pressure is not the issue).
  - `/` inode use ~`3%`.
- Quota probe:
  - `quota -s` returned no actionable quota output in this environment.

## Root Cause Assessment
- Primary cause is **free-space exhaustion on `/data`** during large RData write operations.
- There is no indication of inode exhaustion.
- The observed save failure is consistent with late-stage write failure under tight free-space conditions.

## Top Consumers (ranked)
- `du -xhd1 /data/muscat_data/jaguir26`:
  - `project1_ucsc_phd`: `579G`
  - `exdqlm`: `69G`
  - `project1_ucsc_phd_BACKUP_20260121_010041`: `30G`
  - `projects`: `21G`
  - `.cache`: `6.9G`
- Within `project1_ucsc_phd`:
  - `repro`: `379G`
  - `prism_data`: `55G`
  - `frames`: `6.6G`
  - `Project`: `6.1G`
  - `.venv`: `5.0G`
  - `data`: `3.6G`
- Within `repro`:
  - `baseline_runs`: `259G`
  - `runs`: `119G`
  - `recovery`: `1.3G`

## Recommended Cleanup Targets
1. `repro/baseline_runs` (archive/compress/prune oldest first).
2. `repro/runs` failed and superseded runs (especially large historical runs >7G each).
3. Historical backups not needed for immediate reproducibility (e.g., `project1_ucsc_phd_BACKUP_20260121_010041`).
4. Large caches under `/data/muscat_data/jaguir26/.cache` when safe.

## Guardrails Added in This Follow-up
- Fail-fast storage preflight checks (optional via config; default OFF).
- Atomic model-state save path to avoid leaving 0-byte final artifacts on write failure.
- Cleanup helper script with dry-run default:
  - `repro/tools/cleanup_runs.sh`

# Storage Retention Policy

## Purpose
Keep `/data` headroom stable for unified runs while preserving reproducibility-critical baselines and canonical evidence runs.

## Protected Set (never prune by default)
A run is protected if any of the following hold:

1. Run ID is listed in `repro/protected_runs.yaml` under `protected_run_ids`.
2. Run ID is referenced by `validation.canonical_run_id` in `config/unified_runs/*.yaml` (excluding `__SELF__`).
3. Run directory contains any marker: `.canonical.keep`, `.run_keep`, `.protect_run`.
4. Run is in-progress/recent (safety window; default from cleanup tooling).
5. Run is in `repro/baseline_runs` and baseline flags are not explicitly enabled.

## Default Retention Knobs
- `keep_recent`: `12`
- `keep_last_success`: `12`
- `older_than_days`: `21`
- `thin_old_days`: `21`
- `safety_window_hours`: cleanup-tool default

## Allowed Operations
- `thin_failed`: thin failed/pending run artifacts only.
- `thin_old`: thin old completed non-protected runs.
- `delete_failed`: delete old failed/unfinished non-protected runs.
- `inventory_root_rdata`: inventory repo-root standalone `.RData` files only.
- `prune_root_rdata`: optional explicit prune of repo-root standalone `.RData` files.

## Baseline Policy
`repro/baseline_runs` is immutable by default.
Baseline thinning/deletion requires all of:

1. `--include-baseline`
2. Explicit baseline mode flag (for example `--thin-baseline`)
3. Allowlist approval in `repro/protected_runs.yaml` (`baseline_delete_allowlist`)
4. `--apply`

## Apply Protocol (required)
1. Run dry-run plan with full intended flags.
2. Review summary: estimated reclaim, affected runs/actions, blocked protected candidates.
3. Confirm no protected/canonical/baseline violations.
4. Re-run with `--apply` using identical flags.
5. Record before/after `df -h` and `df -i`, plus one lightweight validation check on a protected reference run.

## Failed Run Closure Rule
- failed/incomplete runs are quarantined before they are unprotected for cleanup.

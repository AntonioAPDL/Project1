# Environment Lock Strategy (Unified Workflow)

Date: 2026-02-07

## Current reproducibility lock model

The unified workflow captures run-scoped environment artifacts under:

- `repro/runs/<RUN_ID>/env/R_sessionInfo.txt`
- `repro/runs/<RUN_ID>/env/R_installed_packages.csv`
- `repro/runs/<RUN_ID>/env/python_pip_freeze.txt`
- `repro/runs/<RUN_ID>/env/renviron_snapshot.txt`
- `repro/runs/<RUN_ID>/env/threads_snapshot.txt`

These artifacts are now mandatory and are written by `R/unified/utils_env_capture.R` during run initialization.

## Drift checks

When `validation.canonical_run_id` is provided, validation compares current vs canonical env artifacts and writes:

- `repro/runs/<RUN_ID>/validate/env_drift_report.json`

Status is `pass` only when all required env files exist in both runs and normalized contents match.

## Existing repo lock inputs

- Python pinned requirements: `env/requirements_imcmc_env.txt`
- Python bootstrap installer: `env/bootstrap_imcmc_env.sh`
- R package install helper (non-lock): `install_packages.R`
- Build/link env defaults: `.Renviron`

## Long-term lock decision

Adopt a two-layer strategy:

1. Keep mandatory run-scoped capture (already implemented).
2. Add formal R lock management (`renv`) in a follow-up migration:
   - introduce `renv.lock`
   - enforce `renv::restore()` in CI and run bootstrap
   - include `renv.lock` hash in manifest inputs

Until `renv` migration is complete, environment reproducibility is enforced by captured artifacts + env drift checks, not by a single static lockfile.

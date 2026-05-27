# exDQLM Multivariate Keep Grid Recovery - 2026-05-27

## Scope

This note records the recovery of the epsilon/discount-factor grid rooted at:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524`

It does not modify or relaunch the older protected production roots. The goal is to complete the existing
`exdqlm_multivar_keep` grid cleanly, keep failed specifications as informative failures, and prevent the controller
from freezing again.

## Current State Before Recovery

The refreshed matrix health check on 2026-05-27 showed:

| phase | status | count |
| --- | --- | ---: |
| report | pass | 116 |
| fit | fail | 2 |
| not_started | not_started | 32 |

There were no active grid model jobs and both recorded queue PID files were stale. The last queue-controller log entry
was:

`[2026-05-26T22:08:29Z] controller stop exit_code=1`

The controller stopped because `check_multimodel_v8_matrix_health.py` attempted to parse a `run_manifest.yaml` while it
was temporarily not a YAML mapping. The same manifest was valid when re-read later, so this was a read-during-write
operational failure, not a model-fit failure.

## Root Cause Classes

| issue | evidence | classification | recovery action |
| --- | --- | --- | --- |
| Queue froze | `queue.log` fatal health-refresh traceback against a transient manifest parse | controller robustness defect | fixed by atomic YAML writes plus tolerant health/status handling |
| Two failed rows | q20 pseudo-data guard failures at iter 32 and iter 47 | genuine unstable grid specs under fail-fast guard policy | keep as `FAIL`; do not silently force into ranking |
| Failed-run `.RData` retention | 12 failed-run `.RData` files totaling about 90.3 GiB | cleanup gap on failed fit path | fixed by failure-time cleanup in cleanup-enabled wrapper; existing leaked files can be removed after preserving logs |

## Failed Spec Classification

The two failed rows are:

| cutoff | spec | failing quantile | failure |
| --- | --- | --- | --- |
| `20220511` | `c02_eps090` | `q20` | pseudo-data guard fail at iter `32`; `FFF/history` and `E_uts` exceeded caps |
| `20221225` | `c03_eps060` | `q20` | pseudo-data guard fail at iter `47`; `FFF/history`, `FFF_forecast`, and `E_uts` exceeded caps |

These are not queue failures. They are the fail-fast behavior requested for unstable pseudo-data conditions. Retrying the
same deterministic config is not expected to add information. A rescue attempt would be a new diagnostic specification
with different stabilization policy, not a replacement for the original grid row.

## Implemented Hardening

1. `scripts/multimodel_v8_lib.py`
   - `write_yaml(...)` now writes to a same-directory temp file, fsyncs it, and atomically replaces the target.

2. `R/unified/manifest.R`
   - `unified_manifest_write(...)` now writes the run manifest through a same-directory temp file and atomic rename.

3. `scripts/unified_run.R`
   - resolved config writing now uses the same atomic text-write pattern;
   - cleanup-enabled runs now remove `.RData` on stage failure as well as after successful post;
   - cleanup counts are recorded in `manifest$rdata_cleanup`.

4. `scripts/check_multimodel_v8_matrix_health.py`
   - an unreadable or transiently malformed manifest is reported as `phase=manifest`, `status=pending`,
     `note=manifest_unreadable:...` instead of aborting the health refresh.

5. `scripts/run_multimodel_v8_queue.py`
   - `stage_status(...)` treats unreadable manifests as `pending`;
   - health-refresh command failures are logged as warnings and do not kill the queue loop.

## Tests

Focused tests added or extended:

| command | purpose |
| --- | --- |
| `python3 -m unittest tests.python.test_multimodel_v8_tooling tests.python.test_multimodel_v8_queue_contract -v` | queue liveness, malformed manifest handling, atomic Python YAML write, cleanup wrapper selection |
| `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_unified_manifest_atomic.R')"` | R manifest atomic replacement contract |

Both focused test commands passed on 2026-05-27.

## Relaunch Policy

Relaunch only the `32` `not_started` rows with the same memory-gated policy:

| setting | value |
| --- | ---: |
| ordinary max concurrent rows | 4 |
| heavy cutoff max concurrent rows | 4 |
| pause disk gate | 25 GiB |
| launch disk gate | 35 GiB |
| ordinary launch memory gate | 170 GiB MemAvailable |
| heavy launch memory gate | 190 GiB MemAvailable |
| continue on failed rows | yes |
| skip compare bundles during queue | yes |
| cleanup `.RData` after post and on failure | yes |

The two failed rows remain terminal failures in the main grid. They should appear as `FAIL` in the CRPS table and in
`grid_failure_log.csv`.

## Runtime Evidence To Preserve Before Cleanup

Before removing failed-run `.RData`, preserve:

- each failed q20 `logs/pseudodata_guard/pseudodata_guard_events.csv`;
- the q20 `fit.log` tail showing the guard failure;
- an inventory of failed-run `.RData` files and reclaimed bytes.

Large `.RData` files from the two failed runs are not needed for the CRPS ranking table and should not be retained in
the grid root once the compact failure evidence is captured.

## Cleanup Evidence

The compact runtime evidence was written to:

`reports/he2_exdqlm_multivar_keep_grid_recovery_20260527/`

The failed-run cleanup then removed exactly the inventory-listed `.RData` files:

| item | value |
| --- | ---: |
| removed `.RData` files | 12 |
| removed size | 90.304 GiB |
| remaining `.RData` / `.rda` under grid runs | 0 |
| `/data` free space after cleanup | 431 GiB |

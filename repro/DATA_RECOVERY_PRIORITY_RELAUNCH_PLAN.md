# Data Recovery Priority Relaunch Plan

Last updated: 2026-04-08  
Primary run root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z`

Purpose:

- freeze a durable checkpoint before stopping the currently running recovery lanes
- preserve already-finished outputs on disk
- relaunch the remaining work in a quieter, more monitorable, priority-driven order
- avoid redoing already-finished shards, years, or issue dates

## 1) Priority Order

1. `GLOFAS historical v3.1`
2. `GLOFAS operational forecasts`
3. `NWM retrospective v1.2`
4. `GLOFAS historical v4.0`

## 2) Resume Model

| lane | durable resume unit | what is reused on relaunch | likely in-flight loss if stopped mid-run |
|---|---|---|---|
| `GLOFAS historical v3.1` | monthly zip shard | existing non-empty monthly zips | current in-flight month(s) |
| `GLOFAS operational forecasts` | issue-date GRIB | existing non-empty per-issue GRIBs | current in-flight issue date(s) |
| `NWM retrospective v1.2` | yearly CSV shard | existing non-empty yearly CSVs | current open years restart from year start |
| `GLOFAS historical v4.0` | monthly zip shard | existing non-empty monthly zips | current in-flight month(s) |

## 3) Freeze + Stop

Freeze checkpoint:

```bash
python3 scripts/freeze_recovery_checkpoint.py \
  --recovery-run-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z
```

Preview the stop targets:

```bash
python3 scripts/stop_recovery_priority_lanes.py \
  --recovery-run-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z
```

Apply the stop only after the checkpoint is frozen:

```bash
python3 scripts/stop_recovery_priority_lanes.py \
  --recovery-run-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z \
  --apply
```

## 4) Relaunch Controller

Stage the prioritized queue bundle:

```bash
python3 scripts/run_prioritized_recovery_queue.py \
  --mode plan \
  --recovery-run-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z
```

Run the sequential queue after the current lanes are stopped:

```bash
python3 scripts/run_prioritized_recovery_queue.py \
  --mode run \
  --recovery-run-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z \
  --v31-workers 8 \
  --v31-passes 6 \
  --op-splits 6 \
  --nwm-v12-max-workers 8 \
  --v40-workers 4 \
  --v40-passes 6 \
  --poll-seconds 60
```

## 5) Monitoring

One-shot prioritized status:

```bash
python3 scripts/run_prioritized_recovery_queue.py \
  --mode status \
  --recovery-run-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z
```

Checkpoint bundles and queue plans are written under:

- `.../status/checkpoint_<UTCSTAMP>/`
- `.../status/priority_queue_<UTCSTAMP>/`

The queue controller writes:

- `priority_plan.json`
- `README.md`
- `commands/`
- `status/queue_status.json`
- `logs/phase_*.log`

## 6) Less-Quiet Progress

To reduce silent-running behavior:

- `NWM v1.2` now emits periodic `[PROGRESS]` heartbeats while processing each year
- the prioritized queue writes a structured `queue_status.json`
- the GLOFAS operational health summary now deduplicates rerun manifests and reports progress from actual downloaded GRIB issue dates
- the generalized GLOFAS historical refill tool writes explicit per-product status JSON files

## 7) Recommended Defaults

| lane | default concurrency | reason |
|---|---:|---|
| `GLOFAS historical v3.1` | `8 workers` | moderate parallelism for monthly shard refill without assuming local CPU is the bottleneck |
| `GLOFAS operational forecasts` | `6 splits` | already validated and stable; uses the same proven split strategy |
| `NWM retrospective v1.2` | up to `8 workers`, capped by remaining years | resume skips finished yearly shards automatically |
| `GLOFAS historical v4.0` | `4 workers` | last priority lane; enough to make progress without overcommitting remote requests |

## 8) Important Caveat

Stopping now is safe for already-finished outputs, but not free:

- completed shards/years/issue dates are durable and resumable
- in-flight units that have not yet written their final output file will need to be redone

That tradeoff is acceptable for this reroute, but it should be recorded explicitly in the checkpoint bundle before the stop is applied.

## 9) Operational Tail Repair

If the prioritized queue stalls at `GLOFAS operational forecasts` with `touched == expected` but `completed < expected`, do not full-relaunch the entire queue immediately.

Instead:

1. freeze a fresh checkpoint
2. identify the latest non-done issue dates from the split manifests
3. relaunch only the affected split tails against the existing campaign root and manifests
4. let the live queue controller advance naturally once the missing GRIBs appear

Plan-only dry run:

```bash
python3 scripts/repair_glofas_operational_tail.py \
  --recovery-run-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z
```

Apply the targeted repair:

```bash
python3 scripts/repair_glofas_operational_tail.py \
  --recovery-run-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/data_recovery/site=11160500/recovery_run=site11160500_recovery_20260406T185022Z \
  --apply
```

This writes a documented bundle under:

- `.../family=glofas_operational_forecasts/full_runs/<campaign>/status/operational_tail_repair_<UTCSTAMP>/`

The bundle contains:

- `repair_plan.json`
- `README.md`
- per-split retry interval files
- replayable retry commands
- post-apply session and checkpoint records

Why this is preferred:

- keeps the already-completed operational issue dates on disk
- appends successful retry rows into the existing split manifests
- avoids restarting the whole prioritized queue from phase 2
- keeps the handoff to `NWM retrospective v1.2` automatic once `1176 / 1176` is reached

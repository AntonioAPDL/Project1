# Featurecov cf1 Epsilon Relaunch Runbook

This runbook is the supported restart path for the live `multimodel_v8_featurecov_cf1_eps_sweep_20260416` campaign when the queue controller stops or needs to be resumed from the current matrix state.

## Goals

- Resume from the current matrix status without duplicating live fits.
- Refuse unsafe restarts when failed rows or orphaned pending rows are present.
- Launch the queue controller detached from the interactive shell so it survives terminal loss.
- Record a timestamped relaunch plan plus PID and stdout artifacts for later audit.

## Preconditions

- The matrix directory already exists and contains `matrix_plan.csv` plus `launch_settings.env`.
- The live fits, if any, are allowed to continue.
- Disk free space is checked before relaunch, but the controller may still be restarted while below launch thresholds so it can keep monitoring active fits and resume automatically later.

## Supported Relaunch Command

```bash
python3 scripts/relaunch_multimodel_v8_featurecov_cf1_eps_campaign.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_featurecov_cf1_eps_sweep_20260416/control/featurecov_cf1_eps_v1
```

## Guardrails Enforced By The Relaunch Tool

- Refuses to start if another `run_multimodel_v8_queue.py` controller is already active for the same matrix.
- Refuses to start if any matrix row is in `fail`.
- Refuses to start if any row is `pending` but no matching live fit process exists.
- Caps ordinary concurrency to a safer default of `6` unless explicitly overridden.
- Writes relaunch artifacts to `MATRIX_DIR/controller_state/`:
  - `relaunch_plan_<timestamp>.md`
  - `last_relaunch.json`
  - `controller.pid`
  - `controller_stdout.log`

## Validation After Relaunch

1. Confirm the controller PID exists in `ps`.
2. Confirm [queue.log](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_featurecov_cf1_eps_sweep_20260416/control/featurecov_cf1_eps_v1/queue.log) gets a new `controller start` heartbeat.
3. Confirm the live fit count remains stable or decreases naturally.
4. Confirm new launches only begin when disk headroom is above `launch_free_gb`.

## Operational Notes

- The queue controller already skips rows marked `pending` or `pass`, so a clean restart does not duplicate active fits.
- The relaunch tool is intentionally conservative. If orphaned pending rows are detected, repair those rows first instead of forcing a blind restart.
- The queue controller now logs signal- and exception-driven shutdowns so future controller exits leave a clearer trail in `queue.log`.

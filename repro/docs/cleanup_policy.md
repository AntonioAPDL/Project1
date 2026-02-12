# Cleanup Policy (Safe Retention + Thinning)

## What Is Protected (and Why)

The cleanup workflow protects runs from deletion/thinning unless policy explicitly allows action.

Protected by default:

1. All baseline runs under `repro/baseline_runs/**`.
2. Any run in `repro/protected_runs.yaml` under `protected_run_ids`.
3. Any run referenced by `validation.canonical_run_id` in `config/unified_runs/*.yaml` (except `__SELF__`).
4. Any run with a protection marker file in its root:
   - `.canonical.keep`
   - `.run_keep`
   - `.protect_run`
5. Any run modified in the last 6 hours (clock-skew safety).

In-progress safety:

- Unfinished runs (`timestamps.finished_at_utc: null`) that were modified within the safety window are treated as in-progress and protected.

## Recommended Retention Defaults

Suggested operational defaults:

- `--keep-last 15`
- `--older-than-days 21`
- `--thin-old --thin-old-days 21`
- `--delete-failed --older-than-days 7` (for stale unfinished runs)

## Thinning Rules (Conservative)

`--thin-old` removes only heavy model artifacts and cache paths for candidate runs:

- `fit/**/outputs/*.RData`
- `fit/**/outputs/*.rds`
- `fit/**/cache/**`
- `post/**/cache/**`

`--thin-old` preserves:

- `run_manifest.yaml`
- `resolved_config.yaml`
- `fit/**/logs/**`
- `post/logs/**`
- `validate/**`
- `report/**`
- `post/outputs/<RUN_ID>/**`

## How to Add a Protected Run ID

Edit `repro/protected_runs.yaml`:

1. Add the run id under `protected_run_ids`.
2. Add a short reason in `notes.<RUN_ID>`.

Example:

```yaml
protected_run_ids:
  - 20260211_120855
notes:
  "20260211_120855": "P6 combined orchestration evidence"
```

## Baseline Deletion Safety

Baseline runs are never considered unless `--include-baseline` is explicitly passed.

Even with `--include-baseline`, baseline runs still require explicit allowlisting via:

- `baseline_delete_allowlist` in `repro/protected_runs.yaml`

If a baseline run is not in `baseline_delete_allowlist`, it remains protected.

## Commands

Dry-run inventory + plan (default safe):

```bash
bash repro/tools/cleanup_runs.sh --dry-run
```

Dry-run with recommended retention/thinning:

```bash
bash repro/tools/cleanup_runs.sh \
  --dry-run \
  --keep-last 15 \
  --older-than-days 21 \
  --thin-old \
  --thin-old-days 21 \
  --delete-failed
```

Apply same policy (destructive):

```bash
bash repro/tools/cleanup_runs.sh \
  --apply \
  --keep-last 15 \
  --older-than-days 21 \
  --thin-old \
  --thin-old-days 21 \
  --delete-failed
```

Generate run inventory files:

```bash
python3 repro/tools/run_inventory.py
# writes repro/run_inventory.csv and repro/run_inventory.json
```

## Audit Logs

Every run of cleanup tooling writes audit logs to:

- `repro/cleanup_logs/<timestamp>_{dryrun|apply}.log`
- `repro/cleanup_logs/<timestamp>_{dryrun|apply}.json`

The logs include the full plan and exact paths selected for deletion/thinning.

# Unified Workflow README

## Entrypoint

```bash
Rscript --vanilla scripts/unified_run.R --config <yaml> [--dry-run]
```

- `--config` is required.
- `--dry-run` validates config, writes `resolved_config.yaml` and `run_manifest.yaml`, and exits.

## Config template

Start from:

- `config/unified_run.template.yaml`

## Strict vs fast

Set in config:

- `run.repro_mode: strict` for deterministic single-thread defaults and zero-tolerance comparisons.
- `run.repro_mode: fast` for throughput-oriented runs with tolerance-based validation.

## Example: strict dry-run

```bash
Rscript --vanilla scripts/unified_run.R \
  --config config/unified_run.template.yaml \
  --dry-run
```

## Example: strict execute (selected stages)

```bash
Rscript --vanilla scripts/unified_run.R --config /tmp/unified_stage8.yaml
```

## Canonical run comparison

Set:

- `validation.canonical_run_id: <RUN_ID>`

Validation will compare against:

- `repro/runs/<canonical_run_id>/post/outputs/<canonical_run_id>/`

and write:

- `repro/runs/<RUN_ID>/validate/compare_report.json`
- `repro/runs/<RUN_ID>/validate/env_drift_report.json` (when canonical run provided)

## Drift approval workflow

Drift is tracked through `change_approval` in `run_manifest.yaml`:

- `status: pending|approved|rejected`
- approver, rationale, expected-diff patterns, and thresholds

A run with drift should not be treated as accepted until approval is explicitly marked `approved`.

## Outputs

All unified workflow outputs are run-scoped under:

- `repro/runs/<RUN_ID>/...`

Key files:

- `resolved_config.yaml`
- `run_manifest.yaml`
- `validate/compare_report.json`
- `validate/write_audit/...`
- `report/summary.md`
- `report/summary.json`
- `env/*`

## Legacy entrypoints

Legacy scripts are preserved and now emit deprecation notices:

- `scripts/run_DISC_Optimal_Synth_Ranges_W.R`
- `scripts/run_environmetrics_figures.R`

Use `scripts/unified_run.R` for all new orchestration.

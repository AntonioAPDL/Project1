# Unified Workflow README

## Entrypoint

```bash
Rscript --vanilla scripts/unified_run.R --config <yaml> [--dry-run]
```

- `--config` is required.
- `--dry-run` validates config, writes `resolved_config.yaml` and `run_manifest.yaml`, and exits.

## Production Heavy Run Harness

Committed heavy config:

- `config/unified_runs/heavy_site11160500_cutoff20221225.yaml`

Heavy runner:

- `repro/run_unified_heavy.sh`

Run commands:

```bash
bash repro/run_unified_heavy.sh
```

```bash
FORECATS=1 bash repro/run_unified_heavy.sh
```

```bash
RUN_TWICE=1 bash repro/run_unified_heavy.sh
```

Notes:

- Required external file: `/data/muscat_data/jaguir26/projects/Project/Input/exAL/parameters/parameters.txt`
- Legacy fit/post CSV inputs are `retros_2022-12-25.csv`, `nws_forecast.csv`, and `weighted_time_series.csv`.
- Those legacy CSVs are treated as `log1p_cms`; unified adapters convert and assert scale contracts before fit/post legacy `log(...)` paths.
- The heavy runner creates run-scoped CSV copies under `repro/runs/<RUN_ID>/inputs/`; if a numeric column has non-finite values, it applies a deterministic nearest-finite repair before adapter conversion so the strict adapter contract remains enforceable.
- The heavy runner writes a resolved config for each run under `repro/runs/<RUN_ID>/resolved_config.yaml` with run-scoped overrides (run_id, optional canonical run, optional forecats auto-enable).
- If `FORECATS=1` and no matching existing bundle is found under `data/forecats_inputs/site=11160500/cutoff_date=2022-12-25/`, the heavy run proceeds with `forecats` disabled and writes an explicit skip reason into run report outputs.

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

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

## Implementation Modes

Model-family implementation modes are configured under `models.<family>.implementation_mode`.

- Default modes:
  - `models.exdqlm_univar.implementation_mode: theory_aligned`
  - `models.ndlm_main.implementation_mode: theory_aligned`
- Legacy fallback remains supported explicitly with:
  - `legacy_bridge`

Example legacy override:

```yaml
models:
  run_exdqlm_univar: true
  run_ndlm_main: true
  exdqlm_univar:
    implementation_mode: legacy_bridge
  ndlm_main:
    implementation_mode: legacy_bridge
```

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

## Validator Profiles And Commands

Validation profiles:

- `production`: canonical 7-quantile enforcement (`1,5,10,50,90,95,99`) with strict production gates.
- `production_proof`: config-declared quantile enforcement for bounded proof runs, with all other production-like gates retained.
- `smoke`: lightweight contract for smoke runs.

Canonical run-scoped commands:

```bash
# Canonical production runs (expected auto resolution: production)
bash repro/tools/validate_run.sh <RUN_ID> --profile auto --exit-nonzero
```

```bash
# Proof/bounded runs (expected auto resolution: production_proof)
bash repro/tools/validate_run.sh <RUN_ID> --profile auto --exit-nonzero
```

```bash
# Explicit full canonical production validation
bash repro/tools/validate_run.sh <RUN_ID> --profile production --exit-nonzero
```

Important:

- Do not run `--profile production` on bounded proof runs (expected `FAIL` by design if not all 7 quantiles exist).

## Canonical Production Run (7 Quantiles, All Families)

Committed config:

- `config/unified_runs/production_canonical_family.yaml`

Run command:

```bash
Rscript --vanilla scripts/unified_run.R --config config/unified_runs/production_canonical_family.yaml
```

Validator command:

```bash
bash repro/tools/validate_run.sh <RUN_ID> --profile auto --exit-nonzero
```

Notes:

- This config enables all three families with theory-aligned univariate/NDLM implementation modes.
- Canonical quantiles are `[0.01, 0.05, 0.10, 0.50, 0.90, 0.95, 0.99]`.

## Production-Proof Run (Bounded Quantiles)

Committed proof config:

- `config/unified_runs/production_proof_p7b_family.yaml`

Proof runs are non-canonical and intended for bounded gate/orchestration validation, not canonical production equivalence.

## Extreme-Quantile Stabilization (Opt-In)

For q-tail debugging (for example `q=0.01`), multivar DISC-W now supports opt-in controls under:

```yaml
fit:
  exdqlm_multivar:
    gamma_sigma:
      warmup_freeze_iters: 0
      freeze_target: "gamma_sigma"
      guard_refreeze_iters: 0
      init:
        mode: "legacy"
        gamma: 0.0
        sigma_floor: 1.0e-3
        sigma_scale: 1.0
      objective_guard:
        enabled: false
        fail_fast: false
        log_failures: true
        mode: "penalty"
        penalty: 1.0e12
```

Notes:

- Defaults preserve current behavior (`warmup_freeze_iters=0`, `objective_guard.enabled=false`).
- `objective_guard.mode=penalty` keeps the prior behavior (finite-penalty fallback on non-finite objective calls).
- `objective_guard.mode=adaptive_freeze` triggers refreeze windows (`guard_refreeze_iters`) when the non-finite pattern is detected.
- `warmup_freeze_iters>0` applies initial freeze to the selected target (`freeze_target: gamma_sigma|states`).
- `init.mode=robust` seeds gamma/sigma from conservative defaults (`gamma`) and robust response spread (`sigma_floor`, `sigma_scale`); `init.mode=legacy` keeps previous seeds.

Committed isolated q=0.01 debug template:

- `config/unified_runs/debug_q01_multivar_extreme.yaml`

## Write-Audit Policy

- Production default: `write_audit.enforce_from_stage: 4` (audit starts at `validate` and includes `report`).
- Migration/proof recommendation: `write_audit.enforce_from_stage: 2` (audit from `fit` onward for fit/post isolation evidence).
- Example overlay config: `config/unified_runs/migration_write_audit_from_fit.yaml`.

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

## Posterior Table Exports

During post stage, table exports are written under:

- `repro/runs/<RUN_ID>/post/outputs/<RUN_ID>/`

Files:

- `gamma_summary.csv`
- `sigma_summary.csv`
- `covariate_effects_summary.csv`
- optional snippets: `gamma_summary.tex`, `sigma_summary.tex`, `covariate_effects_summary.tex`
- `posterior_table_exports_README.md`

Column contract:

- `gamma_summary.csv` and `sigma_summary.csv`:
  - `quantile`, `source`, `stat`, `center`, `q2_5`, `q97_5`, `ci_str`
- `covariate_effects_summary.csv`:
  - `covariate`, `quantile`, `center`, `q2_5`, `q97_5`, `ci_str`, `time_index`, `notes`

Center policy:

- `gamma` / `sigma`: `center` is posterior median (matches the quantile-based summary currently used in post outputs).
- covariate effects: `center` is posterior mean (matches the existing component summary block).

Control flag:

- `post.export_tables: true|false` (default `true`) in unified config.

## Legacy entrypoints

Legacy scripts are preserved and now emit deprecation notices:

- `scripts/run_DISC_Optimal_Synth_Ranges_W.R`
- `scripts/run_environmetrics_figures.R`

Use `scripts/unified_run.R` for all new orchestration.

# HE3 exDQLM Multivar Ablation Workflow

This workflow runs the HE3 ablation study for the finalized `exdqlm_multivar_keep`
winner selected from the completed `featurecov_cf1_eps` sweep.

## Study Design

- Baseline family: `exdqlm_multivar_keep`
- Selection source: finalized best-by-cutoff HE2 winners from the completed
  `multimodel_v8_featurecov_cf1_eps_sweep_20260416` study
- Fixed per cutoff:
  - best epsilon from HE2
  - `c_factor = 1.0`
  - featurecov covariates and deterministic climate handoff
- Ablation variants:
  - `full`
  - `noTrend`
  - `noTF`
  - `noH1`
  - `noH2`
  - `noH3`

## Variant Semantics

| Variant | Trend | Harmonic 1 | Harmonic 2 | Harmonic 3 | Transfer / Covariates |
|---|---:|---:|---:|---:|---:|
| `full` | on | on | on | on | on |
| `noTrend` | off | on | on | on | on |
| `noTF` | on | on | on | on | off |
| `noH1` | on | off | on | on | on |
| `noH2` | on | on | off | on | on |
| `noH3` | on | on | on | off | on |

Seasonal harmonic mapping:

- `H1 = 1`
- `H2 = 2`
- `H3 = 1 / 6.8068493`

`noTF` is implemented as:

- `fit.exdqlm_multivar.legacy.use_covariates = false`
- `models.exdqlm_multivar.forecast_transfer_mode = drop`

This removes transfer use in both the historical fit and the forecast handoff.
Under the shared fit/post artifact contract, that also switches the legacy bundle suffix
from `_DISC` to `_simp`, so post-stage resolution must follow the same `use_covariates`
setting rather than assuming the ordinary transfer-enabled filename.
At post load time, `_simp` multivariate bundles are aliased onto the canonical
`*_exAL_synth_DISC` object names so the downstream smoke/publication modules can
consume a stable interface regardless of whether transfer/covariates were enabled.

## Structural Wiring

Shared structure logic lives in:

- [R/unified/families/exdqlm_multivar_structure.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/exdqlm_multivar_structure.R)

It is consumed by:

- [DISC_Optimal_Synth_Ranges_W.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W.r)
- [DISC_Optimal_Synth_Ranges_W_transfer_forecast.r](/data/muscat_data/jaguir26/project1_ucsc_phd/DISC_Optimal_Synth_Ranges_W_transfer_forecast.r)
- [R/environmetrics/20_model_setup.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/environmetrics/20_model_setup.R)

Unified stage bridges export the ablation contract through:

- `DISC_W_INCLUDE_TREND`
- `DISC_W_ENABLED_HARMONIC_INDICES`
- `UNIFIED_EXDQLM_MULTIVAR_INCLUDE_TREND`
- `UNIFIED_EXDQLM_MULTIVAR_ENABLED_HARMONIC_INDICES`

## Runtime Layout

- Template:
  [config/multimodel_v8_he3_exdqlm_ablation.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_he3_exdqlm_ablation.template.yaml)
- Artifact root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20260420`
- Matrix dir:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20260420/control/he3_exdqlm_ablation_v1`

Generated control artifacts:

- `matrix_plan.csv`
- `matrix_status.csv`
- `selection_manifest.csv`
- `matrix_metadata.yaml`
- `launch_settings.env`
- `plan_summary.md`
- `validation_summary.md`

Summary outputs:

- `reports/he3_exdqlm_ablation/he3_ablation_long.csv`
- `reports/he3_exdqlm_ablation/he3_ablation_wide.csv`
- `reports/he3_exdqlm_ablation/he3_ablation_summary.md`
- `reports/he3_exdqlm_ablation/he3_table_rows.tex`
- `reports/he3_exdqlm_ablation/audit/he3_ablation_audit.csv`
- `reports/he3_exdqlm_ablation/audit/he3_ablation_lead_buckets.csv`
- `reports/he3_exdqlm_ablation/audit/he3_ablation_audit.md`

## Launch Policy

- Total study rows: `30`
- Reused full references: `5`
- New launched rows: `25`
- Queue concurrency:
  - ordinary cutoffs: up to `4`
  - heavy cutoff `20221225`: up to `1`
- Pilot gating:
  - group `1`: `20211112`
  - group `2`: `20221225`
  - group `3`: remaining cutoffs

The queue only advances to the next group after the current group has passed.

## Commands

Build the matrix:

```bash
python3 scripts/build_he3_exdqlm_ablation_matrix.py \
  --template config/multimodel_v8_he3_exdqlm_ablation.template.yaml
```

Validate the frozen references and generated configs:

```bash
python3 scripts/validate_he3_exdqlm_ablation.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20260420/control/he3_exdqlm_ablation_v1 \
  --template config/multimodel_v8_he3_exdqlm_ablation.template.yaml
```

Launch the controller:

```bash
python3 scripts/launch_he3_exdqlm_ablation.py \
  --template config/multimodel_v8_he3_exdqlm_ablation.template.yaml
```

Build the final summary after completion:

```bash
python3 scripts/build_he3_exdqlm_ablation_summary.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20260420/control/he3_exdqlm_ablation_v1
```

Run the inheritance audit after completion:

```bash
python3 scripts/audit_he3_exdqlm_ablation.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20260420/control/he3_exdqlm_ablation_v1 \
  --output-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20260420/reports/he3_exdqlm_ablation/audit
```

The audit checks that each launched ablation row:

- preserves the same fixed covariate bundle, engineered lag/interaction files, and fit adapters as the source full-model run
- preserves the same fixed discount factors, forecast-covariance settings, and fit hyperparameters
- changes only the intended structural toggles:
  - trend on/off
  - enabled harmonic indices
  - transfer/covariate usage
- resolves the correct target synthesized model id in post (`keep` vs `drop`)
- shows lead-bucket diagnostics so large degradations can be distinguished from malformed runs

## Testing

Primary regression coverage:

- [tests/python/test_he3_exdqlm_ablation_tooling.py](/data/muscat_data/jaguir26/project1_ucsc_phd/tests/python/test_he3_exdqlm_ablation_tooling.py)

That suite checks:

- 30-row matrix generation
- 5 reused full references and 25 launch rows
- `noTF` config wiring
- end-to-end validator pass on a synthetic frozen study

The live validator also executes a structure smoke check against the real R helper.

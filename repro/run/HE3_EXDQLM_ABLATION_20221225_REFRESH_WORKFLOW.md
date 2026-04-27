# HE3 `20221225` Refresh Workflow

This workflow refreshes the HE3 ablation slice for cutoff `12/25/2022` so the
full-model reference is the current published HE2 `exAL-M-T1` winner rather than
the earlier `eps360cf1` winner.

## Why This Refresh Exists

The original HE3 study reused the old full reference:

- `multimodel_20221225_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1`
- mean CRPS `0.6143974397`

The current published HE2 row now uses:

- `multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep`
- mean CRPS `0.4375250570`

The two runs share the same scientific input contract:

- same retrospective input
- same raw `nws` forecast
- same raw `glofas` forecast
- same `PPT|SOIL|PCA`
- same deterministic-climate future files
- same engineered lag / square / interaction features
- same transfer mode and likelihood

The scientific difference is the full-model state-evolution discount block.

## Refresh Scope

- cutoff filter: `20221225`
- total rows: `6`
- reused full reference rows: `1`
- launched ablation rows: `5`

Variants:

- `full` -> reuse the published HE2 winner directly
- `noTrend`
- `noTF`
- `noH1`
- `noH2`
- `noH3`

## Runtime Policy

- `fit.parallel.workers = 1`
- `run.threads.mc_cores = 1`
- queue concurrency up to `4`

The single-core setting applies to each launched quantile model so the refresh
remains efficient without reproducing the heavier `7`-worker launch contract
from the earlier study.

## Template

- [config/multimodel_v8_he3_exdqlm_ablation_20221225_refresh.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_he3_exdqlm_ablation_20221225_refresh.template.yaml)

## Commands

Build the focused matrix:

```bash
python3 scripts/build_he3_exdqlm_ablation_matrix.py \
  --template config/multimodel_v8_he3_exdqlm_ablation_20221225_refresh.template.yaml
```

Validate the matrix and frozen references:

```bash
python3 scripts/validate_he3_exdqlm_ablation.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20221225_refresh_20260426/control/he3_exdqlm_ablation_20221225_refresh_v1 \
  --template config/multimodel_v8_he3_exdqlm_ablation_20221225_refresh.template.yaml
```

Dry-run the controller launch command:

```bash
python3 scripts/launch_he3_exdqlm_ablation.py \
  --template config/multimodel_v8_he3_exdqlm_ablation_20221225_refresh.template.yaml \
  --dry-run
```

Launch the controller:

```bash
python3 scripts/launch_he3_exdqlm_ablation.py \
  --template config/multimodel_v8_he3_exdqlm_ablation_20221225_refresh.template.yaml
```

Build the focused summary after completion:

```bash
python3 scripts/build_he3_exdqlm_ablation_summary.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20221225_refresh_20260426/control/he3_exdqlm_ablation_20221225_refresh_v1
```

Run the inheritance audit after completion:

```bash
python3 scripts/audit_he3_exdqlm_ablation.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20221225_refresh_20260426/control/he3_exdqlm_ablation_20221225_refresh_v1 \
  --output-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_20221225_refresh_20260426/reports/he3_exdqlm_ablation/audit
```

## Acceptance Gates

- The full row must resolve to the published HE2 source run and exact CRPS.
- All launched rows must inherit the same shared scientific inputs as the full row.
- The launched rows may differ only in the intended structure toggles:
  - trend on/off
  - enabled harmonic indices
  - transfer / covariate usage
- No row may silently inherit the older `eps360cf1` full-model discount block.

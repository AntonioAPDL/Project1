# HE2 Wave A NDLM Validator Runbook

Date: 2026-05-16

## Purpose

This runbook defines the **approved Stage 1 operator path** for the first remaining-family relaunch wave:

- `ndlm_univar_keep`
- `ndlm_main_drop`
- `ndlm_main_keep`

The goal is to make Wave A launchable only after we have:

1. frozen the Stage 1 launcher/spec contract,
2. refreshed the revised-article main-model bundle and cutoff-wide figure families,
3. generated Wave A configs from the approved manifest-driven relaunch builder,
4. and passed the prelaunch validator under the corrected shared-input contract.

## Approved files

- Stage 1 contract builder:
  - `scripts/build_he2_full_crps_stage1_contract.py`
- Stage 1 contract bundle:
  - `reports/he2_full_crps_stage1_contract_20260516/`
- Approved relaunch builder:
  - `scripts/build_he2_bayesian_publication_relaunch_configs.py`
- Approved prelaunch validator:
  - `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`
- Approved launcher:
  - `scripts/launch_he2_bayesian_publication_relaunch.py`
- Wave A template:
  - `config/he2_bayesian_publication_relaunch_wave_a_ndlm_20260516.template.yaml`
- Wave A batch:
  - `config/he2_relaunch_batches/he2_wave_a_ndlm_remaining_families_20260516.yaml`

The older family-specific matrix builders are **not** approved launch authorities for Wave A.

## Scope

Wave A covers:

- all 5 HE2 cutoffs
- 3 NDLM families
- 15 Bayesian rows total

This scope is also frozen in:

- `reports/he2_full_crps_stage1_contract_20260516/wave_a_ndlm_rows.csv`

## Preconditions

Before validating Wave A, refresh the Stage 1 workflow and revised-article evidence.

### 1. Rebuild the Stage 1 contract bundle

```bash
python3 scripts/build_he2_full_crps_stage1_contract.py
```

Required outputs:

- `reports/he2_full_crps_stage1_contract_20260516/HE2_FULL_CRPS_STAGE1_LAUNCHER_QUALIFICATION_20260516.md`
- `reports/he2_full_crps_stage1_contract_20260516/remaining_family_relaunch_matrix.csv`
- `reports/he2_full_crps_stage1_contract_20260516/remaining_family_spec_freeze.csv`
- `reports/he2_full_crps_stage1_contract_20260516/wave_a_ndlm_rows.csv`

### 2. Refresh the revised-article generated assets

```bash
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_all_generated_assets.py
```

Required figure-side outputs:

- `Evironmetrics---REVISED-DOC-Corrected-2/artifacts/five_cutoff_setup_support/`
- `Evironmetrics---REVISED-DOC-Corrected-2/figures/forecast_context_by_cutoff/`
- `Evironmetrics---REVISED-DOC-Corrected-2/artifacts/five_cutoff_main_model_synthesis/`
- `Evironmetrics---REVISED-DOC-Corrected-2/artifacts/five_cutoff_reference_synthesis/`
- `Evironmetrics---REVISED-DOC-Corrected-2/figures/multivariate_synthesis_by_cutoff/`
- `Evironmetrics---REVISED-DOC-Corrected-2/figures/reference_synthesis_by_cutoff/`
- `Evironmetrics---REVISED-DOC-Corrected-2/reports/five_cutoff_synthesis_review/FIVE_CUTOFF_SYNTHESIS_REVIEW.md`

## Build step

Generate the Wave A relaunch matrix and configs with the approved template and batch.

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_wave_a_ndlm_20260516.template.yaml \
  --batch-file config/he2_relaunch_batches/he2_wave_a_ndlm_remaining_families_20260516.yaml
```

Required builder outputs:

- `matrix_plan.csv`
- `selection_summary.csv`
- `frozen_spec_manifest.csv`
- `cutoff_bundle_audit.csv`
- `he2_publication_relaunch_scope.md`

Wave A acceptance at the build stage:

1. `matrix_plan.csv` contains 15 rows
2. `selection_summary.csv` contains only `ndlm` rows
3. `frozen_spec_manifest.csv` preserves the current publication-winning NDLM row specs
4. `cutoff_bundle_audit.csv` shows the corrected shared-input lineage for all 5 cutoffs

## Validation step

Run the prelaunch validator against the same template and batch.

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_wave_a_ndlm_20260516.template.yaml \
  --batch-file config/he2_relaunch_batches/he2_wave_a_ndlm_remaining_families_20260516.yaml
```

Expected validator behavior:

- bundle build: `passed`
- family smokes: `passed`
- cutoff smokes: `passed`
- NDLM fit smoke: `passed`
- NDLM full-pipeline smoke: `passed`
- quantile smoke scopes: `skipped`

The quantile smoke scopes are expected to be skipped because Wave A intentionally selects only NDLM rows.

Wave A validation is a **go** only if:

1. the validator returns exit code `0`
2. no bundle-identity check fails
3. no NDLM smoke fails
4. skipped smoke scopes are limited to quantile classes that are intentionally absent from the selected batch

## Optional dry-run launch preview

Before a real queue launch, print the exact queue command:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_wave_a_ndlm_20260516.template.yaml \
  --batch-file config/he2_relaunch_batches/he2_wave_a_ndlm_remaining_families_20260516.yaml \
  --dry-run
```

## Real launch command

Only after the validator passes:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_wave_a_ndlm_20260516.template.yaml \
  --batch-file config/he2_relaunch_batches/he2_wave_a_ndlm_remaining_families_20260516.yaml
```

## Stop / reset rule

If Wave A needs a clean restart, use the approved reset helper against the same template:

```bash
python3 scripts/reset_he2_bayesian_publication_relaunch_state.py \
  --template config/he2_bayesian_publication_relaunch_wave_a_ndlm_20260516.template.yaml
```

Do not hand-delete matrix state or runtime directories.

## Evidence to retain

Keep these after validation and after launch:

- `reports/he2_full_crps_stage1_contract_20260516/`
- Wave A `matrix_plan.csv`
- Wave A `frozen_spec_manifest.csv`
- Wave A `cutoff_bundle_audit.csv`
- validator output directory under the Wave A runtime root
- revised-article synthesis/forecast-context manifests

## Bottom line

Wave A is ready to move only if the manifest-driven builder, the shared-input validator, and the revised-article Stage 1 asset refresh all agree on the same corrected lineage.

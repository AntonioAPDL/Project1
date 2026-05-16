# HE2 exdqlm_multivar_keep All-Cutoff Rerun Runbook

Date: 2026-05-16

## Purpose

Prepare and validate a clean all-cutoff rerun package for `exdqlm_multivar_keep` using:

- the manifest-driven publication relaunch builder
- the corrected shared input bundles
- the exact publication-winning per-cutoff exdqlm specs
- the current corrected runtime codebase

This runbook is intentionally **no-launch**. It ends at validated readiness.

## Approved launcher contract

Use only:

- `scripts/build_he2_bayesian_publication_relaunch_configs.py`
- `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`
- `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_rerun_20260516.template.yaml`
- `config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_rerun_20260516.yaml`

Do not use the older family-specific matrix builders for this rerun.

## Frozen publication-winning spec source

Generate the audited spec freeze and bundle contract:

```bash
python3 scripts/build_he2_exdqlm_multivar_keep_rerun_contract.py
```

Artifacts are written to:

- `reports/he2_exdqlm_multivar_keep_rerun_contract_20260516/`

## Builder dry-build

Build the rerun configs without launching:

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_rerun_20260516.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_rerun_20260516.yaml
```

Expected result:

- `5` selected rows
- `5` generated configs
- `cutoff_bundle_audit.csv` written under the rerun matrix root
- `frozen_spec_manifest.csv` reflects the per-cutoff spec freeze, especially the `20221225` discount override

## Prelaunch validator

Run the validator on the same template and batch. This performs bundle checks plus smoke runs, but it does not start the queue controller.

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_rerun_20260516.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_rerun_20260516.yaml
```

Expected validator behavior:

- bundle build: pass
- within-cutoff bundle alignment: pass
- quantile fit smokes: run the representative execution matrix on `20210123 q50`, `20211221 q50`, and `20221225 q50/q65`
- full-pipeline quantile smokes: run on `20210123`, `20211221`, and `20221225`, with `20221225` including `q65`
- NDLM/univariate smoke scopes: expected to skip because the selected rerun scope is quantile multivariate only

## Readiness note

After the validator passes, build the readiness note:

```bash
python3 scripts/build_he2_exdqlm_multivar_keep_rerun_readiness.py
```

This emits a reviewer-facing summary under:

- `reports/he2_exdqlm_multivar_keep_rerun_contract_20260516/`

## Explicit stop condition

Do **not** run the publication relaunch queue controller in this stage.

No command from this runbook should start the live relaunch.

## Launch gate for a later step

Only after the contract, builder, validator, and readiness note are all green should we decide whether to relaunch the 5 exdqlm rows for real.

# HE2 exdqlm_univar Shared Relaunch Plan

## Purpose

Prepare a clean, reproducible, no-launch implementation plan for `exdqlm_univar` under the same corrected HE2 publication relaunch workflow used by the live shared-spec multivariate campaigns.

This stage does **not** launch anything.

## Scope

- family: `exdqlm_univar`
- manuscript label: `exAL-U-T1`
- cutoffs:
  - `20210123`
  - `20211112`
  - `20211221`
  - `20220511`
  - `20221225`
- reference live campaigns:
  - `exdqlm_multivar_keep`
  - `exdqlm_multivar_drop`

## Investigation builder

Rebuild the no-launch investigation bundle with:

```bash
python3 scripts/build_he2_exdqlm_univar_shared_relaunch_investigation.py
```

Outputs land here:

- `reports/he2_exdqlm_univar_shared_relaunch_investigation_20260516/`

Key artifacts:

- `HE2_EXDQLM_UNIVAR_SHARED_RELAUNCH_INVESTIGATION_20260516.md`
- `exdqlm_univar_scope_matrix.csv`
- `bundle_parity_table.csv`
- `spec_parity_table.csv`
- `reuse_adaptation_mapping_table.csv`
- `readiness_summary.json`

## Current boundary

- use the approved manifest-driven publication relaunch builder / validator path
- do not reuse the older univariate featurecov launcher directly
- do not launch the univariate campaign from this stage
- do not disturb the live multivariate `keep` or `drop` runs

## What the investigation must settle before packaging

1. exact shared-bundle parity to the canonical `20260510` publication shared-input lineage
2. exact univariate projection of the multivariate shared discount bundle
3. explicit policy for `epsilon` and `c_factor`, because the current univariate fit path does not appear to consume them
4. partial q50 stabilization mapping for univariate EXDQLM under the approved validator path

## Next implementation boundary after this stage

Only after the investigation outputs are reviewed should we create:

- `config/he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml`
- `config/he2_relaunch_batches/exdqlm_univar_all_cutoffs_sharedspec_20260516.yaml`
- no-launch validation artifacts for the final exact univariate batch

Until then, this remains a planning-and-audit stage only.

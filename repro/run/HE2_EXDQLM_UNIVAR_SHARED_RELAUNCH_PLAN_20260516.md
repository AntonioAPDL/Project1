# HE2 exdqlm_univar Shared Relaunch Plan

## Purpose

Prepare the full no-launch `exdqlm_univar` shared-spec relaunch package under the approved HE2 Bayesian publication relaunch workflow.

This stage does **not** launch anything.

## Contract

- family: `exdqlm_univar`
- manuscript label: `exAL-U-T1`
- corrected shared input lineage: `multimodel_v8_he2_publication_shared_inputs_20260510`
- full history: `1987-05-29 -> cutoff`
- deterministic climate: blended `PPT` and `SOIL`
- climate factor alias: `PCA(alias=GDPC1)`
- shared projected state-evolution discount set: `set10_manual_20260516`
- non-applicable knobs remain absent:
  - `epsilon`
  - `c_factor`
  - `df_discrep`
- published univariate implementation mode remains `legacy_bridge`
- multivariate-style q50 gamma/sigma stabilization knobs are not operative under `legacy_bridge`

## Package files

- template: `config/he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml`
- batch: `config/he2_relaunch_batches/exdqlm_univar_all_cutoffs_sharedspec_20260516.yaml`
- report builder: `scripts/build_he2_exdqlm_univar_shared_relaunch_plan.py`
- validation status builder: `scripts/build_he2_exdqlm_univar_shared_relaunch_validation_status.py`
- report root: `reports/he2_exdqlm_univar_shared_relaunch_plan_20260516/`

## Rebuild the report bundle

```bash
python3 scripts/build_he2_exdqlm_univar_shared_relaunch_plan.py
```

## Builder dry-run

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_univar_all_cutoffs_sharedspec_20260516.yaml
```

## Exact-final-batch no-launch validation

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_univar_all_cutoffs_sharedspec_20260516.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_univar_all_cutoffs_sharedspec_20260516.yaml \
  --outdir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516/control/prelaunch_validation_exact_final_batch_20260516
```

## Rebuild validation status artifacts

```bash
python3 scripts/build_he2_exdqlm_univar_shared_relaunch_validation_status.py
```

## Validation goals

1. builder generates exactly 5 `exdqlm_univar` rows
2. all generated configs point to the canonical `20260510` shared-input bundle lineage
3. full-history support starts at `1987-05-29`
4. shared projected state evolution is applied exactly:
   - `df_t=0.99999999`
   - `df_s1=0.99999`
   - `df_s2=0.99999`
   - `df_s67=0.99999`
   - `lambda=0.97`
   - `df_trans=0.9999999`
   - `df_covs=0.9999999`
5. `df_discrep` remains absent
6. `epsilon` and `c_factor` remain absent by design
7. no launch claim depends on multivariate-style q50 gamma/sigma overrides
8. the real operative scientific projection is:
   - canonical shared inputs
   - full-history retrospective window
   - shared univariate state-evolution discount block
9. the real operative validation gates are the exact-final-batch q50 smoke runs
10. no queue launch occurs during validation

## Current launch boundary

- ready to package and validate in no-launch mode
- not ready to launch until the exact-final-batch validator and targeted q50 smokes pass
- do not disturb the live multivariate `keep` or `drop` relaunches

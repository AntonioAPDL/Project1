# HE2 AL Shared Relaunch Plan

## Purpose

Prepare three no-launch HE2 AL relaunch packages that mirror the corrected shared-spec exAL relaunches already established for:

- `exdqlm_multivar_keep`
- `exdqlm_multivar_drop`
- `exdqlm_univar`

The AL packages are:

- `dqlm_multivar_al_keep`
- `dqlm_multivar_al_drop`
- `dqlm_univar_al`

This stage does **not** launch anything.

## Historical contract confirmed from code

The historical AL implementation is operative, not nominal:

- `gamma = 0` under AL
- latent `s_t` contributions are set to `0` under AL
- the gamma/scale delta approximation becomes sigma-only under AL

Primary evidence:

- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- `R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R`
- `R/unified/stages/stage_fit.R`
- `config/multimodel_v8_all9_featurecov.template.yaml`
- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`

## Package inventory

- template: `config/he2_bayesian_publication_relaunch_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.template.yaml`
- batch: `config/he2_relaunch_batches/dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.yaml`
- template: `config/he2_bayesian_publication_relaunch_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.template.yaml`
- batch: `config/he2_relaunch_batches/dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.yaml`
- template: `config/he2_bayesian_publication_relaunch_dqlm_univar_al_all_cutoffs_sharedspec_20260517.template.yaml`
- batch: `config/he2_relaunch_batches/dqlm_univar_al_all_cutoffs_sharedspec_20260517.yaml`
- report builder: `scripts/build_he2_al_shared_relaunch_plan.py`
- validation status builder: `scripts/build_he2_al_shared_relaunch_validation_status.py`
- report root: `reports/he2_al_shared_relaunch_plan_20260517/`

## Shared corrected input contract

All three AL packages use:

- shared bundle artifact root:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
- shared bundle run id:
  - `20260510_publication_shared_r01`
- full retrospective / USGS window:
  - `1987-05-29 -> cutoff`
- deterministic blended covariates:
  - `PPT`, `SOIL`
- climate factor alias:
  - `PCA(alias=GDPC1)`
- same lag/interactions/covariate contract as the exAL shared-spec relaunches

## Shared modern relaunch choice

These AL packages intentionally reuse the **current corrected exAL shared-spec relaunch bundle** where applicable:

- multivariate AL keep/drop use:
  - `epsilon=30.0`
  - `c_factor=1.0`
  - shared discount block:
    - `df_t=0.99999999`
    - `df_s1=0.99999`
    - `df_s2=0.99999`
    - `df_s67=0.99999`
    - `df_discrep=0.99999`
    - `lambda=0.97`
    - `df_trans=0.9999999`
    - `df_covs=0.9999999`
- univariate AL uses the same shared discount block except `df_discrep` remains absent
- univariate AL keeps `forecast_cov` absent by design

This is a deliberate shared-spec relaunch choice. It is not the same thing as replaying the historical per-cutoff AL winners exactly.

## Rebuild the report bundle

```bash
python3 scripts/build_he2_al_shared_relaunch_plan.py
```

## Builder dry-runs

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.template.yaml \
  --batch-file config/he2_relaunch_batches/dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.yaml

python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.template.yaml \
  --batch-file config/he2_relaunch_batches/dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.yaml

python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_dqlm_univar_al_all_cutoffs_sharedspec_20260517.template.yaml \
  --batch-file config/he2_relaunch_batches/dqlm_univar_al_all_cutoffs_sharedspec_20260517.yaml
```

## Exact-final-batch no-launch validation

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.template.yaml \
  --batch-file config/he2_relaunch_batches/dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.yaml \
  --outdir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517/control/prelaunch_validation_exact_final_batch_20260517

python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.template.yaml \
  --batch-file config/he2_relaunch_batches/dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.yaml \
  --outdir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517/control/prelaunch_validation_exact_final_batch_20260517

python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_dqlm_univar_al_all_cutoffs_sharedspec_20260517.template.yaml \
  --batch-file config/he2_relaunch_batches/dqlm_univar_al_all_cutoffs_sharedspec_20260517.yaml \
  --outdir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_univar_al_all_cutoffs_sharedspec_20260517/control/prelaunch_validation_exact_final_batch_20260517
```

## Rebuild validation status artifacts

```bash
python3 scripts/build_he2_al_shared_relaunch_validation_status.py
```

## Late-cutoff AL multivariate follow-up

The original exact-final-batch AL multivariate validators failed on the late
`20221225 q65` hard-case smoke under the lighter validator slice.

To isolate whether that was a true AL instability or a validator-slice artifact,
the current workflow now runs two no-launch production-clone diagnostics:

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_dqlm_multivar_al_keep_20221225_q65_prodclone_diagnostic_20260517.template.yaml \
  --batch-file config/he2_relaunch_batches/dqlm_multivar_al_keep_20221225_q65_prodclone_diagnostic_20260517.yaml \
  --outdir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_20221225_q65_prodclone_diagnostic_20260517/control/prelaunch_validation_prodclone_20221225_q65_20260517

python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_dqlm_multivar_al_drop_20221225_q65_prodclone_diagnostic_20260517.template.yaml \
  --batch-file config/he2_relaunch_batches/dqlm_multivar_al_drop_20221225_q65_prodclone_diagnostic_20260517.yaml \
  --outdir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_20221225_q65_prodclone_diagnostic_20260517/control/prelaunch_validation_prodclone_20221225_q65_20260517
```

Those diagnostics intentionally restore the production-like q65 fit contract:

- `n_samp = 2000`
- `min_update_iters = 50`
- `min_total_iters = 50`
- `max_iter = 100`

They preserve the same corrected shared bundles, full-history contract, GDPC/PPT/SOIL
covariates, and AL likelihood mode as the main AL packages.

## Validation goals

1. the builder selects exactly 5 rows for each AL family package
2. all generated configs point to the canonical `20260510` shared bundle lineage
3. all generated configs pin full history to `1987-05-29 -> cutoff`
4. AL likelihood mode remains operative in generated configs
5. multivariate AL rows reuse the shared exAL relaunch epsilon / c_factor / discount block intentionally
6. univariate AL keeps `forecast_cov` absent and `df_discrep` absent intentionally
7. univariate AL exact-final-batch validation clears through the approved manifest-driven path
8. late-cutoff AL multivariate q65 prodclone diagnostics determine whether keep/drop can be promoted cleanly
9. the live exAL keep/drop/univar campaigns remain undisturbed

## Launch boundary

- do not launch the AL packages in this stage
- only launch after:
  - univariate AL exact-final-batch validation is green
  - multivariate AL keep/drop late-cutoff q65 prodclone diagnostics are green

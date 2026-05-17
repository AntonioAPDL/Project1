# HE2 AL Shared Relaunch Packages

Date: 2026-05-17

## Findings

- historical AL is a first-class likelihood mode, not a post-hoc naming convention
- the user recollection is substantially correct at the operative fit layer:
  - `gamma = 0` under AL
  - latent `s_t` contributions are forced to `0` under AL
  - the gamma/scale delta approximation reduces to sigma-only optimization under AL
- the clean modern implementation is **not** a new ad-hoc gamma clamp; it is the existing `dqlm_*` AL family set routed through the approved manifest-driven relaunch workflow
- the new packages intentionally reuse the corrected shared bundle lineage and the current exAL shared-spec discount bundle for relaunch parity
- that last point is a deliberate relaunch choice and is **not** identical to the historical per-cutoff AL publication-winning epsilon/discount selections

## Historical Contract Evidence

- `family_ids`: `config/multimodel_v8_all9_featurecov.template.yaml`
  - Historical AL families already exist as first-class family ids with likelihood_mode=al and model_key mapped onto exdqlm implementations.
- `fit_mode_plumbing`: `R/unified/stages/stage_fit.R`
  - Modern unified fit stage exports DISC_W_LIKELIHOOD_MODE and UNIV_LIKELIHOOD_MODE so AL vs exAL is selected at runtime without a separate launcher path.
- `multivar_al_operative_contract`: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
  - AL mode fixes gamma to 0, forces E.sts and E.sts2 to 0, and reduces the gamma/scale delta approximation to sigma-only optimization.
- `univar_al_operative_contract`: `R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R`
  - AL mode initializes gamma at 0, keeps Es at 0, ignores gamma inside the objective, and solves only for sigma in the legacy_bridge univariate fit loop.
- `post_model_identity`: `R/environmetrics/02_helpers_core.R`
  - Post/report helper code already maps AL likelihood_mode rows to dqlm_* synth model ids, so AL output identities are already supported in the modern post pipeline.
- `publication_lineage`: `reports/he2_publication_manifest/he2_bayesian_publication_manifest.csv`
  - Historical HE2 publication rows already include AL-U-T1, AL-M-T0, and AL-M-T1 across all five cutoffs with the same covariate/lag/interaction contract as their exAL counterparts.

## Package Scope

| Family | Label | Model class | Reference exAL family | Template | Batch |
|---|---|---|---|---|---|
| `dqlm_multivar_al_keep` | `AL-M-T1` | `quantile_multivariate` | `exdqlm_multivar_keep` | `/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_bayesian_publication_relaunch_dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.template.yaml` | `/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_relaunch_batches/dqlm_multivar_al_keep_all_cutoffs_sharedspec_20260517.yaml` |
| `dqlm_multivar_al_drop` | `AL-M-T0` | `quantile_multivariate` | `exdqlm_multivar_drop` | `/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_bayesian_publication_relaunch_dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.template.yaml` | `/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_relaunch_batches/dqlm_multivar_al_drop_all_cutoffs_sharedspec_20260517.yaml` |
| `dqlm_univar_al` | `AL-U-T1` | `quantile_univariate` | `exdqlm_univar` | `/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_bayesian_publication_relaunch_dqlm_univar_al_all_cutoffs_sharedspec_20260517.template.yaml` | `/data/muscat_data/jaguir26/project1_ucsc_phd/config/he2_relaunch_batches/dqlm_univar_al_all_cutoffs_sharedspec_20260517.yaml` |

## Reuse vs Adaptation

- `manifest-driven builder`: `directly_reusable`
  - path: `scripts/build_he2_bayesian_publication_relaunch_configs.py`
  - note: AL families are already present in MODEL_ID_BY_FAMILY and MODEL_KEY_BY_FAMILY.
- `prelaunch validator`: `directly_reusable`
  - path: `scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py`
  - note: No family-specific launcher fork is needed; AL rows validate through the same smoke pipeline.
- `queue/controller`: `directly_reusable`
  - path: `scripts/run_multimodel_v8_queue.py`
  - note: AL packages use the same serial-by-cutoff queue contract and artifact-root-scoped controller behavior.
- `shared input bundles`: `directly_reusable`
  - path: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
  - note: AL packages point to the same corrected 20260510 shared bundle lineage as the live exAL packages.
- `historical AL family ids`: `directly_reusable`
  - path: `config/multimodel_v8_all9_featurecov.template.yaml`
  - note: The clean implementation uses existing dqlm_* AL families instead of inventing new family ids or ad-hoc patches.
- `shared-spec package templates and batches`: `requires_adaptation`
  - path: `config/he2_bayesian_publication_relaunch_*_sharedspec_20260517.template.yaml`
  - note: Three new AL shared-spec templates and batches are required so the current exAL launch contract can be mirrored cleanly.
- `likelihood-mode enforcement`: `requires_adaptation`
  - path: `config/he2_relaunch_batches/dqlm_*_all_cutoffs_sharedspec_20260517.yaml`
  - note: Batch patches explicitly pin likelihood_mode=al; univariate AL also pins implementation_mode=legacy_bridge.
- `gamma=0 / sigma-only fit behavior`: `not_reimplemented`
  - path: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r; R/unified/families/exdqlm_univar/03_updates_vb_or_fitloop.R`
  - note: Operative AL fit behavior already exists in code and is validated rather than rewritten.

## Readiness

- status: `partially_validated_followup_active`
- shared bundle artifact root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
- shared bundle run id: `20260510_publication_shared_r01`
- shared data start: `1987-05-29`
- runbook: `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/HE2_AL_SHARED_RELAUNCH_PLAN_20260517.md`

Current operational read:

- `dqlm_univar_al`: exact-final-batch validator passed
- `dqlm_multivar_al_keep`: original light validator was inconclusive for late `20221225 q65`; production-clone no-launch diagnostic is now running
- `dqlm_multivar_al_drop`: original light validator was inconclusive for late `20221225 q65`; production-clone no-launch diagnostic is now running

Launch boundary for this report:
- package creation and no-launch validation only
- do not disturb the currently running exAL keep/drop/univar relaunches
- do not launch the AL packages until:
  - `dqlm_univar_al` remains green
  - `dqlm_multivar_al_keep` late-cutoff q65 prodclone validation is green
  - `dqlm_multivar_al_drop` late-cutoff q65 prodclone validation is green

# NDLM Parity Audit Workflow

Last updated: 2026-04-21
Status: complete

## Objective

Establish whether the Normal-likelihood models used in the manuscript tables are true Normal counterparts of the quantile-model families, or whether materially different implementation choices are affecting the comparison.

The audit covers:

- `N-U-T1` / `ndlm_univar_keep`
- `N-M-T0` / `ndlm_main_drop`
- `N-M-T1` / `ndlm_main_keep`

against the corresponding univariate and multivariate DQLM / exDQLM families.

## Success Criteria

The audit is successful when we can:

1. trace each manuscript/table NDLM label to a specific exported run and unified family
2. verify which codepaths, configs, and runtime artifacts define the current NDLM models
3. prove whether per-cutoff inputs, transfer covariates, deterministic-climate blends, and key hyperparameters are aligned with the quantile models
4. trace the multivariate NDLM forecast-window covariance prior from config to code to runtime diagnostics
5. state clearly whether the main remaining difference is the likelihood or whether other discrepancies matter
6. if the current manuscript-facing NDLM rows are not on the intended shared contract, produce a corrected rerun path that is launchable, tested, and reproducible

## Phase Structure

### Phase 1. Inventory and provenance

Deliverable:

- [NDLM_PARITY_AUDIT_PHASE1_INVENTORY_20260420.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/NDLM_PARITY_AUDIT_PHASE1_INVENTORY_20260420.md)

Purpose:

- identify the current source-of-truth codepaths, configs, manifests, runtime outputs, and theory docs
- separate current unified NDLM code from older legacy NDLM scripts
- identify manuscript/export provenance surfaces that must be reconciled later

### Phase 2. Label-to-family verification

Deliverables:

- [label_mapping_check.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/label_mapping_check.csv)
- [PHASE2_LABEL_MAPPING_SUMMARY.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/PHASE2_LABEL_MAPPING_SUMMARY.md)

Purpose:

- verify that `N-U-T1`, `N-M-T0`, and `N-M-T1` resolve to the intended unified families
- confirm whether the manuscript tables currently rely on baseline TT runs, NDLM relaunch runs, or some mixture

Phase 2 status:

- complete
- current manuscript HE2 NDLM rows align with the final featurecov summary, not the older packaged best9 export manifest

### Phase 3. Specification parity matrix

Deliverables:

- [spec_parity_matrix.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/spec_parity_matrix.csv)
- [spec_parity_summary.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/spec_parity_summary.md)

Purpose:

- compare NDLM vs DQLM/exDQLM settings for:
  - transfer mode
  - deterministic climate
  - base covariates
  - engineered terms
  - discount factors
  - covariance priors
  - stabilization settings

Phase 3 status:

- complete
- current HE2 comparisons are still mostly anchored in the older `multimodel_v8_20260402` source-run lineage
- the authoritative Phase 3 rows do **not** yet use the newer featurecov transfer-function blocks with lags/interactions or deterministic-climate handoff
- NDLM main differs from the multivariate quantile rows in discount/stabilization fields beyond likelihood alone, so later phases must test whether those differences are intended and fair

### Phase 4. Input parity by cutoff

Deliverables:

- [input_hash_audit.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/input_hash_audit.csv)
- [input_contract_notes.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/input_contract_notes.md)

Purpose:

- verify that the same cutoff uses the same retrospective, forecast, and covariate source files across model classes

Phase 4 status:

- complete
- all `135` cutoff/group/artifact contracts are hash-aligned across the authoritative NDLM and quantile-model rows
- many literal configured paths in the older resolved configs are stale, so later audit phases must use archived run-local inputs as the effective source of truth

### Phase 5. Forecast-window covariance prior audit

Deliverables:

- [wishart_prior_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/wishart_prior_audit.md)
- [wishart_runtime_trace.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/wishart_runtime_trace.csv)

Purpose:

- trace forecast-window covariance prior fields from config into NDLM main code and saved diagnostics

Phase 5 status:

- complete
- the original audit showed that all authoritative HE2 multivariate NDLM rows use the `theory_aligned` NDLM main engine with `anchor_mode=terminal_Q_hist`
- the active forecast prior is IW-like and anchored to terminal historical `Q_T`
- `epsilon0` falls back to `T` in all audited HE2 rows because config-level `epsilon` is blank
- the original discrepancy was that `dof_offset` and `scale_mult` were forwarded through `stage_fit` but not used in the active theory-aligned anchor builder
- that discrepancy has now been remediated for the corrected rerun path; see [ndlm_contract_remediation_report.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/ndlm_contract_remediation_report.md)

### Phase 6. Transfer/blend audit

Deliverables:

- [covariate_contract_audit.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/covariate_contract_audit.csv)
- [blend_contract_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/blend_contract_audit.md)

Purpose:

- verify parity of blended precipitation / soil forecast covariates, lags, interactions, and transfer-function activation

Phase 6 status:

- complete
- all `45` authoritative HE2 rows remain on the older five-covariate contract (`ELI`, `ONI`, `PPT`, `SOIL`, `PCA`)
- all `45` intended all-9 featurecov reference configs instead use the reduced `PPT`, `SOIL`, `PCA` base inputs plus `inputs.covariate_features` and deterministic-climate blending
- `0 / 45` authoritative rows carry runtime `covariate_features.csv`, and `0 / 45` carry runtime deterministic-climate summaries
- transfer-mode and `use_covariates` semantics still match, so the key discrepancy in this phase is the broader covariate / forecast-blend contract rather than mislabeled `keep/drop`
- the generated all-9 featurecov configs express that contract through reduced fit covariates plus `inputs.covariate_features` and `inputs.deterministic_climate`; they do not need a separate `transfer_function_covariates` key to enforce it

### Phase 7. Corrective rerun specification freeze

Rescoped deliverables:

- `ndlm_rerun_spec_freeze.md`
- `ndlm_rerun_acceptance_gates.md`

Purpose:

- freeze the corrected NDLM rerun contract before any relaunch
- decide which NDLM-specific settings remain intentional versus which must be harmonized or patched for fairness

Phase 7 status:

- complete
- frozen in [ndlm_rerun_spec_freeze.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/ndlm_rerun_spec_freeze.md)
- the earlier audit phases showed that the manuscript-facing NDLM rows were not on the intended featurecov/blended-forecast contract
- the corrected rerun contract now fixes that by freezing:
  - the `15`-row NDLM scope
  - the reduced `PPT/SOIL/PCA` base covariates
  - engineered feature generation
  - deterministic-climate blending
  - one consistent NDLM main and NDLM univariate spec across cutoffs

Phase 7 settled:

- corrected rerun scope: `15` NDLM rows (`3` NDLM families x `5` cutoffs)
- corrected input contract: reduced `PPT`, `SOIL`, `PCA` base inputs plus engineered covariate features and deterministic-climate blending
- corrected prior contract: whether `dof_offset` and `scale_mult` are made active or retired from the public surface
- fairness contract: which NDLM damping / state-evolution / stabilization settings remain intentionally family-specific

### Phase 8. Code and contract remediation

Planned deliverables:

- `ndlm_contract_remediation_report.md`
- regression tests for all remediated codepaths

Purpose:

- patch the active code/config gaps identified in earlier phases
- ensure the corrected NDLM rerun can actually realize the intended featurecov contract at runtime

Phase 8 status:

- complete
- remediation summary: [ndlm_contract_remediation_report.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/ndlm_contract_remediation_report.md)

Implemented remediation targets:

- theory-aligned multivariate NDLM prior path now uses `dof_offset` and `scale_mult`
- runtime contract checks now exist through the dedicated prelaunch validator
- corrected builder paths now exist for NDLM featurecov runs

### Phase 9. Automated rerun scaffolding

Planned deliverables:

- `ndlm_rerun_matrix.csv`
- corrected rerun builder / validator / launcher / queue wrapper
- controller/logging notes for the rerun campaign

Purpose:

- make the corrected NDLM rerun automatic instead of manual
- keep the rerun reproducible, documented, and easy to audit later

Phase 9 status:

- complete
- current surfaces:
  - [build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py)
  - [validate_ndlm_featurecov_rerun_prelaunch.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/validate_ndlm_featurecov_rerun_prelaunch.py)
  - [launch_multimodel_v8_ndlm_featurecov_rerun.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/launch_multimodel_v8_ndlm_featurecov_rerun.py)
  - [run_multimodel_v8_ndlm_featurecov_rerun.sh](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_multimodel_v8_ndlm_featurecov_rerun.sh)
  - [NDLM_FEATURECOV_RERUN_WORKFLOW.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/NDLM_FEATURECOV_RERUN_WORKFLOW.md)

### Phase 10. Pilot rerun gate

Planned deliverables:

- no separate pilot report; this stage was superseded by the strengthened family-level prelaunch validation bundle

Purpose:

- validate promotion readiness before the full rerun

Current status:

- waived as a separate six-row campaign
- replaced by a stronger prelaunch gate consisting of:
  - Python regression tests
  - R regression tests
  - `data_prep_shared` smoke runs for all three NDLM families
- evidence:
  - [prelaunch_validation_summary.json](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/prelaunch_validation_20260421T045415Z/prelaunch_validation_summary.json)

### Phase 11. Full NDLM rerun

Planned deliverables:

- corrected NDLM rerun outputs for all `15` target rows
- rerun matrix status and queue/controller logs

Purpose:

- relaunch the full NDLM manuscript family set across all cutoffs under the corrected shared contract

Current status:

- complete
- the first launch attempt surfaced one additional builder-side USGS cache-path bug, which was fixed in the rerun builder and validator
- the next launch attempt surfaced an NDLM-only post-stage contract leak, which was fixed in `stage_post.R`
- the corrected rerun then completed cleanly:
  - `15 / 15` target rows passed
  - `0` failed
  - controller completed with `exit_code=0`
- final evidence:
  - [matrix_status.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/matrix_status.csv)
  - [queue.log](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/queue.log)

### Phase 12. Final discrepancy report

Planned deliverables:

- `ndlm_final_audit_summary.md`

Decision outcomes:

- `A`: NDLM is correctly wired and the performance gap is a genuine modeling result
- `B`: NDLM is mostly correct, but non-likelihood discrepancies materially affect fairness
- `C`: NDLM is materially mismatched and the current comparison should not be trusted until fixed

Current status:

- complete
- final synthesis written in:
  - [ndlm_final_audit_summary.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/ndlm_final_audit_summary.md)
- outcome for the original manuscript-facing NDLM rows:
  - they should be retired, because they came from the older pre-featurecov contract
- outcome for the corrected rerun:
  - it resolves the major fairness defects and now provides the manuscript-facing NDLM CRPS values to use in HE2

## Corrected Rerun Checklist

### Specification freeze

- [x] confirm the corrected rerun scope is the `15`-row NDLM matrix
- [x] write the authoritative corrected NDLM contract
- [x] define the final acceptance gates for a launchable corrected NDLM row

### Remediation

- [x] patch NDLM prior-path gaps
- [x] add regression tests for the remediated contract
- [x] prove the corrected configs use reduced `PPT/SOIL/PCA` fit covariates
- [x] prove the corrected rows generate engineered feature matrices
- [x] prove the corrected rows generate deterministic-climate blended forecast artifacts

### Automation

- [x] generate the corrected NDLM rerun matrix automatically
- [x] validate the rerun matrix before launch
- [x] relaunch through an automated queue/controller path

### Pilot and promotion

- [x] replace the separate pilot campaign with the stronger family-level prelaunch smoke gate
- [x] review smoke artifacts and promote the full rerun

### Full rerun and synthesis

- [x] complete the full `15`-row corrected NDLM rerun
- [x] rebuild NDLM manuscript-facing summaries
- [x] compare corrected NDLM results against the current HE2/HE4 values
- [x] decide whether the manuscript tables must be updated

## Reproducible Command Skeleton

Phase 1 inventory commands used:

```bash
rg --files R/unified/families/ndlm_main R/unified/families/ndlm_univar scripts | rg 'ndlm|run_ndlm'
rg --files config /data/muscat_data/jaguir26/project1_ucsc_phd_runtime | rg 'ndlm|featurecov_cf1|selection_manifest|contract|theory|best9'
rg -n "N-U-T1|N-M-T0|N-M-T1|ndlm_main_keep|ndlm_main_drop|ndlm_univar_keep|Normal Dynamic Linear Model|Wishart|wishart|theory_aligned|theory contract" /data/muscat_data/jaguir26/project1_ucsc_phd /data/muscat_data/jaguir26/project1_ucsc_phd_runtime /data/muscat_data/jaguir26/Corrections---Project-1 -g '!**/.git/**'
find /data/muscat_data/jaguir26 -maxdepth 3 \( -iname '*ndlm*' -o -iname '*wishart*' -o -iname '*theory*' \) | sort
```

## Primary Working Files

- Tracker: [TRACKER_NDLM_PARITY_AUDIT.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/TRACKER_NDLM_PARITY_AUDIT.md)
- Phase 1 inventory: [NDLM_PARITY_AUDIT_PHASE1_INVENTORY_20260420.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/NDLM_PARITY_AUDIT_PHASE1_INVENTORY_20260420.md)
- Rerun workflow: [NDLM_FEATURECOV_RERUN_WORKFLOW.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/NDLM_FEATURECOV_RERUN_WORKFLOW.md)

## Guardrails

- Do not assume manuscript labels are correctly mapped until Phase 2 completes.
- Do not treat runtime CRPS differences as model-quality evidence until provenance and parity checks complete.
- Treat legacy NDLM scripts as historical references unless a current unified config still points into them.
- Preserve a clean distinction between:
  - current unified NDLM family code
  - older baseline-TT export runs
  - dedicated NDLM relaunch runs

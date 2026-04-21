# NDLM Parity Audit Tracker

Last updated: 2026-04-20
Owner: Codex + jaguir26
Status: Audit Phases 1-6 complete; corrective rerun plan staged

## Purpose

Audit the Normal-likelihood models used in the manuscript tables to determine whether:

- `N-U-T1`, `N-M-T0`, and `N-M-T1` are mapped to the intended unified model families
- the NDLM models use the same inputs, covariates, transfer-function specification, and forecast products as the quantile models wherever they are supposed to
- the multivariate NDLM forecast-window covariance prior is implemented as intended
- the main structural difference between NDLM and its quantile-model counterparts is the likelihood, or whether other discrepancies materially affect fairness

## Target Models

- `N-U-T1` expected to map to `ndlm_univar_keep`
- `N-M-T0` expected to map to `ndlm_main_drop`
- `N-M-T1` expected to map to `ndlm_main_keep`

These mappings will be formally verified during the audit and should not be treated as final until Phase 2 is complete.

## Audit Questions

1. What are the current source-of-truth configs, codepaths, runtime artifacts, and documentation for the NDLM models?
2. Do the NDLM table labels resolve to the intended unified model families and compare/export artifacts?
3. Are the per-cutoff inputs identical across NDLM and the corresponding quantile-model families?
4. Are transfer-function covariates, lags, interactions, and deterministic-climate blends aligned across model classes?
5. Is the multivariate NDLM using the intended forecast-window covariance prior and hyperparameter contract?
6. After holding all non-likelihood pieces fixed, is the main difference truly the likelihood?

## Planned Phases

### Phase 1. Inventory and provenance

Deliverables:

- `ndlm_audit_inventory.md`
- source-of-truth path list for code, configs, runtime artifacts, and documentation

### Phase 2. Label-to-family verification

Deliverables:

- `label_mapping_check.csv`
- notes on any export/manuscript labeling discrepancies

### Phase 3. Spec parity matrix

Deliverables:

- `spec_parity_matrix.csv`
- structured comparison of NDLM vs exDQLM/DQLM counterparts

### Phase 4. Input parity by cutoff

Deliverables:

- `input_hash_audit.csv`
- file-level parity check for retrospectives, forecasts, and covariates

### Phase 5. Forecast-window prior audit

Deliverables:

- `wishart_prior_audit.md`
- runtime trace of prior parameters from config to model code

### Phase 6. Transfer/blend audit

Deliverables:

- `covariate_contract_audit.csv`
- alignment check for base covariates, engineered terms, and blend rules

### Phase 7. Corrective rerun specification freeze

Deliverables:

- `ndlm_rerun_spec_freeze.md`
- explicit acceptance gates for the corrected NDLM rerun contract

### Phase 8. Code and contract remediation

Deliverables:

- `ndlm_contract_remediation_report.md`
- patched NDLM code/config paths with regression coverage

### Phase 9. Automated rerun scaffolding

Deliverables:

- `ndlm_rerun_matrix.csv`
- automated builder / validator / launcher / queue wrapper for the corrected NDLM campaign

### Phase 10. Pilot rerun gate

Deliverables:

- no separate pilot report; this stage was superseded by the strengthened family-level prelaunch validation bundle

### Phase 11. Full NDLM rerun

Deliverables:

- corrected NDLM rerun outputs for all `15` target rows (`3` NDLM families x `5` cutoffs)
- rerun matrix status and controller logs

### Phase 12. Final discrepancy report and manuscript update guidance

Deliverables:

- `ndlm_final_audit_summary.md`
- decision outcome: correctly wired vs materially mismatched

## Current Status

| Phase | Status | Notes |
| --- | --- | --- |
| Phase 1 | complete | Inventory and provenance report written; see `NDLM_PARITY_AUDIT_PHASE1_INVENTORY_20260420.md` |
| Phase 2 | complete | Label/provenance mapping built and validated; see `reports/ndlm_parity_audit/label_mapping_check.csv` |
| Phase 3 | complete | Spec parity matrix built and validated; see `reports/ndlm_parity_audit/spec_parity_matrix.csv` |
| Phase 4 | complete | Input hash audit built and validated; see `reports/ndlm_parity_audit/input_hash_audit.csv` |
| Phase 5 | complete | Wishart/IW prior-path audit written; see `reports/ndlm_parity_audit/wishart_prior_audit.md` |
| Phase 6 | complete | Covariate / transfer / blend audit built and validated; see `reports/ndlm_parity_audit/covariate_contract_audit.csv` |
| Phase 7 | complete | Frozen corrected rerun contract; see `reports/ndlm_parity_audit/ndlm_rerun_spec_freeze.md` |
| Phase 8 | complete | Prior-path and scaffolding remediation implemented; see `reports/ndlm_parity_audit/ndlm_contract_remediation_report.md` |
| Phase 9 | complete | Builder / validator / launcher / wrapper implemented for the corrected NDLM campaign |
| Phase 10 | waived | Replaced by a stronger prelaunch gate with regression tests plus three family-level smoke runs |
| Phase 11 | complete | Corrected NDLM rerun finished cleanly: `15 / 15` target rows passed, `0` failed, controller exited with `exit_code=0` |
| Phase 12 | complete | Final synthesis written; corrected manuscript-facing NDLM values documented in `reports/ndlm_parity_audit/ndlm_final_audit_summary.md` |

## Final Outcome

- The original manuscript-facing NDLM rows were not a clean shared-contract comparison and should no longer be treated as such.
- The corrected rerun is now complete for all `15` target rows (`3` NDLM families x `5` cutoffs).
- The rerun used the intended shared featurecov / blended-forecast contract:
  - reduced base covariates `PPT`, `SOIL`, `PCA`
  - engineered `covariate_features.csv`
  - deterministic-climate blending
  - active multivariate NDLM prior knobs `dof_offset` and `scale_mult`
- The corrected manuscript-facing NDLM CRPS values are now the rerun outputs summarized in:
  - [ndlm_final_audit_summary.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/ndlm_final_audit_summary.md)
  - [matrix_status.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/matrix_status.csv)
  - [queue.log](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/queue.log)

## Expected Audit Artifacts

Recommended persistent outputs:

- `repro/run/NDLM_PARITY_AUDIT_WORKFLOW.md`
- `repro/NDLM_PARITY_AUDIT_PHASE1_INVENTORY_20260420.md`
- `reports/ndlm_parity_audit/label_mapping_check.csv`
- `reports/ndlm_parity_audit/PHASE2_LABEL_MAPPING_SUMMARY.md`
- `reports/ndlm_parity_audit/spec_parity_matrix.csv`
- `reports/ndlm_parity_audit/spec_parity_summary.md`
- `reports/ndlm_parity_audit/input_hash_audit.csv`
- `reports/ndlm_parity_audit/input_contract_notes.md`
- `reports/ndlm_parity_audit/wishart_runtime_trace.csv`
- `reports/ndlm_parity_audit/wishart_prior_audit.md`
- `reports/ndlm_parity_audit/covariate_contract_audit.csv`
- `reports/ndlm_parity_audit/blend_contract_audit.md`
- `reports/ndlm_parity_audit/ndlm_rerun_spec_freeze.md`
- `reports/ndlm_parity_audit/ndlm_rerun_acceptance_gates.md`
- `reports/ndlm_parity_audit/ndlm_contract_remediation_report.md`
- `reports/ndlm_parity_audit/ndlm_rerun_launch_summary.md`
- `reports/ndlm_parity_audit/ndlm_final_audit_summary.md`
- `repro/run/NDLM_FEATURECOV_RERUN_WORKFLOW.md`

## Phase 1 Working Notes

- Completed.
- Main outputs:
  - [NDLM_PARITY_AUDIT_WORKFLOW.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/NDLM_PARITY_AUDIT_WORKFLOW.md)
  - [NDLM_PARITY_AUDIT_PHASE1_INVENTORY_20260420.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/NDLM_PARITY_AUDIT_PHASE1_INVENTORY_20260420.md)
- Key provenance fact identified:
  - the current best9 export manifest packages NDLM rows from `multimodel_v8_20260402` baseline-TT runs
  - a separate dedicated NDLM relaunch runtime exists under `multimodel_v8_ndlm_20260411`
  - reconciling these two lineages is a required next step before any fairness or CRPS interpretation

## Phase 3 Working Notes

- Completed.
- Main outputs:
  - [spec_parity_matrix.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/spec_parity_matrix.csv)
  - [spec_parity_summary.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/spec_parity_summary.md)
- Key findings:
  - `44 / 45` authoritative HE2 comparison rows still resolve to the older `multimodel_v8_20260402` source-run tree.
  - Deterministic climate is disabled in all authoritative Phase 3 rows.
  - All Phase 3 rows use the same fit-covariate list: `ELI`, `ONI`, `PPT`, `SOIL`, `PCA`.
  - None of the authoritative current HE2 source configs expose the newer featurecov transfer-function blocks with lags and interactions.
  - NDLM main rows differ systematically from the multivariate quantile rows in `df_covs`, fit damping (`lam1`, `lam2`), and prior/stabilization fields.
  - Only one current HE2 cell (`N-M-T1` at cutoff `20210123`) comes from the dedicated `ndlm_relaunch_20260411` lineage.

## Phase 4 Working Notes

- Completed.
- Main outputs:
  - [input_hash_audit.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/input_hash_audit.csv)
  - [input_contract_notes.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/input_contract_notes.md)
- Key findings:
  - Effective archived inputs are fully hash-aligned across all NDLM and quantile-model rows within each cutoff/comparison group (`135 / 135` contracts).
  - Literal configured paths are often stale (`176` missing configured-path references), but the archived run-local snapshots exist for all `405` audited artifacts.
  - The single relaunch-backed NDLM keep row uses copied run-local snapshots, and those hashes match the baseline-TT counterparts for the same cutoff/group.
- Input content is therefore not the main source of the NDLM performance gap in the current HE2 table.

## Phase 5 Working Notes

- Completed.
- Main outputs:
  - [wishart_runtime_trace.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/wishart_runtime_trace.csv)
  - [wishart_prior_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/wishart_prior_audit.md)
- Key findings:
  - All `10` authoritative HE2 multivariate NDLM rows already use the `theory_aligned` NDLM main engine with `kalman_backend=cpp`.
  - All `10` rows use the runtime forecast prior anchor mode `terminal_Q_hist`.
  - The active anchor builder implements an IW-like terminal-historical anchor with `nu0 = d_k + 1 + epsilon0` and `S0 = epsilon0 * c_factor * W_T_k + diag(jitter)`.
  - Because the authoritative HE2 NDLM main configs leave `epsilon` blank, runtime `epsilon0` falls back to `T` for all `10` rows.
  - `dof_offset` and `scale_mult` are exposed by the config surface and forwarded through `stage_fit`, but they are not used in the active theory-aligned fit path.
  - This means the NDLM forecast-window prior contract is only partially implemented relative to the public config surface.

## Phase 6 Working Notes

- Completed.
- Main outputs:
  - [covariate_contract_audit.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/covariate_contract_audit.csv)
  - [blend_contract_audit.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/blend_contract_audit.md)
- Key findings:
  - All `45 / 45` authoritative HE2 rows are still on the older five-covariate contract: `ELI`, `ONI`, `PPT`, `SOIL`, `PCA`.
  - All `45 / 45` intended all-9 featurecov reference configs use the reduced `PPT`, `SOIL`, `PCA` base covariates plus `inputs.covariate_features` and deterministic-climate blending.
  - `0 / 45` authoritative rows carry `covariate_features.csv`, and `0 / 45` carry `deterministic_climate_summary.txt`.
  - Transfer-mode semantics and `use_covariates` semantics still align (`45 / 45`), so the Phase 6 discrepancy is not mislabeled `keep/drop`.
  - The manuscript-facing NDLM rows are therefore coherent within the older regime, but not yet comparable under the newer shared featurecov/blended-forecast contract.

## Decision After Phase 6

- We now have enough evidence to justify a corrected NDLM rerun.
- The current manuscript-facing NDLM rows are not invalid because of bad data files, but they are not a clean likelihood-only comparison under the intended article specification.
- The corrective target is a rerun of all NDLM manuscript families under the shared all-9 featurecov contract:
  - `ndlm_univar_keep`
  - `ndlm_main_drop`
  - `ndlm_main_keep`
- The minimum corrected campaign is therefore `15` rows: `3` NDLM families x `5` cutoffs.
- We should not launch that rerun until the NDLM contract is frozen, the active prior-gap issues are patched or explicitly retired, and runtime contract checks prove the rerun rows really carry:
  - reduced `PPT/SOIL/PCA` fit covariates
  - `covariate_features.csv`
  - deterministic-climate blended forecast artifacts

## Phase 7-9 Working Notes

- Completed.
- Main outputs:
  - [ndlm_rerun_spec_freeze.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/ndlm_rerun_spec_freeze.md)
  - [ndlm_rerun_acceptance_gates.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/ndlm_rerun_acceptance_gates.md)
  - [ndlm_contract_remediation_report.md](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/ndlm_contract_remediation_report.md)
  - [NDLM_FEATURECOV_RERUN_WORKFLOW.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/NDLM_FEATURECOV_RERUN_WORKFLOW.md)
- Key results:
  - `dof_offset` and `scale_mult` are now active in the theory-aligned NDLM main prior path and are preserved in diagnostics/state outputs.
  - The corrected rerun builder now rewrites the fit covariate base set to `PPT`, `SOIL`, `PCA` and always enables engineered features plus deterministic-climate blending.
  - The dedicated prelaunch validator passed:
    - `15 / 15` configs generated
    - Python regression tests passed
    - R regression tests passed
    - `3 / 3` NDLM family smoke runs produced both `covariate_features.csv` and deterministic-climate summaries
- Validation evidence:
  - [prelaunch_validation_summary.json](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/prelaunch_validation_20260421T045415Z/prelaunch_validation_summary.json)

## Phase 11 Working Notes

- Completed.
- First launch attempt exposed one additional builder-side issue:
  - blank source `usgs_cache_path` values were being normalized to the repo root, which caused a strict `data_prep_shared` failure on the first `20210123 / ndlm_main_keep` row
- Root fix implemented:
  - blank path handling corrected in [build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_multimodel_v8_ndlm_featurecov_rerun_matrix_configs.py)
  - campaign-level fallback `inputs.fit.usgs_cache_path` frozen in [multimodel_v8_ndlm_featurecov_rerun.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_ndlm_featurecov_rerun.template.yaml)
  - validator tightened so `usgs_cache_path` must be a real file, not just an existing path
- Second launch attempt cleared shared-input prep but surfaced one NDLM-only post-stage issue:
  - `multivar_output_suffix` was not initialized for NDLM-only post runs
  - fixed in [stage_post.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/stages/stage_post.R)
- Both formerly failing `20210123` NDLM-main rows were replayed cleanly and then the full corrected rerun completed:
  - [matrix_status.csv](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/matrix_status.csv)
  - [queue.log](/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_ndlm_featurecov_rerun_20260420/control/ndlm_featurecov_v1/queue.log)
- Final Phase 11 result:
  - `15 / 15` target rows passed
  - `0` failed
  - controller completed with `exit_code=0`

## Archived Forward Plan

### Phase 7. Corrective rerun specification freeze

Goal:

- define one authoritative corrected NDLM rerun contract that matches the intended all-9 featurecov design as closely as possible

Must answer:

- which NDLM settings should stay family-specific and which must be harmonized for fairness?
- do we keep current NDLM damping / state-evolution settings, or partially harmonize them with the quantile multivariate families?
- do we activate `dof_offset` and `scale_mult`, or remove them from the public contract if they are not scientifically intended?

Required deliverables:

- written rerun contract
- acceptance gates for launch readiness
- explicit list of fields that are intentionally likelihood-specific versus unintentionally divergent

### Phase 8. Code and contract remediation

Goal:

- patch any active mismatches between the intended NDLM contract and the current implementation

Expected remediation targets:

- multivariate NDLM prior path (`dof_offset`, `scale_mult`)
- runtime contract checks for featurecov artifacts
- any config-builder gaps preventing NDLM from using the same blended forecast / engineered-feature regime as the other families

### Phase 9. Automated rerun scaffolding

Goal:

- make the corrected NDLM rerun launchable end to end without ad hoc manual edits

Expected tooling:

- corrected NDLM rerun matrix builder
- prelaunch validator
- launcher / queue wrapper
- summary / audit hooks so the rerun is reproducible and easy to inspect

### Phase 10. Pilot rerun gate

Goal:

- prove the corrected contract works before launching all `15` NDLM rows

Recommended pilot:

- easy cutoff: `20211112`
- hard cutoff: `20221225`
- all `3` NDLM families on both cutoffs

Launch gate:

- do not promote to the full rerun unless all pilot rows pass and runtime artifacts confirm the corrected featurecov contract

### Phase 11. Full NDLM rerun

Goal:

- relaunch the full corrected NDLM matrix across all `5` cutoffs and `3` NDLM families

Target matrix:

- `ndlm_univar_keep`
- `ndlm_main_drop`
- `ndlm_main_keep`
- cutoffs: `20210123`, `20211112`, `20211221`, `20220511`, `20221225`

### Phase 12. Final synthesis

Goal:

- compare corrected NDLM results against the current manuscript values and decide whether the HE2/HE4 tables must be updated
- state clearly whether the remaining gap is then plausibly attributable to likelihood, or whether deeper structural differences still matter

## Immediate Next Step

- Keep the manuscript NDLM rows synchronized to the corrected rerun outputs.
- Retain the archived run-local inputs and rerun artifacts as the source of truth for any future reviewer follow-up.

## Working Checklist

### 1. Specification Freeze

- [x] Confirm the corrected rerun target is the `15`-row NDLM matrix across all `5` cutoffs
- [x] Write the authoritative corrected NDLM contract against the all-9 featurecov specification
- [x] Decide which NDLM hyperparameters remain intentionally family-specific
- [x] Decide whether `dof_offset` and `scale_mult` must be made active or removed from the public contract
- [x] Define exact runtime acceptance criteria for a launchable corrected NDLM row

### 2. Code / Contract Remediation

- [x] Patch active NDLM prior-path gaps in the theory-aligned multivariate engine
- [x] Verify the corrected NDLM configs consume reduced `PPT/SOIL/PCA` fit covariates
- [x] Verify engineered feature generation is active
- [x] Verify deterministic-climate blending is active
- [x] Add regression tests for all new codepaths and contract assumptions

### 3. Automated Rerun Tooling

- [x] Build corrected NDLM rerun config generator
- [x] Build corrected NDLM prelaunch validator
- [x] Build corrected NDLM launcher / queue wrapper
- [x] Build rerun audit hooks so runtime artifacts are automatically checked
- [x] Document the rerun workflow end to end

### 4. Pilot Gate

- [x] Replace the separate pilot campaign with stronger family-level prelaunch smoke gates
- [x] Confirm all three NDLM families pass `data_prep_shared` + `fit` + `post` smoke runs
- [x] Confirm runtime featurecov artifacts exist for all smoke rows
- [x] Promote the matrix after strengthened validation passes

### 5. Full Corrected NDLM Rerun

- [x] Launch all remaining corrected NDLM rows automatically
- [x] Monitor queue health and runtime artifacts
- [x] Build corrected NDLM summaries for manuscript-facing metrics
- [x] Compare corrected CRPS values against the current manuscript values
- [x] Prepare final recommendation on whether manuscript tables must be updated

## Resolved Concerns

- The poor NDLM rows in the original manuscript table were not caused by bad archived inputs or label mismatch.
- The main fairness problem was the older pre-featurecov contract plus the inactive multivariate prior knobs.
- The multivariate NDLM forecast-window prior path now matches the corrected public rerun contract.
- The corrected rerun is complete and supplies the manuscript-facing NDLM CRPS values under the intended shared featurecov/blended-input contract.

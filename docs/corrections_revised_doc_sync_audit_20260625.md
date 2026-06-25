# Corrections/Revised-Article Sync Audit

Date: 2026-06-25

## Purpose

This audit records the current synchronization state between:

- workflow/code repo: `/data/muscat_data/jaguir26/project1_ucsc_phd`
- revised article repo: `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2`
- corrections response repo: `/data/muscat_data/jaguir26/Corrections---Project-1`

The goal is to make the revised article and corrections response reviewable item-by-item without losing the provenance contract that connects manuscript claims, generated tables, figures, and workflow validation evidence.

## Tracker Status

The corrections tracker contains 22 items:

| Status | Count | Interpretation |
|---|---:|---|
| `done` | 21 | Implemented in the corrections response and cross-checked against the revised article/workflow contract. |
| `done_pending_final_archive_doi` | 1 | HE-5 software availability is implemented, except for the final permanent workflow archive DOI, which must not be claimed until the final archive is created. |

The pending item is intentional. The current contract states that CRAN `exdqlm` and the public workflow repository are available, while the permanent workflow archive DOI remains a final-release step.

## Main Audit Finding

The overall corrections/revised-article wiring is coherent after this pass. The only inconsistency found was stale provenance wording for three selected-model interpretation figures:

- `fig:dry_quantile`
- `fig:rainy_quantile`
- `fig:80_components`

The revised article tests already required these figures to be wired to the current representative selected-model authority, but the workflow publication-freeze validator and several prose provenance notes still described them as pending a clean replay. This audit resolves that mismatch.

Current contract:

- `fig:synth1`, `fig:dry_quantile`, `fig:rainy_quantile`, and `fig:80_components` are all wired to the current representative `2022-12-25 exAL-M-T1` selected-output authority.
- The dry/wet and 80-month figures remain interpretation diagnostics, not forecast-validation evidence.
- The HE2 forecast-validation evidence remains the five-cutoff table/figure family and should not be conflated with the representative selected-model diagnostics.

## Files Updated

Workflow repo:

- `scripts/validate_publication_freeze.py`
  - now requires all selected-model figures to have `current_model_output_wired = true`;
  - now requires `source_class = current_selected_model_representative`;
  - no longer accepts the stale `selected_model_support_pending_clean_replay_refresh` state.
- `docs/current_authority_refresh_runbook.md`
  - now states that selected-model diagnostics must be refreshed when the representative selected model changes;
  - preserves the distinction between interpretation diagnostics and forecast-validation evidence.

Revised article repo:

- `MANUSCRIPT_ASSET_MANIFEST.json`
  - updated `fig:dry_quantile`, `fig:rainy_quantile`, and `fig:80_components` to `source_class = current_selected_model_representative`.
- `artifacts/representative_selected_model_2022_12_25/authoritative_support/README.md`
  - updated the support-bundle contract to say the figures are wired to the same current representative selected-output authority as the synthesis figure.
- `docs/exal_m_t1_artifact_run_map.md`
  - replaced stale pending-replay language with the current representative-authority contract.
- `docs/figure_table_provenance.md`
  - replaced stale pending-replay language in the figure provenance map and resolved-gaps summary.

Corrections repo:

- no source edits were needed in this pass.

## Validation Evidence

Workflow validation:

- `python3 -m py_compile scripts/validate_publication_freeze.py scripts/validate_revision_cross_repo_wiring.py`
- `python3 scripts/validate_revision_cross_repo_wiring.py --check-only --strict`
  - report: `reports/revision_cross_repo_wiring_check_20260625_corrections_doc_audit_after_freeze_fix/`
  - result: 614 checks, 0 failures.
- `python3 scripts/validate_publication_freeze.py`
  - report: `reports/publication_freeze_validation_20260625_corrections_doc_audit_after_freeze_fix/`
  - result: 686 checks, 0 failures.

Revised article validation:

- `python3 -m unittest discover -s tests -v`
  - result: 28 tests, 0 failures.
- `pdflatex`, `bibtex`, `pdflatex`, `pdflatex` on `wileyNJD-APA.tex`
  - result: compiled successfully to `output.pdf`.

Corrections response validation:

- `make`
  - result: clean/no rebuild needed.

## Manual Review Guide

Recommended review order:

1. Read `Corrections---Project-1/tracker_master.csv` and use the 22 IDs as the checklist.
2. In the corrections PDF/source, review HE-1 through HE-7 first because these carry the high-level revision narrative.
3. In the revised article, cross-check the corresponding sections:
   - methodology/formulation changes,
   - forecast-validation design,
   - benchmark CRPS and NWS-horizon tables,
   - selected-model interpretation figures,
   - software/code availability.
4. Then review the Reviewer 1 major/minor items, focusing on whether each corrections response says what was changed and whether the revised article actually contains the change.
5. Treat HE-5 as complete except for the final permanent archive DOI; do not change the wording to imply the final archive exists until it actually does.

## Remaining Watch Items

- The permanent workflow archive DOI remains pending by design.
- The selected-model diagnostic figures are current for the representative selected-output authority, but they are still interpretation diagnostics only.
- The active N-M-T1 broad screen is unrelated to this audit and should continue to be monitored separately.

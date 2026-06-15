# Pending Final Workflow Archive Release Notes

Date: 2026-06-15

## Status

This repository is public and is the study-specific workflow repository for the
revised Santa Cruz River forecasting article. The permanent workflow archive DOI
has not yet been minted. Its status is pending final revision freeze.

Do not cite this file as evidence that a final archived release exists. The
final DOI fields in the manuscript, corrections response, and software
availability manifest must remain `pending` until the archive has actually been
created.

## Intended Final Release Contents

The final workflow release should include:

- source code for model setup, fitting orchestration, post-processing, table
  generation, figure generation, and validators;
- canonical workflow runbooks and reproducibility contracts;
- compact manifests and configuration files required to identify the
  publication-facing assets;
- validation scripts that connect this workflow repository, the revised article
  repository, and the corrections response repository.

## Intentionally Excluded From Git

The workflow release should not add local-only or heavyweight artifacts to git:

- `.RData`, `.rda`, `.rds`, or equivalent runtime state files;
- generated `reports/` payloads unless a compact report is explicitly selected;
- raw forecast archives and basin-specific restricted data products;
- large intermediate support CSVs that are not manuscript-facing tables;
- local environment caches and machine-specific logs.

## Validation Before Minting The Final Archive

Before the final release is archived:

1. confirm the workflow, revised article, and corrections repositories are clean;
2. run the workflow-side publication-freeze validator;
3. run the workflow-side cross-repository wiring validator;
4. run the revised article tests and compile the article;
5. run the corrections response build;
6. confirm the selected software license;
7. create a versioned workflow release tag;
8. archive the release with a permanent service such as Zenodo or OSF;
9. replace all `pending` archive DOI fields with the final DOI;
10. rerun all validators and compiles after the DOI update.

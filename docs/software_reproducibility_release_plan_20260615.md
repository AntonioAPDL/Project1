# Software Reproducibility Release Plan

Date: 2026-06-15

This document summarizes the implementation-side release plan for HE-5. The
full contract lives in:

- `repro/run/REVISION_SOFTWARE_REPRODUCIBILITY_CONTRACT_20260615.md`

## Decision

Use a layered reproducibility contract:

1. CRAN `exdqlm` is the public reusable estimation package.
2. GitHub `AntonioAPDL/Project1` is the public study-specific workflow.
3. The revised article repository is the publication freeze of figures, tables,
   generated TeX fragments, and compact provenance manifests.
4. A permanent workflow archive DOI will be minted after final revision freeze,
   not during active correction drafting.

## Why This Is The Correct Path

- The article repository is intentionally not a full compute environment. It
  carries the manuscript-facing artifacts and compact manifests.
- The workflow repository is the only appropriate place for model orchestration,
  runtime configuration, post-stage generation, and validator logic.
- The old `repro/REPRODUCE_PAPER.md` is a legacy record and should not be used
  as the current reproduction contract.
- The package-level method is already public through CRAN. The workflow-level
  DOI should freeze the final workflow state, not an intermediate patch set.

## Required Implementation State

- Manuscript `Code availability` text names the CRAN package, package DOI, and
  workflow repository.
- Corrections HE-5 response mirrors the manuscript wording.
- Article repo contains:
  `artifacts/software_availability/software_availability_manifest.json`
- Workflow validators check the manifest and prose.
- Validation reports record current commit metadata at validation time.

## Follow-Up After Final Article Freeze

After the final correction pass:

1. Push all three repositories.
2. Run publication freeze and cross-repo wiring validators.
3. Confirm article and corrections compile.
4. Create a workflow release.
5. Archive the workflow release.
6. Replace `pending` DOI fields in the manuscript, corrections response, and
   article-side manifest.
7. Re-run all validators and compiles.

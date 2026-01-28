# Provenance and Recovery Plan

## What happened
- The notebook `Environmetrics_Figures.ipynb` was historically the workflow for producing submitted-paper figures.
- It required manual comment/uncomment patterns and specific execution order.
- Recently the notebook was broadly uncommented and modified to fix errors, which:
  - overwrote figures under `Environmetrics/`,
  - further changed the notebook itself,
  - introduced persistent errors (especially in the Univariate block).
- Therefore the current notebook in this repo is **contaminated** and not guaranteed to reproduce the submitted paper.

## Gold standard
- The authoritative submitted-paper figures are in the manuscript repo:
  `https://github.com/AntonioAPDL/Evironmetrics---BAYESIAN-QUANTILE-BASED-CORRECTION-AND-SYNTHESIS-OF-RIVER-FLOW-FORECASTS`
- Gold figures live in `/DISC/` in that repo.
- We treat those PNGs as the canonical reference for recovery.

## Recovery approach
1) Clone the manuscript repo outside this repo and record a stable gold baseline hash list.
2) Extract the **oldest** version of `Environmetrics_Figures.ipynb` from this repo’s git history
   without overwriting the current file.
3) Provide comparison tooling to measure any current outputs against the gold DISC figures
   by filename and SHA256.

## Next manual step (by user)
- Trial-and-error run the **oldest** notebook version:
  `repro/recovery/Environmetrics_Figures__OLDEST.ipynb`
- After each run, compare outputs with the gold baseline using:
  `repro/compare_to_gold_DISC.py`

## How to validate success
- The comparison report should show:
  - No missing gold files
  - No extra files
  - No hash mismatches
- `repro/gold_DISC_figures.sha256` is the only authoritative baseline.

## After recovery succeeds
- Only then proceed to:
  - cleaning and restructuring,
  - building a headless R script,
  - modularizing the workflow,
  - addressing reviewer revisions.

## Final decision (current canonical)
- Canonical notebook: `repro/recovery/Environmetrics_Figures__OLDEST.ipynb`
- Canonical output folder: `Environmetrics_reproduce/`
- Visual match to submitted-paper figures confirmed manually.
- We will not chase hash mismatches with the manuscript /DISC/ folder.
- All future script extraction should target `Environmetrics_reproduce/`.

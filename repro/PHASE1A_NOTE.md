# Phase 1.A Note - Environmetrics_Figures.ipynb

## How to run (current recommended path)
1) Open `Environmetrics_Figures.ipynb` with an R kernel.
2) Set the top config cell:
   - `SKIP_UNIVARIATE <- TRUE` for faster runs (paper figures only).
   - `SKIP_UNIVARIATE <- FALSE` to include univariate analysis.
3) Run All.

Observed runtime:
- `SKIP_UNIVARIATE <- TRUE`: ~55 minutes on this server.
- `SKIP_UNIVARIATE <- FALSE`: ~100 minutes on this server.

## Univariate block changes (robust fixes)
- Added `standardize()` utility and `site_code` to the config.
- Added `initial_delta_uni` aligned to `OptimalModelSLexAL.r`.
- Univariate section was moved to the end of the notebook so all dependencies are defined before it runs.
- The univariate covariate diagnostic now uses the same `X_f` as the full model (no overriding of covariate dimensions).

## Skip behavior
- The block between `## START Univariate Aalyses` and `## END Univariate Aalyses` is guarded by `if (!SKIP_UNIVARIATE) { ... }`.
- Additional univariate-dependent cells later in the notebook are also guarded, so "Run All" succeeds with `SKIP_UNIVARIATE <- TRUE`.

## Known warnings (non-fatal)
- Several `mbcsToSbcs` warnings due to Unicode en-dashes in plot titles.
- Plot warnings like "plot type 'line' will be truncated to first character."

No refactors beyond Phase 1.A were made.

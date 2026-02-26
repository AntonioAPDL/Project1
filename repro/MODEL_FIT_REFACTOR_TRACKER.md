# Model-Fit Refactor & Optimization Tracker (living doc)
Project: `/data/muscat_data/jaguir26/project1_ucsc_phd`  
Scope: the *model-fitting* pipeline (DISC/exAL) and its C++ dependencies  
Primary objective: make the fit pipeline reproducible, modular, documented, and optimizable **without changing behavior/outputs**.  
Last updated: 2026-02-25

---

## 0) Big picture: how the repo is wired today

**Fitting (model outputs)**  
- Primary fitting entrypoint (current): `DISC_Optimal_Synth_Ranges_W.r` (exAL + synthesis + discrepancy).  
- Related fitting scripts:
  - `DISC_Optimal_Synth_Ranges_NDLM.r` (NDLM baseline).
  - `DISC_Optimal_Synth_Ranges.r` (non-weighted / older variant).
- Typical execution pattern: called once per quantile `p0` (e.g., 0.05/0.20/…/0.95), often in parallel via tmux wrappers (e.g., `run_scripts_synth_DISC_W.py`).

**Post-processing (paper figures)**  
- Post-processing (current modularized pipeline): `R/environmetrics/*` executed by `scripts/run_environmetrics_figures.R`.  
- The post-processing modules assume the model `.RData` outputs exist and are consistent with the expected object names.

**Goal**: refactor the *fit* pipeline to the same quality level as `R/environmetrics/`, while keeping compatibility with post-processing.

---

## 1) Canonical behavior (non-negotiable invariants)

### 1.1 Outputs and filenames
- For exAL runs, the fitting script currently writes:
  - `DISC_variables_<XX>_exAL_synth_DISC.RData` under the project root,
    where `<XX>` is `sprintf("%.0f", p0 * 100)` and `ending <- "_exAL_synth_DISC"`.
- The file contains many objects whose names are **part of the contract** (post-processing expects them by name).

### 1.2 Determinism and RNG
- **No semantic changes.** Any refactor/optimization must preserve:
  - object values
  - save/load behavior (same names, same shapes)
  - RNG behavior (same `set.seed()` placement; avoid adding/removing RNG draws)
  - floating-point accumulation order **unless proven safe**.

### 1.3 “Warm start” behavior (`USE_PREV`)
- `DISC_Optimal_Synth_Ranges_W.r` uses `USE_PREV <- TRUE` and, depending on `p0`,
  loads the corresponding `DISC_variables_*_exAL_synth_DISC.RData` to initialize the run:
  - this is a behavior dependency that must be preserved or explicitly redesigned (with a flag and documented).

---

## 2) Fit pipeline inventory (DISC_Optimal_Synth_Ranges_W.r)

### 2.1 External inputs (current)
The script currently reads inputs from:

**Outside this repo (absolute paths):**
- `.../projects/Project/Input/exAL/covariates/cov_1_ELI.csv`
- `.../projects/Project/Input/exAL/covariates/cov_2_ONI.csv`

**Inside this repo (absolute paths but local):**
- `nws_forecast.csv`
- `weighted_time_series.csv`
- `prism_precipitation_santa_cruz_1987_2023.csv`
- `soil_moisture_data/soil_moisture_big_trees_daily_avg_1987_2023.csv`
- `pca.csv`

**Network / API:**
- USGS NWIS daily flow via `dataRetrieval::readNWISdv(...)`

### 2.2 C++ compilation and dependencies
The script sets compiler/linker environment variables and compiles C++ at runtime:
- env vars:
  - `PKG_CXXFLAGS` includes Eigen/Boost include paths + `-DEIGEN_DONT_VECTORIZE`
  - `PKG_LIBS` links Lapack/Blas/Boost + `-fopenmp`
  - `LD_LIBRARY_PATH` points at local libs
- runtime compilation (per run):
  - `sampling_exal.cpp`
  - `sampling_truncnorm.cpp`
  - `DISC_kalman_synth.cpp`

### 2.3 Major conceptual blocks (what exists, roughly)
This script contains:
- heavy helper/utility function definitions (some duplicates exist)
- data ingest + preprocessing (USGS + covariates + forecast matrices)
- model setup (trend + seasonal + covariate extensions)
- iterative fitting loop (VB-like) with many update functions:
  - `update_sts`, `update_uts`, `update_gamma_sigma`, etc.
- sampling / retrospective + forecast generation:
  - `DISC_generate_synth_samples_retro_part(...)` (C++)
  - GIG + truncnorm sampling (C++)
- output packaging:
  - heavy use of `assign()` to create many variables by name
  - `save_variables()` uses `eval(parse(text = ...))` to call `save(...)`
- diagnostics:
  - KL/JSD computations (KDE-based; potentially expensive)

---

## 3) Risk register (things that can silently break reproducibility)

### 3.1 OpenMP + RNG concerns (C++)
Some C++ code uses OpenMP parallel loops and/or seeds threads from R RNG:
- Determinism may depend on:
  - fixed thread count
  - static scheduling
  - avoiding `R::runif()` inside parallel regions

**Action (planning)**:
- Define a “repro mode” (default) that pins `OMP_NUM_THREADS=1` (or a fixed count) and documents it.
- Only introduce “fast mode” after equivalence is proven and validated.

### 3.2 Runtime compilation variability
`sourceCpp()` + local toolchain can introduce variability across machines.

**Action (planning)**:
- Move C++ into a package-style structure or prebuilt shared library; load deterministically.
- Record exact compile flags and library paths in a single place.

### 3.3 Dynamic save/assign
`assign()` + `eval(parse(...save(...)))` is fragile and makes it hard to reason about what is saved.

**Action (planning)**:
- Replace with deterministic, explicit saving from a dedicated environment (keeps object names identical).

### 3.4 External absolute paths + network calls
Hard-coded absolute paths and network downloads block portability.

**Action (planning)**:
- Adopt repo-local “inputs root” (e.g., `data_raw/`) + bootstrap scripts.
- Cache USGS data locally and optionally disable network use via a flag.

---

## 4) Hotspots and likely bottlenecks (where to profile first)

### 4.1 One-time overhead per run
- `sourceCpp()` compile time (dominant if repeated per p0)
- `readNWISdv()` network IO + parsing

### 4.2 Iterative fit loop (dominant compute)
The `while (FLAG & iter < max_iter)` loop is the expected main CPU consumer, especially:
- repeated linear algebra (Cholesky/inversions)
- repeated creation of large block-diagonal matrices
- repeated allocation of arrays/lists

### 4.3 Sampling / post-fit simulation
- GIG + truncnorm sampling (C++), retrospective + forecast generation (C++).

### 4.4 Diagnostics (often optional, sometimes expensive)
- KDE-based KL/JSD on large matrices.

---

## 5) Refactor strategy (phased, equivalence-first)

### Phase 0 — Freeze baseline + contracts (no code change)
Deliverables:
- A “contract sheet” listing:
  - inputs required (with current paths)
  - outputs produced (filenames and object names)
  - key flags: `n.samp`, `USE_PREV`, `cut`, etc.
- A baseline run record (one p0) with:
  - runtime summary
  - output `.RData` file size + timestamp
  - environment snapshot (`sessionInfo()`, compiler vars, OMP vars)

### Phase 1 — Mirror modularization (no semantics, keep order)
Goal: restructure **without changing computation**.

Proposed module layout (similar to `R/environmetrics/`):
```
R/model_fit_disc/
  00_paths.R            # all file paths + dates + site code
  00_setup.R            # libs + deterministic env + OMP settings (repro mode)
  01_cpp_build.R        # compile/load C++ (initially still sourceCpp, but centralized)
  10_inputs.R           # read/validate inputs (USGS, forecasts, covariates)
  20_preprocess.R       # build X, Y, ensembles, standardize, future covs
  30_model_setup.R      # trend/seas, discrepancy structures, df mats
  40_fit_loop.R         # while-loop + update functions (kept verbatim first)
  50_sampling.R         # calls to C++ sample generators (kept verbatim)
  60_outputs.R          # deterministic packaging + save to RData (same names)
  90_diagnostics.R      # KL/JSD computations; behind a flag
```

Entry point:
- `scripts/run_disc_fit_exal.R` (thin wrapper)
  - parses CLI args (`p0`, `n.samp`, `USE_PREV`, `REPRO_MODE`, etc.)
  - sources modules in a fixed order
  - writes the same `.RData` as today (initially still in repo root)

**Equivalence gate**: output `.RData` loads to identical objects (names, dims, key summaries).  
(Byte-identical serialization is not guaranteed, so validate by object identity.)

### Phase 2 — Output hygiene + compatibility
Goal: separate “code repo” from “large outputs” without breaking downstream.

Plan:
- Introduce an outputs root (gitignored):
  - `outputs/model_fit/` (or similar)
- Keep a compatibility layer:
  - either symlink/copy the canonical `DISC_variables_*` into the expected location, or
  - update post-processing path logic to read from outputs root (config-driven).

### Phase 3 — Remove dynamic assign/eval(parse) (still no semantic change)
Replace:
- `assign(...)` + `eval(parse(text = save_cmd))`
With:
- a dedicated environment `out_env <- new.env(parent = emptyenv())`
- explicit assignment into `out_env` with the exact target names
- `save(list = ls(out_env), file = ..., envir = out_env)`

This improves safety and performance without changing the object names.

### Phase 4 — Path portability + caching
Goal: eliminate absolute paths and network fragility.

Plan:
- Put all non-code inputs into a repo-local (gitignored) root, e.g.:
  - `data_raw/covariates/` (ELI, ONI)
  - `data_raw/usgs/` (cached NWIS downloads)
- Add bootstrap scripts:
  - `scripts/bootstrap_fit_inputs.sh` (copies external covariates in)
  - `scripts/cache_usgs_data.R` (writes cached USGS time series)
- Add config file (YAML) that records:
  - all file locations
  - date cutoffs
  - site code(s)

### Phase 5 — Profiling + targeted optimizations
Goal: speed up while preserving results.

Rules:
- One optimization chunk per commit.
- Add per-section timers similar to `profile_section()` used in `R/environmetrics/00_setup.R`.

Typical optimizations (candidate list):
- Avoid repeated conversions `as.matrix()`/`Matrix()` inside loops.
- Precompute block-diagonal structures reused each iter.
- Preallocate arrays/lists; avoid growing objects inside loops.
- Move invariant computations out of the while-loop.
- For diagnostics (KL/JSD), compute only when requested.

### Phase 6 — C++ stabilization
Goal: stop compiling per run and control reproducibility/performance tradeoffs.

Plan:
- Package-ize C++ under `src/` and expose R wrappers under `R/` (or `R/model_fit_disc/`).
- Define two modes:
  - `REPRO_MODE=TRUE`: pinned threads, deterministic schedule; prioritize identical results.
  - `FAST_MODE=TRUE`: allow OpenMP parallelism; validated against repro mode within tolerance/metrics.

---

## 6) Integration with post-processing workflow

Target end state:
- One orchestrated workflow:
  1) Fit model outputs for all p0 (exAL + NDLM baseline).
  2) Run post-processing pipeline (`scripts/run_environmetrics_figures.R`) using those outputs.

Deliverables:
- `scripts/run_all_paper.sh` (or `Makefile`) to run:
  - fits → post-processing → figures
- Documentation under `repro/`:
  - “how to reproduce paper” with exact commands and expected artifacts

---

## 7) NDLM calibration debug checklist (active, no-rerun first)

Intent:
- Diagnose NDLM overfitting behavior with existing artifacts first.
- Keep this efficient: no refits unless a specific gate says a rerun is needed.
- Be most rigorous on:
  - NDLM likelihood/update path,
  - NDLM vs multiv exDQLM state-evolution parity,
  - NDLM modern vs legacy parity.

### 7.1 Baseline freeze (required, no edits)
- [x] Lock and cite the latest NDLM evidence bundle:
  - `repro/runs/diag_p10_ndlm_only_specalign_r05_20260225_073723/run_manifest.yaml`
  - `repro/runs/diag_p10_ndlm_only_specalign_r05_20260225_073723/fit/ndlm_main/logs/ndlm_theory_summary.log`
  - `repro/runs/diag_p10_ndlm_only_specalign_r05_20260225_073723/diagnostics/ndlm/ndlm_iter_trace.csv`
  - `repro/runs/diag_p10_ndlm_only_specalign_r05_20260225_073723/diagnostics/ndlm/ndlm_fit_vs_observed_coverage.csv`
- [x] Write `repro/docs/ndlm_calibration_debug_<timestamp>/baseline_note.md` with:
  - active hyperparameters (`df_*`, `lambda`, `max_iter`),
  - convergence state,
  - top observed quality symptom.
  - Evidence: `repro/docs/ndlm_calibration_debug_20260225T231718Z/baseline_note.md`

### 7.2 Likelihood/update-path audit (rigorous item #1)
Primary question:
- Is the apparent overfit driven by Gaussian likelihood/update behavior vs expected smoother behavior?

Checklist:
- [x] Audit NDLM Gaussian update math and implementation alignment:
  - `R/unified/families/ndlm_main/03_vb_updates.R`
  - `R/unified/families/ndlm_main/02_model_spec.R`
  - `R/unified/families/ndlm_main/ndlm_kalman_backend.cpp`
- [x] Add diagnostics export (no model refit yet):
  - filtered one-step mean/residual series,
  - smoothed mean/residual series,
  - side-by-side summary table.
- [x] Define pass/fail criterion:
  - if smoother is much tighter than one-step filter, classify as expected smoothing effect;
  - if both are unrealistically tight, classify as likely model/update issue.
  - Evidence: `repro/docs/ndlm_calibration_debug_20260225T231718Z/likelihood_update_audit.md`
  - New outputs wired in post diagnostics: `ndlm_fit_modes_series.csv`, `ndlm_fit_modes_coverage.csv`, `ndlm_dynamic_fit_modes_full.png`

### 7.3 NDLM vs multiv exDQLM parity audit (rigorous item #2)
Primary question:
- Is `W_t`/discount evolution wired equivalently (except for likelihood)?

Checklist:
- [x] Build side-by-side mapping table:
  - NDLM current:
    - `R/unified/families/ndlm_main/03_vb_updates.R`
    - `R/unified/families/ndlm_main/ndlm_kalman_backend.cpp`
  - multiv reference:
    - `R/environmetrics/20_model_setup.R`
    - `DISC_kalman_synth.cpp`
    - `scripts/run_DISC_Optimal_Synth_Ranges_W.R`
- [x] Verify block-level parity for:
  - discount matrix construction,
  - `W_t` formation and transition blocks,
  - forecast-window covariance handling contract.
- [x] Record parity outcomes in:
  - `repro/docs/ndlm_calibration_debug_<timestamp>/parity_ndlm_vs_multiv.md`
  - Evidence: `repro/docs/ndlm_calibration_debug_20260225T231718Z/parity_ndlm_vs_multiv.md`

### 7.4 Modern NDLM vs legacy NDLM parity audit (rigorous item #3)
Primary question:
- Are current behaviors intentional deviations (Wishart-forecast update path) or accidental drift?

Checklist:
- [x] Compare modern NDLM to legacy anchors:
  - `scripts/_notebook_linearized.R`
  - `DISC_kalman_synth_NDLM.cpp`
  - `kalman_synth_NDLM.cpp`
- [x] Produce a drift table with three labels only:
  - `intentional_theory_update`,
  - `legacy_technical_debt`,
  - `unexpected_mismatch`.
- [x] Save:
  - `repro/docs/ndlm_calibration_debug_<timestamp>/legacy_parity.md`
  - Evidence: `repro/docs/ndlm_calibration_debug_20260225T231718Z/legacy_parity.md`

### 7.5 Decision gate before any rerun
- [x] Rerun only if at least one of these is true:
  - diagnostics export is missing required series,
  - parity audit found an `unexpected_mismatch`,
  - likelihood audit cannot classify root cause with current artifacts.
- [x] If rerun is required:
  - execute one NDLM-only lean lane, one core, single config change per run.
- [x] If rerun is not required:
  - move directly to minimal code fix proposal + targeted test plan.
  - Gate decision recorded: `repro/docs/ndlm_calibration_debug_20260225T231718Z/decision_gate.md`

### 7.6 Closure criteria for this checklist
- [x] Root cause class selected with evidence path(s).
- [x] One minimal fix scope proposed (or explicit no-fix conclusion if behavior is expected).
- [x] Regression guardrails listed (what must not regress).
- [x] Tracker updated with final status and evidence links.

## 8) Progress log (append-only)
- 2026-02-04: Initial fit-pipeline refactor/optimization tracker created (analysis-only; no code changes in fit pipeline yet).
- 2026-02-25: Added NDLM calibration debug checklist focused on likelihood-path audit, multiv parity audit, and legacy parity audit; set no-rerun-first policy.
- 2026-02-25: Executed NDLM calibration checklist without refit; added fit-mode diagnostics exports (one-step/filtered/smoothed), completed likelihood/parity audits, and recorded gate decision plus evidence bundle under `repro/docs/ndlm_calibration_debug_20260225T231718Z/`.

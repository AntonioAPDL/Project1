# Figure Polish And Rewire Tracker

Date: 2026-05-08
Owner: Codex + Antonio
Status: Planning complete, implementation not started in this pass.

## Goal

Polish and rewire the current manuscript and appendix figure families so that:

- figure styling is consistent and publication-quality across the paper
- labels, units, scales, legends, captions, and manuscript prose all agree
- regenerated outputs remain reproducible from the current workflow
- testing and acceptance checks are explicit before any commit/push
- anything that depends on the later PCA rebuild or full-history rerun is clearly separated from the work we can finish now

This tracker covers only the figure-polish and figure-contract pass. It does not yet refit models, redo PCA, or rerun all cutoffs on the new fit scale.

## Repos And Families In Scope

Workflow repo root:
- `/data/muscat_data/jaguir26/project1_ucsc_phd`

Article repo root:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2`

Figure families:
- Setup/support family (Figures 1--4 and Appendix A3--A6 panels A/B/C/D)
- Current-model historical-support family (Figures 5, 6, A1)
- Post-publication posterior-synthesis family (Figure 7, Figure A2, and raw-ensemble companion outputs)

## Locked Findings From Investigation

### 1. Figure 2 currently shows raw support covariates, not standardized covariates

Evidence:
- Figure 2 support source files are:
  - precipitation: `cov_01_PPT.csv` with column `PRCP_mm`
  - soil moisture: `cov_02_SOIL.csv` with column `Daily_Avg_Soil_Moisture`
  - PCA: `cov_03_PCA.csv` with column `Static_PCA`
- Representative selected-run files inspected at:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_publication_replay_representatives_20260506/20221225_exal_m_t1/runs/multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep/inputs/shared/covariates/cov_01_PPT.csv`
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_publication_replay_representatives_20260506/20221225_exal_m_t1/runs/multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep/inputs/shared/covariates/cov_02_SOIL.csv`
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_publication_replay_representatives_20260506/20221225_exal_m_t1/runs/multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep/inputs/shared/covariates/cov_03_PCA.csv`
- Current manuscript text still says the transfer covariates are standardized precipitation and standardized soil moisture at:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/wileyNJD-APA.tex`

Implication:
- Figure 2 and its surrounding prose need a consistent contract. For the current setup/support figure family, the clean contract is to show the raw cutoff-specific support files with explicit units.

### 2. Figure 3 and Figure 4 are on the correct display scale, but their presentation contract is still too verbose

Evidence:
- Both use `figure_flow_axis_label(plot_scale)` from:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/figure_style_contract.R`
- Figure 3 subtitle still carries historical support-window text from:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/setup_support_bundle_v2_helpers.R`
- Figure 4 legend labels still append coverage date ranges from:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/forecats_plot_bundle.R`

Implication:
- We can simplify the visual contract without changing the data contract.

### 3. Figure 7 and Figure A2 already support raw-ensemble companion outputs, but those companions are run-scoped post adapters on the `log1p_cms` scale

Evidence:
- Rendering entrypoint:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/render_focus_publication_posterior_plot.R`
- Shared plotting logic:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/post_publication_figures.R`
- Companion input contract documented at:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/POST_PUBLICATION_FIGURES_WORKFLOW.md`
- Actual companion inputs for the representative run:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_publication_replay_representatives_20260506/20221225_exal_m_t1/runs/multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep/post/inputs/nws_post_adapter.csv`
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_publication_replay_representatives_20260506/20221225_exal_m_t1/runs/multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep/post/inputs/glofas_post_adapter.csv`
- Run manifest confirms those adapter files are stored as `log1p_cms`.

Implication:
- The existing companion outputs are not raw `cms` curves; they are adapter-scale ensemble references on `log1p_cms`.
- For the current polish pass we should preserve that contract and label/document it honestly.
- If later we want truly raw-`cms` companion figures, that is a separate enhancement.

### 4. Figure A1 is not currently plotting the long-cycle component shifted by the mean trend level

Evidence:
- Current renderer builds `component = 6` directly from state quantile arrays in:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/scripts/render_current_model_output_support_figures.R`
- The article text identifies the long-cycle harmonic as the approximately 80-month component.
- Legacy figure code confirms component indexing conventions and the harmonic setup in:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/Environmetrics_Figures__OLDEST_linearized.R`

Implication:
- Figure A1 needs an interpretive fix, not just a style fix.
- The careful target for this pass is:
  - plot the 80-month seasonal component after shifting it by the posterior mean trend level
  - keep the observed USGS series for reference
  - document whether the credible band is the shifted seasonal band or the full joint trend+seasonal uncertainty band

### 5. Full-history status is still mixed across cutoffs

Current cutoff classes:
- short-window support bundles:
  - `2021-01-23`
  - `2021-11-12`
- corrected full-history support bundles:
  - `2021-12-21`
  - `2022-05-11`
  - `2022-12-25`

Implication:
- Forecast-window figures can still be regenerated for all five cutoffs.
- Full-history setup/support documentation is only fully fixed today for the three corrected full-history cutoffs.

## Decisions For The Figure-Polish Pass

These decisions are locked for the next implementation pass unless Antonio explicitly changes them.

1. Flow display scale for the support and post-publication figure families stays on `log1p_cms`.
2. Flow axis wording should be normalized across all applicable figures to one human-readable form.
3. Figure 2 should show raw support covariates with explicit units.
4. Figure 2 prose and caption should be corrected to match the raw support-file contract.
5. Figure 4 legend entries should show product/version labels only, without coverage-date sublabels.
6. Figure 7 and Figure A2 should be restyled to align visually with Figure 4 while keeping their own content contract.
7. Figure A1 should be reworked to plot the long-cycle component shifted by the mean trend level, pending careful implementation and validation.
8. Appendix A3--A6 four-panel composites remain useful as repo-side documentation even if some or all are later removed from the manuscript appendix.

## Proposed Canonical Label Contract

### Flow figures

Canonical y-axis label:
- `River flow [log(1 + m^3 s^-1)]`

Applies to:
- Figure 1
- Figure 3
- Figure 4
- Figure 5
- Figure 6
- Figure 7
- Figure A1
- Figure A2
- Appendix A3--A6 panel C/D where applicable

### Covariate figure (Figure 2)

Facet labels:
- `Precipitation [mm]`
- `Soil moisture [m^3 m^-3]`
- `1st GDPC`

Rationale:
- precipitation and soil moisture are raw support variables with physical units
- first GDPC is dimensionless and can remain name-only

## Work Packages

### WP1. Shared style and label contract

Targets:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/figure_style_contract.R`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/setup_support_bundle_v2_helpers.R`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/forecats_plot_bundle.R`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/post_publication_figures.R`

Checklist:
- [x] unify flow-axis wording across figure families
- [x] centralize flood-threshold line styling and label styling
- [x] centralize product color usage where feasible
- [x] ensure consistent title sizing, legend sizing, line widths, and point sizes
- [x] remove support-window subtitles from Figures 2 and 3
- [x] make Figure 4 x-axis simply `Date`

Acceptance:
- all flow figures share one axis-label contract
- Figure 1 / Figure 4 / Figure 7 / Figure A2 use visually aligned flood-threshold cues where applicable
- legends no longer feel like they come from separate workflows

### WP2. Setup/support family polish (Figures 2--4 + appendix panel D inheritance)

Targets:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/setup_support_bundle_v2_helpers.R`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/forecats_plot_bundle.R`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/wileyNJD-APA.tex`

Checklist:
- [x] Figure 2: remove subtitle
- [x] Figure 2: add unit-qualified facet labels
- [x] Figure 2: keep compact, publication-quality strip formatting
- [x] Figure 3: remove subtitle
- [x] Figure 3: keep normalized flow-axis wording
- [x] Figure 4: remove coverage-date legend sublabels
- [x] Figure 4: keep only product/version naming in legend
- [x] Figure 4: ensure flood-threshold styling matches Figure 1
- [x] Figure 4: remove ugly wording like `cutoff-centered` from manuscript prose/caption
- [x] propagate Figure 4 style cleanup into the appendix panel-D generation automatically

Acceptance:
- Figure 2 is precise, readable, and unit-explicit
- Figure 3 is clean and uncluttered
- Figure 4 reads like a polished main-text figure, not an internal diagnostic plot

### WP3. Historical-support family polish (Figures 5, 6, A1)

Targets:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/scripts/render_current_model_output_support_figures.R`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/wileyNJD-APA.tex`

Checklist:
- [x] Figure 5: fix y-range to `0--7`
- [x] Figure 6: produce manuscript version at `0--7`
- [x] Figure 6: produce repo companion version at `0--20`
- [x] align title/axis/line/ribbon formatting more closely with the flow-family standard
- [x] Figure A1: confirm component-6 extraction pathway
- [x] Figure A1: implement `80-month component + posterior mean trend level`
- [x] Figure A1: define and document the uncertainty-band contract
- [x] Figure A1 caption: describe the plot honestly and compactly

Acceptance:
- Figures 5 and 6 are directly comparable
- Figure A1 is interpretable against observed flow and no longer floating on an arbitrary component-only level

### WP4. Posterior-synthesis family restyle (Figure 7, Figure A2, companion outputs)

Targets:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/post_publication_figures.R`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/render_focus_publication_posterior_plot.R`
- `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/wileyNJD-APA.tex`

Checklist:
- [x] align Figure 7 and Figure A2 visual style with Figure 4 where possible
- [x] unify flow-axis wording to the shared contract
- [x] clean up titles/subtitles/captions to avoid stale `log(log(1+x))` wording
- [x] decide whether flood-threshold lines belong in both Figure 7 and A2
- [x] if yes, render them from a shared helper rather than duplicating styling
- [x] regenerate raw-ensemble companion outputs for all target cutoffs
- [x] ensure companion outputs are clearly documented as `post adapter` ensemble references on `log1p_cms`

Cutoff production scope for companion outputs:
- [x] representative cutoff `2022-12-25`
- [x] full-history cutoff `2022-05-11`
- [x] full-history cutoff `2021-12-21`
- [x] short-window cutoff `2021-11-12` if only forecast-window context is required
- [x] short-window cutoff `2021-01-23` if only forecast-window context is required

Acceptance:
- Figure 7 and Figure A2 feel like part of the same paper as Figure 4
- raw-ensemble companion outputs exist and are reproducible for the intended cutoffs

### WP5. Appendix scope cleanup

Targets:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/wileyNJD-APA.tex`
- appendix-generation scripts under `Evironmetrics---REVISED-DOC-Corrected-2/scripts`

Checklist:
- [x] keep A3--A6 generation in the repo and retain the current manuscript appendix placement for this pass
- [x] update appendix prose to avoid implying more than the panels show
- [x] keep generation and manifest wiring intact in the repo
- [x] ensure `forecats.png` remains available for every cutoff regardless of manuscript inclusion

Acceptance:
- appendix scope is intentional, not just inherited from legacy figure volume

## Manuscript Prose And Caption Corrections

Targets:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/wileyNJD-APA.tex`

Checklist:
- [x] replace `cutoff-centered` wording with reader-facing language
- [x] fix Figure 2 prose so it matches the raw support-covariate figure contract
- [x] tighten Figure 2, 3, 4, A1, A2 captions to be compact and informative
- [x] remove any stale `log(log(1+x))` wording for figures that are now on `log1p`
- [x] ensure Figure 7/A2 text describes what is actually plotted
- [x] align appendix descriptions with the current cutoff classes and support status

Acceptance:
- captions are compact, informative, and technically correct
- manuscript text and rendered figures agree on scale/unit/lineage

## Reproducibility And Wiring Checklist

Workflow-side reruns to use during implementation:
- [x] `python3 scripts/render_exal_m_t1_setup_support_by_cutoff_v2.py --clean`
- [x] `python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_current_model_output_support_figures.py`
- [x] `python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_exal_m_t1_generated_assets.py`
- [x] `python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_all_generated_assets.py`

Manifest and appendix wiring checks:
- [x] `selection_manifest.json` still points to the intended canonical figure outputs
- [x] appendix composite panels regenerate from the updated canonical subfigures
- [x] `DISC/` promoted figures refresh from updated generated assets
- [x] any new companion outputs are recorded in workflow/article manifests where appropriate

## Testing And Review Checklist

### Automated / script-level
- [x] rerun targeted support-family tooling tests if touched
- [x] rerun any post-publication figure tests if touched
- [x] run smoke renders for all three figure families after code changes

### Manual visual review
- [x] Figure 1 flood thresholds, label placement, and typography
- [x] Figure 2 facet-strip wording, unit clarity, and panel balance
- [x] Figure 3 panel symmetry and y-axis readability
- [x] Figure 4 legend readability, source naming, and flood-threshold consistency
- [x] Figure 5 and 6 shared scale comparison
- [x] Figure 7 and A2 style match against Figure 4
- [x] Figure A1 interpretability after trend shift
- [x] Appendix panel-D consistency across cutoffs

### Manuscript compile
- [x] full article compile succeeds
- [x] captions/prose compile cleanly after edits
- [x] no stale figure references remain

## Hold Points / Not In This Pass

These are explicitly out of scope for the figure-polish pass.

- [ ] PCA rebuild
- [ ] full-history rerun for the short-window cutoff bundles
- [ ] model refits on a revised fit-scale contract
- [ ] table provenance repairs beyond any caption/prose references needed for consistency

## Proposed Implementation Order

1. WP1 shared style contract
2. WP2 setup/support family polish
3. WP3 historical-support family polish
4. WP4 posterior-synthesis family restyle and companion outputs
5. WP5 appendix scope cleanup
6. manuscript compile + visual review + manifest sanity check
7. commit/push only after all acceptance checks pass

## Ready-To-Start Assessment

Implementation readiness: YES.

Rationale:
- the remaining uncertainties are now small enough to handle inside implementation
- the only substantive interpretive change is Figure A1, and it is isolated and documented
- the PCA/full-history rerun work is clearly separated, so we do not need to block this figure pass on later modeling work

## Final Pre-Implementation Questions To Resolve During The Next Pass

These do not block implementation start, but they should be decided explicitly during the work.

1. Should Figure 7 and Figure A2 include flood-threshold lines, or should those remain unique to the direct flow-display figures?
2. Should the manuscript retain all appendix four-panel composites, or move some/all of them to repo-only documentation?
3. For Figure A1, should the uncertainty band represent:
   - shifted seasonal band only, or
   - full joint uncertainty of trend-plus-seasonal sum?

Default recommendation if not otherwise specified:
- include flood lines in Figure 7 but not A2 unless visually helpful
- keep appendix composites generated in repo, then decide manuscript inclusion after visual review
- use seasonal band shifted by posterior mean trend level for Figure A1 in this pass

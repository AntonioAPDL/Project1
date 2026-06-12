# HE2 Revised-Doc Wiring And Rewire Audit (2026-05-17)

## Purpose

This audit turns the revised-doc figure/table state into a single rewiring plan. It separates three different failure modes so we stop mixing them together:

1. **Wiring problems**: the manuscript is pointing at the wrong artifact family or old runtime root.
2. **Renderer problems**: the manuscript is pointing at the right family, but the generator transforms or displays it incorrectly.
3. **Model-output problems**: the manuscript is pointing at the right latest output, but the latest output itself is scientifically or numerically suspect.

## Executive Summary

- Manuscript assets tracked here: `9` figures and `4` tables.
- Article figure lineage status counts: `{"unchanged_intentionally": 8, "updated_now": 39}`.
- Representative keep bundle source: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_multivar_keep`.
- Representative keep bundle currently records `replay_mean_crps = 162225957192096.50` against `published_crps = 0.4375`.
- Historical-support render metadata now records `display_flow_scale = log1p_cms` and `internal_flow_scale = log1p_cms`.
- Benchmark table should remain frozen now.

## Core Findings

### 1. What is well wired right now

- Setup/support manuscript figures are wired to the canonical `five_cutoff_setup_support` bundle and its validated `20260516` full-history/GDPC contract.
- The manuscript representative synthesis figure (`fig:synth1`) is synced to the latest `20260516` `exAL-M-T1` keep rerun and copied through `artifacts/representative_selected_model_2022_12_25/`.
- The appendix support reference synthesis (`fig:synth2`) is synced to the latest `20260516` exAL univar rerun.
- Representative keep-side appendix/source tables (`components`, `gamma`, `sigma`) are generated from the representative keep bundle and are wired correctly at the article layer.

### 2. What is synced but not yet trustworthy

- `fig:synth1` is **current**, but the current representative keep bundle already records an extreme replay CRPS. That means the figure may look bad because the latest rerun output is bad, not because the article is stale.
- The dry/wet historical-support figures and the 80-month component figure are **current**, and the renderer scale contract has now been repaired to `log1p_cms -> log1p_cms` for this replay lane.

### 3. What should stay frozen

- The benchmark CRPS table should stay frozen. It is still sourced from the frozen publication manifest plus raw baselines and should not be refreshed until NDLM is canonical-bundle aligned, AL multivariate families are complete, and exAL benchmark rows are reconciled.

## Action Matrix

| Area | Current state | What to do next | Needs model rerun? |
|---|---|---|---:|
| Setup/support manuscript figures | trusted and current | keep current | no |
| Representative keep synthesis figure | current but quality-flagged | audit latest keep outputs before promoting any new table layer | conditional |
| Historical-support dry/wet/component figures | current with repaired scale contract | keep current and reuse the replay/state-summary contract for future rewires | conditional on replay change |
| Representative keep appendix/source tables | current | keep current unless representative keep rerun changes | conditional |
| Benchmark CRPS table | frozen non-authoritative | hold | yes family set |

## Recommended Phase Order

### Phase A: Repair article-side historical-support rendering

Goal: make Figures 5, 6, and A1 trustworthy without touching model specs.

Status: complete in this audit cycle.

Completed tasks:
- patched `Evironmetrics---REVISED-DOC-Corrected/scripts/render_current_model_output_support_figures.R` so the internal scale is read from the replay contract instead of hardcoding `log_log1p_cms`;
- regenerated `artifacts/historical_support_from_current_models/`;
- rebuilt article refresh/audit outputs;
- synced the rerendered historical-support figures into the manuscript figure tree.

### Phase B: Audit current exAL keep output quality

Goal: determine whether the weird forecast-window synthesis figures reflect a real keep-run problem.

Tasks:
- audit representative keep `2022-12-25` post outputs, CRPS summaries, forecast-window quantiles, and source-map lineage;
- compare representative keep behavior across the five cutoff-wide synthesis figures;
- decide whether the issue is plotting-only, post-metric-only, or a true model-output problem.

Rerun policy for this phase:
- do **not** change `epsilon` / `c_factor` first;
- if a rerun is needed, warm-up/stabilization changes come first;
- only after that, consider quantile-specific tuning with explicit approval.

### Phase C: Hold benchmark table and build final rewrite-ready binding layer

Goal: make future rewires safe and explicit.

Status: complete for the current revised-doc refresh layer.

Completed tasks:
- kept the benchmark CRPS table frozen;
- introduced a single article-to-runtime binding file so refresh scripts stop relying on embedded defaults;
- made each asset family (`setup_support`, `representative_keep`, `historical_support`, `cutoff_synthesis`, `benchmark_table`) choose its runtime roots from that binding layer;
- future reruns can now be rewired by editing one binding file and rerunning one audited refresh entrypoint.

### Phase D: Model-family rerun gates

- `exAL-M-T1`: rerun only if Phase B confirms the current representative keep outputs are genuinely broken.
- `exAL-M-T0` and `exAL-U-T1`: no immediate rerun for revised-doc figures; revisit only during benchmark-table rebuild.
- `AL-M-T1` and `AL-M-T0`: reopen only as warm-up/stabilization investigations.
- NDLM families: canonical shared-bundle rerelaunch is required before benchmark-table rebuild.

## Deliverables In This Audit Package

- `manuscript_asset_tracker.csv`: one row per manuscript figure/table with current wiring state, action gate, and rerun need.
- `generated_family_tracker.csv`: one row per generated asset family with the current runtime root and rewiring recommendation.
- `family_rewire_gate_tracker.csv`: family-level rerun/rewire decisions.
- `rewire_summary.json`: machine-readable top summary.

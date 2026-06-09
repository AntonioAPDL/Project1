# Revision Cross-Repo Progress Audit

Date: 2026-06-09

Scope:

- Code/workflow repo: `/data/muscat_data/jaguir26/project1_ucsc_phd`
- Revised article repo: `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-2`
- Corrections/rebuttal repo: `/data/muscat_data/jaguir26/Corrections---Project-1`

This note is a cross-repo audit overview of where the project stands after the
recent model-repair, publication-manifest, and ablation work. It is not a final
submission checklist. Its purpose is to identify what is now solid, where the
article/corrections/code wiring is drifting, and what validation plan should be
run before the final `.tex` and table refresh.

## Current Git State

All three repositories were clean at the time of this audit, with local commits
not yet pushed:

| repo | branch | local state |
|---|---|---|
| code/workflow | `feature/export_posterior_tables` | clean, ahead of origin by 17 commits |
| revised article | `main` | clean, ahead of origin by 5 commits |
| corrections | `main` | clean, ahead of origin by 2 commits |

Recent workflow-side commits include the HE3 finalizer/audit hardening,
state-norm and gamma-state guard repairs, HE3 ablation launch/finalization, and
HE2 publication-manifest promotion. Recent revised-article commits include HE2
benchmark refreshes and HE3 ablation artifact synchronization. Recent
corrections commits update the HE3 ablation response and add the raw-NWS
exception for HE3.

## Executive Findings

1. The code/runtime side is much stronger than it was a few weeks ago. The
   exDQLM multivariate `keep` path was audited from theory to runtime, repaired,
   guarded, plotted on a comparable scale, and promoted to a five-cutoff
   canonical winner set.
2. The HE2 benchmark table in the revised article is now generated from the
   current publication freeze, not from the older April CF1 sweep. The table
   correctly shows that `exAL-M-T1` wins the first four cutoffs, while `RAW-NWS`
   wins the final `2022-12-25` cutoff and `AL-M-T1` is the best corrected
   Bayesian model at that final cutoff.
3. The HE3 ablation study is complete and reproducible: `30/30` rows passed,
   all `5 x 5` launched ablations passed audit, runtime input inheritance was
   checked, and article/corrections tables were synchronized.
4. The corrections article is now stale for HE2. Its HE2 table and HE2 prose
   still use older values and overclaim that `exAL-M-T1` is best in all five
   cutoffs and beats raw baselines across the panel. That conflicts with the
   current revised article benchmark table and with the current HE2 closeout
   document.
5. The revised article itself still contains at least one stale conclusion
   sentence saying `exAL-M-T1` attains the lowest CRPS "in every case." That
   conflicts with the revised article's own benchmark paragraph and table.
6. HE4 quantile check-loss evidence exists in runtime outputs and in the
   corrections document, but it is not currently exposed as a generated table in
   the revised article manifest. The HE4 builder still defaults to the older
   April CF1 sweep, so HE4 must be revalidated against the current June HE2
   publication manifest before final submission.
7. The article asset manifest covers five tables and nine figures. HE2, HE3,
   representative covariate effects, gamma, and sigma are represented. HE4 is
   not represented, and all figure/source paths still need a final file/hash
   existence check.

## Progress Timeline

### Corrections and Article Rewiring

The May workflow established a canonical revised-article path in
`repro/run/CANONICAL_REVISED_ARTICLE_WORKFLOW.md`. That runbook names
`scripts/unified_run.R` and `R/unified/stages/stage_post.R` as the canonical
model/post entrypoints, and describes article-side refresh helpers in
`Evironmetrics---REVISED-DOC-2/scripts/`. It also defines the current setup and
support figure contract: full `1987-05-29 -> cutoff` support for USGS and raw
covariates, corrected retrospective support, a strict `cutoff - 28` to
`cutoff + 28` forecast-context window, and `log1p_cms` scale.

The revised article now has a manifest-driven asset model in
`Evironmetrics---REVISED-DOC-2/MANUSCRIPT_ASSET_MANIFEST.json`. The manifest
currently registers:

- `tab:benchmark_crps_models`
- `tab:components_23_31`
- `tab:gamma_sigma_intervals1`
- `tab:gamma_sigma_intervals2`
- `tab:he3_ablation_crps`
- nine manuscript figures, including setup/support figures, historical
  summaries, selected-model synthesis, and appendix support.

### exDQLM Multivariate Keep Repair and Promotion

The exDQLM multivariate `keep` workflow went through a full implementation audit
after the `loglog1p -> log1p` transform change exposed instability. The tracked
audit chain includes:

- `docs/exdqlm_multivar_keep_ultimate_audit_plan.md`
- `docs/exdqlm_multivar_keep_state_contract_audit.md`
- `docs/exdqlm_multivar_keep_latent_st_ut_audit.md`
- `docs/exdqlm_multivar_keep_pseudodata_kalman_audit.md`
- `docs/exdqlm_multivar_keep_final_findings.md`
- `docs/exdqlm_multivar_keep_repair_and_transform_regression_plan.md`
- `docs/exdqlm_multivar_keep_near_zero_gamsig_repair_report_20260523.md`
- `docs/exdqlm_multivar_keep_grid_guard_promotion_readout_20260530.md`
- `docs/exdqlm_multivar_keep_authoritative_refocus_20260601.md`

The final refocus decision is that the apparent `2022-05-11` model failure was
mainly a plotting-scale artifact, not evidence of a broken Kalman/latent update.
The authoritative exDQLM multivariate `keep` set is the completed canonical-grid
winner set in:

`reports/exdqlm_multivar_keep_grid_eval_guard_promotion_final_20260530/combined_winners_by_cutoff.csv`

The promoted winner specs are documented in
`docs/exdqlm_multivar_keep_authoritative_refocus_20260601.md` and
`docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`. The selected
cutoff specs are:

| cutoff | spec | epsilon | key note |
|---|---|---:|---|
| 2021-01-23 | `c04_eps365` | 365 | canonical-grid winner |
| 2021-11-12 | `c04_eps365` | 365 | canonical-grid winner |
| 2021-12-21 | `c03_eps030` | 30 | canonical-grid winner |
| 2022-05-11 | `c02_eps060` | 60 | canonical-grid winner; plotting-scale concern resolved |
| 2022-12-25 | `c05_eps030` | 30 | canonical-grid winner; raw NWS beats it in CRPS |

Important implementation repairs from this period include:

- state norm guards scaled by observation-window length;
- gamma/state rollback and recovery behavior;
- first-iteration state guard rollback baseline repair;
- terminal health warning semantics;
- VB latent audit aggregation;
- fixed synthesis y-axis limits for comparable cutoff-window figures;
- promoted post-stage latent/component audit traces for `E[s_t]`, `E[s_t^2]`,
  `E[u_t]`, `E[1/u_t]`, pseudo-data summaries, ELBO, gamma, sigma, and
  `state_norm_sq / T`.

The project also produced a six-index GDPC alternative for
`NOI, SOI, ESPI, PNA, WHWP, AMO` in
`docs/canonical_gdpc_subset6_noi_soi_espi_pna_whwp_amo_20260527.md`, but that
candidate is not promoted into the current five-cutoff publication bundle.

### HE2 Benchmark Table

The current HE2 publication closeout is
`docs/he2_publication_manifest_promotion_closeout_20260608.md`.

That closeout promotes all `9 x 5 = 45` Bayesian table cells onto the canonical
20260510 shared-input-bundle contract and identifies the article-side freeze:

`Evironmetrics---REVISED-DOC-2/artifacts/he2_publication_freeze/`

The generated revised-article table is:

`Evironmetrics---REVISED-DOC-2/tables/generated_tex/benchmark_crps_main_table.tex`

The current generated table has:

- `exAL-M-T1`: `0.1397, 0.0472, 0.2654, 0.0323, 0.6655`
- `AL-M-T1`: `0.1459, 0.0555, 0.2778, 0.0572, 0.6276`
- `RAW-NWS`: `0.8304, 1.3719, 0.2812, 0.2837, 0.5568`

Therefore the correct HE2 interpretation is:

- `exAL-M-T1` is best overall in the first four cutoffs.
- `RAW-NWS` is best overall at `2022-12-25`.
- `AL-M-T1` is the best corrected Bayesian row at `2022-12-25`.
- The corrected Bayesian models do not uniformly dominate the raw operational
  baseline.

The revised article benchmark paragraph already states this correctly in
`wileyNJD-APA.tex`, immediately after the HE2 table. However, the revised
article conclusion still contains the stale sentence that `exAL-M-T1` attains
the lowest forecast-window CRPS "in every case." That must be patched.

### HE3 Ablation

The authoritative HE3 ablation runtime root is:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608`

The final status JSON is:

`control/he3_exdqlm_ablation_authoritative_winners_v1/finalize_status_20260609T165219Z.json`

Final status:

| item | value |
|---|---:|
| matrix rows passed | 30 / 30 |
| full reference rows | 5 |
| launched ablation rows | 25 |
| audit rows | 25 |
| lead-bucket rows | 30 |
| runtime input detail rows | 200 |
| `.RData` remaining after cleanup | 0 |

The finalizer report is:

`reports/he3_exdqlm_ablation/finish_gate/he3_finish_gate_20260609T165234Z.md`

The runtime input audit was hardened in
`scripts/audit_he3_exdqlm_ablation.py`. It keeps strict SHA-256 comparison as
the primary contract, while allowing canonical parsed CSV equality for generated
adapter CSVs where the only difference is writer precision. The detail table is:

`reports/he3_exdqlm_ablation/audit/he3_ablation_runtime_input_detail.csv`

The revised article now includes:

`Evironmetrics---REVISED-DOC-2/tables/generated_tex/he3_ablation_crps_main_table.tex`

The article artifact bundle is:

`Evironmetrics---REVISED-DOC-2/artifacts/he3_exdqlm_ablation_authoritative/`

HE3 is the strongest cross-repo wiring point right now: runtime, audit,
article table, article manifest, and corrections text are all connected. The
HE3 text correctly notes the raw-NWS exception at `2022-12-25`.

### HE4 Quantile Check Loss

Runtime HE4 outputs exist at:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_featurecov_cf1_eps_sweep_20260416/reports/final_featurecov_cf1_eps_analysis/he4_quantile_check_loss/`

The workflow is documented in:

`repro/run/HE4_QUANTILE_CHECK_LOSS_WORKFLOW.md`

The builder is:

`scripts/build_he4_quantile_check_loss_tables.py`

The existing HE4 builder computes forecast-window pinball/check loss for
`tau in {0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95}` for:

- `exAL-M-T1`
- `AL-M-T1`
- `exAL-U-T1`
- `AL-U-T1`

However, the default HE4 input contract still points at the older
`multimodel_v8_featurecov_cf1_eps_sweep_20260416` selection root, and the
current revised-article generated table manifest does not include an HE4 table.
The corrections article includes a hard-coded HE4 table, but it has not yet
been regenerated or validated against the current June HE2 publication freeze.

HE4 should be treated as "runtime evidence exists, publication wiring not yet
authoritative."

## Cross-Repo Wiring Map

| result family | source of truth now | revised article target | corrections target | current status |
|---|---|---|---|---|
| HE2 CRPS benchmark | code repo `reports/he2_publication_manifest/` and article `artifacts/he2_publication_freeze/` | `tables/generated_tex/benchmark_crps_main_table.tex` | HE2 response table/prose | article table current; corrections stale |
| HE3 ablation | HE3 runtime root and `reports/he3_exdqlm_ablation/` | `tables/generated_tex/he3_ablation_crps_main_table.tex` plus article artifact bundle | HE3 response table/prose | current and synchronized |
| HE4 quantile check loss | old CF1 sweep HE4 runtime report | not currently in article generated-table manifest | hard-coded HE4 response table/prose | must be rebuilt or explicitly frozen |
| representative covariate effects | article artifact `representative_selected_model_2022_12_25/covariate_effects_summary.csv` | `representative_covariate_effects_table.tex` | narrative only | table present; source-to-TeX validation still needed |
| gamma/sigma appendix | article artifact `representative_selected_model_2022_12_25/gamma_summary.csv`, `sigma_summary.csv` | appendix generated TeX tables | narrative only | tables present; source-to-TeX validation still needed |
| setup/support figures | `five_cutoff_setup_support` and manifest source paths | manuscript figures and manifest | reviewer narrative | figure paths present; final file/hash check still needed |
| historical/support figures | `historical_support_from_current_models` and manifest source paths | manuscript figures and manifest | reviewer narrative | manifest present; final file/hash check still needed |

## Confirmed Good

The following are ready to be treated as strong evidence, subject to final
compilation and manifest checks:

1. HE2 code-side publication manifest: all 45 Bayesian benchmark cells promoted
   and documented.
2. Revised article HE2 benchmark table: generated from the current HE2 freeze
   and correctly showing the raw-NWS final-cutoff exception.
3. exDQLM multivariate `keep` production winner set: documented and promoted
   after the log1p/latent/gamma-sigma/plotting audit cycle.
4. HE3 ablation runtime matrix: complete, audited, cleaned of `.RData`, and
   synchronized to article/corrections artifacts.
5. HE3 ablation scientific conclusion: full `exAL-M-T1` is best among the
   component-ablation rows at all five cutoffs; removing trend, transfer, or any
   retained harmonic worsens CRPS.
6. Third harmonic semantics: HE3 `H3` is the noninteger frequency
   `1 / 6.8068493`, not the integer third harmonic.
7. Current transform policy: the revised workflow uses `log1p_cms` consistently
   for observations, retrospectives, forecast products, fit internals, and post
   outputs.

## High-Priority Problems

### P0. Corrections HE2 Is Stale

`Corrections---Project-1/main.tex` still contains an older HE2 table with values
such as `exAL-M-T1 = 0.1569, 0.0284, 0.2369, 0.0210, 0.4375`. Those are not the
current revised-article values. Its HE2 prose also says `exAL-M-T1` is
best-performing in all five cutoffs and that the best corrected model
outperforms the best raw forecast baseline across the panel.

This conflicts with:

- the current revised-article HE2 generated table;
- the HE2 closeout document;
- the article benchmark paragraph;
- the HE3 corrections paragraph that already acknowledges the final-cutoff
  raw-NWS exception.

Required fix: regenerate or replace the HE2 corrections table/prose from the
current HE2 publication freeze and explicitly state the `2022-12-25` raw-NWS
exception.

### P0. Revised Article Conclusion Has a Stale Overclaim

`Evironmetrics---REVISED-DOC-2/wileyNJD-APA.tex` has a correct benchmark
interpretation after the table, but the conclusions section still says
`exAL-M-T1` has the lowest CRPS "in every case." This is false under the current
table.

Required fix: revise the conclusion to match the benchmark paragraph: the
multivariate transfer models are strongest corrected models overall,
`exAL-M-T1` wins the first four cutoffs, `AL-M-T1` is the best corrected
Bayesian row at `2022-12-25`, and raw NWS is the lowest table entry at that
final cutoff.

### P1. HE4 Is Not Yet Current-Manifest Wired

The HE4 runtime table exists, but:

- the builder defaults to the older April CF1 sweep;
- the revised article manifest does not list an HE4 table;
- the corrections article hard-codes HE4 values;
- the HE4 text says the diagnostics are summarized in the revised manuscript,
  but the current revised article does not expose a HE4 generated table in the
  manifest.

Required fix: decide whether HE4 belongs in the revised article main text,
appendix, or corrections-only response. Then rebuild HE4 from the current HE2
publication manifest, or explicitly freeze the old CF1 source as a legacy
corrections-only artifact with a clear reason.

### P1. Corrections TODO Block Remains Open

The corrections file still has internal TODOs near the top, including HE2,
HE3/HE4 section-number placeholders, HE6 forecast-input timing wording, and
several reviewer-review checks.

Required fix: close, remove, or intentionally convert every internal TODO before
final submission.

### P1. Need a Cross-Repo Table Validator

The revised article now uses generated TeX, the corrections article uses
hard-coded tables, and runtime/code reports use CSV/JSON. There is no single
validator yet that compares:

- runtime/source CSVs;
- article artifact CSVs;
- article generated TeX;
- corrections hard-coded TeX;
- prose claims about winners and raw baselines.

Required fix: implement a cross-repo validation script before the final `.tex`
refresh.

### P2. Need a Figure/Manifest/File-Existence Gate

The article manifest records source and manuscript figure paths, but this audit
did not yet run a full file-existence/hash validator over every figure and
table source. This is necessary before final compilation and before pushing.

Required fix: validate every manifest source path, every manuscript include, and
every generated table source path.

## Recommended Next Validation Plan

### Phase A. Freeze Source-of-Truth Inventory

Create one machine-readable cross-repo inventory that records, for each table
and figure:

- result family: HE2, HE3, HE4, representative effects, gamma/sigma, setup
  figures, historical figures;
- source CSV/JSON/runtime root;
- article artifact path;
- generated TeX path;
- corrections TeX location, if any;
- expected status: current, stale, legacy, or intentionally omitted.

### Phase B. Implement Table-Value Validator

Build a validator that:

1. reads HE2 from `artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv`
   plus raw rows from `artifacts/five_cutoff_crps_validation_sources/`;
2. reads HE3 from `artifacts/he3_exdqlm_ablation_authoritative/he3_ablation_long.csv`;
3. reads representative tables from
   `artifacts/representative_selected_model_2022_12_25/*.csv`;
4. optionally rebuilds HE4 from the current HE2 manifest;
5. parses generated article TeX rows;
6. parses corrections hard-coded tables;
7. fails on numeric mismatches beyond display rounding tolerance.

### Phase C. Patch Known Text Contradictions

Patch at minimum:

- revised article conclusion stale "lowest CRPS in every case" sentence;
- corrections HE2 table and HE2/HE6 prose overclaims;
- corrections TODO block or placeholder section-number statements.

### Phase D. Decide and Rebuild HE4

Choose one of two defensible paths:

1. promote HE4 into the revised article generated table system and regenerate it
   from the current June HE2 publication manifest; or
2. keep HE4 as corrections-only evidence, but clearly document its source and
   rerun it under the current manifest if the numerical values changed.

The stronger path is to regenerate HE4 from the same current HE2 publication
freeze that drives the CRPS table.

### Phase E. Manifest and Figure Gate

Run a full manifest check over:

- `MANUSCRIPT_ASSET_MANIFEST.json`;
- `tables/generated_tex/manifest.csv`;
- all `\input{...}` paths;
- all `\includegraphics{...}` paths;
- article artifact source files;
- corrections tables/figures, if any.

The check should report missing files, stale paths, table labels not in the
manifest, and manifest entries not referenced by the manuscript.

### Phase F. Compile Both Documents

Compile the revised article and corrections article. Inspect logs for:

- undefined references;
- missing figures;
- overfull/underfull boxes in table-heavy sections;
- unresolved bibliography entries;
- stale labels or section references.

### Phase G. Commit and Push Only After Clean Gates

After phases A-F pass:

1. commit code-repo validation scripts/docs;
2. commit revised-article text/table/manifest updates;
3. commit corrections text/table updates;
4. push all three repos together only after a final `git status` and compile
   check.

## Bottom Line

The scientific/modeling backend is no longer the main blocker. The current
blocker is cross-repo publication consistency. HE2 and HE3 have strong runtime
and artifact evidence, but the corrections article and the revised article
conclusion still contain stale claims from earlier runs. HE4 exists as runtime
evidence but is not yet wired into the same current manifest system as HE2 and
HE3.

The immediate next move should be a source-to-TeX validation pass, followed by
patching the stale HE2/HE4/corrections text and compiling both documents.

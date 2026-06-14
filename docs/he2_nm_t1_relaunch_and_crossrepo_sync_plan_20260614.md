# HE2 N-M-T1 Relaunch And Cross-Repo Sync Plan

Date: 2026-06-14

## Purpose

This plan defines the next controlled repair pass for the suspicious
`N-M-T1` / `ndlm_main_keep` HE2 benchmark row and the follow-on
article/corrections synchronization. It supersedes any informal assumption that
the current publication freeze is scientifically final for `N-M-T1`.

The current revised article and corrections article are internally synced, but
the `N-M-T1` row is empirically suspicious enough that it should be rerun and
re-audited before the HE2 table is treated as final.

## Repositories And Current Gate State

Workflow repository:

- root: `/data/muscat_data/jaguir26/project1_ucsc_phd`;
- branch: `feature/export_posterior_tables`;
- checked head for this plan: `b8c0d08`.

Revised article repository:

- root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2`;
- branch: `main`;
- checked head for this plan: `38e1230`;
- tracked remote: `origin =
  https://github.com/AntonioAPDL/Evironmetrics---REVISED-DOC-Corrected-2.git`.

Corrections repository:

- root: `/data/muscat_data/jaguir26/Corrections---Project-1`;
- branch: `main`;
- checked head for this plan: `7fd2fb0`.

Validation status before any new relaunch:

```bash
python3 scripts/validate_publication_freeze.py \
  --workflow-root /data/muscat_data/jaguir26/project1_ucsc_phd \
  --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2 \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1 \
  --report-dir /tmp/publication_freeze_check_nm_t1_planning \
  --require-clean
```

Result: pass.

```bash
python3 scripts/validate_revision_cross_repo_wiring.py \
  --workflow-root /data/muscat_data/jaguir26/project1_ucsc_phd \
  --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2 \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1 \
  --output-dir /tmp/revision_cross_repo_wiring_nm_t1_planning \
  --check-only --strict
```

Result: pass.

Interpretation: the repos are coherent at the current freeze. This does not
mean the `N-M-T1` CRPS values are scientifically satisfactory.

## Source Of The Current N-M-T1 Values

The active HE2 publication manifest is:

`Evironmetrics---REVISED-DOC-Corrected-2/artifacts/he2_publication_freeze/he2_bayesian_publication_manifest.csv`

Current `N-M-T1` rows:

| Cutoff | Active run | Lineage | CRPS |
|---|---|---|---:|
| `20210123` | `multimodel_20210123_v8_he2pubgdpc1r1_ndlm_main_keep` | `ndlm_publication_promotion_20260607:canonical_bundle_promoted` | 3.214902 |
| `20211112` | `multimodel_20211112_v8_he2pubgdpc1r1_ndlm_main_keep` | `ndlm_publication_promotion_20260607:canonical_bundle_promoted` | 0.890963 |
| `20211221` | `multimodel_20211221_v8_he2tbl1fix20260612_ndlm_main_keep` | `he2_table1_targeted_repair_20260612:canonical_bundle_targeted_repair` | 3.043623 |
| `20220511` | `multimodel_20220511_v8_he2pubgdpc1r1_ndlm_main_keep` | `ndlm_publication_promotion_20260607:canonical_bundle_promoted` | 0.868198 |
| `20221225` | `multimodel_20221225_v8_he2pubgdpc1r1_ndlm_main_keep` | `ndlm_publication_promotion_20260607:canonical_bundle_promoted` | 3.888629 |

The current manifest builder declares the NDLM authority roots and `N-M-T1`
lineage in
`scripts/build_he2_bayesian_publication_manifest.py:155-179` and the expected
label/likelihood/transfer contract in
`scripts/build_he2_bayesian_publication_manifest.py:750-759`.

The manifest builder also enforces the current covariate/input feature contract
for promoted Bayesian rows:
`scripts/build_he2_bayesian_publication_manifest.py:730-740`.

## Why N-M-T1 Needs A Separate Root-Cause Pass

The June 13 repair plan correctly installed a selective promotion policy:

- promote a repaired row only when CRPS is lower or tied;
- keep the previous lower-CRPS row when the repaired row is worse.

That policy is documented in
`docs/he2_table1_root_repair_and_article_sync_plan_20260613.md:786-810`.

Under that policy, two attempted `N-M-T1` repairs were explicitly not promoted:

| Cutoff | Previous CRPS | Repaired CRPS | Delta |
|---|---:|---:|---:|
| `20210123` | 3.21490235 | 3.22348413 | +0.00858178 |
| `20221225` | 3.88862909 | 3.89354704 | +0.00491795 |

The current publication-freeze validator now encodes those non-promoted
fallback values in `scripts/validate_publication_freeze.py:40-48` and checks
them in `scripts/validate_publication_freeze.py:180-198`. If a new `N-M-T1`
run is promoted, that validator must be updated intentionally.

Older `ndlm_featurecov_rerun_postfix_20260421` `N-M-T1` outputs had much lower
CRPS:

| Cutoff | Current CRPS | Old postfix CRPS | Old source |
|---|---:|---:|---|
| `20210123` | 3.214902 | 0.527523 | `multimodel_v8_ndlm_featurecov_rerun_postfix_20260421` |
| `20211112` | 0.890963 | 0.072216 | `multimodel_v8_ndlm_featurecov_rerun_postfix_20260421` |
| `20211221` | 3.043623 | 0.607141 | `multimodel_v8_ndlm_featurecov_rerun_postfix_20260421` |
| `20220511` | 0.868198 | 0.041580 | `multimodel_v8_ndlm_featurecov_rerun_postfix_20260421` |
| `20221225` | 3.888629 | 0.536271 | `multimodel_v8_ndlm_featurecov_rerun_postfix_20260421` |

Those old values are not automatically promotable because the publication table
now requires the canonical 20260510 input-bundle contract:
`docs/he2_table1_targeted_repair_relaunch_20260612.md:91-102`.

However, they are strong diagnostic evidence that the current full-history
`N-M-T1` behavior should not be accepted without explanation.

## Current Runtime Diagnostic Snapshot

`N-M-T1` is a normal/NDLM row. It does not use the exAL `s_t` / `u_t`
variational latent updates, so the warmup-freeze patches used for AL/exAL
quantile rows are not the root lever here. The relevant layers are the NDLM
state-space fit, the keep-transfer forecast construction, sigma estimates,
forecast covariance, transform scale, and post-stage synthesis scoring.

Current versus old `N-M-T1` diagnostics:

| Cutoff | Source | CRPS | T | sigma_usgs | sigma_nws | sigma_glofas | latent_var_cap_last |
|---|---|---:|---:|---:|---:|---:|---:|
| `20210123` | current | 3.214900 | 12294 | 0.039876 | 0.159054 | 0.494993 | 0.004685 |
| `20210123` | old postfix | 0.527523 | 1081 | 0.016464 | 0.659629 | 1.919630 | 0.017436 |
| `20211112` | current | 0.890963 | 12587 | 0.076008 | 0.220741 | 0.031393 | 0.001390 |
| `20211112` | old postfix | 0.072216 | 1081 | 0.018225 | 0.880542 | 8.610350 | 0.013868 |
| `20211221` | current | 3.043623 | 12626 | 0.038518 | 0.202249 | 0.241883 | 0.002985 |
| `20211221` | old postfix | 0.607141 | 12626 | 0.015828 | 0.722912 | 11.430300 | 0.014668 |
| `20220511` | current | 0.868198 | 12767 | 0.109121 | 0.251622 | 0.010021 | 0.000716 |
| `20220511` | old postfix | 0.041580 | 12767 | 0.015776 | 0.689985 | 11.310800 | 0.005267 |
| `20221225` | current | 3.888629 | 12995 | 0.037442 | 0.198800 | 0.325533 | 0.003439 |
| `20221225` | old postfix | 0.536271 | 1081 | 0.016037 | 1.067963 | 10.347400 | 0.030238 |

The current forecast-window quantile summaries also show raw-scale blowups after
the `log1p` inverse transform:

| Cutoff | Current q50 log1p range | Truth log1p range | Current q95 raw max |
|---|---:|---:|---:|
| `20210123` | 1.270 to 18.612 | 0.412 to 3.341 | 8.75e+11 |
| `20211112` | 1.295 to 1.852 | 0.429 to 0.645 | 15.8 |
| `20211221` | 3.219 to 14.279 | 1.279 to 3.625 | 1.70e+08 |
| `20220511` | 1.297 to 1.712 | 0.421 to 0.570 | 20.7 |
| `20221225` | 1.904 to 17.301 | 0.565 to 5.364 | 7.12e+09 |

Initial interpretation:

1. The issue is not explained by `s_t` or `u_t`; `N-M-T1` is NDLM/normal.
2. The issue is not a missing post artifact; every active `N-M-T1` row has CRPS
   tables and forecast-window quantile tables.
3. The issue is plausibly an interaction among full-history support, estimated
   source sigmas / latent forecast covariance, keep-transfer forecast-state
   propagation, and the `log1p` raw-scale inverse.
4. For `20211221` and `20220511`, old postfix and current runs both used full
   `T`, but their sigma and forecast quantile behavior differ substantially.
   That means the relaunch must also check code-path/post-stage changes, not
   only support-window length.

## Relaunch Design

Do not relaunch broad model families. Relaunch only `N-M-T1` first.

Runtime root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_nm_t1_root_relaunch_20260614`

Scope:

- five cutoffs: `20210123`, `20211112`, `20211221`, `20220511`, `20221225`;
- family: `ndlm_main_keep` only;
- current canonical 20260510 shared input bundle only for promotable candidates;
- `data_start = 1987-05-29`;
- covariates: `PPT|SOIL|PCA` where `PCA` is the GDPC compatibility alias;
- covariate features: lags `1|2|3`, squares, and interaction;
- seasonality: `[1, 2, 1/6.8068493]`, not literal harmonic `3`;
- forecast transfer: `keep`;
- max iterations: `100`, unless a diagnostic probe explicitly asks otherwise.

Candidate specs:

| Candidate | Purpose | Promotable? | Specification |
|---|---|---|---|
| A | current-control replay | yes if improved by current code/output refresh | Clone the active publication `N-M-T1` spec exactly. |
| B | intended repair-spec replay | yes if CRPS improves and gates pass | Same as A but force `df_trans=df_covs=0.99999999` for every cutoff, matching the 2026-06-12 requested `N-M-T1` override. |
| C | old-window compatibility probe | no | Reproduce the old 1081-row support window for the cutoffs where old postfix used it, only to isolate support-window sensitivity. |
| D | sigma/forecast-covariance stress probe | no until justified | Add bounded/smoothed source-sigma or forecast-variance diagnostics only after A/B explain whether the current fit is a stable optimum or a pathological covariance collapse. |

Candidate C and D are diagnostics, not publication replacements. They can
explain the failure mode, but only A/B-style canonical-bundle outputs can enter
Table 1.

## Required Implementation Stages

### Stage 0: Freeze Before Touching Tables

- Re-run both cross-repo validators.
- Record current workflow, article, and corrections heads.
- Save the current `N-M-T1` rows and all five active forecast-window quantile
  CSVs under an untracked report folder.
- Confirm no current production run is touched.

Acceptance gate: validators pass and the report has exact source paths for all
five current rows.

### Stage 1: Build A Dedicated N-M-T1 Diagnostic Report

Create a reproducible diagnostic script/report that compares current active
`N-M-T1` rows against the old postfix rows and any newly relaunched candidates.
Minimum outputs:

- mean CRPS, median CRPS, max per-lead CRPS;
- per-lead CRPS table;
- `T`, `K`, `K_overlap`, `nws_len`, `glofas_len`;
- `sigma_usgs`, `sigma_nws`, `sigma_glofas`;
- `state_norm_sq / T` when available in progress logs;
- `latent_var_cap_last`;
- q05/q50/q95 ranges on `log1p` and raw scales;
- maximum raw-scale forecast quantile after inverse transform;
- input hashes for parameters, retros, NWS, GloFAS, and covariates;
- config diff against active manifest row.

Output target:

`reports/he2_nm_t1_runtime_diagnostic_20260614/`

Acceptance gate: the report can be regenerated from paths and does not require
manual spreadsheet editing.

### Stage 2: Generate Isolated Relaunch Configs

Use the existing HE2 publication relaunch builder where possible, but add an
`N-M-T1`-only matrix mode if necessary. The generated matrix must contain
exactly:

- 5 rows for Candidate A; and
- 5 rows for Candidate B.

Optional Candidate C/D probes must be marked `diagnostic_only=true` in the
matrix and excluded from any manifest-promotion script.

Acceptance gates:

- generated row count equals expected count;
- all generated configs resolve to the canonical 20260510 bundle for A/B;
- materialized input hashes are equal within each cutoff across A/B;
- harmonics are `[1, 2, 0.146910847578189]`;
- lag/square/interaction contract matches the current publication manifest;
- dry-run launch prints only the new isolated runtime root.

### Stage 3: Prelaunch Validation

Run a narrow prelaunch validation:

- one full-history single-iteration NDLM smoke for the longest cutoff;
- one full-pipeline post smoke for one cutoff;
- config audit for every row.

Acceptance gates:

- no missing materialized inputs;
- post smoke produces `crps_forecast_summary.csv`,
  `crps_forecast_per_time.csv`, and `ndlm_forecast_window_quantiles.csv`;
- diagnostic values are finite;
- no post-stage mismatch in `model_id = ndlm_main_synth_keep`.

### Stage 4: Relaunch A/B Candidates

Launch only after Stages 0-3 pass.

Resource plan:

- one worker per `N-M-T1` row;
- at most 5 concurrent rows unless the server is otherwise idle;
- no broad 7-quantile scheduling is needed because this is a single NDLM row;
- retain lightweight logs and CSV outputs;
- remove large `.RData`/`.rda` after post unless a run fails or is explicitly
  marked for debugging.

Acceptance gates:

- every A/B run reaches `report/pass`;
- CRPS summaries exist;
- diagnostic report is refreshed with candidate rows;
- if a row fails, do not patch around it; inspect fit logs, diagnostics, config,
  and post outputs to identify the root failure.

### Stage 5: Selection And Promotion Decision

For each cutoff:

1. compare Candidate A, Candidate B, and the current active freeze row;
2. promote only the lowest CRPS canonical-bundle row that passes all validation
   gates;
3. if no candidate improves the current row, keep the current row but document
   the reason;
4. never promote Candidate C/D outputs to the article table.

Acceptance gates:

- selection report contains all candidates and exact source paths;
- any promoted replacement has lower CRPS than the current active row;
- replacement overlay count and validator expectations are updated intentionally.

### Stage 6: Rebuild HE2/HE4/HE3 Assets

After any promotion:

- rebuild the workflow-side HE2 publication manifest;
- refresh
  `Evironmetrics---REVISED-DOC-Corrected-2/artifacts/he2_publication_freeze/`;
- rebuild article generated table includes;
- sync the corrections generated HE2 response table from the same article-side
  source;
- rebuild HE4 check-loss artifacts even though `N-M-T1` is not one of the four
  HE4 synthesis competitors, to prove no accidental dependency changed;
- re-run HE3 ablation validation. The HE3 ablation table is anchored to the
  selected `exAL-M-T1` winners and should not need rerunning unless its source
  manifest changes. The article-side HE3 source is described in
  `Evironmetrics---REVISED-DOC-Corrected-2/MANUSCRIPT_ASSET_MANIFEST.json`.

Acceptance gates:

- revised Table 1 includes the selected `N-M-T1` values with five decimals;
- corrections Table 1 response table matches the article table values;
- HE4 table regenerates without changes except expected timestamps/manifests;
- HE3 table either has no diff or has a documented source-triggered diff;
- publication-freeze validator passes after updating any expected
  non-promoted-fallback logic.

### Stage 7: Prose And Cross-Reference Audit

Audit and patch only prose that becomes stale after the selected `N-M-T1`
decision.

Required text locations:

- revised article Table 1 setup and interpretation:
  `Evironmetrics---REVISED-DOC-Corrected-2/wileyNJD-APA.tex:353-371`;
- revised article selected-specification transition:
  `Evironmetrics---REVISED-DOC-Corrected-2/wileyNJD-APA.tex:375`;
- corrections model-label and HE2 response section:
  `/data/muscat_data/jaguir26/Corrections---Project-1/main.tex:158-181`;
- corrections HE3 response section:
  `/data/muscat_data/jaguir26/Corrections---Project-1/main.tex:192`.

Likely prose outcome:

- If `N-M-T1` improves but remains far from the selected rows, the main
  interpretation probably does not change.
- If `N-M-T1` becomes competitive with AL/exAL multivariate rows, update the
  HE2 discussion explicitly and re-check all claims about "strongest corrected"
  models.
- The corrections text should remain concise and should not over-explain
  internal relaunch mechanics unless the scientific conclusion changes.

Acceptance gates:

- revised article compiles;
- corrections article compiles;
- figure/table references resolve;
- no stale hard-coded CRPS values remain outside generated table includes.

## Table And Style Rules

- Table numbers should be generated from source CSVs, not manually edited.
- CRPS/check-loss values shown in manuscript tables must use five decimals.
- The revised article and corrections article must not carry divergent CRPS
  values for the same label/cutoff.
- Any hard-coded prose claim about model ranking must be checked against the
  regenerated source table.
- Overleaf-safe article outputs should include only manuscript tables and
  figures, not large support CSVs or `.RData` files.

## Do Not Do

- Do not overwrite the current publication freeze before the new selection gate
  passes.
- Do not promote old postfix values unless they are reproduced under the current
  canonical input-bundle contract.
- Do not relaunch all nine model families to fix one `N-M-T1` row.
- Do not apply AL/exAL `s_t` / `u_t` warmup logic to `N-M-T1`; that layer is not
  active for the normal NDLM row.
- Do not edit corrections tables by hand.

## Immediate Next Checklist

- [ ] Create the reproducible `N-M-T1` diagnostic report script.
- [ ] Generate the diagnostic report comparing active current rows, old postfix
      rows, and the two 2026-06-12 targeted repair attempts.
- [ ] Add the isolated A/B `N-M-T1` relaunch matrix builder or matrix mode.
- [ ] Add focused tests for generated row count, canonical input bundle, harmonic
      contract, and Candidate A/B discount-factor contracts.
- [ ] Run build-only and prelaunch validation.
- [ ] After validation passes, launch the isolated A/B relaunch.
- [ ] Refresh the diagnostic report and select the best canonical-bundle row per
      cutoff.
- [ ] Patch manifest overlay and validators only for rows that improve.
- [ ] Regenerate HE2, HE4, and HE3 validation assets.
- [ ] Sync revised article and corrections article generated tables.
- [ ] Compile both documents and rerun strict cross-repo validation.

## Current Recommendation

Proceed with Stages 0-3 before launching. The evidence is strong enough to
justify a relaunch, but the relaunch should be `N-M-T1`-only and diagnostic-led.
The old postfix outputs show that much better `N-M-T1` behavior is possible, but
the publication standard is the current canonical 20260510 full-history bundle.
The next repair is therefore not "copy the old table"; it is "reproduce or
explain the old good behavior under the current canonical contract, then promote
only rows that actually improve."

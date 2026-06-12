# HE2 Full-History Repair Forward Plan

Date: 2026-05-07

## Purpose

This document freezes the forward plan for the next major repair cycle after the current article-side wiring and provenance work.

The immediate goal is **not** to rerun models yet. The immediate goal is to make sure the project is now structured so that when we do rerun models:

1. the workflow repo produces the right artifacts,
2. the revised article repo receives refreshed bundles automatically,
3. the corrections repo stays aligned to the revised article source of truth,
4. and we do not repeat the same manual synchronization work.

This plan exists because the historical-support audit revealed a serious modeling-contract issue:

- if the intended scientific contract is that all published Bayesian rows should use the full historical support from `1987-05-29` to cutoff,
- then the currently published Bayesian rows at cutoffs `2021-01-23`, `2021-11-12`, and `2022-12-25` do not satisfy that contract.

Reference audit:
- `/data/muscat_data/jaguir26/project1_ucsc_phd/reports/he2_publication_manifest/historical_support_audit_20260507/historical_support_audit.md`
- mirrored article snapshot:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2/generated/he2_historical_support_audit_20260507/historical_support_audit.md`

## Governing principle

We must preserve two truths simultaneously:

1. **Preserve the currently published table exactly** as a frozen, documented publication state.
2. **Enforce the intended full-history contract** in the next rerun cycle so that future corrected results are methodologically coherent.

That means the project must support two parallel states:

- a frozen publication-state lineage,
- and a forward corrected lineage.

Those states must never be mixed implicitly.

## What is already locked

### Publication-state freeze

The current publication state is frozen by:
- `reports/he2_publication_manifest/he2_bayesian_publication_manifest.md`
- `reports/publication_replay/publication_replay_matrix.md`
- `reports/he2_publication_manifest/historical_support_audit_20260507/historical_support_audit.md`
- article-side snapshots under:
  - `Evironmetrics---REVISED-DOC-Corrected-2/generated/he2_publication_manifest_snapshot/`
  - `Evironmetrics---REVISED-DOC-Corrected-2/generated/he2_historical_support_audit_20260507/`

### Article-side generated-asset wiring

The revised article repo is now the canonical freeze point for generated assets and review bundles.

Current canonical generated families under:
- `Evironmetrics---REVISED-DOC-Corrected-2/generated/`

Current refresh entrypoint:
- `Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_all_generated_assets.py`

Current generated-asset index entrypoint:
- `Evironmetrics---REVISED-DOC-Corrected-2/generated/README.md`
- `Evironmetrics---REVISED-DOC-Corrected-2/generated/asset_inventory.csv`

### Corrections synchronization rule

The corrections repo should now treat the revised article repo as its manuscript/evidence source of truth for figure/table role descriptions and frozen generated bundles.

## Scope of the next repair cycle

The next repair cycle should cover the Bayesian HE2 panel only.

Out of scope for the first repair pass:
- raw forecast reference rows (`RAW-GLOFAS`, `RAW-NWS`)
- optional figure restyling
- new scientific analyses unrelated to the historical-support contract

In scope:
- all 45 Bayesian HE2 rows
- all cutoffs with short-window effective support
- the exact shared-input contract used by fit
- canonical GDPC master-covariate reproducibility hardening
- article and corrections auto-refresh after reruns

## Confirmed affected cutoffs

From the historical-support audit, the currently published Bayesian rows use short-window effective support at:

- `2021-01-23`
- `2021-11-12`
- `2022-12-25`

Cutoffs already consistent with the intended full-history contract:

- `2021-12-21`
- `2022-05-11`

## Confirmed affected publication rows

Because `retros`, `nws_forecast`, and `glofas_forecast` are aligned within each cutoff, the cutoff-level issue propagates across the full Bayesian row family at each affected cutoff.

That means the following rows are affected at each of the three problematic cutoffs:

- `N-U-T1`
- `N-M-T0`
- `N-M-T1`
- `AL-U-T1`
- `AL-M-T0`
- `AL-M-T1`
- `exAL-U-T1`
- `exAL-M-T0`
- `exAL-M-T1`

Total affected publication rows:
- `27`

## Required future workstreams

### Workstream A. Full-history shared-input reconstruction

Goal:
- rebuild the affected cutoffs so the effective support used by fit truly begins at `1987-05-29`.

This requires:
- rebuilding the retrospective source bundles for the affected cutoffs,
- confirming the intended NWS retrospective construction,
- confirming the intended GloFAS retrospective selection,
- and ensuring the final `retros.csv` delivered to fit preserves full common-date support rather than collapsing to a short window.

Key references:
- `repro/UNIFIED_MULTIMODEL_WORKFLOW_TRACKER.md`
- `repro/FORECATS_INPUTS_AND_WEIGHTING_PLAN.md`
- `repro/MULTIMODEL_V8_HISTFIX_20260407.md`
- `repro/run/EXAL_M_T1_SETUP_SUPPORT_V2_SOURCE_MANIFEST.md`

### Workstream B. Publication-state preservation

Goal:
- keep the current table and provenance reproducible while the corrected reruns are being developed.

This means:
- do not overwrite the current publication manifests,
- do not overwrite the article-side publication snapshots,
- and always label new corrected artifacts as a new lineage.

### Workstream C. Canonical GDPC master-covariate reproducibility hardening

Goal:
- make the large-scale climate covariate generation and preservation as reproducible and inspectable as the other covariate inputs.
- the chosen future contract is a canonical master `GDPC1`, not the legacy frozen static-PCA artifact.

This work is required because the large-scale climate factor is part of the common covariate contract across the Bayesian rows, and we need a clear answer to:

- where the preserved climate-factor input comes from,
- how it is regenerated if needed,
- what source data feed it,
- and how article-side bundles will be refreshed if the canonical factor changes.

Canonical design note:
- see `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/CANONICAL_GDPC_MASTER_COVARIATE_REPORT_20260509.md`
- implementation tracker: `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/CANONICAL_GDPC_IMPLEMENTATION_TRACKER_20260509.md`
- source-pipeline runbook: `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/CANONICAL_GDPC_SOURCE_PIPELINE_RUNBOOK_20260509.md`
- full-pipeline runbook: `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/CANONICAL_GDPC_MASTER_PIPELINE_RUNBOOK_20260509.md`
- the agreed future direction is one master `GDPC1` built over `1987-05-29 -> 2023-01-22` using the 17-index daily climate matrix, with shared-master leakage across cutoffs accepted by design
- no expensive automatic lag cross-validation will be used in the canonical implementation; the lag count will be frozen explicitly in metadata
- the stationarity decision is also frozen now: keep the full 17 standardized daily series in levels and do not difference or detrend them before fitting `GDPC1`
- the bounded simple lag screen over `k in {1, 2, 3}` selected `k = 2`, with `k = 3` timing out under the `900` second per-candidate cap
- the implemented canonical fit now uses `k = 2`, `tol = 1e-3`, `niter_max = 200`, and criterion label `BIC`, with sign orientation anchored to positive correlation with `oni`

Minimum deliverables for this workstream:
- one GDPC provenance note/runbook,
- one explicit regeneration path,
- one canonical master GDPC artifact plus compatibility aliases for downstream workflow consumers,
- one article-side frozen snapshot or manifest entry,
- one validation check that the GDPC file used by reruns matches the intended canonical source.

### Workstream D. Automatic article/corrections refresh after reruns

Goal:
- when new corrected reruns land, the revised article repo and corrections repo update through documented refresh steps rather than manual ad hoc copying.

Required contract:
1. workflow rerun artifacts are validated first,
2. article-side bundles refresh through article scripts,
3. article review pages regenerate,
4. corrections text is synchronized against the revised article provenance state.

## Recommended implementation order for the future repair cycle

### Phase 0. No-rerun architecture freeze

Done now:
- article-side generated asset inventory
- workflow-side canonical runbooks
- historical-support audit
- setup/support figure families mirrored in the article repo

### Phase 1. Canonical GDPC master-covariate reproducibility hardening

Do this before rerunning corrected Bayesian rows.

Reason:
- the large-scale climate covariate is part of the common covariate contract and should not remain an under-documented dependency when we rebuild the affected cutoffs.

### Phase 2. Full-history bundle reconstruction for affected cutoffs

Build corrected cutoff-specific shared-input bundles for:
- `2021-01-23`
- `2021-11-12`
- `2022-12-25`

Acceptance requirement:
- `inputs/shared/data_start_filter_summary.txt` must report `common_date_min=1987-05-29`

### Phase 3. Rerun the affected Bayesian rows

Rerun all affected Bayesian publication rows for the three cutoffs above.

Expected rerun count if done at the publication-row level:
- `27`

### Phase 4. Validate corrected outputs before touching the article

Require at minimum:
- `summary.json`
- `compare_report.json`
- `crps_forecast_summary.csv`
- `inputs/shared/data_start_filter_summary.txt`
- refreshed provenance manifests

### Phase 5. Refresh article-side bundles automatically

Use article-side scripts to refresh:
- setup/support bundles
- selected-model bundles
- publication snapshots if a corrected publication state is intentionally adopted
- article review reports
- generated asset inventory

### Phase 6. Update the manuscript and corrections repo intentionally

Only after corrected reruns and bundle refreshes:
- update figure/table links as needed
- update manuscript interpretations if numbers change
- update corrections text if the publication story is intentionally revised

## Article-side organization rule

From this point forward, the revised article repo should be the stable freeze point for generated assets used in manuscript work.

That means:
- every important generated family should live under `Evironmetrics---REVISED-DOC-Corrected-2/generated/`
- every family should have a README/manifest/review path when feasible
- the generated asset index should be refreshed after asset changes
- manuscript-facing `DISC/` files should always be traceable back to a generated family and manifest

## Things to avoid

Do not do these in the future repair cycle:
- overwrite current publication snapshots in place without preserving the publication-state lineage
- rerun models before PCA reproducibility is clarified
- patch manuscript figures directly without refreshing the generated bundle family first
- update corrections text before the revised article provenance state is refreshed
- mix publication-state and corrected-state results in the same manifest without explicit labels

## Operational takeaway

We now have enough structure to move carefully.

The next rerun cycle should not start with more modeling. It should start with:

1. canonical GDPC master-covariate reproducibility hardening,
2. corrected full-history bundle reconstruction for the three affected cutoffs,
3. and then controlled reruns with automatic article-side refresh.

That is the path most likely to keep the project clean, reproducible, and reversible.

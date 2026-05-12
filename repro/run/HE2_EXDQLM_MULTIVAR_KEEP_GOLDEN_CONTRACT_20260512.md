# HE2 exdqlm_multivar_keep Golden Contract

Date: 2026-05-12

## Purpose

This note freezes the first successful end-to-end proof row for the repaired `exdqlm_multivar_keep` family under the canonical shared-input and GDPC-backed relaunch workflow.

The retained row is the contract we should preserve and reuse when scaling to the remaining cutoffs.

## Authoritative successful row

- runtime root:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20210123_row_final_20260512`
- run id:
  - `multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_multivar_keep`
- manifest:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20210123_row_final_20260512/runs/multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_multivar_keep/run_manifest.yaml`
- report summary:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20210123_row_final_20260512/runs/multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_multivar_keep/report/summary.md`
- validation compare report:
  - `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20210123_row_final_20260512/runs/multimodel_20210123_v8_he2pubgdpc1r1_exdqlm_multivar_keep/validate/compare_report.json`

## Why this row matters

This row proves all of the following together:

1. the canonical shared-input relaunch stack works for `exdqlm_multivar_keep`
2. the GDPC-backed compatibility alias path is wired correctly
3. the repaired q35 path holds in a real row, not just in sidecar probes
4. the quantile-specific policy map is stable enough for full-row execution
5. the main workflow can keep the useful post/report outputs without retaining expensive fit `.RData` payloads
6. the relaunch contract must stay on `log1p_cms` end to end; the older internal `log_log1p_cms` path is no longer acceptable for current workflow runs

## Retained outputs

Keep this root because it already contains the products we need downstream:

- post outputs and manifests under `post/outputs/**`
- figures such as ELBO and observed-series diagnostics
- tables including CRPS summaries and parameter summaries
- validation outputs under `validate/**`
- final summaries under `report/**`

## Retention rule

For successful relaunch rows, the preferred contract is:

- keep:
  - `post/**`
  - `validate/**`
  - `report/**`
  - `run_manifest.yaml`
  - key logs and health files
- do not retain:
  - large fit-stage `.RData` payloads after successful `post`

This matches the current cleanup-enabled runner behavior:

- `scripts/run_unified_with_cleanup.sh`
- `scripts/unified_run.R`

## Quantile policy map frozen by this row

- `q05`: base spec
- `q20`: reduced-sigma init rescue
- `q35`: state-freeze + generic state guard/hold
- `q50`: validated median init + median hold
- `q65`: reduced-sigma init rescue
- `q80`: reduced-sigma init rescue
- `q95`: base spec

## Transform policy frozen by this row

- retrospective storage scale: `log1p_cms`
- exdqlm multivar fit internal scale: `log1p_cms`
- exdqlm multivar post internal scale: `log1p_cms`
- forecast ensemble adapters into fit/post: `log1p_cms`
- post/publication figure display scale: `log1p_cms`

Do not reintroduce `log_log1p_cms` into the current relaunch workflow.

## Next workflow use

Use this row as the policy and output contract for the all-cutoff `exdqlm_multivar_keep` relaunch batch before widening to the broader HE2 matrix.

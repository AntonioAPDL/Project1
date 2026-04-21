# Phase 3 NDLM Specification Parity Summary

Status: complete

## Audit Scope

- Built a 45-row spec matrix covering `5` cutoffs x `3` comparison groups x `3` model variants.
- Comparison groups: `univar_keep`, `multivar_drop`, `multivar_keep`.
- Each row is traced to the authoritative current HE2 source run and its `resolved_config.yaml`.

## Headline Findings

- Source-run lineage is still dominated by the older `multimodel_v8_20260402` tree: `44` of `45` rows. Only `1` row comes from the dedicated NDLM relaunch lineage.
- Deterministic climate is disabled in all authoritative Phase 3 rows (`0` enabled, `45` disabled).
- All rows share the same fit-covariate set: `ELI|ONI|PPT|SOIL|PCA`.
- The newer featurecov transfer-function blocks (`PPT/SOIL/PCA` with lags and interactions) are absent from all authoritative Phase 3 source configs: `0` of `45` rows expose `inputs.transfer_function_covariates`.
- Snapshot preference differs by lineage: `44` rows prefer the older `forecats` snapshot path, while `1` rows do not.

## NDLM-vs-Quantile Specification Notes

- NDLM main rows use `state_df_covs` values 0.9999, 0.99999999, versus 0.99999 for the multivariate quantile rows.
- NDLM main legacy fit damping pairs are (0.999999, 0.9), while the quantile rows use (1.0, 1.0). The NDLM univariate rows expose no analogous `lam1/lam2` fields in the resolved configs.
- Multivariate exDQLM / DQLM source runs expose both `drop` and `keep` through `forecast_transfer_modes`, whereas NDLM baseline rows separate `keep` and `drop` into distinct source runs.
- In the older multivariate quantile configs, the family-level default `forecast_transfer_mode` is often still `drop` even for HE2 cells that resolve to `keep`; the active `keep` interpretation comes from the compare-layer provenance plus the supported transfer-mode list, not from a keep-only config file.
- The one relaunch-backed NDLM row is `ndlm_main_keep` at cutoff `20210123`; it carries the stricter relaunch prior fields `dof_offset=4`, `scale_mult=1.0`, and `jitter=1e-08`.

## Implication For Later Phases

- Phase 4 must compare file-level inputs across these authoritative older source runs before we interpret the NDLM CRPS gap as a modeling result.
- Phase 5 must trace the NDLM main forecast-window covariance prior carefully, because the current HE2 rows mix baseline-TT NDLM runs with one relaunch-tuned NDLM row.

## Outputs

- CSV: [spec_parity_matrix.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/spec_parity_matrix.csv)

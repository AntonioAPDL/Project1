# exAL-M-T1 Discount Probe Parity Audit

This audit checks whether the completed `exAL-M-T1` discount-factor probe runs differ from the current HE2 `exAL-M-T1` row **only** in the discount-factor block.

## Main Conclusion

- The two completed probe campaigns, `Featurecov custom discount probe` and `Featurecov NDLM-tight discount probe`, are **discount-only variants of each other** for `exdqlm_multivar_keep`.
- They are **not** discount-only variants of the current HE2 `exAL-M-T1` baseline.
- Relative to the current HE2 baseline, both completed probe campaigns use the same raw parameters, retrospective series, NWS forecast, GloFAS forecast, and PCA file, but they use **different forecast-window PPT/SOIL covariate files, a different engineered covariate-feature file, and different deterministic-climate future files**.
- The first real covariate divergence starts at the forecast window, not in the historical segment.

## Pair Summary

| Pair key | Left | Right | Only-discount rows | Rows | Per-row hash diff count | Diff files |
| --- | --- | --- | --- | --- | --- | --- |
| baseline_vs_custom | Current HE2 baseline | Featurecov custom discount probe | 0 | 5 | 5 | covariates/cov_01_PPT.csv|covariates/cov_02_SOIL.csv|covariates/covariate_features.csv|deterministic_climate/deterministic_precip_future.csv|deterministic_climate/deterministic_soil_future.csv |
| baseline_vs_ndlm_tight | Current HE2 baseline | Featurecov NDLM-tight discount probe | 0 | 5 | 5 | covariates/cov_01_PPT.csv|covariates/cov_02_SOIL.csv|covariates/covariate_features.csv|deterministic_climate/deterministic_precip_future.csv|deterministic_climate/deterministic_soil_future.csv |
| custom_vs_ndlm_tight | Featurecov custom discount probe | Featurecov NDLM-tight discount probe | 5 | 5 | 0 |  |

## Cutoff-Level Baseline vs Probe Input Differences

| Cutoff | Baseline vs custom matches | Baseline vs custom diff files | First feature diff date | Baseline vs NDLM-tight matches | Baseline vs NDLM-tight diff files | First feature diff date |
| --- | --- | --- | --- | --- | --- | --- |
| 20210123 | 5 | covariates/cov_01_PPT.csv|covariates/cov_02_SOIL.csv|covariates/covariate_features.csv|deterministic_climate/deterministic_precip_future.csv|deterministic_climate/deterministic_soil_future.csv | 2021-01-24 | 5 | covariates/cov_01_PPT.csv|covariates/cov_02_SOIL.csv|covariates/covariate_features.csv|deterministic_climate/deterministic_precip_future.csv|deterministic_climate/deterministic_soil_future.csv | 2021-01-24 |
| 20211112 | 5 | covariates/cov_01_PPT.csv|covariates/cov_02_SOIL.csv|covariates/covariate_features.csv|deterministic_climate/deterministic_precip_future.csv|deterministic_climate/deterministic_soil_future.csv | 2021-11-13 | 5 | covariates/cov_01_PPT.csv|covariates/cov_02_SOIL.csv|covariates/covariate_features.csv|deterministic_climate/deterministic_precip_future.csv|deterministic_climate/deterministic_soil_future.csv | 2021-11-13 |
| 20211221 | 5 | covariates/cov_01_PPT.csv|covariates/cov_02_SOIL.csv|covariates/covariate_features.csv|deterministic_climate/deterministic_precip_future.csv|deterministic_climate/deterministic_soil_future.csv | 2021-12-22 | 5 | covariates/cov_01_PPT.csv|covariates/cov_02_SOIL.csv|covariates/covariate_features.csv|deterministic_climate/deterministic_precip_future.csv|deterministic_climate/deterministic_soil_future.csv | 2021-12-22 |
| 20220511 | 5 | covariates/cov_01_PPT.csv|covariates/cov_02_SOIL.csv|covariates/covariate_features.csv|deterministic_climate/deterministic_precip_future.csv|deterministic_climate/deterministic_soil_future.csv | 2022-05-12 | 5 | covariates/cov_01_PPT.csv|covariates/cov_02_SOIL.csv|covariates/covariate_features.csv|deterministic_climate/deterministic_precip_future.csv|deterministic_climate/deterministic_soil_future.csv | 2022-05-12 |
| 20221225 | 5 | covariates/cov_01_PPT.csv|covariates/cov_02_SOIL.csv|covariates/covariate_features.csv|deterministic_climate/deterministic_precip_future.csv|deterministic_climate/deterministic_soil_future.csv | 2022-12-26 | 5 | covariates/cov_01_PPT.csv|covariates/cov_02_SOIL.csv|covariates/covariate_features.csv|deterministic_climate/deterministic_precip_future.csv|deterministic_climate/deterministic_soil_future.csv | 2022-12-26 |

## Interpretation

- The completed probes are a clean discount-only comparison **with each other**.
- They are **not** a clean discount-only comparison against the current HE2 `exAL-M-T1` row.
- So the earlier CRPS comparison showing that neither completed probe beats the HE2 row is still useful operationally, but it is **confounded** if interpreted as a pure discount-factor sensitivity test relative to the current HE2 baseline.

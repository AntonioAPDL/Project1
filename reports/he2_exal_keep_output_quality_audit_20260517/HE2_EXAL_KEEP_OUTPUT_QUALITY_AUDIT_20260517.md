# HE2 exAL Keep Output Quality Audit (2026-05-17)

## Purpose

This audit checks whether the weird-looking `exAL-M-T1` synthesis figures in the revised doc are caused by stale article wiring or by the current keep rerun outputs themselves.

## Executive Conclusion

- Representative article figure synced to runtime output: `True`.
- Representative keep quality class: `extreme_run_side_issue`.
- Representative keep mean CRPS: `162225957192096.5`.
- Representative keep `q95 / observed_max` ratio: `1.7684e+16`.
- All five cutoffs severe-or-worse: `True`.
- Primary interpretation: the article is synced to the latest keep outputs, and the current keep outputs themselves are numerically implausible.

## Cutoff Matrix

| Cutoff | Synth mean CRPS | GloFAS mean CRPS | NWS mean CRPS | Observed max | q50 max | q80 max | q95 max | q80/obs max | q95/obs max | Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2021-01-23 | 114729517528.2864 | 0.5379 | 2.6668 | 3.3408 | 2.0977 | 2.6542e+11 | 1.0093e+14 | 7.9450e+10 | 3.0212e+13 | `extreme_run_side_issue` |
| 2021-11-12 | 127128551.1975 | 1.5664 | 0.0968 | 3.0992 | 8.2878 | 4.4415e+08 | 5.9084e+11 | 1.4331e+08 | 1.9064e+11 | `extreme_run_side_issue` |
| 2021-12-21 | 600958851676.8989 | 1.7757 | 1.8160 | 4.4372 | 69.1300 | 6.7294e+11 | 4.4342e+14 | 1.5166e+11 | 9.9933e+13 | `extreme_run_side_issue` |
| 2022-05-11 | 4725868148.3834 | 2.0301 | 0.7329 | 0.8291 | 3.8174 | 4.5009e+09 | 2.5702e+12 | 5.4287e+09 | 3.1000e+12 | `extreme_run_side_issue` |
| 2022-12-25 | 162225957192096.5000 | 2.9297 | 1.6609 | 5.3644 | 37.1078 | 3.4768e+14 | 9.4864e+16 | 6.4812e+13 | 1.7684e+16 | `extreme_run_side_issue` |

## Interpretation

- This is **not** primarily an article-staleness problem: the representative manuscript figure matches the current runtime PNG exactly.
- The current keep synthesis quantiles are already pathological in the underlying CSVs, with massive `q80`/`q95` inflation relative to observed values.
- Therefore the keep-family issue should be investigated as a run-side/post-side model-output problem after the historical-support renderer is fixed.

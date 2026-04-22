# NDLM Numeric Reaudit Checks

## Kalman Congruence

- NDLM R vs univariate Gaussian backbone max fitted-mean diff: `0.0000000001`
- NDLM R vs univariate Gaussian backbone max smooth-cov diff: `0.0000000010`
- NDLM R vs NDLM cpp max smooth-cov diff: `0.0000000000`

## Sigma-Mixing Replay

- Smoke-run sigma row means (`usgs`, `nws`, `glofas`): `0.018317`, `0.878655`, `8.646275`
- Pre-fix replay q99.9 / max: `2067.945949` / `7365.636641`
- USGS-only replay q99.9 / max: `1.031747` / `1.100605`
- Explosion ratio (bug over fix): q99.9=`2004.315515`, max=`6692.354087`

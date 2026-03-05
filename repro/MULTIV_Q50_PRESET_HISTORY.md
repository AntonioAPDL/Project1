# Multiv exDQLM q=0.50 Preset History

This file records parameter presets used for isolated multivariate exDQLM median runs.

| Timestamp (UTC) | Config | `initial_delta = [df_t, df_s1, df_s2, df_s67, df_discrep, lambda]` | `[df_trans, df_covs]` | `forecast_cov.c_factor` | `gamma_sigma.max_iter` | `dates.data_start` | Notes |
|---|---|---|---|---:|---:|---|---|
| 2026-02-27 | `config/unified_runs/diag_multiv_only_legacy_bridge_q50_customdelta_20260227.yaml` | `[0.99997, 0.99997, 0.99997, 0.99997, 0.99997, 0.8995]` | `[0.99999999, 0.99999999]` | `100` (default) | `800` (stage default) | `2010-01-01` | Previous baseline |
| 2026-02-27 | `config/unified_runs/diag_multiv_only_legacy_bridge_q50_customdelta_r03_20260227_lambda097_iter100_fullhistory.yaml` | `[0.99997, 0.99997, 0.99997, 0.99997, 0.99997, 0.97]` | `[0.99999999, 0.99999999]` | `100` (default) | `100` | `1987-05-01` | Full-history + lambda update |
| 2026-02-27 | `config/unified_runs/diag_multiv_only_legacy_bridge_q50_customdelta_r04_20260227_lambda097_iter100_fullhistory_cfactor1.yaml` | `[0.99997, 0.99997, 0.99997, 0.99997, 0.99997, 0.97]` | `[0.99999999, 0.99999999]` | `1` | `100` | `1987-05-01` | Full-history + lambda update + `c_factor=1` |
| 2026-02-27 | `config/unified_runs/diag_multiv_only_legacy_bridge_q50_customdelta_r06_20260227_lambda097_iter100_fullhistory_cfactor1.yaml` | `[0.99997, 0.99997, 0.99997, 0.99997, 0.99997, 0.97]` | `[0.99999999, 0.99999999]` | `1` | `100` | `1987-05-01` | Active background rerun (`setsid` launch) |
| 2026-02-27 | `config/unified_runs/diag_multiv_only_legacy_bridge_q50_customdelta_r07_20260227_lambda097_iter040_freeze05_cfactor1.yaml` | `[0.99997, 0.99997, 0.99997, 0.99997, 0.99997, 0.97]` | `[0.99999999, 0.99999999]` | `1` | `40` | `1987-05-01` | Next-run preset (`warmup_freeze_iters=5`) |
| 2026-02-27 | `config/unified_runs/diag_multiv_only_legacy_bridge_q50_customdelta_r08_20260227_lambda097_iter040_freeze05_dfset2.yaml` | `[0.9997, 0.9997, 0.9997, 0.9997, 0.99, 0.97]` | `[0.99999999, 0.99999999]` | `1` | `40` | `1987-05-01` | Active next run with updated discount factors |
| 2026-02-27 | `config/unified_runs/diag_multiv_only_legacy_bridge_q50_customdelta_r09_20260227_lambda097_iter040_freeze05_dfset3.yaml` | `[0.99997, 0.9997, 0.9997, 0.99997, 0.999, 0.97]` | `[0.99999999, 0.99999999]` | `1` | `40` | `1987-05-01` | Active next run after r08 fit failure |

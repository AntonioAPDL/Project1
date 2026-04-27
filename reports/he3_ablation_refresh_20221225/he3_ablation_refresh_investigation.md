# HE3 `20221225` Refresh Investigation

## Executive Conclusion

Yes, a focused HE3 relaunch for cutoff `20221225` makes sense.

The original HE3 ablation study remains coherent for `20210123`, `20211112`,
`20211221`, and `20220511`, because those full-reference rows still match the
current published HE2 `exAL-M-T1` winners exactly.

The only cutoff that moved is `20221225`, where the published HE2 winner now
comes from the exact-input discount-grid refinement rather than from the earlier
`featurecov_cf1_eps` sweep.

## What Changed

Original HE3 full reference at `20221225`:

- run id:
  `multimodel_20221225_v8_eps360cf1_exdqlm_multivar_keep_featurecov_cf1`
- mean CRPS:
  `0.6143974397227375`

Current published HE2 full reference at `20221225`:

- run id:
  `multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep`
- mean CRPS:
  `0.4375250570387207`

## What Stayed the Same

The old and new full-reference runs share the same scientific input contract.

Confirmed invariant:

- retrospective input
- raw `nws` forecast
- raw `glofas` forecast
- `PPT` covariate file
- `SOIL` covariate file
- `PCA` covariate file
- `covariate_features.csv`
- `deterministic_precip_future.csv`
- `deterministic_soil_future.csv`
- fit covariate contract `PPT|SOIL|PCA`
- lags `1|2|3`
- squares enabled
- interaction enabled
- deterministic climate enabled
- transfer mode `keep`
- likelihood `exal`

## What Changed Scientifically

The scientific difference is the full-model state-evolution discount block.

Older full reference:

```json
{"df_covs":0.99999,"df_discrep":0.999,"df_s1":0.9999,"df_s2":0.9999,"df_s67":0.9999,"df_t":0.99999999,"df_trans":0.9999999,"lambda":0.97}
```

Current published full reference:

```json
{"df_covs":0.9999999,"df_discrep":0.998,"df_s1":0.9998,"df_s2":0.9998,"df_s67":0.9999,"df_t":0.99999999,"df_trans":0.9999999,"lambda":0.97}
```

So the refresh is not about a new covariate regime or a new blended forecast.
It is specifically about carrying the updated published full-model discount block
through the structural ablations at this cutoff.

## Coherence Decision

The coherent refresh scope is:

- cutoff: `20221225` only
- reused full row: `1`
- launched ablation rows: `5`

This yields a `6`-row focused refresh instead of rerunning the full `30`-row HE3
campaign.

## Efficiency Decision

The refresh template fixes each launched quantile model to:

- `fit.parallel.workers = 1`
- `run.threads.mc_cores = 1`

This keeps the launch efficient and controlled while still allowing up to `4`
simultaneous launched rows in the queue.

## Tooling Readiness

The shared HE3 builder / validator now support:

- cutoff filtering
- explicit source-run overrides
- focused validation for non-30-row campaigns

The dedicated refresh template is:

- [config/multimodel_v8_he3_exdqlm_ablation_20221225_refresh.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_he3_exdqlm_ablation_20221225_refresh.template.yaml)

The focused workflow is:

- [HE3_EXDQLM_ABLATION_20221225_REFRESH_WORKFLOW.md](/data/muscat_data/jaguir26/project1_ucsc_phd/repro/run/HE3_EXDQLM_ABLATION_20221225_REFRESH_WORKFLOW.md)

## Practical Recommendation

Run the focused `20221225` refresh, rebuild the HE3 summary, and update the
corrections repo only if the refreshed ablation values materially change the
reported table or the associated interpretation.

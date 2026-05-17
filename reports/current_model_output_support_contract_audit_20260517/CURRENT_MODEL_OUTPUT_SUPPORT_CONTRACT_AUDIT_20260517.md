# Current-Model Output Support Contract Audit

Date: 2026-05-17

## Summary

- status: `repaired_via_retained_support_contract`
- multivariate corrected run root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep`
- historical-support replay root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_historical_support_replay_20260517/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep_historical_support_replay`
- univariate reference output root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_all_cutoffs_sharedspec_20260516/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_univar/post/outputs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_univar`

## Findings

- missing corrected multivariate fit-cache artifacts: `7`
- retained support replay fit contract present: `True`
- retained state summary present: `True`
- univariate reference synthesis PNG present: `True`
- latest refresh status: `ok`
- latest refresh return code: `0`
- latest historical-support render mode: `rendered_from_historical_support_replay`

Missing fit-cache artifacts:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep/fit/exdqlm_multivar/keep/q=05/outputs/DISC_variables_5_exAL_synth_DISC.RData`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep/fit/exdqlm_multivar/keep/q=20/outputs/DISC_variables_20_exAL_synth_DISC.RData`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep/fit/exdqlm_multivar/keep/q=35/outputs/DISC_variables_35_exAL_synth_DISC.RData`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep/fit/exdqlm_multivar/keep/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep/fit/exdqlm_multivar/keep/q=65/outputs/DISC_variables_65_exAL_synth_DISC.RData`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep/fit/exdqlm_multivar/keep/q=80/outputs/DISC_variables_80_exAL_synth_DISC.RData`
- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_all_cutoffs_sharedspec_20260516/runs/multimodel_20220511_v8_he2pubgdpc1r1_exdqlm_multivar_keep/fit/exdqlm_multivar/keep/q=95/outputs/DISC_variables_95_exAL_synth_DISC.RData`

## Decision

- the corrected article refresh should continue to treat setup/support, forecast-context, and synthesis families as authoritative
- the historical-support rebuild should use a retained corrected artifact contract rather than implicitly requiring fit caches to still exist in the canonical workflow root
- the retained support replay/state-summary contract is now in place and the article-side historical-support bundle is refreshed from it

## Next repair step

- no further contract repair is needed; future refreshes should reuse the retained state-summary artifact or the retained support replay root

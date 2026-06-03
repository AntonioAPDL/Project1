# HE2 AL-M-T0 Blocked Diagnostic Plan

Date: 2026-06-03

## Current Decision

`AL-M-T0` / `dqlm_multivar_al_drop` is **blocked**, not promoted. The 2026-06-03 paired AL clone of the promoted
current-code `exAL-M-T0` drop package completed data preparation but failed the fit-stage gate for all five cutoffs.
No broad relaunch should be started until we either:

1. confirm a new AL-specific discount/epsilon/c_factor specification, or
2. prove from targeted diagnostics that the root problem is code-side numerical/PSD handling rather than the cloned
   scientific spec.

The completed `AL-U-T1` and `exAL-U-T1` rows are separate: those univariate relaunches passed fit/post/validate/report
and should be treated as promotable canonical-bundle rows.

## Evidence Summary

Target root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_from_exal_drop_20260603`

Source root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602`

The source `exAL-M-T0` package is healthy across all five cutoffs and seven quantiles. The AL clone uses the same
input bundle, source structure, transfer-drop contract, epsilon, c_factor, discount factors, and max_iter, with the
intended scientific change `likelihood_mode: exal -> al`.

Observed AL clone failures:

| cutoff | failing lanes | failure signature |
|---|---|---|
| `20210123` | `q35`, `q65` | forecast-health `max_E_sigma` over limit |
| `20211112` | `q35` | post-save `chol(G)` non-positive-definite |
| `20211221` | `q35`, `q80` | `max_E_sigma` over limit; q80 huge state/forecast values |
| `20220511` | `q65` | forecast-health `max_E_sigma=450.658284` |
| `20221225` | `q20`, `q35`, `q65`, `q80` | `chol(G)` non-PD, sigma explosions, forecast `mvrnorm` non-PD |

Code-level gates:

- forecast-health construction and limits: `R/unified/stages/stage_fit.R`
- post-fit fail-fast gate: `R/unified/stages/stage_fit.R`
- forecast MVN sampler: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`
- objective derivative Cholesky path: `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`

## Discount-Factor Decision

Yes, we probably need a new AL-specific spec before any meaningful relaunch. The failed AL clone reused the exAL-M-T0
drop spec exactly, but AL mode removes the `s_t/gamma` contribution and changes the identifiability/numerical behavior
of the same state-space system. A direct exAL-to-AL spec clone is therefore a clean scientific comparison, but the
runtime evidence says it is not stable enough to promote as-is.

The next run should not be a broad production relaunch. It should be a targeted diagnostic using either:

- a confirmed new AL-M-T0 discount/epsilon/c_factor spec from the user, or
- the current failed clone spec only as a control lane.

The tracked placeholder is:

`config/he2_relaunch_batches/al_m_t0_diagnostic_discount_spec_template_20260603.yaml`

## Confirmed Candidate Spec

The current confirmed diagnostic candidate is:

`config/he2_relaunch_batches/al_m_t0_diagnostic_highdf_eps365_cf1_20260603.yaml`

This spec uses:

| parameter | value |
|---|---:|
| `df_t` | `0.99999999` |
| `df_s1` | `0.99999999` |
| `df_s2` | `0.99999999` |
| `df_s67` | `0.99999999` |
| `df_discrep` | `0.99999999` |
| `lambda` | `0.97` |
| `df_trans` | `0.99999999` |
| `df_covs` | `0.99999999` |
| `epsilon` | `365.0` |
| `c_factor` | `1.0` |
| `max_iter` | `100` |

Interpretation: this is the right next diagnostic move, but it is not yet the right broad production move. The spec
tests whether the blocked `AL-M-T0` failures are caused by the direct exAL-to-AL clone being too dynamically loose for
the AL likelihood, while preserving the same input bundles and the same transfer-drop model family. The discrepancy
discount is also set to `0.99999999` so the diagnostic does not leave one state block at the failed clone setting.

Recommended staged launch order:

1. Prepare and inspect no-launch representative diagnostics: four single-quantile lanes covering the main failure
   signatures.
2. If the representative lanes are healthy, launch those four lanes only with retained fit objects and trace outputs.
3. If those pass, prepare/launch the ten failed lanes only.
4. If all failed lanes pass, relaunch all five cutoffs and seven quantiles for `AL-M-T0`.
5. Promote `AL-M-T0` only after fit, post, validate, report, CRPS tables, component summaries, diagnostic plots, and
   cleanup pass on the full relaunch.

Do not launch all five cutoffs and seven quantiles first. That would use more cores and disk while providing less
diagnostic information if the first representative lanes still expose a code-side PSD or scale issue.

## No-Launch Diagnostic Package

New tracked builder:

`scripts/build_he2_dqlm_multivar_al_drop_diagnostic_plan.py`

New tracked validator:

`scripts/validate_he2_dqlm_multivar_al_drop_diagnostic_plan.py`

The package prepares single-quantile, fit-only configs and deliberately writes a `NO_LAUNCH_GUARD.txt` instead of a
launch script. It preserves diagnostics/RData if the configs are later launched manually or by an explicitly approved
queue. This is intentional: the next AL-M-T0 diagnostic needs retained failed objects, not automatic cleanup.

Representative lanes:

| cutoff | q | reason |
|---|---:|---|
| `20211112` | `35` | post-save `chol(G)` non-PD |
| `20211221` | `80` | huge state/forecast and sigma explosion |
| `20220511` | `65` | clean single-lane sigma explosion |
| `20221225` | `80` | forecast `mvrnorm` non-PD |

All failed lanes can also be prepared with `--lane-scope all_failed`.

## Commands That Do Not Launch

Prepare representative diagnostics using the current failed spec as a control:

```bash
python3 scripts/build_he2_dqlm_multivar_al_drop_diagnostic_plan.py --lane-scope representative
```

Validate the no-launch package:

```bash
python3 scripts/validate_he2_dqlm_multivar_al_drop_diagnostic_plan.py --lane-scope representative
```

Prepare diagnostics after filling a confirmed discount spec:

```bash
python3 scripts/build_he2_dqlm_multivar_al_drop_diagnostic_plan.py \
  --lane-scope representative \
  --discount-spec-yaml config/he2_relaunch_batches/al_m_t0_diagnostic_discount_spec_template_20260603.yaml
```

Do not run any generated config until the discount/epsilon/c_factor values are confirmed.

Prepare the confirmed high-discount representative diagnostics without launching:

```bash
python3 scripts/validate_he2_dqlm_multivar_al_drop_diagnostic_plan.py \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_diagnostics_highdf_eps365_cf1_representative_20260603 \
  --lane-scope representative \
  --discount-spec-yaml config/he2_relaunch_batches/al_m_t0_diagnostic_highdf_eps365_cf1_20260603.yaml
```

Prepare the confirmed high-discount all-failed-lane diagnostics without launching:

```bash
python3 scripts/validate_he2_dqlm_multivar_al_drop_diagnostic_plan.py \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_diagnostics_highdf_eps365_cf1_allfailed_20260603 \
  --lane-scope all_failed \
  --discount-spec-yaml config/he2_relaunch_batches/al_m_t0_diagnostic_highdf_eps365_cf1_20260603.yaml
```

Both commands are validators/builders only. They write config matrices and `NO_LAUNCH_GUARD.txt`; they do not create or
run a launch shell.

## Next Implementation Steps

1. Promote the completed univariate AL/exAL rows into the publication manifest and parity gate.
2. Keep `AL-M-T0` out of promotion; record it as blocked pending targeted diagnostics.
3. Use the confirmed high-discount `epsilon=365`, `c_factor=1`, `max_iter=100` spec as the first AL-M-T0 diagnostic
   candidate.
4. Build and validate the no-launch representative and all-failed diagnostic packages.
5. Only after explicit approval, launch the representative diagnostic lanes with retained failed objects.
6. Use those retained objects to decide whether the fix is a spec retune, PSD-safe covariance handling, or both.
7. Relaunch all five `AL-M-T0` cutoffs only after the targeted lanes pass.

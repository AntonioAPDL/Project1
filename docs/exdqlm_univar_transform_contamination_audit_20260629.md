# exDQLM Univariate Transform Contamination Audit

Date: 2026-06-29

## Scope

This audit checks whether the current retained univariate quantile workflow
(`exdqlm_univar`, manuscript label `exAL-U-T1`) is fitted on the intended
`log1p_cms` scale or whether it accidentally reintroduced the old
`log_log1p_cms` scale.

The immediate symptom was that the univariate fits looked shifted downward
relative to the current `log1p(flow)` figures.

## Contract

The current publication relaunch contract is `log1p_only`:

- shared retrospective input is stored on `log1p_cms`;
- raw NWS and GloFAS forecast inputs are adapted to `log1p_cms`;
- model fit internals are declared as `analysis_scale_fit_internal: log1p_cms`;
- post-processing internals are declared as `analysis_scale_post_internal: log1p_cms`.

For the retained 2022-12-25 univariate run, the generated config says:

- `legacy_fit_input_scale: log1p_cms`;
- `analysis_scale_fit_internal: log1p_cms`;
- `analysis_scale_post_internal: log1p_cms`;
- `transform_policy: log1p_only`;
- `implementation_mode: legacy_bridge`.

Representative config:
`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_authoritative_retained_20260628/control/generated_configs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_univar.yaml`

## Root Cause

Confirmed. The retained legacy-bridge univariate script still applied an
additional `log()` to inputs that the unified adapters had already placed on
`log1p_cms`.

Before this patch, [OptimalModelSLexAL.r](/data/muscat_data/jaguir26/project1_ucsc_phd/OptimalModelSLexAL.r:988) had the following contaminated ingress points:

- NWS forecast members: hard-coded `log(nws_forecast[,-1])`;
- GloFAS forecast members: hard-coded `log(glofas_forecast[,-1])`;
- historical USGS response: hard-coded `log(Y)`.

This means the legacy fit consumed `log(log1p(cms))` values while the unified
run config and post-processing contract described the objects as `log1p_cms`.

## Runtime Evidence

Retained run inspected:
`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_authoritative_retained_20260628/runs/multimodel_20221225_v8_he2pubgdpc1r1_exdqlm_univar`

The q50 retained object was compared against the run-scoped
`fit/inputs/retros_fit_adapter.csv`:

| Check | Value |
|---|---:|
| median abs(`theta.out$exps - adapter USGS log1p`) | 1.313493 |
| median abs(`theta.out$exps - log(adapter USGS log1p)`) | 0.169112 |
| corr(`theta.out$exps`, adapter USGS log1p) | 0.906609 |
| corr(`theta.out$exps`, `log(adapter USGS log1p)`) | 0.929022 |

Untracked evidence files:

- `reports/exdqlm_univar_transform_contamination_audit_20260629/README.md`
- `reports/exdqlm_univar_transform_contamination_audit_20260629/q50_runtime_scale_evidence.csv`

Interpretation: this is a fit-scale contamination, not merely a plotting
artifact. The saved posterior state locations are much closer to the
unintended log-log transform than to the declared log1p scale.

## Patch

The fix makes the legacy univariate runner scale-aware instead of hard-coding
ad hoc transforms:

- added [R/unified/univar_legacy_scale_contract.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/univar_legacy_scale_contract.R:1);
- wired [OptimalModelSLexAL.r](/data/muscat_data/jaguir26/project1_ucsc_phd/OptimalModelSLexAL.r:49) to resolve the explicit legacy univariate scale contract;
- replaced the NWS, GloFAS, and USGS response transforms with
  `univar_legacy_transform_flow_*` calls;
- exported `UNIFIED_LEGACY_FIT_INPUT_SCALE`,
  `UNIFIED_ANALYSIS_SCALE_FIT_INTERNAL`, and `UNIFIED_TRANSFORM_POLICY` into
  the univariate subprocess in
  [R/unified/stages/stage_fit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/stages/stage_fit.R:1827).

Under `transform_policy: log1p_only`, the bridge fails closed if a legacy
univariate run requests a non-`log1p_cms` internal scale.

## Validation

Focused tests passed:

```text
python3 -m unittest tests.python.test_log1p_transform_policy tests.python.test_environmetrics_scale_contract_source_contract -v
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_univar_legacy_scale_contract.R')"
python3 -m py_compile scripts/build_he2_bayesian_publication_relaunch_configs.py
```

The test coverage now includes:

- no-op behavior for `log1p_cms -> log1p_cms`;
- explicit `raw_cms -> log1p_cms` conversion;
- matrix-shape preservation for the historical response matrix;
- date-column exclusion for forecast member frames;
- fail-closed behavior for `log_log1p_cms` under `log1p_only`;
- source-level regression checks that the old hard-coded `log()` lines do not
  return.

## Contamination Scope

Known affected outputs:

- retained legacy-bridge `exdqlm_univar` runs produced before this patch,
  including
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_univar_authoritative_retained_20260628`;
- any pre-patch `dqlm_univar_al` run that used the same
  `models.exdqlm_univar.implementation_mode: legacy_bridge` runner.

Not affected by this specific defect:

- `exdqlm_multivar_keep` / `exdqlm_multivar_drop` paths that already use the
  scale-aware `R/environmetrics/10_data_inputs.R` bridge;
- theory-aligned univariate runs through `scripts/run_exdqlm_univar.R`, which
  read `inputs$y` directly from the adapter scale.

## Required Next Step

Do not promote the current retained univariate legacy-bridge outputs as
authoritative. They need to be rerun after this patch before updating any
univariate CRPS rows, univariate synthesis figures, or component diagnostics.

The rerun should use the same canonical shared input bundles and current
publication specs, but now the fit will consume `log1p_cms` consistently from
adapter to state to post-processing.

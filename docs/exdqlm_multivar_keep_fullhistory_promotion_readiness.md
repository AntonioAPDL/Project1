# exDQLM Multivariate Keep Full-History Promotion Readiness

Date: 2026-05-22

Scope: prepare, but do not launch, the next representative HE2 `exdqlm_multivar_keep` run for cutoff
`2022-12-25` using full history, all seven quantiles, full transfer covariates, full harmonics, and the guarded
`log1p_cms` promotion profile established by the audit.

## Status

The audit repair branch was pushed before this readiness pass. This pass closes the promotion gap between the
isolated guarded reproduction launcher and the main HE2 relaunch workflow:

- isolated audit launcher already exported latent and pseudo-data guard environment variables:
  `repro/audits/prepare_exdqlm_keep_guarded_repro.py`;
- active runner consumes those variables:
  `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`;
- main unified fit stage now maps YAML config to the same runner variables:
  `R/unified/stages/stage_fit.R`;
- unified config defaults and validation now include the promoted guard controls:
  `R/unified/config.R`;
- no production run was stopped, relaunched, or modified while preparing this package.

## Target Contract

The no-launch promotion package is:

- template:
  `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_20221225_fullhistory_promotion_20260522.template.yaml`;
- batch:
  `config/he2_relaunch_batches/exdqlm_multivar_keep_20221225_fullhistory_promotion_20260522.yaml`;
- new isolated artifact root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_20221225_fullhistory_promotion_20260522`.

The intended generated run contract is:

| field | promoted value | rationale |
| --- | --- | --- |
| cutoff | `2022-12-25` | representative HE2 exAL-M-T1 cutoff |
| history start | `1987-05-29` | canonical publication relaunch helper pins `DEFAULT_DATA_START` and builder writes `dates.data_start` |
| quantiles | `0.05, 0.20, 0.35, 0.50, 0.65, 0.80, 0.95` | full seven-lane quantile workflow |
| transform | `log1p_cms` with `transform_policy: log1p_only` | current target after loglog1p -> log1p repair |
| input bundle | `multimodel_v8_he2_publication_shared_inputs_20260510`, run id `20260510_publication_shared_r01` | canonical shared parameters, retros, NWS, GLOFAS, and covariates |
| covariates | `PPT`, `SOIL`, `PCA` where `PCA` is the canonical GDPC1 alias | builder debug contract is `PPT|SOIL|PCA(alias=GDPC1)` |
| engineered transfer terms | `PPT_sq`, `SOIL_sq`, `PPT_x_SOIL`, `PPT_lag1:3`, `SOIL_lag1:3` | full transfer function used by the representative source config |
| harmonics | `enabled_harmonic_indices: [1, 2, 3]` | full harmonic state, not reduced h1-only diagnostic |
| discount spec | set09: `df_t=0.99999999`, `df_s1=df_s2=0.9998`, `df_s67=0.9999`, `df_discrep=0.998`, `lambda=0.97`, `df_trans=df_covs=0.9999999` | matches the selected representative source metadata |
| Wishart forecast prior | `epsilon=360.0`, `c_factor=1.0` | selected source metadata records `eps360cf1` for the 2022-12-25 representative |
| VB max iterations | `3000` | matches the successful guarded promotion reproduction, replacing older `100`/`200` relaunch specs |
| latent guard | `latent_ablation.mode: cap_e_inv_u`, `e_inv_u_cap: 5000` | explicit audited cap on `E[1/u_t]`, not a silent default |
| pseudo-data guard | enabled, mode `fail`, caps `FFF=1000`, `QQQ_diag=10000`, `E[1/u]=5000` | fail-fast protection against the audited pseudo-data feedback loop |
| state guard | enabled, start iter `1000`, cap `1e6`, refreeze/hold `20` | delayed guard profile that passed promotion v2 |
| terminal sampling guard | `fail_fast`, lag `20`, require frozen | prevents sampling from a recently guarded/failing terminal fit |

## Why This Is The Right Promotion Package

The older reduced-spec runs were intentionally narrower: many used `data_start=2017-01-01`, h1-only harmonics, PPT-only
transfer, and a reduced discount profile. They were useful for diagnosis, but they are not the representative
full-history publication contract.

The publication representative config for `2022-12-25` points to `set09` and `eps360cf1` metadata in
`config/unified_runs_publication_replay_representatives_20260506/20221225_exal_m_t1/multimodel_20221225_v8_exalm_t1_discount_grid_exact_v1_set09_exdqlm_multivar_keep.yaml`.
The new batch intentionally keeps that representative scientific spec while adding only the audited numerical
guardrails and raising VB iterations to the tested `3000`.

## Promotion Gap Closed

Before this readiness pass, the only way to reproduce the successful promotion-v2 profile was through wrapper-level
environment exports. That was too fragile for the main HE2 workflow because a generated HE2 config could look
promotion-ready while silently missing:

- `DISC_LATENT_ABLATION_MODE`;
- `DISC_LATENT_E_INV_U_CAP`;
- `DISC_PSEUDODATA_GUARD_*`;
- `DISC_GAMSIG_STATE_GUARD_START_ITER`.

The main fit stage now exports those from YAML, and config validation rejects invalid modes, nonpositive caps, and
invalid delayed state-guard starts.

## Required No-Launch Checks

Before any launch command is allowed, run only static/build checks:

1. Parse and validate edited R code:
   `Rscript --vanilla -e "parse('R/unified/config.R'); parse('R/unified/stages/stage_fit.R')"`
2. Validate config guard schema:
   `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_config_mode_resolution.R')"`
3. Validate source contract mapping:
   `python3 -m unittest tests.python.test_disc_sampling_diagnostics_source_contract -v`
4. Validate the new template/batch package:
   `python3 -m unittest tests.python.test_he2_publication_relaunch_template -v`
5. Validate the builder creates the expected generated config in a temporary root:
   `python3 -m unittest tests.python.test_he2_publication_relaunch_builder_selection.HE2PublicationRelaunchBuilderSelectionTests.test_exdqlm_fullhistory_promotion_batch_builds_guarded_20221225_config -v`
6. Run `git diff --check`.

These checks do not launch the model or touch the older live run roots.

## Launch-Readiness Boundary

After the static tests pass, we are ready for a generated-config and prelaunch-review step, not for an automatic
production relaunch. The next manual step should be a no-launch builder invocation to materialize the generated YAML
under the new isolated artifact root, then a prelaunch audit of:

- generated `dates.data_start == 1987-05-29`;
- generated input paths under the canonical 20260510 shared bundle;
- covariate names exactly `PPT`, `SOIL`, `PCA`;
- full transfer-feature list and full harmonic list;
- set09 discounts and `epsilon=360.0`, `c_factor=1.0`;
- guard controls in generated YAML;
- old live roots absent from the generated run root.

Only after that review should the launcher be considered.

## Validation Completed

The following no-launch checks were run while preparing this package:

- `Rscript --vanilla -e "invisible(parse('R/unified/config.R')); invisible(parse('R/unified/stages/stage_fit.R'))"`
  passed.
- `Rscript --vanilla -e "testthat::test_file('tests/testthat/test_config_mode_resolution.R')"` passed with
  49 expectations.
- `python3 -m unittest tests.python.test_disc_sampling_diagnostics_source_contract -v` passed with 6 tests.
- `python3 -m unittest tests.python.test_he2_publication_relaunch_template -v` passed with 19 tests.
- `python3 -m unittest tests.python.test_he2_publication_relaunch_builder_selection.HE2PublicationRelaunchBuilderSelectionTests.test_exdqlm_fullhistory_promotion_batch_builds_guarded_20221225_config -v`
  passed.

These checks built only temporary test artifacts and did not launch a model fit.

## Remaining Risks

The algorithmic failure mechanism is now controlled in the tested q05/q35/q50/q95 promotion-v2 reproduction, but the
full seven-lane full-history/full-spec package has not yet been run end to end. The main residual risks are:

- q95 still showed a large negative terminal gamma in promotion v2, so `sigma/gamma` damping/refreeze remains the
  most important next numerical improvement;
- q20/q65/q80 were not part of the final promotion-v2 runtime evidence set;
- full transfer and full harmonics increase identifiability pressure compared with reduced h1/PPT diagnostics;
- the `E[1/u_t]` cap is a deliberate numerical intervention and must remain named, monitored, and documented.

Therefore the package is ready for no-launch prelaunch validation. It is not evidence that all calibration or tail-lane
scientific behavior is solved.

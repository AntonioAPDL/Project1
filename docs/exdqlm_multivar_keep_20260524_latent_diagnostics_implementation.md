# exDQLM Multivar Keep Latent Diagnostics Implementation

Date: 2026-05-29

Status: implemented and statically prepared. No production or legacy run was stopped, relaunched, or modified.

## Purpose

This implements the first no-run portion of
[`exdqlm_multivar_keep_20260524_latent_diagnostic_plan.md`](exdqlm_multivar_keep_20260524_latent_diagnostic_plan.md):
add enough default-off instrumentation to identify the first unstable quantity in the remaining 20260524 q20 failures,
without changing ordinary grid behavior.

The concrete diagnostic target is the failure family where `E[u_t]` and `FFF` breach hard pseudo-data guards while the
promoted `E[1/u_t]` cap reports zero capped cells. The new evidence must distinguish:

1. latent GIG moment degeneracy,
2. source-specific `gamma/sigma` jumps,
3. pseudo-data denominator/offset blow-up,
4. state feedback,
5. forecast-member bookkeeping,
6. sampling-only walltime failures.

## Implemented Code Changes

| area | file | implementation |
| --- | --- | --- |
| default-off config | `R/unified/config.R` | added `fit.exdqlm_multivar.diagnostics.latent` and validated `enabled`, `report_dir`, `top_k`, `write_iteration_summary`, `write_top_cells` |
| latent sensitivity modes | `R/unified/config.R`; `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r` | added explicit diagnostic modes `cap_e_u_and_e_inv_u` and `freeze_on_e_u_guard`; production default remains `free`, grid configs can still use `cap_e_inv_u` |
| fit env wiring | `R/unified/stages/stage_fit.R` | exports `DISC_W_LATENT_DIAG_*`, `DISC_LATENT_E_U_CAP`, and diagnostic report paths per q-lane |
| dates for diagnostics | `R/disc_w/03_covariates_standardize.R` | returns history and forecast dates so top-cell diagnostics can carry date context |
| latent update trace | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3492` and calls at `:5032`, `:5144` | writes `latent_update_summary.csv` and `latent_update_top_cells.csv`, including `E[s]`, `E[s^2]`, `E[u]`, `E[1/u]`, `psi`, `chi`, residual context, source, date, member, gamma, sigma |
| gamma/sigma trace | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3592` and calls at `:5102`, `:5245` | writes `gamsig_source_iteration_summary.csv`, including source-level gamma/sigma moments, `FFF` ingredients, guard/refreeze metadata, Laplace status |
| pseudo-data trace | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:3815` and guard hook at `:3954` | writes `pseudodata_iteration_summary.csv`; writes `pseudodata_top_cells.csv` on hard guard breach |
| ELBO accounting fix | `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:5310` and `:5315` | forecast `s_t` ELBO terms now use `new.sts.out_f$E.sts2` and `new.uts.out_f$E.inv.uts`, not missing `new.uts.out_f$E.sts2` / `E.uts` |
| config generator | `scripts/prepare_he2_exdqlm_multivar_keep_latent_diag_configs.py` | prepares isolated A/B/C targeted q20 diagnostic configs from the completed grid configs |
| report collector | `scripts/report_he2_exdqlm_multivar_keep_latent_diagnostics.py` | concatenates latent, gamma/sigma, pseudo-data, guard, and sampling diagnostic outputs into one report directory |
| staged overnight runner | `scripts/run_he2_exdqlm_multivar_keep_latent_diag_ladder.py` | runs prepared A/B/C rows phase-by-phase, writes `phase_status.csv`, aggregates reports after each phase, and removes `.RData`/`.rda` artifacts after each row exits |

## Important Semantics

The new diagnostics are off unless `fit.exdqlm_multivar.diagnostics.latent.enabled: true` is present in the q-lane
config. Ordinary runs only see extra parsed defaults and a more complete latent-ablation log line.

`cap_e_u_and_e_inv_u` and `freeze_on_e_u_guard` are deliberately named diagnostic modes. They change the variational
update and should not be promoted silently. Their purpose is to test whether the remaining q20 failures are driven by
the uncapped `E[u_t]` side after A/B source-top-cell evidence says that is plausible.

The ELBO fix is not being claimed as the root cause of the q20 pseudo-data failures. It fixes a real forecast accounting
bug that could make convergence interpretation misleading because R silently summed missing forecast `s_t` terms as
zero.

## Prepared Diagnostic Matrix

The default A/B/C matrix was generated under an isolated runtime root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared`

Key files:

| artifact | path |
| --- | --- |
| matrix plan | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared/control/latent_diag_matrix/latent_diag_matrix_plan.csv` |
| generated configs | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared/control/generated_configs/` |
| dry-run report scaffold | `reports/he2_exdqlm_multivar_keep_latent_diag_report_dryrun_20260529/README.md` |

The generated matrix has 10 one-quantile q20 configs:

| phase | purpose | rows |
| --- | --- | ---: |
| A | exact reproductions of the two failed q20 lanes | 2 |
| B | matched controls by cutoff/spec/epsilon | 6 |
| C | active state-guard sensitivity with `state_guard_start_iter=20` | 2 |

All generated configs preserve the source grid config, cutoff, input bundle, transform, epsilon/discount spec, and run
family, except for the intended deltas: one quantile, diagnostic logging, isolated run root, one core per q-lane, and
phase-specific `state_guard_start_iter` for phase C.

## Verification

Commands run:

```bash
Rscript --vanilla -e "parse('DISC_Optimal_Synth_Ranges_W_transfer_forecast.r'); parse('R/unified/config.R'); parse('R/unified/stages/stage_fit.R'); parse('R/disc_w/03_covariates_standardize.R'); cat('R parse ok\n')"
python3 -m py_compile scripts/report_he2_exdqlm_multivar_keep_latent_diagnostics.py scripts/prepare_he2_exdqlm_multivar_keep_latent_diag_configs.py
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_config_mode_resolution.R')"
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R')"
Rscript --vanilla -e "source('R/unified/deterministic_climate_blend.R'); source('R/unified/config.R'); files <- list.files('/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared/control/generated_configs', pattern='[.]yaml$', full.names=TRUE); stopifnot(length(files) == 10L); for (f in files) unified_load_config(f); cat('validated_configs=', length(files), '\n', sep='')"
```

Results:

| check | result |
| --- | --- |
| R parse | pass |
| Python compile | pass |
| config/unit guard test | pass, 74 expectations |
| latent/pseudo-data source-contract test | pass, 71 expectations |
| generated diagnostic config validation | pass, 10 configs |

## Next Execution Step

When launching is explicitly approved, run only the prepared targeted diagnostic matrix. Do not rerun the full 150-row
grid first. After those q-lanes finish or fail, run:

```bash
python3 scripts/report_he2_exdqlm_multivar_keep_latent_diagnostics.py \
  --root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared \
  --out-dir reports/he2_exdqlm_multivar_keep_latent_diag_report_<timestamp>
```

Then decide from the evidence:

| evidence | fix direction |
| --- | --- |
| source-3 gamma/sigma moves before latent top cells | fix gamma/sigma split/damping/refreeze |
| `psi/chi` or `E[u_t]` moves first | test `cap_e_u_and_e_inv_u` or `freeze_on_e_u_guard` as a named sensitivity |
| active state guard fixes A but controls remain healthy | move `state_guard_start_iter` inside the 100-iteration budget |
| only forecast top cells fail | audit forecast segment/member bookkeeping |
| only sampling walltime appears | treat `c06_eps365` as a sampler/runtime issue, separate from q20 fit failures |

## Overnight Ladder

The staged controller is:

`scripts/run_he2_exdqlm_multivar_keep_latent_diag_ladder.py`

Default execution:

```bash
python3 scripts/run_he2_exdqlm_multivar_keep_latent_diag_ladder.py \
  --matrix-plan /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared/control/latent_diag_matrix/latent_diag_matrix_plan.csv \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared \
  --report-root reports/he2_exdqlm_multivar_keep_latent_diag_overnight_20260529 \
  --phases A,B,C \
  --poll-seconds 60
```

Outputs:

| artifact | path |
| --- | --- |
| controller status | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared/control/overnight_ladder/phase_status.csv` |
| live status | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared/control/overnight_ladder/LIVE_STATUS.md` |
| row logs | `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/exdqlm_keep_latent_diag_20260529_prepared/control/overnight_ladder/run_logs/` |
| report root | `reports/he2_exdqlm_multivar_keep_latent_diag_overnight_20260529/` |

The controller continues through model failures because failed rows are evidence. It only stops on infrastructure or
controller errors.

## Single-Quantile Post-Stage Guard

The q20 diagnostic rows intentionally run one quantile lane at a time. They can still validate the fit-stage latent,
gamma/sigma, pseudo-data, and sampling diagnostics, but they cannot produce a multivariate quantile-synthesis CRPS
object because `post_synthesize_rearranged_sample_cube()` requires at least two sorted quantile probabilities.

To keep one-lane diagnostics from failing after a successful fit, `R/environmetrics/40_figures_smoke_fast.R` now checks
the active quantile grid before historical or forecast multivariate synthesis:

| check | behavior |
| --- | --- |
| fewer than two active probabilities | warn with `SKIP_SINGLE_Q` and return `NULL` for that synthesis product |
| unsorted/non-finite/out-of-range probabilities | warn with `SKIP_BAD_Q_PROBS` and return `NULL` |
| valid multi-quantile grid | continue to `post_synthesize_rearranged_sample_cube()` |

This is a post-stage diagnostic guard only. It does not relax the formal synthesis helper, and it does not alter
production multi-quantile synthesis. The helper still errors on a single quantile lane; the smoke-fast caller now skips
products that are mathematically unavailable for q20-only rows.

Additional verification:

```bash
Rscript -e 'testthat::test_file("tests/testthat/test_post_quantile_synthesis_rearrangement.R")'
git diff --check
```

Result: pass, 24 expectations.

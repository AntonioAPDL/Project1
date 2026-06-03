# HE2 AL-M-T1 Relaunch Plan From Promoted exAL-M-T1 Winners

Date: 2026-06-02

2026-06-03 status update: this `AL-M-T1` package completed all five cutoff rows with
`fit/post/validate/report=pass`, no retained `.RData/.rda`, and is now promoted in the project publication manifest.
The paired current-code `exAL-M-T0` drop package also completed and is promoted; the next multivariate target is
`AL-M-T0`.

## Decision

Yes, the next launch sequence makes sense:

1. run `AL-M-T1` / `dqlm_multivar_al_keep` using the exact five promoted `exAL-M-T1` / `exdqlm_multivar_keep` winner input bundles and winner specs;
2. then prepare/run `exAL-M-T0` / `exdqlm_multivar_drop` on the same canonical bundle contract, followed by its AL counterpart `AL-M-T0`;
3. then prepare/run `exAL-U-T1` / `exdqlm_univar`, followed by its AL counterpart `AL-U-T1`;
4. keep the NDLM families on the same-bundle parity gate so the final HE2 9-model table is apples-to-apples.

The first package is prepared as a no-launch clone package:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_from_exal_winners_20260602`

## Source Of Truth

The source exAL winners are locked in:

`docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`

That manifest fixes the canonical input bundle, start date, max iteration count, quantiles, and winner specs:

- input bundle root: `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_publication_shared_inputs_20260510`
- bundle run id: `20260510_publication_shared_r01`
- data start: `1987-05-29`
- quantiles: `05|20|35|50|65|80|95`
- max iter: `100`
- fit/post scale: `log1p_cms`

The five winner rows are `20210123 c04_eps365`, `20211112 c04_eps365`, `20211221 c03_eps030`, `20220511 c02_eps060`, and `20221225 c05_eps030`.

## Why The AL Switch Is Sufficient

The active multivariate keep implementation reads `DISC_W_LIKELIHOOD_MODE` and defines `DISC_W_AL_MODE` when the value is `al` in `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:739`.

The current code then applies the AL contract directly:

- gamma initialization is forced to zero when `DISC_W_AL_MODE` is true at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1638`;
- `update_sts(...)` returns zero `E.sts` and zero `E.sts2` under AL at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:1920`;
- the sigma/gamma point-moment builder sets `gam <- 0` under AL at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:2215`;
- posterior predictive gamma draws are forced to zero for historical and forecast blocks at `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:6260` and `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r:6487`.

Therefore the correct relaunch preparation is to preserve the promoted exAL configs and switch only:

```yaml
models:
  exdqlm_multivar:
    likelihood_mode: al
    forecast_transfer_mode: keep
```

The validator also checks the latent contract metadata in every generated config. Sampled `s_t` arrays may still be allocated by the legacy sampling code, but gamma is zero and `update_sts(...)` returns zero VB moments, so `s_t` is not an active skew component under AL.

## Prepared Tooling

Builder:

```bash
python3 scripts/build_he2_dqlm_multivar_al_keep_from_exal_winners.py
```

Validator:

```bash
python3 scripts/validate_he2_dqlm_multivar_al_keep_from_exal_winners_prelaunch.py
```

Tests:

```bash
python3 -m unittest tests.python.test_he2_dqlm_multivar_al_keep_from_exal_winners -v
```

The builder writes:

- `control/publication_relaunch_matrix/matrix_plan.csv`
- `control/publication_relaunch_matrix/frozen_spec_manifest.csv`
- `control/publication_relaunch_matrix/source_clone_manifest.csv`
- `control/publication_relaunch_matrix/cutoff_bundle_audit.csv`
- `control/publication_relaunch_matrix/al_keep_run_registry.csv`
- `control/publication_relaunch_matrix/matrix_metadata.yaml`
- `control/publication_relaunch_matrix/AL_KEEP_FROM_EXAL_WINNERS_SCOPE.md`
- `control/generated_configs/*.yaml`

## Resource And Cleanup Policy

The prepared queue uses two cutoff rows at a time. Each row is one multivariate quantile run with seven internal
quantile workers, so the intended maximum active quantile workers is `2 x 7 = 14`.

Queue policy:

- first two cutoffs launch first;
- as those finish, the next two cutoffs are allowed to launch;
- the fifth cutoff launches after capacity opens;
- post-stage cleanup is enabled through `scripts/run_unified_with_cleanup.sh`, which sets `CLEANUP_RDATA_AFTER_POST=1`;
- queued wrappers also prepend `/data/muscat_data/jaguir26/libs/boost/lib` to `LD_LIBRARY_PATH`, which is required for
  the active `Rcpp::sourceCpp(...)` Kalman/sampling shared objects to load `libboost_random.so.1.82.0`;
- large `.RData/.rda` files should not be retained after successful post evidence is written.

Launch incident note: an initial detached launch attempt on 2026-06-02 failed immediately at q05 for the first two
cutoffs because the wrapper environment did not expose `libboost_random.so.1.82.0` to the dynamic loader. This was a
runtime wrapper issue, not an input-bundle or AL likelihood issue. The fix is to set `LD_LIBRARY_PATH` in both unified
queue wrappers before `Rscript` starts.

## Hard Validation Gates

Before launch, validation must pass with zero failures:

1. exactly five run rows and 35 quantile fits;
2. target family is `dqlm_multivar_al_keep`, label `AL-M-T1`, model id `dqlm_multivar_al_synth_keep`;
3. source configs are the promoted exAL winner configs;
4. target configs use `likelihood_mode: al` and `forecast_transfer_mode: keep`;
5. `inputs`, `dates`, `scale_contract`, `stages`, state evolution, structure, and all `fit` settings are identical to the source exAL winner configs except for run identity and debug provenance;
6. harmonics remain `1,2,3`;
7. transfer covariates remain `PPT`, `SOIL`, `PCA`, with squares, interaction, and lags `1,2,3`;
8. cutoff-specific epsilon, c_factor, discount factors, and `max_iter=100` match the authoritative YAML;
9. bundle meta paths point to the 20260510 shared bundle for the matching cutoff;
10. queue state is initialized but no jobs are launched by the builder or validator.

## Launch Command

Only run after explicit launch approval:

```bash
python3 scripts/run_multimodel_v8_queue.py --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_from_exal_winners_20260602/control/publication_relaunch_matrix --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_keep_from_exal_winners_20260602 --ordinary-max-concurrent 2 --pause-free-gb 25.0 --launch-free-gb 35.0 --heavy-free-gb 35.0 --pause-mem-gb 0.0 --launch-mem-gb 0.0 --heavy-mem-gb 0.0 --heavy-cutoff-max-concurrent 2 --poll-seconds 30 --continue-on-fail --skip-compares --no-heavy-cutoff-blocks-ordinary
```

This uses cleanup after post by default through `scripts/run_unified_with_cleanup.sh`.

## Follow-On Family Order

After `AL-M-T1` completes and passes post-output validation:

1. build/run `exAL-M-T0` / `exdqlm_multivar_drop` on the same 20260510 bundle contract;
2. build `AL-M-T0` / `dqlm_multivar_al_drop` as the paired AL clone/check;
3. build `exAL-U-T1` / `exdqlm_univar`;
4. build `AL-U-T1` / `dqlm_univar_al`;
5. rebuild the HE2 publication manifest and article assets only after all pending families pass the same-bundle parity gate.

Do not promote any of these families into the revised article benchmark table until their CRPS tables, synthesis figures, diagnostics, source-config hashes, and cleanup evidence are frozen.

Important drop-family note: older `exdqlm_multivar_drop` shared-spec tooling exists, but it predates the current
authoritative exAL-M-T1 winner-clone promotion. It should be treated as context, not as an already launch-ready
same-bundle parity package. The drop-family wave should get its own refreshed no-launch matrix, validator, 2-row/14-worker
queue policy, and cleanup gate before it is launched.

## 2026-06-02 Current-Code Drop Decision

The older completed `exAL-M-T0` root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_all_cutoffs_sharedspec_20260516`

is not being promoted as the final benchmark row. It completed all five cutoffs and has no retained `.RData/.rda`, but
its post-stage synthesis draws and `log_cms_plus1` CRPS values are pathologically large in multiple cutoffs. That makes
it useful historical evidence, not an authoritative current-code result.

Fresh current-code drop tooling is now the target package:

```bash
python3 scripts/build_he2_exdqlm_multivar_drop_current_relaunch.py
python3 scripts/validate_he2_exdqlm_multivar_drop_current_prelaunch.py
python3 -m unittest tests.python.test_he2_exdqlm_multivar_drop_current_relaunch -v
```

Prepared artifact root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602`

This package reuses the shared-spec `exAL-M-T0` scientific settings (`epsilon=30`, `c_factor=1`, shared high discount
factors), but makes the previously implicit full-harmonic contract explicit (`trend + harmonics 1,2,3`), pins the
canonical 20260510 bundle, uses the same two-cutoff-row/14-quantile-worker queue policy as the AL keep package, and
keeps post-success `.RData/.rda` cleanup enabled. It also promotes the proven `20211112 q50` repair from
`docs/he2_exdqlm_multivar_drop_q50_repair_promotion_20260602.md`.

Launch order: let the active `AL-M-T1` queue keep the 14 intended workers. Launch the fresh `exAL-M-T0` current-code
queue only after `AL-M-T1` finishes or clearly fails and is triaged. The guarded overnight handoff is:

```bash
python3 scripts/launch_he2_exdqlm_drop_after_al_keep.py --poll-seconds 300
```

The handoff script writes:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602/control/publication_relaunch_matrix/drop_after_al_keep_handoff_status.json`

and starts the drop controller in tmux session `he2_exal_drop_q50repair_20260602` only after:

1. the AL-M-T1 matrix status is fully `pass`;
2. no AL-M-T1 `scripts/unified_run.R` process remains active under its artifact root;
3. the current-code exAL-M-T0 prelaunch validator passes;
4. the drop matrix is not already failed, active, or complete.

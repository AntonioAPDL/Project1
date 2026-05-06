# Authoritative R 4.4 Replay Environment

This note records the closest faithful replay environment currently available for
the published `exAL-M-T1` (`exdqlm_multivar_synth_keep`) source runs.

## Why this exists

The published source runs for the selected model were generated under:

- `R 4.4.0`
- the package library rooted at:
  - `/home/jaguir26/R/x86_64-redhat-linux-gnu-library/4.4`

The current system runtime is:

- `R 4.5.3`

and the current package stack differs materially from the authoritative one.
That drift is sufficient to reproduce the `q = 0.20` keep-lane instability in
the representative `2022-12-25` replay.

## Authoritative environment facts

Representative source run:

- `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_20260402/runs/multimodel_20221225_v8_eps90cf1_l2_mv`

Saved environment artifacts:

- `env/R_sessionInfo.txt`
- `env/R_installed_packages.csv`
- `env/renviron_snapshot.txt`
- `env/threads_snapshot.txt`

Key runtime facts from the successful source run:

- `R version 4.4.0 (2024-04-24)`
- package count in saved snapshot: `677`
- key package versions:
  - `Rcpp 1.0.14`
  - `RcppArmadillo 0.12.8.4.0`
  - `nimble 1.2.1`
  - `exdqlm 0.6.0.9000`
  - `dlm 1.1-6.1`
  - `tidyverse 2.0.0`
  - `readr 2.1.5`
  - `lubridate 1.9.3`
  - `tseries 0.10-56`
  - `rvest 1.0.4`

Thread settings:

- `OMP_NUM_THREADS=1`
- `OPENBLAS_NUM_THREADS=1`
- `MKL_NUM_THREADS=1`
- `VECLIB_MAXIMUM_THREADS=1`
- `NUMEXPR_NUM_THREADS=1`

## Current local reconstruction path

We do not currently have a surviving `R 4.4.0` binary on disk. The saved 4.4
package library still exists:

- `/home/jaguir26/R/x86_64-redhat-linux-gnu-library/4.4`

So the local reconstruction path is:

1. build a local `R 4.4.0` runtime
2. run it against the saved 4.4 library tree
3. preserve the single-thread settings from the source run

## Build command

Use:

```bash
scripts/bootstrap_r440_runtime.sh
```

This builds a local runtime under:

- `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runtime/r-4.4.0/install`

The build uses:

- `--with-readline=no`

because the local batch replay does not need interactive readline support and
the required development headers are not present on this machine.

## Representative replay config

Generate the representative keep-lane `q = 0.20` config with:

```bash
python3 scripts/build_authoritative_r440_replay_config.py
```

That produces:

- `config/unified_runs_exalm_t1_r440_20260506/paper_exalm_t1_r440_q20_keep_20221225_20260506.yaml`

This config:

- uses the authoritative shared inputs from the published `2022-12-25` source run
- restricts the replay to:
  - `exdqlm_multivar`
  - `forecast_transfer_mode = keep`
  - `q = 0.20`
- disables post/validate/report so the test isolates fit stability first

## Representative replay command

Run:

```bash
scripts/run_authoritative_r440_replay.sh \
  config/unified_runs_exalm_t1_r440_20260506/paper_exalm_t1_r440_q20_keep_20221225_20260506.yaml
```

The wrapper sets:

- `R_LIBS=/home/jaguir26/R/x86_64-redhat-linux-gnu-library/4.4`
- `R_LIBS_USER=""`
- `R_LIBS_SITE=""`
- `PATH` so child `Rscript` calls resolve to the rebuilt local `R 4.4.0`
- `ENVIRONMETRICS_LIBS_ONLY=1` so legacy scripts do not append `~/R/libs`
- the saved single-thread settings

## Representative replay outcome

The representative keep-lane replay completed successfully at:

- `/data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/paper_exalm_t1_r440_q20_keep_20221225_20260506`

Key result:

- the normalized `q = 0.20` keep-lane fit trace matches the authoritative
  published source-run trace exactly after removing:
  - the library-path header lines
  - runtime-only timing strings
  - the run-local output path

That means the replay recovered the same numerical path as the published run,
not merely a stable approximation.

The recovery required four fixes:

1. build and use a local `R 4.4.0` runtime
2. force child `Rscript` calls to use that local runtime via `PATH`
3. prevent legacy scripts from reintroducing `~/R/libs`
4. use `exdqlm::combineMods()` in the shared multivariate structure helper
   instead of `mod1 + mod2`

## Interpretation of outcomes

The earlier `q = 0.20` failures were not caused by the discount block or by
input/version mismatches. They came from replay drift:

- `R 4.5.x` package/runtime drift
- child fit jobs escaping back to the system `Rscript`
- legacy user-library injection
- an incorrect shared helper that replaced the package-native
  `combineMods()` path

With those repaired, the representative authoritative replay reproduces the
published selected-model fit path.

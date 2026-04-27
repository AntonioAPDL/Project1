# HE2 Univariate Featurecov Rerun

This runbook defines the launch contract for `multimodel_v8_univar_featurecov_he2_rerun_20260422`.

## Goal

- rerun the 10 missing HE2 univariate quantile rows under the proper blended-featurecov contract
- keep `PPT + SOIL + PCA` as the fit covariates
- enable deterministic blended climate and engineered lag / square / interaction features
- give each of the 7 quantile fits its own CPU core
- run the 10 rows in controlled row-level batches rather than as a one-shot burst

## Scope

- families:
  - `dqlm_univar_al`
  - `exdqlm_univar`
- cutoffs:
  - `20210123`
  - `20211112`
  - `20211221`
  - `20220511`
  - `20221225`
- total rows: `10`

## Queue Contract

- `ordinary_max_concurrent = 4`
- `fit_parallel_workers = 7` for both univariate families
- `heavy_cutoff_max_concurrent = 4`
- `heavy_cutoff_blocks_ordinary = false`
- `poll_seconds = 15`

This consumes up to `28` fit cores at a time through row-level batches of `4`, with each active row internally using `7` quantile workers.

Expected batch shape:

1. rows `1-4`
2. rows `5-8`
3. rows `9-10`

## Why This Contract

- The historical HE2 univariate AL/exAL rows still point to baseline TT outputs.
- The repaired univariate fit path now uses the same engineered feature table that post uses.
- A 4-row queue keeps the campaign efficient without repeating the earlier “controller launches everything at once” failure mode.
- The heavy-cutoff serialization is disabled because this campaign is only 10 rows and we want consistent batching across cutoffs.

## Prelaunch Validation

Run:

```bash
python3 scripts/validate_univar_featurecov_he2_prelaunch.py \
  --config config/multimodel_v8_univar_featurecov_he2_rerun_20260422.template.yaml
```

What this validates:

- the matrix builds to exactly `10` rows
- every generated config is univariate-only and uses `PPT, SOIL, PCA`
- deterministic blended climate and engineered covariate features are enabled
- `mc_cores = 7` and `fit.parallel.workers = 7`
- focused Python and R regression tests pass
- one full end-to-end smoke run per family passes through `data_prep_shared`, `fit`, `post`, `validate`, and `report`

## Launch

To scaffold only:

```bash
bash scripts/run_multimodel_v8_univar_featurecov_he2_rerun.sh \
  --config config/multimodel_v8_univar_featurecov_he2_rerun_20260422.template.yaml
```

To scaffold and launch:

```bash
bash scripts/run_multimodel_v8_univar_featurecov_he2_rerun.sh \
  --config config/multimodel_v8_univar_featurecov_he2_rerun_20260422.template.yaml \
  --launch
```

To detached-launch with a recorded controller PID and `last_launch.json`:

```bash
python3 scripts/launch_multimodel_v8_univar_featurecov_he2_rerun.py \
  --template config/multimodel_v8_univar_featurecov_he2_rerun_20260422.template.yaml
```

## Post-Run Next Step

After the 10-row rerun finishes:

1. read the new univariate CRPS rows from the campaign compare/report outputs
2. merge them into the current HE2 audit/update workflow
3. refresh the `AL-U-T1` and `exAL-U-T1` cells in `Corrections---Project-1`

This campaign is intentionally non-destructive:

- it writes to a new artifact root
- it does not overwrite prior featurecov or NDLM campaigns
- it preserves the current manuscript state until the new rows are verified

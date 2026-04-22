# NDLM Featurecov Postfix 15-Core Relaunch

This runbook defines the clean relaunch contract for `multimodel_v8_ndlm_featurecov_rerun_postfix_20260421`.

## Goal

- run one CPU core per NDLM model row
- allow all 15 campaign rows to run concurrently
- disable the generic heavy-cutoff serialization for this campaign
- archive the interrupted partial attempt before rebuilding
- rebuild, validate, and relaunch from a clean campaign root

## Queue Contract

- `ordinary_max_concurrent = 15`
- `fit_parallel_workers = 1` for every NDLM family
- `heavy_cutoff_max_concurrent = 15`
- `heavy_cutoff_blocks_ordinary = false`
- `poll_seconds = 5`

This means the campaign consumes up to 15 cores through row-level parallelism, not through intra-row parallelism.

## Relaunch Procedure

1. Stop the live queue controller for the matrix.
2. Stop any active run processes whose command line belongs to this postfix campaign.
3. Archive the current `runs`, `reports`, and `control` trees under `artifact_root/relaunch_archive/<timestamp>/`.
4. Archive the generated config directory contents.
5. Rebuild the matrix configs from the postfix template.
6. Run the NDLM prelaunch validation suite.
7. Launch a fresh queue controller with the queue contract above.
8. Record the relaunch metadata in `controller_state/last_relaunch.json`.

## Implementation

Use:

```bash
python3 scripts/relaunch_multimodel_v8_ndlm_featurecov_rerun.py \
  --template config/multimodel_v8_ndlm_featurecov_rerun_postfix_20260421.template.yaml
```

## Expected Result

- a clean archived copy of the interrupted attempt
- a rebuilt matrix with queue settings written into `launch_settings.env`
- a validated relaunch using the documented 15-row one-core contract

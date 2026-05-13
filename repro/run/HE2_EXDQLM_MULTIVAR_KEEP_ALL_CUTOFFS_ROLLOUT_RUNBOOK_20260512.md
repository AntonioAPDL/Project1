# HE2 exdqlm_multivar_keep All-Cutoffs Rollout Runbook

Date: 2026-05-12

## Goal

Scale the repaired `exdqlm_multivar_keep` family from the successful `20210123` proof row to all 5 HE2 publication cutoffs under the canonical shared-input / GDPC relaunch workflow.

This rollout now follows a strict transform rule:

- retros, forecast ensembles, observations, fit internals, and post internals stay on `log1p_cms`
- `log_log1p_cms` is not allowed in the current relaunch workflow

## Inputs

- template:
  - `config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml`
- batch:
  - `config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_quantile_map_20260512.yaml`
- cleanup manifest:
  - `config/he2_recent_runtime_cleanup_20260512.yaml`
- golden contract:
  - `repro/run/HE2_EXDQLM_MULTIVAR_KEEP_GOLDEN_CONTRACT_20260512.md`
- transform policy:
  - `repro/run/LOG1P_ONLY_TRANSFORM_POLICY_20260512.md`

## Workflow classes covered

The validator for this template explicitly covers both cutoff action classes:

- representative short-history cutoff requiring `rebuild_full_history_and_refresh_GDPC`
  - `20210123`
- representative full-history cutoff requiring `refresh_GDPC_only`
  - `20211221`

## Queue profile

This rollout uses a disk-guarded serial queue contract:

- `ordinary_max_concurrent=1`
- `pause_free_gb=25`
- `launch_free_gb=35`
- `heavy_free_gb=35`
- `heavy_cutoff_max_concurrent=1`

The intent is to avoid the earlier launch stall caused by unrealistic free-space thresholds.

For higher throughput after validation passes, the template also exposes a dual-row profile:

- profile: `disk_guarded_dual`
- ordinary rows in parallel: `2`
- per row fit workers: `7`
- per row `mc_cores`: `7`
- effective quantile-model concurrency: `14`

This is the efficient launch mode for the all-cutoff family rollout. A literal batch size of `15` is not natural for this family because each row contains `7` quantile submodels, so the clean parallelism units are `7` or `14`.

## Cleanup policy

Before rollout, prune large superseded HE2 runtime artifacts while preserving compact evidence:

```bash
python3 scripts/cleanup_he2_runtime_artifacts.py \
  --config config/he2_recent_runtime_cleanup_20260512.yaml
python3 scripts/cleanup_he2_runtime_artifacts.py \
  --config config/he2_recent_runtime_cleanup_20260512.yaml \
  --apply
```

## Validation

Run the family-wide prelaunch validator:

```bash
python3 scripts/validate_he2_bayesian_publication_relaunch_prelaunch.py \
  --config config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_quantile_map_20260512.yaml
```

Expected result:

- all 5 cutoff bundle checks pass
- representative multivariate quantile fit smokes pass for `20210123` and `20211221`
- representative multivariate full-pipeline smokes pass for `20210123` and `20211221`
- smoke `.RData` payloads are pruned automatically after successful validation

## Launch

After validation passes, launch via the relaunch controller:

```bash
python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_all_cutoffs_20260512.template.yaml \
  --batch-file config/he2_relaunch_batches/exdqlm_multivar_keep_all_cutoffs_quantile_map_20260512.yaml \
  --profile disk_guarded_dual
```

## Retention expectation

Successful rows should keep post/report/validate outputs and should not retain large fit `.RData` payloads after `post`.

## Exit criteria

1. all 5 `exdqlm_multivar_keep` cutoffs launch and complete
2. q35 remains stable across the family rollout
3. retained artifacts stay compact enough for broader HE2 scale-up

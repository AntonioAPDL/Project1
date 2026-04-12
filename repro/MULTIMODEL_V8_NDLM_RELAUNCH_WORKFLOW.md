# Multimodel v8 NDLM Relaunch Workflow

## Purpose

This workflow isolates the three NDLM families from the current 9-model unified workflow so we can retune them cleanly without rerunning the quantile families.

Target families:

- `ndlm_main_synth_keep`
- `ndlm_main_synth_drop`
- `ndlm_univar_synth_keep`

The design goal is to reuse the current `v8` execution stack:

- central YAML control
- generated unified configs
- existing `run_multimodel_v8_queue.py`
- existing `run_unified_with_cleanup.sh`
- existing `unified_run.R`

while adding a custom compare-merge step that replaces only the NDLM rows in an authoritative compare bundle.

## Central Campaign YAML

Primary config:

- [multimodel_v8_ndlm_campaign.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/multimodel_v8_ndlm_campaign.template.yaml)

The YAML controls:

- artifact root
- matrix dir
- generated config dir
- queue defaults
- per-cutoff template config sources
- per-cutoff authoritative compare bundles
- enabled NDLM families
- NDLM tuning specs

The current template ships with one baseline spec:

- `current_v8`

and one active user retune spec:

- `ndlm_tune_20260411_v1`

This baseline is the exact live NDLM parameterization currently used in the authoritative v8 runs.

The active retune spec currently enabled in the campaign template is:

- `ndlm_tune_20260411_v1`

## Current Live NDLM Values

### `ndlm_main`

| parameter | current value |
|---|---:|
| `df_t` | `0.99999999` |
| `df_s1` | `0.9999` |
| `df_s2` | `0.9999` |
| `df_s67` | `0.9999` |
| `df_discrep` | `0.999` |
| `lambda` | `0.97` |
| `df_trans` | `0.9999999` |
| `df_covs` | `0.9999` |
| seasonal period | `363.5854` |
| seasonal harmonics | `1`, `2`, `0.1469118904` |
| forecast cov `c_factor` | `1.0` |
| forecast cov `epsilon` | `null` |
| forecast cov `dof_offset` | `4` |
| forecast cov `scale_mult` | `1.0` |
| forecast cov `jitter` | `1e-8` |
| `cov_eig_floor` | `1e-8` |
| `cov_eig_cap` | `1e8` |
| `cov_diag_jitter` | `1e-10` |
| `sigma_upper_cap` | `1e12` |
| `sigma_update_damping` | `1.0` |
| `latent_var_cap_mult` | `1e4` |
| `latent_var_cap_abs` | `1e8` |
| gamma/sigma `min_total_iters` | `50` |
| gamma/sigma `max_iter` | `100` |
| gamma/sigma `elbo_tol` | `1e-6` |
| gamma/sigma `elbo_rel_tol` | `2.5e-4` |

### `ndlm_univar`

| parameter | current value |
|---|---:|
| `df_t` | `0.99999999` |
| `df_s1` | `0.9999` |
| `df_s2` | `0.9999` |
| `df_s67` | `0.9999` |
| `lambda` | `0.97` |
| `df_trans` | `0.9999999` |
| `df_covs` | `0.99999` |
| seasonal period | `363.5854` |
| seasonal harmonics | `1`, `2`, `3` |
| `n0` | `20` |
| `S0` | `1` |
| `horizon_cap` | `90` |
| `posterior_draws` | `64` |
| `cov_eig_floor` | `1e-8` |
| `cov_eig_cap` | `1e8` |
| `cov_diag_jitter` | `1e-10` |

## Authoritative Inputs By Cutoff

The campaign template already points each cutoff at the right baseline templates and compare bundles.

- `20210123`, `20211112`, `20221225`: canonical `v8` TT configs and TT compare bundles
- `20211221`, `20220511`: corrected hist-fix TT configs and TT compare bundles

This keeps the NDLM relaunch aligned with the current authoritative workflow without relaunching the quantile families.

## Implemented Files

### Builder and wrapper

- [build_multimodel_v8_ndlm_matrix_configs.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_multimodel_v8_ndlm_matrix_configs.py)
- [build_multimodel_v8_ndlm_compare_bundle.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/build_multimodel_v8_ndlm_compare_bundle.py)
- [run_multimodel_v8_ndlm_campaign.sh](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_multimodel_v8_ndlm_campaign.sh)

### Shared queue/controller integration

- [run_multimodel_v8_queue.py](/data/muscat_data/jaguir26/project1_ucsc_phd/scripts/run_multimodel_v8_queue.py)

The queue now supports a matrix-local custom compare builder declared in `matrix_metadata.yaml`.

### NDLM parameter plumbing

- [stage_fit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/stages/stage_fit.R)
- [ndlm_main/00_constants.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/00_constants.R)
- [ndlm_main/03_vb_updates.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/03_vb_updates.R)
- [ndlm_main/07_state_registry.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_main/07_state_registry.R)
- [ndlm_univar/00_constants.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_univar/00_constants.R)
- [ndlm_univar/03_filter_forecast_fit.R](/data/muscat_data/jaguir26/project1_ucsc_phd/R/unified/families/ndlm_univar/03_filter_forecast_fit.R)
- [unified_run.template.yaml](/data/muscat_data/jaguir26/project1_ucsc_phd/config/unified_run.template.yaml)

These changes make the following configurable from YAML for NDLM relaunches:

- seasonal period
- seasonal harmonics
- transfer-mode-specific NDLM runs
- `df_t`, `df_s1`, `df_s2`, `df_s67`
- `lambda`, `df_trans`, `df_covs`
- `df_discrep` for `ndlm_main`
- forecast covariance prior controls for `ndlm_main`
- `n0`, `S0`, `horizon_cap`, `posterior_draws` for `ndlm_univar`
- stabilization controls

## Build Only

To build the NDLM campaign scaffolding without launching any runs:

```bash
bash scripts/run_multimodel_v8_ndlm_campaign.sh \
  --config config/multimodel_v8_ndlm_campaign.template.yaml
```

This creates:

- `matrix_plan.csv`
- `matrix_status.csv`
- `matrix_metadata.yaml`
- `campaign_snapshot.yaml`
- `dependency_preservation.csv`
- `spec_parameter_table.csv`
- generated unified configs for the three NDLM families across the enabled cutoffs/specs

## Launch Later

The wrapper supports launch, but it is opt-in:

```bash
bash scripts/run_multimodel_v8_ndlm_campaign.sh \
  --config config/multimodel_v8_ndlm_campaign.template.yaml \
  --launch
```

By default, the wrapper does not launch anything.

## Compare Merge Behavior

The custom compare builder:

- starts from the configured authoritative compare bundle for each cutoff
- preserves quantile-model and ensemble rows exactly as they are
- replaces only the NDLM rows produced by the relaunched NDLM runs for the active spec
- writes a new compare bundle at `multimodel_{cutoff}_v8_{spec_id}_compare`

This gives an apples-to-apples comparison surface for NDLM retuning without disturbing the quantile-model lineage.

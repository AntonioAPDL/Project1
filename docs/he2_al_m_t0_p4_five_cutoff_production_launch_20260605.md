# HE2 AL-M-T0 P4 Five-Cutoff Production Launch - 2026-06-05

## Purpose

Promote the passed AL-M-T0 P4 q65 recovery policy from the two-cutoff smoke to
the full five-cutoff publication production run.

This launch uses the same scientific/input contract that passed the smoke:

- source clone family: `exAL-M-T0` / `exdqlm_multivar_drop`;
- target family: `AL-M-T0` / `dqlm_multivar_al_drop`;
- likelihood switch: `exal -> al`;
- forecast transfer mode: `drop`;
- canonical publication input bundle;
- data start: `1987-05-29`;
- cutoffs: `20210123`, `20211112`, `20211221`, `20220511`, `20221225`;
- active quantiles: `05`, `20`, `35`, `50`, `65`, `80`, `95`;
- discount factors: all state/covariance discount factors `0.99999999`;
- `lambda = 0.97`;
- Wishart forecast covariance prior: `epsilon = 365`, `c_factor = 1`;
- full transfer feature contract inherited from the promoted source configs;
- cleanup after successful post/report enabled.

## P4 Policy

Policy overlay:

`config/he2_relaunch_batches/al_m_t0_p4_q65_guard_recovery_overlay_20260605.yaml`

The P4-specific production change is q65-only state/covariance damping:

| quantile | max iter | freeze target | state guard | state blend | cov blend | terminal guard |
|---|---:|---|---|---:|---:|---|
| q35 | 160 | `gamma_sigma` | enabled | 1.0 | 1.0 | fail-fast |
| q65 | 220 | `gamma_sigma` | enabled | 0.15 | 0.5 | fail-fast |

The stale source q50 `freeze_target=states` override is explicitly dropped.

## Artifact Root

Production root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p4_production_20260605`

Matrix directory:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p4_production_20260605/control/publication_relaunch_matrix`

Generated configs:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p4_production_20260605/control/generated_configs`

## Prelaunch Validation

Validation report:

`reports/he2_al_m_t0_p4_production_20260605/prelaunch_validation/PRELAUNCH_VALIDATION_SUMMARY.md`

Validation command:

```bash
python3 scripts/validate_he2_dqlm_multivar_al_drop_from_exal_drop_prelaunch.py \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p4_production_20260605 \
  --source-artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_drop_current_relaunch_q50repair_20260602 \
  --policy-spec-yaml config/he2_relaunch_batches/al_m_t0_p4_q65_guard_recovery_overlay_20260605.yaml \
  --skip-smoke \
  --outdir reports/he2_al_m_t0_p4_production_20260605/prelaunch_validation
```

Validated checks:

| Check | Status |
|---|---|
| Python compile for builder/validator | passed |
| five generated target configs exist | passed |
| source-to-target clone contract | passed |
| AL/drop target family contract | passed |
| P4 policy overlay applied | passed |
| source `.RData/.rda` cleanup | passed |
| q50 stale source override removed | passed |
| q65 P4 recovery policy present | passed |

Targeted tests:

```bash
python3 -m unittest \
  tests.python.test_he2_remaining_quantile_al_exal_relaunch \
  tests.python.test_he2_al_m_t0_gamsig_cycle_audit \
  tests.python.test_disc_sampling_diagnostics_source_contract \
  tests.python.test_stage_fit_quantile_gamma_sigma_overrides -v
```

Result: `24` tests passed.

## Queue Contract

The queue uses two cutoff rows concurrently and seven quantile workers per row:

| Setting | Value |
|---|---:|
| cutoff rows at once | 2 |
| quantile workers per row | 7 |
| max active quantile workers | 14 |
| pause free GB | 25 |
| launch free GB | 35 |
| heavy free GB | 35 |
| continue on fail | true |
| skip compare bundles | true |
| cleanup successful post `.RData` | true |

Launch command:

```bash
python3 scripts/run_multimodel_v8_queue.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p4_production_20260605/control/publication_relaunch_matrix \
  --artifact-root /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_dqlm_multivar_al_drop_p4_production_20260605 \
  --ordinary-max-concurrent 2 \
  --pause-free-gb 25.0 \
  --launch-free-gb 35.0 \
  --heavy-free-gb 35.0 \
  --pause-mem-gb 0.0 \
  --launch-mem-gb 0.0 \
  --heavy-mem-gb 0.0 \
  --heavy-cutoff-max-concurrent 2 \
  --poll-seconds 30 \
  --continue-on-fail \
  --skip-compares \
  --no-heavy-cutoff-blocks-ordinary
```

## Monitoring Plan

During the run, monitor:

- `matrix_status.csv` for row phase/status;
- fit logs with `scripts/summarize_he2_al_m_t0_fit_logs.py`;
- gamma/sigma cycle audit with `scripts/audit_he2_al_m_t0_gamsig_cycles.py`;
- `/data` free space and retained `.RData` counts;
- q35/q65 guard counts and terminal failures;
- post artifact summaries, CRPS tables, and publication figure manifests.

Promotion gate:

1. all five rows close through `report/pass`;
2. all 35 quantile fits are two-cycle free;
3. q65 rows have at least 50 gamma/sigma updates and terminal health pass;
4. post CRPS and publication figures exist for every cutoff;
5. successful rows retain zero fit `.RData` files after cleanup.

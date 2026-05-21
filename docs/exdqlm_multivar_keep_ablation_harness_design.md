# exDQLM Multivariate Keep Ablation Harness Design

Date: 2026-05-21

## Purpose

This document closes tracker item `T1`: design and implement the smallest safe ablation harness needed to isolate
whether the repaired `log1p_cms` stability gain came mainly from `sigma/gamma`, the latent `s_t/u_t` updates,
pseudo-data guardrails, or their interaction.

The harness is diagnostic. It does not change production defaults.

## Existing Control

The first repaired guarded q05/q35/q50/q95 run is the control:

- tracked summary:
  [exdqlm_multivar_keep_guarded_repro_20260521.md](/data/muscat_data/jaguir26/project1_ucsc_phd/docs/exdqlm_multivar_keep_guarded_repro_20260521.md)
- untracked report root:
  `reports/exdqlm_keep_guarded_repro_guarded_log1p_q05_q35_q50_q95_20260521/`

It used:

1. active `log1p_cms`,
2. forecast `update_uts` `TT_sub` indexing fix,
3. stable positive-truncated-normal `s_t` moments/entropy,
4. closed-form half-order `u_t` moments,
5. warning-mode pseudo-data guards,
6. post-save objective disabled for isolated audit runtime.

Because those changes were active together, this control proves material stabilization but not a single root cause.

## Harness Implementation

The single-run preparer is:

`repro/audits/prepare_exdqlm_keep_guarded_repro.py`

It now accepts:

| option | meaning |
| --- | --- |
| `--ablation-mode control` | repaired path, no extra diagnostic intervention |
| `--ablation-mode fixed-gamsig` | freezes `sigma/gamma` updates for the run |
| `--ablation-mode latent-freeze` | reuses previous latent moments after each latent update |
| `--ablation-mode latent-cap-e-inv-u` | caps updated `E[1/u]` before `sigma/gamma` and next pseudo-data construction |
| `--ablation-mode fixed-gamsig-latent-cap` | combines fixed `sigma/gamma` with `E[1/u]` capping |

The matrix preparer is:

`repro/audits/prepare_exdqlm_keep_ablation_matrix.py`

It prepares multiple isolated conditions, writes a matrix manifest, and creates a sequential master launcher. This
keeps the ablation plan reproducible without hand-built run roots.

## Active Runner Controls

### Fixed `sigma/gamma`

This uses the active runner's existing gamma/sigma freeze controls, but the source of truth must be the generated
YAML policy consumed by `R/unified/stages/stage_fit.R`. Wrapper-level `DISC_GAMSIG_*` exports are retained as
manifest breadcrumbs, but fit workers rebuild those values from `fit.exdqlm_multivar.gamma_sigma`.

| environment variable | value |
| --- | --- |
| `DISC_GAMSIG_FREEZE_TARGET` | `gamma_sigma` |
| `DISC_GAMSIG_FREEZE_ITERS` | `max_iter + 5` |
| `DISC_GAMSIG_MIN_UPDATE_ITERS` | `0` |

For `fixed-gamsig` and `fixed-gamsig-latent-cap`, the preparer also writes:

| generated YAML key | value |
| --- | --- |
| `fit.exdqlm_multivar.gamma_sigma.freeze_target` | `gamma_sigma` |
| `fit.exdqlm_multivar.gamma_sigma.warmup_freeze_iters` | `max_iter + 5` |
| `fit.exdqlm_multivar.gamma_sigma.min_update_iters` | `0` |
| `fit.exdqlm_multivar.gamma_sigma.state_refresh_schedule.enabled` | `false` |
| each existing `quantile_overrides.*.warmup_freeze_iters` | `max_iter + 5` |
| each existing `quantile_overrides.*.min_update_iters` | `0` |
| each existing `quantile_overrides.*.state_refresh_schedule.enabled` | `false` |

Interpretation:

1. latent and state updates still run,
2. `sigma/gamma` expectations are held at their initialized/current values,
3. if this removes q05 `E[1/u]` bursts, `sigma/gamma` dynamics or calibration become the leading suspect.

### Latent Freeze

New diagnostic controls:

| environment variable | value |
| --- | --- |
| `DISC_LATENT_ABLATION_MODE` | `freeze` |

The active runner updates `s_t/u_t`, then immediately replaces `new.sts.out`, `new.uts.out`, forecast `new.sts.out_f`,
and forecast `new.uts.out_f` with their previous-iteration values before `sigma/gamma` updates and before the next
pseudo-data construction.

Interpretation:

1. `sigma/gamma` and state updates can proceed against previous latent moments,
2. if this stabilizes a suspect lane, latent dynamics are a leading suspect,
3. this is diagnostic-only unless promoted by a later policy decision.

### Latent `E[1/u]` Cap

New diagnostic controls:

| environment variable | value |
| --- | --- |
| `DISC_LATENT_ABLATION_MODE` | `cap_e_inv_u` |
| `DISC_LATENT_E_INV_U_CAP` | numeric cap, default `5000` |

The active runner caps historical and forecast `E[1/u]` after latent updates. This cap affects subsequent
`sigma/gamma` updates and the next iteration's pseudo-data construction.

Interpretation:

1. this directly tests the q05 live guard signal,
2. if capped q05 removes the transient without destabilizing q35/q50/q95, it becomes a candidate production guard
   response,
3. the cap intentionally does not claim to preserve exact ELBO algebra; it is a production-safety candidate that must
   be documented if promoted.

## Recommended Ablation Matrix

Use the existing guarded run as the repaired control. Then run:

| condition | lanes | purpose |
| --- | --- | --- |
| `fixed-gamsig` | q05/q35/q50/q95 | isolate `sigma/gamma` dynamics |
| `latent-freeze` | q05/q35/q50/q95 | isolate latent moment dynamics |
| `latent-cap-e-inv-u` | q05 first if time constrained, otherwise q05/q35/q50/q95 | test q05 guard response |
| `fixed-gamsig-latent-cap` | optional after first three | test interaction if first three are ambiguous |

Default command to prepare the first matrix:

```bash
python3 repro/audits/prepare_exdqlm_keep_ablation_matrix.py \
  --tag ablation_log1p_q05_q35_q50_q95_20260521 \
  --conditions fixed-gamsig,latent-freeze,latent-cap-e-inv-u \
  --quantiles 0.05,0.35,0.5,0.95 \
  --max-iter 3000 \
  --workers 4 \
  --guard-mode warn
```

The script writes a matrix report under:

`reports/exdqlm_keep_ablation_matrix_<tag>/`

## Runtime Acceptance Criteria

For each condition:

1. all requested lanes either write `.RData` or fail with a classified guard/error,
2. guard event CSVs are retained,
3. runtime stability audit is regenerated from any written `.RData` files,
4. curated evidence bundle is regenerated for the condition if it completes,
5. `docs/exdqlm_multivar_keep_repair_tracker.md` is updated.

Interpretation rules:

1. If `fixed-gamsig` removes the q05 `E[1/u]` burst, prioritize `sigma/gamma` recalibration or damping.
2. If `latent-freeze` removes the burst but `fixed-gamsig` does not, prioritize latent dynamics and guard response.
3. If only `latent-cap-e-inv-u` removes the burst, the root remains upstream but the production safety mechanism is
   promising.
4. If all ablations are stable, the original failure was likely interactional and repaired by the combined stack.
5. If any ablation reintroduces q50-scale state explosion, inspect pseudo-data and component decomposition before
   broad production.

## Validation

Implemented tests:

1. `tests/python/test_exdqlm_keep_ablation_tooling.py`
2. `tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R`

Minimum validation commands:

```bash
python3 -m py_compile repro/audits/prepare_exdqlm_keep_guarded_repro.py
python3 -m py_compile repro/audits/prepare_exdqlm_keep_ablation_matrix.py
python3 -m unittest tests.python.test_exdqlm_keep_ablation_tooling -v
Rscript --vanilla -e "testthat::test_file('tests/testthat/test_exdqlm_multivar_keep_latent_pseudodata_audit.R')"
```

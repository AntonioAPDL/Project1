# HE3 Current-Authority noTF Guard-Loop Audit

Timestamp: 2026-06-26.

This audit covers the current HE3 exDQLM multivariate ablation blocker in:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_current_authority_20260625`

The active NDLM broad-screen campaign is separate and was not modified.

## Executive Finding

The current blocker is not evidence of a Kalman crash, non-finite pseudo-data, or
an absolute state explosion. It is a relative state-growth guard loop in the
`2021-12-21/noTF/q50` lane caused by a tiny previous accepted state-norm
denominator and a missing `state_norm_ratio_ref_floor` in the HE3
current-authority template.

The corrected policy keeps all hard safety gates:

- finite ELBO/state/sigma/gamma guard;
- absolute state-norm cap;
- delayed relative state-growth guard.

It adds the scale-aware denominator floor already implemented in the shared
DISC-W guard helper:

```yaml
state_norm_abs_cap_scale: per_time
state_norm_ratio_ref_floor: 0.1
```

This is a root-cause fix for the false-positive relative ratio, not a loosening
of the terminal gates or a suppression of the failure.

## Runtime Evidence

Current matrix:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_current_authority_20260625/control/he3_exdqlm_ablation_current_authority_v1/matrix_status.csv`

After refreshing from manifests, the only failed row is:

`multimodel_20211221_v8_he2partial20260623_exdqlm_multivar_keep_he3_noTF`

The sibling `2021-12-21/noTrend` row is complete; a stale status snapshot had
previously shown it as pending.

The failed q50 diagnostics are:

`.../runs/multimodel_20211221_v8_he2partial20260623_exdqlm_multivar_keep_he3_noTF/fit/q=50/logs/sampling_diagnostics.log`

with terminal preflight:

```text
[sampling_preflight] p0=0.5 phase=vb_terminal elapsed=0.000s detail=update_iters=0 min_update_iters=50 guard_count=44 last_guard_iter=119
```

The repeated guard message in `fit.log` is:

```text
state_growth_effective_ratio=25.73363 exceeds max_ratio=25
raw_state_growth_ratio=25.73363
ref_floor_total=NA
sigma_exp=0.4615097
gamma_exp=0
state_norm_sq=18157.5
crit_state_norm_sq=0
gamsig_update_iters=0
frozen=true
```

All other noTF quantiles reached sampling finalization. The q50 state is also
small on the long-history diagnostic scale:

| Quantity | Value |
|---|---:|
| `T` | 12626 |
| `state_norm_sq` | 18157.5 |
| `state_norm_sq / T` | 1.4381 |
| configured absolute cap, per time | 1,000,000 |

With the intended floor:

| Quantity | Value |
|---|---:|
| `state_norm_ratio_ref_floor * T` | 1262.6 |
| effective ratio | 14.3810 |
| configured max ratio | 25 |

Therefore the failed q50 proposal is bounded under the hard cap and would not
trip the relative guard once the near-zero denominator is regularized.

## Code Contract

The relevant guard implementation is `disc_w_iteration_guard_decision(...)` in:

`R/disc_w/09_fit_guards.R`

The helper already supports:

1. unconditional finite checks once `theta_update` is true;
2. hard absolute state-norm caps;
3. scale-aware relative state-growth checks using
   `state_norm_ratio_ref_floor`;
4. raw ratio logging plus effective-ratio logging.

The stage bridge already exports the optional floor when configured:

`R/unified/stages/stage_fit.R`

The config parser already accepts and validates the key:

`R/unified/config.R`

The deterministic test locking the intended semantics is:

`tests/testthat/test_disc_w_fit_guards.R`

where a q35-like near-zero denominator fixture passes with
`state_norm_ratio_ref_floor = 0.1` but a material effective jump still fails.

## Prior Repair Context

The June 9 HE3 repair documented why the finite guard, absolute cap, q50
gamma-zero re-anchoring, and state-norm scale must remain distinct:

`docs/he3_exdqlm_ablation_recovery_plan_20260609.md`

The June 13 Table 1 repair introduced the scale-aware denominator floor as the
correct fix for false-positive relative jumps from tiny previous states:

`docs/he2_table1_root_repair_and_article_sync_plan_20260613.md`

The current HE3 failure is the same denominator pathology in a current-authority
ablation row. The code was already capable of the correct behavior; the HE3
current-authority template omitted the required floor.

## Implemented Fix

The HE3 current-authority template now sets:

`config/multimodel_v8_he3_exdqlm_ablation_current_authority_20260625.template.yaml`

```yaml
fit_policy:
  exdqlm_multivar:
    gamma_sigma_overrides:
      stabilization:
        state_guard_enabled: true
        state_guard_start_iter: 20
        state_guard_refreeze_iters: 20
        state_hold_after_guard_iters: 20
        state_norm_max_ratio: 25
        state_norm_abs_cap: 1.0e6
        state_norm_abs_cap_scale: per_time
        state_norm_ratio_ref_floor: 0.1
```

The generated HE3 configs inherit the same policy in:

`config/unified_runs_he3_exdqlm_ablation_current_authority_20260625/`

The validator now fails any HE3 launch config where the relative state-growth
guard is active inside the VB budget but no positive
`state_norm_ratio_ref_floor` is present:

`scripts/validate_he3_exdqlm_ablation.py`

The Python tooling tests now check that the floor is inherited both by the
resolved fit config and by the `he3_ablation.gamma_sigma_overrides` metadata:

`tests/python/test_he3_exdqlm_ablation_tooling.py`

## Validation After Patch

The following checks passed after regenerating the current-authority HE3 configs:

```bash
python3 -m py_compile \
  scripts/build_he3_exdqlm_ablation_matrix.py \
  scripts/run_he3_exdqlm_ablation_queue.py \
  scripts/validate_he3_exdqlm_ablation.py \
  scripts/audit_he3_exdqlm_ablation.py \
  scripts/he3_exdqlm_ablation_lib.py

python3 -m unittest tests.python.test_he3_exdqlm_ablation_tooling -v

Rscript --vanilla -e 'testthat::test_file("tests/testthat/test_disc_w_fit_guards.R")'

python3 scripts/validate_he3_exdqlm_ablation.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_current_authority_20260625/control/he3_exdqlm_ablation_current_authority_v1 \
  --template config/multimodel_v8_he3_exdqlm_ablation_current_authority_20260625.template.yaml
```

Additional config audit:

- 25 generated launch configs checked;
- 0 missing `state_norm_ratio_ref_floor` in the resolved fit config;
- 0 missing `state_norm_ratio_ref_floor` in HE3 metadata.

## Recovery Procedure

1. Regenerate the HE3 matrix/configs from the patched current-authority template.
2. Validate the matrix with `scripts/validate_he3_exdqlm_ablation.py`.
3. Archive the failed `2021-12-21/noTF` run directory under
   `failed_evidence/`.
4. Relaunch only the archived failed row first.
5. If it passes, resume the queue for the remaining not-started rows.
6. After all 30 rows pass, run the standard HE3 completion hooks:
   - `scripts/build_he3_exdqlm_ablation_summary.py`;
   - `scripts/audit_he3_exdqlm_ablation.py`;
   - `scripts/sync_he3_ablation_article_tables.py`;
   - final validation/compile checks in the article and corrections repos.

## Residual Risk

This fix addresses the observed guard-loop root cause. It does not claim that
every remaining ablation row must pass. Remaining rows can still fail for valid
model-specific reasons, but a bounded long-history state should no longer be
rejected only because the previous accepted state norm is too close to zero to
define a meaningful relative growth denominator.

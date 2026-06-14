# HE2 Table 1 Root Repair And Article Sync Plan

Date: 2026-06-13

## Purpose

This plan freezes the current state of the HE2 Table 1 targeted repair campaign
and defines the next implementation path for finishing the remaining model
launches, updating manuscript-facing CRPS/check-loss tables, and keeping the
workflow reproducible across:

- `project1_ucsc_phd`;
- `Evironmetrics---REVISED-DOC-Corrected-2`;
- `Corrections---Project-1`.

The immediate rule is: do not refresh the article/corrections tables until the
remaining repair queue is finished and the failed lane has been fixed at the
root. The current article and corrections repositories are internally
consistent, but the Table 1 source is intentionally stale relative to the
unfinished targeted repair queue.

## Current State

### Repositories

Workflow repository:

- root: `/data/muscat_data/jaguir26/project1_ucsc_phd`;
- branch: `feature/export_posterior_tables`;
- pre-plan implementation baseline: `a16d693`;
- plan commits added after that baseline:
  - `8ea431c` documents the initial root-repair/article-sync plan;
  - `53d67f5` ignores the local live checklist pattern;
  - `541bbaa` refines the guard repair from a material-scale clause to a
    scale-aware reference-floor design;
  - `67c9623` wires the scale-aware state-growth reference floor through the
    active R/unified fit path and adds focused guard/config tests.

Revised article repository:

- root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2`;
- branch: `main`;
- checked head during this audit: `599d8fb`;
- tracked remote: `origin =
  https://github.com/AntonioAPDL/Evironmetrics---REVISED-DOC-Corrected-2.git`;
- note: the clone also has a local `clean_source` remote, but `main` tracks
  `origin/main`.

Corrections repository:

- root: `/data/muscat_data/jaguir26/Corrections---Project-1`;
- branch: `main`;
- checked head during this audit: `a66b68e`;
- status during this audit: clean and synced with `origin/main`.

### Cross-Repo Validation Snapshot

The current manuscript/corrections wiring is internally consistent before the
new Table 1 repair values are promoted:

```bash
python3 scripts/validate_revision_cross_repo_wiring.py \
  --workflow-root /data/muscat_data/jaguir26/project1_ucsc_phd \
  --article-root /data/muscat_data/jaguir26/project1_ucsc_phd/Evironmetrics---REVISED-DOC-Corrected-2 \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1 \
  --output-dir /tmp/revision_cross_repo_wiring_check_latest \
  --check-only --strict
```

Result: pass.

The representative selected-output lineage check also passes:

```bash
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/validate_authoritative_output_lineage.py \
  --article-root Evironmetrics---REVISED-DOC-Corrected-2 \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1 \
  --report-dir /tmp/authoritative_output_lineage_check_latest
```

Result: pass.

These checks mean the repos are coherent today. They do not mean the HE2 Table
1 repair campaign is complete.

## Executive Decision

Do not relaunch the remaining targeted repair queue yet. The failed row should
first be replayed under a repaired state-growth guard, because the current
failure is driven by an unstable denominator in the relative state-growth ratio,
not by a large absolute state.

The first implementation step is therefore a narrow numerical guard repair:

`state_growth_effective_ratio = state_norm_sq / max(prev_state_norm_sq, state_norm_ratio_ref_floor * T)`

when `state_norm_abs_cap_scale = per_time`.

This preserves the existing absolute cap and terminal fail-fast gates. It only
regularizes the denominator used by the relative-ratio guard when the previous
accepted state norm is too close to zero to define a meaningful relative growth
rate.

## Targeted Repair Queue State

Runtime root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612`

Status file:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/publication_relaunch_matrix/matrix_status.csv`

Current count:

| Status | Rows |
|---|---:|
| pass | 16 |
| fail | 1 |
| not_started | 7 |
| total | 24 |

By cutoff:

| Cutoff | pass | fail | not started |
|---|---:|---:|---:|
| 20210123 | 5 | 0 | 0 |
| 20211112 | 3 | 0 | 0 |
| 20211221 | 5 | 0 | 0 |
| 20220511 | 3 | 1 | 1 |
| 20221225 | 0 | 0 | 6 |

Failed row:

| Cutoff | Family | Run id | Failed phase |
|---|---|---|---|
| 20220511 | `dqlm_multivar_al_drop` | `multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_drop` | fit |

Rows not started because the fail-fast queue stopped at the failed row:

- `20220511 exdqlm_multivar_drop`;
- `20221225 dqlm_multivar_al_drop`;
- `20221225 dqlm_univar_al`;
- `20221225 exdqlm_multivar_drop`;
- `20221225 exdqlm_univar`;
- `20221225 ndlm_main_keep`;
- `20221225 ndlm_univar_keep`.

## Failed-Lane Evidence

Failed log:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/runs/multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_drop/fit/q=35/logs/fit.log`

The terminal q35 state is:

| Quantity | Value |
|---|---:|
| final iteration | 160 |
| `gamsig_update_iters` | 11 |
| required `min_update_iters` | 50 |
| final `sigma_exp` | 0.05693132 |
| final `gamma_exp` | 0 |
| final `state_norm_sq` | 22702.47 |
| observation length used for scale check | 12767 |
| `state_norm_sq / T` | 1.778214929 |
| repeated guard count | 54 |
| repeated guard reason | `state_growth_ratio=610.3149 exceeds max_ratio=25` |
| inferred previous accepted `state_norm_sq` | about 37.198 |
| inferred previous accepted `state_norm_sq / T` | about 0.002914 |

The key point is that the relative state-growth ratio is large because the
previous accepted state norm is tiny. The absolute per-time state scale is not
large. This differs from the old catastrophic AL-M-T0 failures, where the
state norm per time and sigma became genuinely explosive.

The generated config for this run uses the repaired warmup policy:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/generated_configs/multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_drop.yaml`

Relevant q35 settings:

- `warmup_freeze_iters: 40`;
- `min_update_iters: 50`;
- `max_iter: 160`;
- `freeze_target: gamma_sigma`;
- `state_norm_max_ratio: 25`;
- `state_norm_abs_cap: 1.0e12`;
- `state_norm_abs_cap_scale: per_time`;
- `state_blend_alpha: 1.0`;
- `cov_blend_alpha: 1.0`;
- terminal sampling guard in `fail_fast` mode.

## Guard Path

The active guard helper is `R/disc_w/09_fit_guards.R`, function
`disc_w_iteration_guard_decision(...)`.

The helper currently:

1. computes `state_growth_ratio = state_norm_sq / prev_state_norm_sq` when the
   guard is active and the gamma/sigma block is not frozen;
2. hard-fails on non-finite ELBO/state/sigma/gamma;
3. hard-fails on the absolute state norm cap, using `state_norm_sq / T` when
   `state_norm_abs_cap_scale = per_time`;
4. hard-fails on `state_growth_ratio > state_norm_max_ratio`, regardless of
   whether the absolute state norm is benign.

Both main entrypoints call this helper:

- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`;
- `DISC_Optimal_Synth_Ranges_W.r`.

Existing tests cover non-finite payloads, delayed guard start, absolute cap
semantics, and backoff behavior. They do not yet test the present failure mode:
a huge relative ratio caused by a near-zero previous accepted state norm while
the current absolute state norm per observation remains small.

## Working Diagnosis

The leading diagnosis is a guard-policy deadlock, not a new broad model failure:

- the failed q35 path repeatedly rolls back the same otherwise finite proposal;
- the proposal has modest `state_norm_sq / T = 1.78`;
- `sigma_exp` is small and finite;
- `gamma_exp = 0`, as expected under the AL-forced model;
- the queue stopped only because the repeated rollback left only 11 valid
  gamma/sigma update iterations before the terminal minimum-update gate.

This does not prove the q35 fit is publishable. It does show that relaunching
the same config without a guard semantic repair is likely to reproduce the same
failure.

## What Not To Do

Do not use any of these as the primary fix:

- disable the state guard;
- raise `state_norm_max_ratio` until q35 passes;
- lower `min_update_iters`;
- disable terminal fail-fast;
- treat the failed row as publishable because the absolute state norm is small;
- rebuild manuscript tables from partial campaign outputs.

Those moves would either hide a real failure mode or make the publication table
non-reproducible.

Also do not implement the denominator floor as an undocumented constant inside
one entrypoint. It must be wired through the shared guard helper and, if used by
the Table 1 queue, through unified config validation and stage-fit environment
export.

## Root Fix Plan

### Phase 1: Add A Scale-Aware Reference Floor To The State-Growth Guard

The root implementation fix should preserve all hard safety checks while
preventing ratio-only false positives from tiny reference states.

Recommended semantics:

1. Keep the non-finite guard unchanged.
2. Keep the absolute state norm cap unchanged.
3. Continue to compute and log the raw `state_growth_ratio`.
4. Compute a second, effective ratio using a scale-aware lower bound for the
   previous accepted state norm. The lower bound must be interpreted on the
   same scale as the absolute cap:
   - if `state_norm_abs_cap_scale = per_time`, use
     `max(prev_state_norm_sq, state_norm_ratio_ref_floor * T)`;
   - if `state_norm_abs_cap_scale = total`, use
     `max(prev_state_norm_sq, state_norm_ratio_ref_floor)`.
5. Apply the ratio guard to the effective ratio, while retaining the raw ratio
   in diagnostics.

The intended design is:

- add a first-class config/env key such as
  `stabilization.state_norm_ratio_ref_floor` /
  `DISC_GAMSIG_STATE_NORM_RATIO_REF_FLOOR`;
- interpret this key on the current cap scale (`per_time` or `total`) rather
  than adding a second scale key;
- keep legacy behavior when the key is absent, unless a deliberate global
  default is justified by tests;
- use the q35 failed-lane fixture to validate that a tiny previous accepted
  state norm does not create a meaningless ratio-only failure;
- use catastrophic historical fixtures to validate that genuine explosions are
  still blocked.

The initial candidate value for the failed q35 replay is
`state_norm_ratio_ref_floor = 0.1` on the per-time scale. With
`T = 12767`, this makes the q35 effective denominator `1276.7` rather than the
observed previous accepted norm `37.198`, yielding an effective ratio of about
`17.8`, below the configured cap of `25`. This is intentionally conservative:
it fixes the near-zero denominator pathology without raising
`state_norm_max_ratio`.

This is stronger than simply changing `state_norm_max_ratio`, because it
separates two concepts:

- absolute numerical safety;
- relative jump from the immediately previous accepted iterate, with the
  denominator regularized only when that previous iterate is too close to zero
  to define a meaningful relative growth rate.

The calibration evidence from the current repair queue supports this direction:
completed exAL-M-T0 q35 rows have terminal `state_norm_sq / T` values ranging
from about `37.8` to `395.9`, while the failed AL-M-T0 q35 proposal has
`state_norm_sq / T = 1.778`. The failed proposal is therefore not suspicious on
absolute scale; the suspicious value is the denominator
`prev_state_norm_sq / T = 0.002914`.

### Phase 2: Test The New Guard Semantics

Add focused tests in `tests/testthat/test_disc_w_fit_guards.R`:

1. q35-like fixture:
   - `state_norm_sq = 22702.47`;
   - `state_norm_length = 12767`;
   - `prev_state_norm_sq = 37.19796`;
   - `state_norm_max_ratio = 25`;
   - `state_norm_ratio_ref_floor = 0.1` under per-time scaling;
   - absolute cap large enough to be irrelevant;
   - expected result: no ratio-only guard reason.
2. reference-floor fixture:
   - same raw ratio geometry but current `state_norm_sq / T` large enough that
     the effective ratio remains above the cap even after applying the
     reference floor;
   - expected result: ratio guard fires.
3. catastrophic absolute fixture:
   - old-style huge state norm;
   - expected result: absolute cap still fires before ratio logic.
4. non-finite fixture:
   - expected result: finite guard still fires before state-growth logic.

The new key must be wired through all active layers, not only the helper:

- `R/disc_w/09_fit_guards.R`;
- `DISC_Optimal_Synth_Ranges_W.r`;
- `DISC_Optimal_Synth_Ranges_W_transfer_forecast.r`;
- `R/unified/config.R`;
- `R/unified/stages/stage_fit.R`;
- Python tests for generated Table 1 configs if the repair queue uses the key.

### Phase 3: Isolated q35 Reproduction Before Queue Relaunch

Before restarting the 24-row queue, run only the failed `20220511`
`dqlm_multivar_al_drop` q35 fit under the patched guard using the exact same
input bundle and discount/prior settings.

The isolated replay must be derived from the generated unified config:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/generated_configs/multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_drop.yaml`

Do not hand-build an approximate config for this replay. The point is to test
one code-path change against the same model, bundle, priors, and warmup policy.

Acceptance criteria:

- fit reaches terminal iteration without repeated guard lockout;
- `gamsig_update_iters >= 50`;
- fit/post health files are produced;
- `state_norm_sq / T` remains far below the production health limit;
- `sigma_exp` remains finite and within the existing health gate;
- `gamma_exp` remains fixed at 0 for the AL-forced model;
- no retained `.RData` is required after evidence capture unless explicitly
  requested.

### Phase 4: If q35 Still Fails, Use A Minimal Damping Ladder

If the semantic guard fix is not enough, do not broaden the campaign. Run a
small q35-only ladder analogous to the validated q65 P4 repair:

| Candidate | `state_blend_alpha` | `cov_blend_alpha` | Notes |
|---|---:|---:|---|
| A | 0.25 | 0.5 | mild damping |
| B | 0.15 | 0.5 | same state damping scale used by q65 P4 |
| C | 0.10 | 0.5 | stronger damping if A/B fail |

Use the smallest intervention that passes the same terminal gates. Do not
lower the gates to force a pass.

### Phase 5: Resume Only The Needed Queue Rows

After q35 passes in isolation:

1. preserve the 16 passed rows;
2. use the selected `--run-ids` reset path to archive/reset only the failed row
   and the seven not-started rows;
3. relaunch the targeted repair queue for those rows only;
4. keep cleanup enabled after post, so publication runs do not retain heavy
   `.RData` files;
5. keep fail-fast enabled for the publication queue, so no failed value can be
   silently promoted.

The target completion state is 24 of 24 rows at `report/pass`.

The reset summary must be inspected before relaunch. It should list exactly
eight selected run IDs and preserve the 16 completed rows.

### Phase 5 Implementation Update: q35 Damping-A Selected

The scale-aware reference floor was implemented and tested first. The first
isolated q35 replay used the exact generated failed-row config plus
`state_norm_ratio_ref_floor = 0.1`:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/he2_table1_q35_guard_floor_replay_20260613/runs/multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_drop_q35_guardfloor_replay`

That replay showed the floor semantics were wired correctly, but floor-only
was not enough for this lane. The repeated guard moved from a near-zero
denominator false positive to a genuine candidate jump relative to the
regularized denominator:

| Quantity | Value |
|---|---:|
| repeated iteration | 52 |
| `state_growth_effective_ratio` | 610.3149 |
| raw `state_growth_ratio` | 610.3149 |
| `ref_floor_total` | 1276.7 |
| configured max ratio | 25 |

The correct next step was therefore the pre-planned minimal damping ladder, not
loosening the terminal gates or raising `state_norm_max_ratio`.

Candidate A passed in isolation with the same generated model config, the same
input bundle, the same terminal gates, and only q35 stabilization changed to:

- `state_norm_ratio_ref_floor: 0.1`;
- `state_blend_alpha: 0.25`;
- `cov_blend_alpha: 0.5`.

Successful replay root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/he2_table1_q35_guard_floor_dampingA_replay_20260613/runs/multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_drop_q35_guardfloor_dampingA_replay`

Fit log:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/he2_table1_q35_guard_floor_dampingA_replay_20260613/runs/multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_drop_q35_guardfloor_dampingA_replay/fit/q=35/logs/fit.log`

Captured evidence:

`reports/he2_table1_q35_guard_floor_dampingA_replay_20260613/FIT_LOG_SUMMARY.md`

Terminal fit summary:

| Quantity | Value |
|---|---:|
| final iteration | 160 |
| `gamsig_update_iters` | 120 |
| final `sigma_exp` | 0.05416865 |
| final `gamma_exp` | 0 |
| final `state_norm_sq` | 13687.35 |
| `state_norm_sq / T` | 1.0720885083 |
| guard count | 0 |
| frozen terminal state | false |
| terminal fail | false |

This is now the selected policy for the targeted Table 1 q35 row. It is
minimal, scoped to the problematic quantile, preserves all fail-fast gates, and
is explicitly tested in
`tests/python/test_he2_table1_targeted_repair_20260612.py`.

The generated queue configs were rebuilt after this promotion:

```bash
python3 scripts/build_he2_bayesian_publication_relaunch_configs.py \
  --config config/he2_bayesian_publication_relaunch_table1_targeted_repair_20260612.template.yaml
```

The generated failed-row config now contains the selected q35 policy:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_table1_targeted_repair_20260612/control/generated_configs/multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_drop.yaml`

Focused validation after the promotion:

```bash
python3 -m unittest \
  tests.python.test_he2_publication_relaunch_builder_selection \
  tests.python.test_he2_publication_relaunch_validator \
  tests.python.test_he2_table1_targeted_repair_20260612 \
  tests.python.test_disc_sampling_diagnostics_source_contract \
  tests.python.test_stage_fit_quantile_gamma_sigma_overrides

Rscript -e 'testthat::test_file("tests/testthat/test_disc_w_fit_guards.R"); testthat::test_file("tests/testthat/test_disc_w_state_blend.R")'
```

Result: all focused Python and R tests passed.

The queue can now be resumed by resetting exactly the failed row plus the seven
rows that were blocked by queue fail-fast:

- `multimodel_20220511_v8_he2tbl1fix20260612_dqlm_multivar_al_drop`;
- `multimodel_20220511_v8_he2tbl1fix20260612_exdqlm_multivar_drop`;
- `multimodel_20221225_v8_he2tbl1fix20260612_dqlm_multivar_al_drop`;
- `multimodel_20221225_v8_he2tbl1fix20260612_dqlm_univar_al`;
- `multimodel_20221225_v8_he2tbl1fix20260612_exdqlm_multivar_drop`;
- `multimodel_20221225_v8_he2tbl1fix20260612_exdqlm_univar`;
- `multimodel_20221225_v8_he2tbl1fix20260612_ndlm_main_keep`;
- `multimodel_20221225_v8_he2tbl1fix20260612_ndlm_univar_keep`.

Do not reset the 16 rows already at `report/pass`.

### Phase 6: Build Repair Compare Outputs

Once all 24 selected rows pass:

1. build compare bundles for each affected cutoff;
2. verify CRPS tables exist under every run-local post output;
3. verify `run_manifest.yaml` reports `fit`, `post`, `validate`, and `report`
   as `pass`;
4. verify heavy `.RData/.rda/.Rda` cleanup for publication run roots;
5. write a delta report comparing current article Table 1 values versus the
   repaired values.

### Phase 7: Promote Through A Manifest Overlay, Not A Manual Table Patch

The current publication manifest builder hard-codes promoted family roots in
`scripts/build_he2_bayesian_publication_manifest.py`. The relevant constants
are:

- `PROMOTED_AL_KEEP_ROOT`;
- `PROMOTED_EXAL_DROP_ROOT`;
- `PROMOTED_AL_DROP_ROOT`;
- `PROMOTED_UNIVAR_AL_EXAL_ROOT`;
- `PROMOTED_NDLM_ROOT`.

The Table 1 repair campaign is a targeted replacement of selected cells, not a
new global family root. The robust promotion path is therefore a formal
replacement overlay keyed by:

- `cutoff`;
- `family`;
- `manuscript_label`;
- `run_id`;
- `run_root`;
- `campaign_lineage`;
- `replacement_reason`;
- `score_source`;
- `expected input bundle id`.

The builder should:

1. build the default 45-row manifest;
2. apply the replacement overlay for completed targeted-repair rows;
3. require every overlay row to have `fit/post/validate/report = pass`;
4. require every overlay row to match the canonical 20260510 shared input
   bundle;
5. require local CRPS sources to exist;
6. fail if any selected overlay row is still `fail` or `not_started`.

This prevents accidental manual editing of Table 1 and makes future replacement
campaigns repeatable.

### Phase 8: Regenerate HE2, HE4, Article, And Corrections Assets

After the manifest overlay passes:

1. rebuild `reports/he2_publication_manifest/*`;
2. refresh the revised article snapshot under
   `Evironmetrics---REVISED-DOC-Corrected-2/artifacts/he2_publication_freeze`;
3. rebuild generated article tables with
   `Evironmetrics---REVISED-DOC-Corrected-2/scripts/build_generated_table_includes.py`;
4. rebuild HE4 quantile check-loss tables from the refreshed HE2 manifest,
   because HE4 depends on current HE2 AL/exAL quantile-family rows;
5. sync generated table includes into `Corrections---Project-1`;
6. run the strict cross-repo validator again;
7. compile the revised article and corrections document.

Table values should stay at the manuscript-standard precision currently used by
the generated table scripts: five decimals for displayed CRPS/check-loss values.

### Phase 9: Commit Order

Use small commits in this order:

1. workflow root fix and tests;
2. targeted repair completion docs and manifests;
3. manifest-overlay promotion tooling;
4. article generated artifacts/tables;
5. corrections generated table includes/prose links.

Push only after each repository is clean and the relevant validation gates pass.

## Acceptance Gates

Do not promote repaired values unless all of these pass:

| Gate | Required result |
|---|---|
| Guard unit tests | pass |
| Table 1 package tests | pass |
| q35 isolated replay | pass |
| 24-row repair queue | 24 `report/pass` rows |
| heavy runtime cleanup | no publication-retained `.RData/.rda/.Rda` unless explicitly retained |
| manifest overlay validation | pass |
| canonical input-bundle congruence | pass for every repaired row |
| HE2 generated table rebuild | pass |
| HE4 check-loss rebuild | pass |
| revised article cross-repo validation | pass |
| corrections sync validation | pass |
| revised article compile | pass |
| corrections compile | pass |

## Definition Of Done

This repair is complete only when all of the following are true:

1. The q35 guard replay passes with the original terminal gates intact.
2. The targeted repair matrix reaches 24 of 24 rows at `report/pass`.
3. The refreshed HE2 manifest applies targeted repairs through a validated
   overlay, not manual table edits.
4. HE2 Table 1 and HE4 check-loss tables are regenerated from the refreshed
   manifest.
5. The revised article and corrections repo both consume the same generated
   table sources.
6. Cross-repo validation and document compiles pass.
7. The workflow, revised article, and corrections repos are clean and their
   final heads are recorded.

## Current Recommendation

The next implementation pass should reset only the eight rows listed in the
Phase 5 implementation update and relaunch them under the rebuilt generated
configs. The 16 completed rows should remain archived/preserved. Promotion to
the article and corrections repositories should still wait until the targeted
repair matrix reaches 24 of 24 rows at `report/pass` and the manifest overlay
validation gates pass.

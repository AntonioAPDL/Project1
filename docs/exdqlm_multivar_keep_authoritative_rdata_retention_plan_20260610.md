# exDQLM Multivar Keep Authoritative RData Retention Plan

Date: 2026-06-10

Scope: clean obsolete retained `.RData` / `.rda` fit-state blobs, then rerun the current
authoritative HE2 `exAL-M-T1` / `exdqlm_multivar_keep` winner set in a new isolated
no-cleanup runtime root so all five cutoff models retain their per-quantile fit-state
objects for careful figure polishing.

## Current State

The current production-authoritative winner source of truth is
[`docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`](exdqlm_multivar_keep_authoritative_specs_20260601.yaml).
It points to the completed grid root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_epsilon_discount_grid_20260524`

Inventory on 2026-06-10 confirmed:

| Category | Files | Size GiB | Action |
|---|---:|---:|---|
| current authoritative grid | 0 | 0.00 | already clean |
| selected-output support rerun | 0 | 0.00 | already clean |
| protected old live roots named by user | 23 | 19.92 | do not delete |
| R package/library `.rda` under `repro/runtime` | 30 | ~0.00 | do not delete |
| warmstart seed outputs | 7 | 22.22 | cleanable after manifest |
| legacy/diagnostic/repro fit-state outputs | 41 | 30.86 | cleanable after manifest |

The production roots therefore are clean, but the workspace is not globally free of
large retained fit-state objects. The new retained rerun will intentionally reintroduce
`.RData` under one isolated 2026-06-10 root.

Post-cleanup execution update:

| Check | Result |
|---|---|
| cleanup dry-run report | `repro/reports/cleanup_runs/20260610T081435Z_exdqlm_keep_pre_retained_rerun_20260610_dryrun` |
| cleanup apply report | `repro/reports/cleanup_runs/20260610T081543Z_exdqlm_keep_pre_retained_rerun_20260610_apply` |
| deleted files | 48 |
| deleted bytes | 56,992,986,063 planned; 56,871,358,464 observed freed |
| `/data` free after cleanup | about 493 GiB |
| remaining model `.RData` outside new retained root | only protected old-live roots |
| remaining `.rda` outside protected old-live roots | package/library data under `repro/runtime` |

## Cleanup Contract

Use the tracked cleanup manifest:

[`config/he2_rdata_cleanup/exdqlm_keep_pre_retained_rerun_20260610.yaml`](../config/he2_rdata_cleanup/exdqlm_keep_pre_retained_rerun_20260610.yaml)

This manifest:

1. excludes the four protected old live run roots named by the user;
2. excludes the current authoritative grid and selected-output support roots;
3. excludes the planned retained-rerun root;
4. never targets `repro/runtime` package-library `.rda` files;
5. writes a dry-run/apply report under `repro/reports/cleanup_runs`;
6. copies compact evidence files into `repro/quarantine/cleanup_runs` before deletion.

Dry-run:

```bash
python3 scripts/cleanup_he2_runtime_artifacts.py \
  --config config/he2_rdata_cleanup/exdqlm_keep_pre_retained_rerun_20260610.yaml
```

Apply only after the dry-run inventory is reviewed:

```bash
python3 scripts/cleanup_he2_runtime_artifacts.py \
  --config config/he2_rdata_cleanup/exdqlm_keep_pre_retained_rerun_20260610.yaml \
  --apply
```

Post-cleanup gate:

```bash
find /data/muscat_data/jaguir26/project1_ucsc_phd_runtime \
  -type f \( -iname '*.RData' -o -iname '*.rda' \) -printf '%s %p\n'
```

Expected after apply: only protected old-live roots and any deliberately excluded
non-model package/library data remain before the new retained rerun starts.

## Retained Rerun Contract

The retained rerun must not modify the completed authoritative grid. It will be built
under:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_authoritative_rdata_retention_20260610`

The exact-winner matrix builder is:

[`scripts/build_he2_exdqlm_multivar_keep_authoritative_retained_matrix.py`](../scripts/build_he2_exdqlm_multivar_keep_authoritative_retained_matrix.py)

It reads the authoritative YAML and clones exactly these five source rows:

| Cutoff | Winner spec | Source run |
|---|---|---|
| 20210123 | `c04_eps365` | `multimodel_20210123_v8_he2grid_c04_eps365_exdqlm_multivar_keep` |
| 20211112 | `c04_eps365` | `multimodel_20211112_v8_he2grid_c04_eps365_exdqlm_multivar_keep` |
| 20211221 | `c03_eps030` | `multimodel_20211221_v8_he2grid_c03_eps030_exdqlm_multivar_keep` |
| 20220511 | `c02_eps060` | `multimodel_20220511_v8_he2grid_c02_eps060_exdqlm_multivar_keep` |
| 20221225 | `c05_eps030` | `multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep` |

It then rewrites only run identity and runtime root paths, preserving:

- canonical 20260510 input bundle contract;
- log1p analysis scale;
- active quantiles `05|20|35|50|65|80|95`;
- winner-specific discount factors, `epsilon`, and `c_factor`;
- `max_iter = 100`;
- transfer `keep` semantics;
- q50 component diagnostics and post export settings from the winner configs.

Prepare matrix:

```bash
python3 scripts/build_he2_exdqlm_multivar_keep_authoritative_retained_matrix.py \
  --reset-status
```

Launch command is written into:

`.../control/publication_relaunch_matrix/RETAINED_RDATA_SCOPE.md`

Prepared matrix path after the 2026-06-10 prelaunch build:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_authoritative_rdata_retention_20260610/control/publication_relaunch_matrix`

Prepared matrix validation:

| Check | Result |
|---|---|
| exact rows | 5 |
| quantile fits | 35 |
| generated config run-root rewrite | pass |
| retained/no-cleanup debug contract | pass |
| current `.RData` in retained root before launch | 0 |

The launch uses `scripts/run_unified_without_cleanup.sh` through the queue
`--no-cleanup` flag, so `CLEANUP_RDATA_AFTER_POST=0` and the 35 fit-state
objects survive post.

## Resource Plan

Available machine snapshot at planning time:

| Resource | Observed |
|---|---:|
| CPU threads | 64 |
| memory available | ~495 GiB |
| `/data` free | ~440 GiB before cleanup |

Prior no-cleanup smoke evidence retained 21 `.RData` files totaling about
154.38 GiB. Scaling to 35 quantile files suggests roughly 250 to 270 GiB for
this retained rerun. The cleanup manifest is expected to free about 53 GiB from
cleanable stale objects, leaving a comfortable but finite disk margin.

Queue defaults for this retained rerun:

| Setting | Value | Rationale |
|---|---:|---|
| run rows | 5 | one per cutoff winner |
| quantile workers per row | 7 | one per quantile |
| maximum active quantile workers | 35 | uses roughly half of 64 CPU threads |
| `ordinary_max_concurrent` | 5 | launch all five rows if memory/disk gates allow |
| `heavy_cutoff_max_concurrent` | 1 | only one `20221225` row exists |
| launch free-space gate | 300 GiB | avoid starting retained rows if disk margin is too low |
| heavy free-space gate | 320 GiB | extra guard for the longest cutoff |
| launch memory gate | 160 GiB | retain enough headroom for post loads |
| heavy memory gate | 180 GiB | extra guard for the longest cutoff |

## Validation Gates

Before launch:

1. `python3 -m py_compile scripts/build_he2_exdqlm_multivar_keep_authoritative_retained_matrix.py`
2. `python3 -m unittest tests.python.test_he2_exdqlm_keep_authoritative_retained_matrix -v`
3. cleanup dry-run has zero protected/current targets;
4. retained matrix has exactly five rows and 35 quantile fits;
5. generated configs preserve winner specs and point at the new root.

During launch:

1. monitor `matrix_status.csv`;
2. monitor `/data` free space;
3. verify no active process uses a protected old root;
4. check that each row reaches `report/pass`.

After launch:

1. exactly 35 `.RData` / `.rda` fit-state files exist under the retained rerun root;
2. all five runs have `fit/post/validate/report=pass`;
3. post outputs and figure manifests exist for each cutoff;
4. rerun CRPS is numerically consistent with the authoritative grid within expected
   Monte Carlo/posterior sampling variation;
5. plotting scripts can load retained `.RData` directly from the retained root.

## Decision

This plan is coherent and useful: production remains clean, old stale blobs are
removed under an auditable manifest, and the new isolated retained rerun provides
the state objects needed to polish plots without repeatedly refitting.

Do not update the production-authoritative YAML to point at this retained root
unless we explicitly decide the retained rerun should replace the completed
cleanup-enabled grid as the publication lineage. The default intent is support
and plotting, not changing the selected model.

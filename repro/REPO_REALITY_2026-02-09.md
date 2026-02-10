# Repo Reality Report (2026-02-09 Reconciliation Chunk)

## 1) Snapshot At Chunk Start

- Repository: `/data/muscat_data/jaguir26/project1_ucsc_phd`
- Branch: `feature/export_posterior_tables`
- HEAD at start: `ccbc26a` (`feat: make post run-scoped via manifest-driven artifact paths`)
- Ahead/behind vs `origin/feature/export_posterior_tables` at start: `ahead 2`, `behind 0`

### Uncommitted files at chunk start

Modified:
- `DISC_Optimal_Synth_Ranges_NDLM.r`
- `OptimalModelSLexAL.r`
- `R/unified/config.R`
- `R/unified/stages/stage_fit.R`
- `config/unified_run.template.yaml`
- `tests/testthat/test_post_sort_keep_na.R`

Untracked:
- `config/unified_runs/smoke_p2_legacy_bridge.yaml`
- `repro/UNIFIED_WORKFLOW_MASTER_2026-02-07.md`
- `repro/last_heavy_exit.txt`
- `repro/tmp_heavy_20260208_183714_postexports.yaml`
- `repro/tmp_heavy_20260208_183742_postexports.yaml`
- `repro/tools/validate_run.sh`
- `scripts/export_posterior_tables_from_fit_outputs.R`

## 2) Phase Reality Before Reconciliation

Based on committed history only (before this chunk commit):

- **P2** tracker was marked `[x]`, but core P2 wiring still depended on local uncommitted files:
  - legacy output env overrides in `OptimalModelSLexAL.r` and `DISC_Optimal_Synth_Ranges_NDLM.r`
  - model toggles/defaults in `R/unified/config.R` + `config/unified_run.template.yaml`
  - legacy-bridge orchestration in `R/unified/stages/stage_fit.R`
  - smoke config `config/unified_runs/smoke_p2_legacy_bridge.yaml`
- **P5** partial work *was* committed in `ccbc26a`, including run-scoped post artifact pathing and strict env wiring.
- **Portability hazard** existed in committed `config/unified_runs/smoke_p5_post_runscoped.yaml`:
  - `run.run_root` was machine-specific (`/tmp/project1_ucsc_phd/repro/runs`).

## 3) Reconciliation Choice Applied

Chosen option: **Option 1 (make P2 truly complete in history)**.

Actions in this chunk:
1. Commit outstanding P2 wiring files so tracker `P2=[x]` reflects committed history.
2. Keep unrelated dirty/untracked files out of this reconciliation commit.
3. Fix P5 smoke config portability by restoring repo-relative default run root.
4. Add local override mechanism documentation without committing `/tmp` defaults.

## 4) Portability Fix Applied

- Updated `config/unified_runs/smoke_p5_post_runscoped.yaml`:
  - `run.run_root: "repro/runs"` (portable default)
- Added tracked example override file:
  - `config/unified_runs/local_overrides.example.yaml`
- Added ignore rule for real local override file:
  - `.gitignore` now ignores `config/unified_runs/local_overrides.yaml`

Local override usage (documented):

```bash
cp config/unified_runs/smoke_p5_post_runscoped.yaml config/unified_runs/local_overrides.yaml
# edit run.run_root in local_overrides.yaml for local /tmp needs
Rscript --vanilla scripts/unified_run.R --config config/unified_runs/local_overrides.yaml
```

## 5) Phase Support By Committed Code (After Reconciliation)

- **P2 status support:** committed and consistent (`[x]`) for legacy bridge scope:
  - toggles in unified config (`run_exdqlm_multivar`, `run_exdqlm_univar`, `run_ndlm_main`)
  - stage-fit legacy wrappers (univar + NDLM) with run-scoped output capture
  - legacy scripts accept run-scoped output env overrides
  - smoke config exists for fit-only bridge validation
- **P5 status support:** remains `[~]` (partial), as intended:
  - run-scoped post path wiring and strict mode behavior are committed
  - full figures-on + validate/report closure remains future work

## 6) Phases Still Dependent On Uncommitted State

For P2/P5 tracker claims after this reconciliation: **none required**.

Remaining dirty/untracked files in the working tree are unrelated to this reconciliation chunk and were intentionally not used to justify phase advancement.

## 7) Evidence References (already-existing runs)

- P2 smoke evidence run (existing):
  - `repro/runs/20260209_183637/run_manifest.yaml`
  - includes artifacts:
    - `fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
    - `fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`
- P5 strict run-scoped smoke evidence run (existing):
  - `/tmp/project1_ucsc_phd/repro/runs/20260209_210504/run_manifest.yaml`
  - `post/logs/post_runner.log`
  - `post/outputs/20260209_210504/post_smoke_marker.txt`


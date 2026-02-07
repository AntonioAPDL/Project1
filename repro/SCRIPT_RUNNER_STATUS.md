# Script Runner Status

Date: 2026-02-07

## Primary orchestration status

Unified workflow entrypoint is active:

- `scripts/unified_run.R`

It supports:

- YAML config loading + fast-fail validation
- manifest initialization/update
- stage toggles (`forecats`, `fit`, `post`, `validate`, `report`)
- write-audit gating
- scale adapters for legacy fit/post bridges
- validation + report outputs under run root

## Current output contract

Unified runs write only to:

- `repro/runs/<RUN_ID>/...`

Legacy script runners are preserved but deprecated for orchestration:

- `scripts/run_DISC_Optimal_Synth_Ranges_W.R`
- `scripts/run_environmetrics_figures.R`

## Validation automation

Manifest-driven validation/report is implemented via:

- `R/unified/stages/stage_validate.R`
- `R/unified/stages/stage_report.R`

Compare tooling path mismatch is resolved by passing manifest/current paths explicitly and supporting `--manifest` in:

- `repro/compare_to_canonical.py`

## Profiling summary

Profile summary integration is manifest-driven and uses:

- `scripts/summarize_profile_run.py` with `--profile-dir` and `--run-log-path` overrides

## Operational notes

- Stage closure evidence is tracked in `repro/STAGE_CLOSURE_STAGE*.md`.
- Unified implementation checklist is tracked in `repro/UNIFIED_WORKFLOW_IMPLEMENTATION_CHECKLIST.md`.

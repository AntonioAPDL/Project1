# P3 Univariate Theory Smoke

- Config: `config/unified_runs/smoke_p3_univar_theory.yaml`
- Command: `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/smoke_p3_univar_theory.yaml`
- Run ID: `20260210_234304`
- Run root: `repro/runs/20260210_234304`

## Closure and Audit

- Manifest: `repro/runs/20260210_234304/run_manifest.yaml`
- `timestamps.finished_at_utc`: `2026-02-11T07:44:59Z`
- Fit write-audit diff: `repro/runs/20260210_234304/validate/write_audit/fit/fs_diff.patch`
- Fit write-audit diff bytes: `0`

## Univariate Theory Artifact Evidence

- `repro/runs/20260210_234304/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
- `repro/runs/20260210_234304/fit/exdqlm_univar/q=50/logs/univar_theory.log`
- `repro/runs/20260210_234304/fit/exdqlm_univar/q=50/logs/univar_theory_summary.log`

## Manifest Hash Evidence

- `fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
  - `sha256: eda975b93a218a46822f7f74dde6e91131ccd71d9f0db59dca3a0fc189cb474c`
- `fit/exdqlm_univar/q=50/logs/univar_theory.log`
  - `sha256: f39185d000e7e7bbae6cc2559962aea358bd73de4a49c17208c162d104493dc7`

## Notes

- This smoke runs `models.exdqlm_univar.implementation_mode=theory_aligned` with `run_exdqlm_multivar=false` and `run_ndlm_main=false`.
- Shared inputs are run-scoped and validated via `forecats -> data_prep_shared` before fit execution.

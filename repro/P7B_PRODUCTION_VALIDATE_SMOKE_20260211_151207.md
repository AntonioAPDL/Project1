# P7B Production Validation Smoke

- Config: `config/unified_runs/smoke_p7b_production_validate.yaml`
- Command:
  - `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/smoke_p7b_production_validate.yaml`
  - `bash repro/tools/validate_run.sh 20260211_151207 --profile production`
  - `bash repro/tools/validate_run.sh 20260211_151207 --profile production --exit-nonzero`
- RUN_ID: `20260211_151207`
- Run root: `repro/runs/20260211_151207`

## Manifest Closure

- Manifest: `repro/runs/20260211_151207/run_manifest.yaml`
- `timestamps.finished_at_utc`: `2026-02-11T23:16:03Z`
- `validation.status`: `pass`

## Validate/Report Outputs

- `repro/runs/20260211_151207/validate/compare_report.json`
- `repro/runs/20260211_151207/validate/compare_report.txt`
- `repro/runs/20260211_151207/validate/env_drift_report.json`
- `repro/runs/20260211_151207/report/summary.md`
- `repro/runs/20260211_151207/report/summary.json`
- Compare metrics (`compare_report.json`): `matched=1, missing=0, extra=0, mismatched=0`

## Write-Audit Evidence

- `repro/runs/20260211_151207/validate/write_audit/fit/fs_diff.patch` size: `0`
- `repro/runs/20260211_151207/validate/write_audit/post/fs_diff.patch` size: `0`
- `repro/runs/20260211_151207/validate/write_audit/validate/fs_diff.patch` size: `0`
- `repro/runs/20260211_151207/validate/write_audit/report/fs_diff.patch` size: `0`

## Production Validator Output

- `validate_run.sh` with `--profile production`: `RESULT=PASS`
- `validate_run.sh` with `--profile production --exit-nonzero`: exit code `0`, `RESULT=PASS`
- Family-aware summary printed by validator:
  - `require_multivar=false`
  - `require_univar=false`
  - `require_ndlm=false`
  - `family_check.*` all `PASS`

## Family Report Metadata

- `repro/runs/20260211_151207/report/summary.json` contains additive field:
  - `report.families.exdqlm_multivar`
  - `report.families.exdqlm_univar`
  - `report.families.ndlm_main`

## Notes

- This P7B production-profile smoke validates family-aware production gating and reporting metadata in a lightweight orchestration path.
- Quantile/family strictness for enabled families is covered by:
  - shell-level validator logic in `repro/tools/validate_run.sh`
  - deterministic regression tests in `repro/tests/test_validate_run.py`.

# P7A Family Validate Smoke

- Config: `config/unified_runs/smoke_p7_family_validate.yaml`
- Command: `Rscript --vanilla scripts/unified_run.R --config config/unified_runs/smoke_p7_family_validate.yaml`
- Run ID: `20260211_131304`
- Run root: `repro/runs/20260211_131304`

## Closure

- Manifest: `repro/runs/20260211_131304/run_manifest.yaml`
- `timestamps.finished_at_utc`: `2026-02-11T21:40:35Z`
- `validation.status`: `pass`

## Compare + Validation Evidence

- Compare report: `repro/runs/20260211_131304/validate/compare_report.json`
  - `matched=4`
  - `missing=0`
  - `extra=0`
  - `mismatched=0`
- Validator command:
  - `bash repro/tools/validate_run.sh 20260211_131304 --profile smoke`
  - Result: `RESULT=PASS`

## Write-Audit Evidence

- `repro/runs/20260211_131304/validate/write_audit/fit/fs_diff.patch` (0 bytes)
- `repro/runs/20260211_131304/validate/write_audit/post/fs_diff.patch` (0 bytes)
- `repro/runs/20260211_131304/validate/write_audit/validate/fs_diff.patch` (0 bytes)
- `repro/runs/20260211_131304/validate/write_audit/report/fs_diff.patch` (0 bytes)

## Family Artifact Evidence

- Multivar DISC-W:
  - `repro/runs/20260211_131304/fit/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData`
- Univar theory:
  - `repro/runs/20260211_131304/fit/exdqlm_univar/q=50/outputs/variables_50_exAL_synth_DISC_uni.RData`
- NDLM theory:
  - `repro/runs/20260211_131304/fit/ndlm_main/outputs/DISC_variables_50_NDLM_synth_DISC.RData`

## Run-Scoped Post Proof

- Post runner log: `repro/runs/20260211_131304/post/logs/post_runner.log`
- Root-load grep:
  - Pattern: `"/data/muscat_data/jaguir26/project1_ucsc_phd/(variables_|DISC_variables_)"`
  - Scope: `repro/runs/20260211_131304/post/logs`
  - Result: no matches

# P7B Production Proof Run Evidence (FAILED at fit preflight)

- Date: 2026-02-12 UTC
- Run ID: `20260212_112137`
- Config: `config/unified_runs/production_proof_p7b_family.yaml`
- Git commit at run start (from manifest): `1db7e55311c890be0e3740fc603d145230d18bc8`

## Commands used

```bash
# space checks
(df -h /data /tmp / && df -i /data /)

# cleanup policy dry-run and apply
bash repro/tools/cleanup_runs.sh --dry-run --older-than-days 0 --keep-recent 40 --keep-last-success 6 --include-baseline-runs
bash repro/tools/cleanup_runs.sh --apply   --older-than-days 0 --keep-recent 40 --keep-last-success 6 --include-baseline-runs

# proof run (single heavy run)
Rscript --vanilla scripts/unified_run.R --config config/unified_runs/production_proof_p7b_family.yaml
```

## Outcome

`RESULT=FAIL` for this proof attempt.

The run progressed through multivariate quantiles `q=05`, `q=50`, and `q=95`, then failed before launching univariate theory fit due to I/O preflight threshold:

```text
Error: [stage_fit univar q=05] Storage preflight failed.
- path: /data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs/20260212_112137/fit/exdqlm_univar/q=05/outputs
- mountpoint: /data
- filesystem: /dev/md124
- free_gb: 94.10
- used_pct: 90.00%
- free_inodes_pct: 96.25%
- free space 94.10 GB below threshold 100.00 GB
- cleanup_suggestions: prune old repro/runs entries, prune repro/baseline_runs, clear large caches under /data/muscat_data/jaguir26/.cache
Execution halted
```

## Evidence paths

- Manifest (not closed):
  - `repro/runs/20260212_112137/run_manifest.yaml`
  - `timestamps.finished_at_utc: null`
  - `validation.status: pending`
- Resolved config:
  - `repro/runs/20260212_112137/resolved_config.yaml`
- Fit artifacts produced before failure:
  - `repro/runs/20260212_112137/fit/q=05/outputs/DISC_variables_5_exAL_synth_DISC.RData`
  - `repro/runs/20260212_112137/fit/q=50/outputs/DISC_variables_50_exAL_synth_DISC.RData`
  - `repro/runs/20260212_112137/fit/q=95/outputs/DISC_variables_95_exAL_synth_DISC.RData`
- Fit logs:
  - `repro/runs/20260212_112137/fit/q=05/logs/fit.log`
  - `repro/runs/20260212_112137/fit/q=50/logs/fit.log`
  - `repro/runs/20260212_112137/fit/q=95/logs/fit.log`
- Write-audit (fit pre-stage snapshot only; run aborted before validate stage):
  - `repro/runs/20260212_112137/validate/write_audit/fit/fs_before.tsv`
- Cleanup reports used to reclaim headroom:
  - `repro/reports/cleanup_runs/cleanup_20260212_201240.log` (dry-run)
  - `repro/reports/cleanup_runs/cleanup_20260212_201249.log` (apply)

## Notes

- This failure is an operational gate trip (storage threshold), not a model-math error.
- Next action for a follow-up proof run is to either:
  1. reclaim additional headroom so `/data` remains >= `run.io.min_free_gb` for the full run, or
  2. lower `run.io.min_free_gb` in the proof config based on measured run footprint and risk tolerance.

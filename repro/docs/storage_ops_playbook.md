# Storage Ops Playbook

## Scope
This playbook covers safe disk-headroom recovery and proof-run gating for unified workflow runs under:

- `repro/runs/*`
- optional baseline cleanup only when explicitly enabled

It does **not** change model math. It is operational tooling only.

## 1) Assess Space

```bash
df -h /data /
df -i /data /
du -xhd1 /data/muscat_data/jaguir26/project1_ucsc_phd/repro | sort -h | tail -n 30
du -xhd1 /data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs | sort -h | tail -n 30
du -xhd1 /data/muscat_data/jaguir26/project1_ucsc_phd/repro/baseline_runs | sort -h | tail -n 30
```

Recommended production-proof headroom:

- free space: `>= 100 GB`
- free inodes: `>= 5%`

These map to `run.io.min_free_gb` and `run.io.min_free_inodes_pct`.

## 2) Protect Canonical Runs

`repro/tools/cleanup_runs.sh` protects runs by default when any of these hold:

1. run_id is referenced by config `validation.canonical_run_id` (except `"__SELF__"`).
2. run directory includes marker file:
   - `.canonical.keep`
   - `.run_keep`
   - `.protect_run`
3. run is in the most-recent `--keep-recent N`.
4. run is in the most-recent successful `--keep-last-success N`.

Baseline runs are never touched unless `--include-baseline-runs` is explicitly set.

## 3) Dry-Run Cleanup (Required First)

```bash
repro/tools/cleanup_runs.sh \
  --dry-run \
  --keep-recent 12 \
  --keep-last-success 12 \
  --older-than-days 14
```

The script writes a timestamped report under:

- `repro/reports/cleanup_runs/cleanup_<UTCSTAMP>.log`

Review the deletion plan before apply.

## 4) Apply Cleanup

```bash
repro/tools/cleanup_runs.sh \
  --apply \
  --keep-recent 12 \
  --keep-last-success 12 \
  --older-than-days 14
```

Re-check headroom immediately:

```bash
df -h /data /
df -i /data /
```

## 5) Production Proof Config

Use:

- `config/unified_runs/production_proof_p7b_family.yaml`

Key gates:

- `run.io.enabled: true`
- `run.io.min_free_gb: 100`
- `run.io.min_free_inodes_pct: 5`
- `write_audit.enforce_from_stage: 2`
- `validation.profile: production`

## 6) Proof Run Command

```bash
Rscript --vanilla scripts/unified_run.R \
  --config config/unified_runs/production_proof_p7b_family.yaml
```

## 7) What NOT to Delete

1. Any run protected by canonical config references.
2. Any run with a protection marker file.
3. Recent successful runs retained by policy.
4. `repro/baseline_runs/*` unless explicitly approved and run with `--include-baseline-runs`.

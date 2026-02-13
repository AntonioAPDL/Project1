# Storage Ops Playbook

## Scope
Operational workflow only. No model semantics changes.

## 1) Assess Space
```bash
df -h /data /
df -i /data /
du -xhd1 /data/muscat_data/jaguir26/project1_ucsc_phd/repro | sort -h | tail -n 30
du -xhd1 /data/muscat_data/jaguir26/project1_ucsc_phd/repro/runs | sort -h | tail -n 30
du -xhd1 /data/muscat_data/jaguir26/project1_ucsc_phd/repro/baseline_runs | sort -h | tail -n 30
```

## 2) Preflight Policy (Run I/O)
Use scoped thresholds in run config:

- `run.io.preflight_scope: legacy`
  - Original behavior: one threshold (`min_free_gb`) on every check.
- `run.io.preflight_scope: fit_start_and_continue`
  - Fit start enforces `min_free_gb_start` (comfort headroom).
  - Later fit checks enforce `min_free_gb_continue` (hard safety floor).
- `run.io.preflight_scope: fit_start_only`
  - Enforce start threshold, then warn-only in-run checks unless free space is critically low (<5 GB).

Evidence emitted to:

- `repro/runs/<RUN_ID>/preflight/*.json`
- `repro/runs/<RUN_ID>/fit/logs/preflight.log`

Recommended production-proof thresholds:

- `min_free_gb_start: 100`
- `min_free_gb_continue: 30` (or `40` if disk pressure remains high)
- `min_free_inodes_pct: 5`

## 3) Protection Rules (Cleanup)
`repro/tools/cleanup_runs.sh` (Python policy backend) protects by default:

1. Runs in `repro/protected_runs.yaml`.
2. Runs referenced by `validation.canonical_run_id` (excluding `__SELF__`).
3. Runs with marker files: `.canonical.keep`, `.run_keep`, `.protect_run`.
4. In-progress/recent runs (6-hour safety window).
5. All baseline runs unless explicitly allowed (`--include-baseline` + allowlist + baseline mode flags).

## 4) Minimal Safe Reclaim Recipe
Run dry-run first for each step:

```bash
# Step 1: thin failed/pending runs only (safe-first)
repro/tools/cleanup_runs.sh --dry-run --thin-failed --keep-last 15 --older-than-days 21

# Step 2: thin old completed non-protected runs
repro/tools/cleanup_runs.sh --dry-run --thin-old --thin-old-days 21 --keep-last 15

# Step 3: optional root .RData inventory (no deletion)
repro/tools/cleanup_runs.sh --dry-run --inventory-root-rdata

# Step 4: optional baseline thinning (explicit and allowlist-gated)
repro/tools/cleanup_runs.sh --dry-run --include-baseline --thin-baseline --thin-old-days 30
```

Apply only after plan review:

```bash
repro/tools/cleanup_runs.sh --apply <same flags as reviewed dry-run>
```

Audit outputs:

- `repro/cleanup_logs/<timestamp>_dryrun.log`
- `repro/cleanup_logs/<timestamp>_dryrun.json`
- `repro/cleanup_logs/<timestamp>_apply.log`
- `repro/cleanup_logs/<timestamp>_apply.json`

## 5) Production-Proof Run Config
Primary config:

- `config/unified_runs/production_proof_p7b_family.yaml`

Key fields:

- `run.io.enabled: true`
- `run.io.preflight_scope: fit_start_and_continue`
- `run.io.min_free_gb_start: 100`
- `run.io.min_free_gb_continue: 30`
- `write_audit.enforce_from_stage: 2`
- `validation.profile: production`

## 6) What NOT to Delete
1. Protected runs (YAML/canonical/marker/in-progress protections).
2. Baselines unless baseline thinning is explicitly enabled and allowlisted.
3. Post outputs and validation/report evidence unless a separate policy explicitly allows it.

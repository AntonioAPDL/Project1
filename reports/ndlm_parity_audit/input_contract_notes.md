# Phase 4 NDLM Input Hash Audit

Status: complete

## Audit Scope

- Audited `405` effective input artifacts across the 45 authoritative Phase 3 source-run rows.
- Artifact set per row: `parameters`, `retros`, `nws`, `glofas`, `ELI`, `ONI`, `PPT`, `SOIL`, `PCA`.

## Headline Findings

- Literal configured paths are stale or missing for `176` audited artifacts, but archived run-local inputs exist for `405` artifacts.
- Effective hashing succeeded for `405` of `405` artifacts; missing effective artifacts: `0`.
- All `135` cutoff/group/artifact contracts are hash-aligned across model variants (`135/135` with one unique hash).
- Path parity is weaker (`0/135` contracts with one unique effective path), which shows that some rows use copied run-local snapshots even when the content is identical.
- Effective input resolution came from archived snapshots for `405` artifacts and from live configured paths for `0` artifacts.
- The single relaunch-backed NDLM keep row contributes `9` archived effective paths inside its run tree, but those files hash-match the baseline-TT counterparts for the same cutoff/group.

## Interpretation

- Phase 4 supports input-content parity across the authoritative HE2 source runs: the NDLM rows and their quantile-model counterparts are seeing the same effective parameters, retrospective series, forecast files, and covariate files within each cutoff/comparison group.
- The main caveat is reproducibility hygiene, not data mismatch: older resolved configs often reference historical top-level paths that no longer exist, while the actual completed runs rely on archived input snapshots under each run root.
- This means later phases should use archived effective inputs as the source of truth, not the literal configured path strings.

## Outputs

- CSV: [input_hash_audit.csv](/data/muscat_data/jaguir26/project1_ucsc_phd/reports/ndlm_parity_audit/input_hash_audit.csv)

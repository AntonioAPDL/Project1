# HE-1 Runtime Feasibility Contract

Status: implemented as a conservative total-runtime benchmark contract for the
Handling Editor HE-1 computational-cost response.

## Source

The latest substantial shared exDQLM/DQLM validation runtime identified for this
revision audit was reported at:

`/data/jaguir26/local/src/exdqlm__wt__shared_fitforecast_v2_1p0p0/validation/fitforecast_v2/runs/20260515_exdqlm_dqlm_dynamic_fitforecast_v2_orchestrated_3500202605200353075941`

Reported last modification time:

`2026-05-20 03:53:15 EDT`

Primary runtime interface:

`interfaces/exdqlm_dqlm_dynamic_fitforecast_v2_shared_interface.csv`

The raw runtime tree was not mounted in the accessible project paths during the
2026-06-15 HE-1 writing pass. The revised article therefore stores only a compact
manifest at:

`Evironmetrics---REVISED-DOC-Corrected-2/artifacts/runtime_benchmark/runtime_manifest.json`

This is deliberate: the Overleaf-facing article repository should not carry full
runtime outputs.

## Measured Object

The shared interface was reported as:

- `1620` rows by `127` columns.
- all `1620` interface rows marked done.
- runtime columns present:
  - `runtime_sec_fit`
  - `runtime_sec_forecast`
  - `fit_runtime_seconds`
  - `forecast_runtime_seconds`
  - `runtime_sec_total`
  - `runtime_sec`

The practical total runtime fields are `runtime_sec_total` and `runtime_sec`.
The component fields `runtime_sec_fit` and `runtime_sec_forecast` were reported
as mostly missing in the sample checked. Consequently, the manuscript and
corrections response must report total end-to-end wall-clock runtime only.

## Planned-Run Nuance

The companion runtime status file `manifests/status_counts.csv` was reported as:

- `done`: `54`
- `pending`: `18`

This means the interface table records completed measured output rows, while the
manifest preserves the broader planned orchestration state. The manuscript should
not imply that every planned orchestration row completed.

## Manuscript-Safe Runtime Claim

Use the following contract:

1. Report a representative single-site end-to-end wall-clock runtime of about two
   hours.
2. State that the benchmark used the total runtime columns
   `runtime_sec_total` / `runtime_sec`.
3. State the hardware context: production Linux server, `64` cores, and roughly
   `503` GiB RAM.
4. State that seven quantile-specific fits can be dispatched in parallel.
5. State that daily refitting is operationally feasible at this single-site
   scale once the input archive is staged.
6. Qualify the benchmark as hardware- and implementation-dependent.
7. Do not report a 100-minute fitting / 20-minute post-processing decomposition
   unless a future runtime source has populated component timing fields.

## Validation

The workflow validator now checks this contract through:

- `scripts/runtime_feasibility_contract.py`
- `scripts/validate_publication_freeze.py`
- `scripts/validate_revision_cross_repo_wiring.py`
- `tests/python/test_he1_runtime_contract.py`

The article-side tests also verify that the runtime manifest and manuscript
wording remain synchronized.


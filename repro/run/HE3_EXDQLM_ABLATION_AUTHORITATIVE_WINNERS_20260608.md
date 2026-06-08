# HE3 exDQLM Authoritative-Winner Ablation Launch

Date: 2026-06-08

This runbook is the current authoritative HE3 ablation workflow. It supersedes the older
April 2026 CF1-sweep HE3 ablation campaign for manuscript-facing values.

## Objective

Run the targeted ablation study for the selected multivariate `exAL-M-T1`
(`exdqlm_multivar_keep`) model across the five rolling-origin cutoffs, using the exact
winner specs frozen in:

- `docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`

The ablation must isolate structural contributions only. Every launched ablation row
inherits the cutoff-specific full winner config/input bundle and changes only the named
component.

## Source Contract

Authoritative full-reference winners:

| Cutoff | Winner spec | Source run | Mean CRPS |
|---|---|---|---:|
| `20210123` | `c04_eps365` | `multimodel_20210123_v8_he2grid_c04_eps365_exdqlm_multivar_keep` | 0.1397088548 |
| `20211112` | `c04_eps365` | `multimodel_20211112_v8_he2grid_c04_eps365_exdqlm_multivar_keep` | 0.0472363501 |
| `20211221` | `c03_eps030` | `multimodel_20211221_v8_he2grid_c03_eps030_exdqlm_multivar_keep` | 0.2653720408 |
| `20220511` | `c02_eps060` | `multimodel_20220511_v8_he2grid_c02_eps060_exdqlm_multivar_keep` | 0.0323251197 |
| `20221225` | `c05_eps030` | `multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep` | 0.6654596601 |

The HE3-compatible source table is generated from that manifest by:

```bash
python3 scripts/build_he3_authoritative_source_table.py
```

Output:

- `config/he3_exdqlm_ablation_authoritative_20260608_best_by_cutoff_long.csv`

The table also includes current `exAL-M-T0` rows from the HE2 publication manifest only
so the post-completion audit can report `noTF` deltas against the drop model. Those rows
are not ablation launch sources.

## Campaign Layout

- Template:
  `config/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608.template.yaml`
- Runtime root:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608`
- Matrix dir:
  `/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608/control/he3_exdqlm_ablation_authoritative_winners_v1`
- Generated configs:
  `config/unified_runs_he3_exdqlm_ablation_authoritative_20260608/`

## Ablation Variants

| Variant | Meaning | Target model id |
|---|---|---|
| `full` | reused full `exAL-M-T1` reference | `exdqlm_multivar_synth_keep` |
| `noTrend` | removes the trend state | `exdqlm_multivar_synth_keep` |
| `noTF` | disables transfer covariates in fit and drops transfer in forecast | `exdqlm_multivar_synth_drop` |
| `noH1` | removes retained harmonic index 1 | `exdqlm_multivar_synth_keep` |
| `noH2` | removes retained harmonic index 2 | `exdqlm_multivar_synth_keep` |
| `noH3` | removes retained harmonic index 3 | `exdqlm_multivar_synth_keep` |

Harmonic index 3 means the third entry in `c(1, 2, 1 / 6.8068493)`, not literal
frequency `3`.

## Launch Policy

- Total rows: 30
- Reused full references: 5
- New launched rows: 25
- `fit.parallel.workers`: 7
- ordinary concurrent rows: 4
- heavy cutoff `20221225`: 1 concurrent row
- group order:
  - group 1: `20211112`
  - group 2: `20221225`
  - group 3: `20210123`, `20211221`, `20220511`

Each launched row uses `scripts/run_unified_with_cleanup.sh`, so `.RData`/`.rda`
artifacts are removed after post-stage completion according to the inherited
`cleanup_rdata_after_post: true` policy.

## Build And Validate

```bash
python3 scripts/build_he3_exdqlm_ablation_matrix.py \
  --template config/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608.template.yaml

python3 scripts/validate_he3_exdqlm_ablation.py \
  --matrix-dir /data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608/control/he3_exdqlm_ablation_authoritative_winners_v1 \
  --template config/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608.template.yaml
```

Validation completed before launch with:

- total rows: 30
- launch rows: 25
- reused rows: 5
- findings: 0

Regression tests completed before launch:

```bash
python3 -m unittest tests.python.test_he3_exdqlm_ablation_tooling -v
```

Result after the noTF/drop save-contract repair: 8 tests passed.

## noTF/drop Save-Contract Repair

The first pilot launch exposed a launch-contract bug in the legacy `drop` entrypoint
used by `noTF`. The `noTF` row correctly set:

- `fit.exdqlm_multivar.legacy.use_covariates: false`
- `models.exdqlm_multivar.forecast_transfer_mode: drop`
- `DISC_W_POST_SAVE_OBJECTIVE_ENABLED=FALSE`

However, `DISC_Optimal_Synth_Ranges_W.r` previously skipped the only call to
`objective_deltas(...)` when the optional post-save objective was disabled. Because the
fit/save side effect lives inside `objective_deltas(...)`, the R process exited with
status zero but wrote no `DISC_variables_*_exAL_synth_simp.RData`. This was a workflow
bug, not evidence that the `noTF` model failed statistically.

The repaired contract is:

1. the legacy `drop` entrypoint always runs one `objective_deltas(...)` evaluation to
   fit and save the selected model state;
2. if `DISC_W_POST_SAVE_OBJECTIVE_ENABLED=FALSE`, it returns immediately after
   `disc_w_save_state(...)`;
3. `stage_fit.R` passes `DISC_W_EXPECTED_RDATA_PATH` to the wrapper; and
4. `scripts/run_DISC_Optimal_Synth_Ranges_W.R` fails loudly with
   `[DISC_W_EXPECTED_RDATA_MISSING]` if the expected RData is absent or empty.

Regression coverage:

- `tests.python.test_he3_exdqlm_ablation_tooling.test_no_tf_drop_fit_still_saves_when_post_objective_disabled`

## Launch

```bash
python3 scripts/launch_he3_exdqlm_ablation.py \
  --template config/multimodel_v8_he3_exdqlm_ablation_authoritative_winners_20260608.template.yaml
```

The controller writes:

- `matrix_status.csv`
- `matrix_status.md`
- `queue.log`
- `controller_state/controller.pid`
- `controller_state/last_launch.json`

## Completion Outputs

When all launch rows pass, the queue automatically runs:

```bash
python3 scripts/build_he3_exdqlm_ablation_summary.py --matrix-dir <matrix-dir>
python3 scripts/audit_he3_exdqlm_ablation.py --matrix-dir <matrix-dir>
python3 scripts/sync_he3_ablation_article_tables.py --matrix-dir <matrix-dir>
```

Expected runtime outputs:

- `reports/he3_exdqlm_ablation/he3_ablation_long.csv`
- `reports/he3_exdqlm_ablation/he3_ablation_wide.csv`
- `reports/he3_exdqlm_ablation/he3_ablation_summary.md`
- `reports/he3_exdqlm_ablation/he3_table_rows.tex`
- `reports/he3_exdqlm_ablation/audit/he3_ablation_audit.csv`
- `reports/he3_exdqlm_ablation/audit/he3_ablation_lead_buckets.csv`
- `reports/he3_exdqlm_ablation/audit/he3_ablation_audit.md`

## Article And Corrections Sync

The completion sync updates:

- `Evironmetrics---REVISED-DOC-2/tables/generated_tex/he3_ablation_crps_main_table.tex`
- `Evironmetrics---REVISED-DOC-2/tables/generated_tex/he3_ablation_crps_body.tex`
- `Evironmetrics---REVISED-DOC-2/MANUSCRIPT_ASSET_MANIFEST.json`
- `Evironmetrics---REVISED-DOC-2/wileyNJD-APA.tex`
- `/data/muscat_data/jaguir26/Corrections---Project-1/main.tex`

The main article receives an `Ablation of the Selected Specification` subsection if it
is not already present. The corrections article stale inline HE3 table is replaced with
the completed authoritative values.

## Guardrails

- Do not edit or stop unrelated live production campaigns.
- Do not use the older April CF1 source table for manuscript-facing HE3 values.
- Treat `full` rows as reused references; do not relaunch them.
- Treat `noTF` as both historical covariate-off and forecast transfer-drop.
- Keep large runtime outputs under the runtime root; do not commit runtime reports by
  default.

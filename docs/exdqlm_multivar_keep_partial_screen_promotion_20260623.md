# exDQLM Multivariate Keep Partial-Screen Promotion

Date: 2026-06-23

This document records the controlled promotion plan and implementation for the
HE2 `exAL-M-T1` / `exdqlm_multivar_keep` partial screening results from:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619`

## Scope

The promotion is intentionally a partial-screen overlay, not a final full-grid
winner manifest. At the 2026-06-23 promotion checkpoint, the screening matrix
had `207` passed rows, `73` failed rows, `4` pending rows, and `31` not-started
rows out of `315`. The promoted rows therefore replace the current publication
authority only for cutoffs where a completed screening row already improves
forecast-window CRPS and passes output/completeness gates. The screening
campaign itself remains exploratory until every row is terminal and a later
full-screen authority overlay is produced.

## Promoted Rows

| cutoff | previous authoritative run | promoted partial-screen run | reason |
|---|---|---|---|
| `20211221` | `multimodel_20211221_v8_he2grid_c03_eps030_exdqlm_multivar_keep` | `multimodel_20211221_v8_he2grid_s02_eps030_exdqlm_multivar_keep` | lower completed CRPS |
| `20220511` | `multimodel_20220511_v8_he2grid_c02_eps060_exdqlm_multivar_keep` | `multimodel_20220511_v8_he2grid_s06_eps001_exdqlm_multivar_keep` | lower completed CRPS |
| `20221225` | `multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep` | `multimodel_20221225_v8_he2grid_s01_eps001_exdqlm_multivar_keep` | lower completed CRPS |

The `20210123` and `20211112` cutoffs remain on the 2026-06-01 authority
because the best completed partial-screen row was worse than the existing
authority for those cutoffs at the checkpoint.

| cutoff | authority CRPS | best completed screen spec | best screen CRPS | decision |
|---|---:|---|---:|---|
| `20210123` | `0.13971` | `s02_eps1450` | `0.15823` | keep existing authority |
| `20211112` | `0.04724` | `s02_eps1450` | `0.11674` | keep existing authority |
| `20211221` | `0.26537` | `s02_eps030` | `0.26045` | promote |
| `20220511` | `0.03233` | `s06_eps001` | `0.02273` | promote |
| `20221225` | `0.66546` | `s01_eps001` | `0.53806` | promote |

## Implemented Authority Path

The current publication authority is now represented by a replacement overlay:

`config/he2_publication_manifest_replacement_overlay_current_authority_20260623.yaml`

The clean rerun template for replaying the three promoted rows into an isolated
publication-authority runtime root is:

`config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_partial_authority_refresh_20260623.template.yaml`

The host-side end-to-end orchestration script is:

`scripts/host_finish_he2_exal_keep_partial_promotion.sh`

This overlay combines:

1. the existing 16 Table 1 targeted repairs from 2026-06-12/13, and
2. the 3 partial-screen `exAL-M-T1` replacements listed above.

The previous 2026-06-01 manifest remains available as the baseline audit trail:

`docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`

The publication manifest builder now uses the 2026-06-23 current-authority
overlay by default. The older Table 1 overlay remains in `config/` as historical
context.

## Clean Authority Rerun

The partial-screen overlay can be used immediately because the promoted runs
already passed fit/post/validate/report, improved CRPS, and retained no heavy
`.RData` artifacts. For a cleaner long-term authority path, replay exactly the
three promoted rows into a dedicated root:

```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd

python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_partial_authority_refresh_20260623.template.yaml \
  --dry-run

python3 scripts/launch_he2_bayesian_publication_relaunch.py \
  --template config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_partial_authority_refresh_20260623.template.yaml \
  --reset-state \
  --start-monitor
```

This template selects only `exAL-M-T1` for `20211221`, `20220511`, and
`20221225` from the refreshed HE2 publication manifest. It therefore inherits
the promoted screening specifications, canonical `20260510` input bundle, full
history start date, current patched workflow, seven quantile lanes per cutoff,
component diagnostics, and post-stage heavy-artifact cleanup. Once those clean
reruns finish, create a new overlay version that points to the clean authority
root rather than the partial-screen root, rebuild the publication manifest, and
repeat the article/corrections/poster sync gates below.

For the complete host-side handoff from an unrestricted shell:

```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
scripts/host_finish_he2_exal_keep_partial_promotion.sh preflight
scripts/host_finish_he2_exal_keep_partial_promotion.sh pause-screen
scripts/host_finish_he2_exal_keep_partial_promotion.sh launch-clean
scripts/host_finish_he2_exal_keep_partial_promotion.sh wait-clean
scripts/host_finish_he2_exal_keep_partial_promotion.sh sync-articles
scripts/host_finish_he2_exal_keep_partial_promotion.sh validate
scripts/host_finish_he2_exal_keep_partial_promotion.sh commit
```

The script also exposes `all`, which runs the same sequence in order. Use the
stepwise form above when you want to inspect the pause and clean-rerun status
before committing.

## Validation Gates

The dedicated validator is:

`scripts/validate_he2_exal_keep_partial_screen_promotion.py`

The operational checkpoint/pause/report helper is:

`scripts/manage_he2_exal_keep_partial_promotion.py`

It checks:

- exactly three partial-screen `exAL-M-T1` replacements;
- replacement cutoffs are `20211221`, `20220511`, and `20221225`;
- each replacement run root exists under the screening campaign;
- fit, post, validate, and report stages are all `pass`;
- required CRPS, figure, and posterior summary outputs exist;
- no retained `.RData`, `.rda`, `.Rda`, or `.rdata` files are present in the
  promoted runs;
- each replacement CRPS is lower than the 2026-06-01 authority;
- the screening matrix is explicitly still incomplete, so the promotion is not
  mislabeled as final full-grid evidence.

Run:

```bash
python3 scripts/validate_he2_exal_keep_partial_screen_promotion.py
python3 scripts/manage_he2_exal_keep_partial_promotion.py status \
  --out-dir reports/he2_exal_keep_partial_screen_promotion_20260623
python3 scripts/manage_he2_exal_keep_partial_promotion.py validate-promotion
```

The default report directory is:

`reports/he2_exal_keep_partial_screen_promotion_20260623/`

## Publication Wiring

The following workflow code was updated so the overlay is first-class:

- `scripts/build_he2_bayesian_publication_manifest.py`
- `scripts/validate_publication_freeze.py`
- `scripts/forecast_design_contract.py`

The manifest builder still validates canonical inputs, pass statuses, CRPS
tables, figure manifests, and heavy-file cleanup. It now permits explicit
`exdqlm_multivar_keep_partial_screen_20260623:*` replacement lineage for
`exAL-M-T1` rows and continues to reject undocumented replacement lineages.

The revised-article HE2 freeze was refreshed with:

```bash
python3 scripts/build_he2_bayesian_publication_manifest.py
python3 scripts/build_he2_publication_parity_gate.py
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/refresh_he2_manifest_snapshot.py \
  --article-root Evironmetrics---REVISED-DOC-Corrected-2 \
  --workflow-root /data/muscat_data/jaguir26/project1_ucsc_phd
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/build_generated_table_includes.py \
  --article-root Evironmetrics---REVISED-DOC-Corrected-2
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/promote_generated_figures_to_disc.py \
  --article-root Evironmetrics---REVISED-DOC-Corrected-2
```

The corrections-response generated HE2 tables must be synchronized from an
unrestricted shell because the corrections repo is read-only in the managed
Codex sandbox used for this pass:

```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd
python3 Evironmetrics---REVISED-DOC-Corrected-2/scripts/sync_corrections_generated_table_includes.py \
  --article-root Evironmetrics---REVISED-DOC-Corrected-2 \
  --corrections-root /data/muscat_data/jaguir26/Corrections---Project-1
```

Until that command is run, `scripts/validate_revision_cross_repo_wiring.py`
will correctly fail on the three updated `exAL-M-T1` cells in the corrections
HE2 response table.

## Validation Results

The following checks passed after wiring the overlay into the workflow and the
revised article:

```bash
python3 -m py_compile \
  scripts/validate_he2_exal_keep_partial_screen_promotion.py \
  scripts/build_he2_bayesian_publication_manifest.py \
  scripts/validate_publication_freeze.py \
  scripts/forecast_design_contract.py

python3 -m unittest \
  tests.python.test_he2_exal_keep_partial_screen_promotion \
  tests.python.test_he2_bayesian_publication_manifest -v

python3 scripts/validate_he2_exal_keep_partial_screen_promotion.py

python3 scripts/validate_publication_freeze.py \
  --report-dir reports/publication_freeze_validation_20260623_partial_exal_keep_overlay_after_article_sync_v2

cd Evironmetrics---REVISED-DOC-Corrected-2
python3 -m unittest discover -s tests -v
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
bibtex output
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
```

The publication freeze validator passes with the partial-screen overlay. The
cross-repo validator is expected to pass after the corrections generated tables
are refreshed with the command above.

## Operational Pause/Resume

This Codex sandbox can read the runtime campaign but cannot write to
`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime` and cannot reliably see
or stop host queue processes. Therefore the host-side pause must be executed
from an unrestricted shell.

Recommended host-side pause procedure, using the tracked helper:

```bash
cd /data/muscat_data/jaguir26/project1_ucsc_phd

# 1. Dry-run: writes the checkpoint and prints matching processes.
python3 scripts/manage_he2_exal_keep_partial_promotion.py pause \
  --checkpoint-dir reports/he2_exal_keep_partial_screen_promotion_20260623/screen_checkpoint

# 2. After reviewing the dry-run process list, stop only the matching screen.
python3 scripts/manage_he2_exal_keep_partial_promotion.py pause \
  --checkpoint-dir reports/he2_exal_keep_partial_screen_promotion_20260623/screen_checkpoint \
  --apply
```

Before resuming, any interrupted `pending` rows must be reconciled against their
run manifests. Rows without terminal pass/fail manifests should be reset to
`not_started` in the screening matrix or relaunched through the existing queue
restart protocol. Completed pass/fail rows must be preserved.

## Resume Policy

After article/poster outputs are refreshed from the overlay, resume the
screening campaign from the same matrix. The remaining search space remains
exploratory until all rows are terminal. If a later `s07`, `s08`, or `s09`
specification improves on the partial overlay, create a new versioned authority
manifest or overlay rather than editing generated tables by hand.

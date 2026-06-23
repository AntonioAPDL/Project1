# exDQLM Multivariate Keep Clean-Authority Promotion

Date: 2026-06-23

This document records the controlled promotion and clean replay of selected HE2
`exAL-M-T1` / `exdqlm_multivar_keep` screening results from:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_overnight_screen_20260619`

## Scope

The authority promoted here is not a final full-grid screening winner manifest.
It is a clean replay of the three completed screening specifications that
improved forecast-window CRPS relative to the 2026-06-01 authority. The broader
screening campaign remains exploratory until every row is terminal and a later
full-screen authority overlay is produced.

The publication-facing authority no longer points to the exploratory screening
root. It points to the isolated clean replay root:

`/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_partial_authority_refresh_20260623`

## Promoted Rows

| cutoff | previous authoritative run | selected screening run | clean authority run | reason |
|---|---|---|---|---|
| `20211221` | `multimodel_20211221_v8_he2grid_c03_eps030_exdqlm_multivar_keep` | `multimodel_20211221_v8_he2grid_s02_eps030_exdqlm_multivar_keep` | `multimodel_20211221_v8_he2partial20260623_exdqlm_multivar_keep` | lower completed CRPS, clean replay passed |
| `20220511` | `multimodel_20220511_v8_he2grid_c02_eps060_exdqlm_multivar_keep` | `multimodel_20220511_v8_he2grid_s06_eps001_exdqlm_multivar_keep` | `multimodel_20220511_v8_he2partial20260623_exdqlm_multivar_keep` | lower completed CRPS, clean replay passed |
| `20221225` | `multimodel_20221225_v8_he2grid_c05_eps030_exdqlm_multivar_keep` | `multimodel_20221225_v8_he2grid_s01_eps001_exdqlm_multivar_keep` | `multimodel_20221225_v8_he2partial20260623_exdqlm_multivar_keep` | lower completed CRPS, clean replay passed |

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
2. the 3 clean-replayed `exAL-M-T1` replacements listed above.

The previous 2026-06-01 manifest remains available as the baseline audit trail:

`docs/exdqlm_multivar_keep_authoritative_specs_20260601.yaml`

The publication manifest builder now uses the 2026-06-23 current-authority
overlay by default. The older Table 1 overlay remains in `config/` as historical
context.

## Clean Authority Rerun

The clean authority rerun has completed. The replay ran exactly the three
promoted rows into the dedicated root named above:

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
`20221225` from the refreshed HE2 publication manifest. It inherits the
selected screening specifications, canonical `20260510` input bundle, full
history start date, current patched workflow, seven quantile lanes per cutoff,
component diagnostics, and post-stage heavy-artifact cleanup. All three clean
replay rows reached fit/post/validate/report `pass`, and no `.RData`/`.rda`
objects remain under the clean replay root.

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

- exactly three selected `exAL-M-T1` replacements;
- replacement cutoffs are `20211221`, `20220511`, and `20221225`;
- each replacement run root exists under the declared screening or clean replay
  root;
- fit, post, validate, and report stages are all `pass`;
- required CRPS, figure, and posterior summary outputs exist;
- no retained `.RData`, `.rda`, `.Rda`, or `.rdata` files are present in the
  promoted runs;
- each replacement CRPS is lower than the 2026-06-01 authority;
- exploratory partial-screen lineage is explicitly non-final, while clean
  replay lineage must have a complete all-pass clean replay matrix.

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

The publication freeze validator, cross-repo validator, revised article tests,
revised article LaTeX/BibTeX compile, corrections `make`, and poster build
passed after refreshing the workflow, revised article, corrections response,
and poster artifacts from the clean-authority overlay.

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

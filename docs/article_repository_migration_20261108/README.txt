Independent revised article and restored submission archive
November 8, 2026

The active revised article is AntonioAPDL/Evironmetrics----Corrected-3.
Its canonical local clone is the workflow's Evironmetrics----Corrected-3 child.
AntonioAPDL/Evironmetrics---REVISED-DOC-Corrected-2 retains the submitted article
contents through a new restoration commit, preserving all historical commits.
No operation is performed in the existing Overleaf project.

Pinned identities

Submitted baseline: 1272bfc10442a28add5a4c74ff641e9b9a8e9666
Submitted tree: 35b2c6d2af808a09618ad7365474826e0bf928fd
Complete revised source: 32ab28b6c709bf001456090751edb413ae747a7b
Corrected-3 initial Overleaf import: 80ac992f4ea1b3feda90add7f3b4dd00451f84a4
Corrected-3 revised candidate: d02c17fa91dd6d64db8ed9166acdb1155488954a
Corrected-2 restoration candidate: fb58225c4ae1f730301ce3864e98ae4db2d9febf

Corrected-3's initial import has the same 440 file contents as the submitted
baseline. Its script permission normalization is explicitly accounted for.
All four November correction commits are transplanted in order with provenance:
  dd7855d -> 897b144  structural revision
  373bed4 -> fbe3414  external references and fitting evidence
  2583ee4 -> c986243  availability/replay clarification
  32ab28b -> d02c17f  saved-output verification and reporting
The independent Overleaf import remains an ancestor of the revised candidate.
At the transplanted d02c17f commit, all 792 revised file paths and blob contents
match the accepted source exactly. A subsequent migration-only test repair
handles EXDEV when /data and /tmp are different filesystems. The one permitted
test-file hash/size change is recorded in portability_adjustment.json; all other
791 file contents and all scientific/manuscript evidence remain unchanged.

The restored Corrected-2 tree, including permissions, is exactly the baseline
tree. A forward commit retains the complete correction history; neither old
nor new main is force-pushed. Backups include submitted and revised source
archives checked against every Git blob, plus the original local revised PDF.
Backup paths and hashes are in backup_verification.json, not duplicated in Git.

Active routing

config/article_repository_binding.json is the current active target binding.
scripts/article_repository_binding.py resolves that target and verifies the
independent repository root, submitted-archive exclusion, and every fetch/push
origin before publication writes. ENVIRONMETRICS_ARTICLE_ROOT may select an
explicit checkout, with the same identity guard for writes.

Read-only historical analysis can still select an old checkout explicitly.
Historical source paths, public URLs, frozen configurations and archived programs
remain unchanged. They record where accepted computations occurred. The live
N14 extraction path resolver is adjusted for the canonical layout; its frozen
replay program and all numerical outputs remain exact.

Run these from the workflow root:
  python3 -B scripts/article_repository_binding.py --check-write-target
  python3 -B docs/article_repository_migration_20261108/run_checks.py --report-dir /tmp/NEW_article_checks

The combined runner accepts --workflow-root, --article-root, --corrections-root,
--public-root and --he3-runtime-root for isolated verification. It passes the
active article explicitly to validators and propagates ENVIRONMETRICS_ARTICLE_ROOT,
NO_REFIT_REPORTING_DIR, NO_REFIT_RESULT_DIR and NO_REFIT_SYNTHESIS_DIR to tests.
Missing required datasets and unexpected skipped checks fail the release gate.
Older dated campaign run_checks.py files remain frozen historical evidence;
the new combined runner is the supported active verification command.

Verification design

The isolated workflow's old article path is pointed at an actual submitted
baseline fixture before the combined checks. This exposes accidental dependence
on corrected helpers or assets remaining in the old checkout. After promotion,
the same checks run again against the canonical layout with the old article
actually restored. Corrected-3 native checks and independent portable replays
verify preserved figures, tables, source data and saved-result arithmetic.

verification_helpers.py provides read-only inventory, initial/migrated/restored
comparison, repository-identity and actual-working-file checks. Independent
reports bind these checks to the helper source. The restored comparison demands
the exact submitted tree and retained corrected-source ancestry.

The 42-page revised article and 30-page submitted source are built separately.
The ignored local PDFs are installed into their respective directories only
after verified source promotion. Restoring a Git tree alone does not replace
an ignored local PDF. Build reports and PDF hashes are retained in proof/.

Overleaf use

Pull the revised source only into the new project linked to Corrected-3. Match
the main document and compiler settings to the reviewed project. The old project
requires no pull, push, relinking, or editing. GitHub import/remote identity can
be verified here; live Overleaf UI synchronization requires access to that project
and is not claimed by a successful GitHub push or a local LaTeX build.

No scientific fitting, baseline training, new posterior draws, authority changes
or replacement of the accepted numerical results is part of this migration.
The supporting Project1 workflow code and previous verification evidence remain.

Legacy validator scope

The active gate uses publication_freeze, revision_cross_repo_wiring and the
protected C1/C2/saved-output checks. Two older selected-authority tests have the
same pre-migration/current schema error: their validator expects a winners list
while the unchanged configuration supplies a replacements overlay. They are
recorded in migration_binding_notes.json and are not counted as passing. No
authority data or fitting record is rewritten to suppress that legacy error.

#!/usr/bin/env bash
set -euo pipefail

ROOT="/data/muscat_data/jaguir26/project1_ucsc_phd"
ARTICLE_ROOT="$ROOT/Evironmetrics---REVISED-DOC-Corrected-2"
CORRECTIONS_ROOT="/data/muscat_data/jaguir26/Corrections---Project-1"
TEMPLATE="$ROOT/config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_partial_authority_refresh_20260623.template.yaml"
REPORT_DIR="$ROOT/reports/he2_exal_keep_partial_screen_promotion_20260623"
FREEZE_REPORT="$ROOT/reports/publication_freeze_validation_20260623_partial_exal_keep_overlay_host_finish"
CROSS_REPO_REPORT="$ROOT/reports/revision_cross_repo_validation_20260623_partial_exal_keep_overlay_host_finish"
CLEAN_PROMOTION_REPORT="$ROOT/reports/he2_exal_keep_clean_authority_promotion_20260623"

cd "$ROOT"

usage() {
  cat <<'USAGE'
Usage:
  scripts/host_finish_he2_exal_keep_partial_promotion.sh preflight
  scripts/host_finish_he2_exal_keep_partial_promotion.sh pause-screen
  scripts/host_finish_he2_exal_keep_partial_promotion.sh launch-clean
  scripts/host_finish_he2_exal_keep_partial_promotion.sh wait-clean
  scripts/host_finish_he2_exal_keep_partial_promotion.sh promote-clean
  scripts/host_finish_he2_exal_keep_partial_promotion.sh sync-articles
  scripts/host_finish_he2_exal_keep_partial_promotion.sh validate
  scripts/host_finish_he2_exal_keep_partial_promotion.sh commit
  scripts/host_finish_he2_exal_keep_partial_promotion.sh all

Notes:
  - Run this from an unrestricted host shell, not the managed Codex sandbox.
  - The clean relaunch writes under project1_ucsc_phd_runtime and starts a
    detached queue controller.
  - The current publication overlay remains the partial-screen overlay until
    promote-clean verifies and repoints the three selected exAL-M-T1 rows to
    the clean replay root.
USAGE
}

require_writable_dir() {
  local path="$1"
  local probe="$path/.he2_partial_promotion_write_probe_$$"
  mkdir -p "$path"
  : > "$probe"
  rm -f "$probe"
}

preflight() {
  python3 -m py_compile \
    scripts/manage_he2_exal_keep_partial_promotion.py \
    scripts/promote_he2_exal_keep_clean_authority.py \
    scripts/validate_he2_exal_keep_partial_screen_promotion.py \
    scripts/build_he2_bayesian_publication_manifest.py \
    scripts/validate_publication_freeze.py \
    scripts/forecast_design_contract.py

  python3 scripts/manage_he2_exal_keep_partial_promotion.py status \
    --out-dir "$REPORT_DIR"
  python3 scripts/manage_he2_exal_keep_partial_promotion.py validate-promotion
  python3 scripts/validate_he2_exal_keep_partial_screen_promotion.py

  require_writable_dir "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime"
  require_writable_dir "$CORRECTIONS_ROOT/tables/generated_tex"

  git status --short
  git -C "$ARTICLE_ROOT" status --short
  git -C "$CORRECTIONS_ROOT" status --short
}

pause_screen() {
  python3 scripts/manage_he2_exal_keep_partial_promotion.py pause \
    --checkpoint-dir "$REPORT_DIR/screen_checkpoint"
  echo
  echo "If the process list above is correct, pausing now."
  python3 scripts/manage_he2_exal_keep_partial_promotion.py pause \
    --checkpoint-dir "$REPORT_DIR/screen_checkpoint" \
    --apply
}

launch_clean() {
  python3 scripts/launch_he2_bayesian_publication_relaunch.py \
    --template "$TEMPLATE" \
    --dry-run

  python3 scripts/launch_he2_bayesian_publication_relaunch.py \
    --template "$TEMPLATE" \
    --reset-state \
    --start-monitor
}

wait_clean() {
  local matrix_dir
  matrix_dir="$(python3 - <<'PY'
import yaml
from pathlib import Path
p=Path("config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_partial_authority_refresh_20260623.template.yaml")
print(yaml.safe_load(p.read_text())["campaign"]["matrix_dir"])
PY
)"
  local status_path="$matrix_dir/matrix_status.csv"
  echo "Waiting for clean authority matrix: $status_path"
  while true; do
    if python3 - <<PY
import csv
from collections import Counter
from pathlib import Path
p=Path("$status_path")
rows=list(csv.DictReader(p.open())) if p.exists() else []
c=Counter(r.get("status","") for r in rows)
print(dict(c))
if rows and all(r.get("status") in {"pass","fail"} for r in rows):
    raise SystemExit(0)
raise SystemExit(1)
PY
    then
      break
    fi
    sleep 120
  done
}

promote_clean() {
  python3 scripts/promote_he2_exal_keep_clean_authority.py \
    --out-dir "$CLEAN_PROMOTION_REPORT" \
    --apply
  python3 scripts/validate_he2_exal_keep_partial_screen_promotion.py \
    --screen-root "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_partial_authority_refresh_20260623" \
    --out-dir "$CLEAN_PROMOTION_REPORT/selected_overlay_validation"
}

sync_articles() {
  python3 scripts/build_he2_bayesian_publication_manifest.py
  python3 scripts/build_he2_publication_parity_gate.py
  python3 "$ARTICLE_ROOT/scripts/refresh_he2_manifest_snapshot.py" \
    --article-root "$ARTICLE_ROOT" \
    --workflow-root "$ROOT"
  python3 "$ARTICLE_ROOT/scripts/build_generated_table_includes.py" \
    --article-root "$ARTICLE_ROOT"
  python3 "$ARTICLE_ROOT/scripts/promote_generated_figures_to_disc.py" \
    --article-root "$ARTICLE_ROOT"
  python3 "$ARTICLE_ROOT/scripts/sync_corrections_generated_table_includes.py" \
    --article-root "$ARTICLE_ROOT" \
    --corrections-root "$CORRECTIONS_ROOT"
  (cd "$ARTICLE_ROOT" && make -f isba2026_poster/Makefile all)
}

validate_all() {
  python3 -m unittest \
    tests.python.test_he2_exal_keep_partial_screen_promotion \
    tests.python.test_he2_bayesian_publication_manifest -v
  python3 scripts/validate_he2_exal_keep_partial_screen_promotion.py \
    --screen-root "/data/muscat_data/jaguir26/project1_ucsc_phd_runtime/multimodel_v8_he2_exdqlm_multivar_keep_partial_authority_refresh_20260623"
  python3 scripts/validate_publication_freeze.py --report-dir "$FREEZE_REPORT"
  python3 scripts/validate_revision_cross_repo_wiring.py \
    --after-patch \
    --output-dir "$CROSS_REPO_REPORT"

  (cd "$ARTICLE_ROOT" && python3 -m unittest discover -s tests -v)
  (
    cd "$ARTICLE_ROOT"
    pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
    bibtex output
    pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
    pdflatex -interaction=nonstopmode -halt-on-error -jobname=output wileyNJD-APA.tex
  )
  (cd "$CORRECTIONS_ROOT" && make)
}

commit_all() {
  git add \
    config/he2_bayesian_publication_relaunch_exdqlm_multivar_keep_partial_authority_refresh_20260623.template.yaml \
    config/he2_publication_manifest_replacement_overlay_current_authority_20260623.yaml \
    docs/exdqlm_multivar_keep_partial_screen_promotion_20260623.md \
    scripts/build_he2_bayesian_publication_manifest.py \
    scripts/forecast_design_contract.py \
    scripts/host_finish_he2_exal_keep_partial_promotion.sh \
    scripts/manage_he2_exal_keep_partial_promotion.py \
    scripts/promote_he2_exal_keep_clean_authority.py \
    scripts/validate_he2_exal_keep_partial_screen_promotion.py \
    scripts/validate_publication_freeze.py \
    tests/python/test_he2_bayesian_publication_manifest.py \
    tests/python/test_he2_exal_keep_partial_screen_promotion.py \
    reports/he2_publication_manifest/he2_bayesian_publication_manifest.md
  git commit -m "Promote partial-screen exAL keep winners"

  (
    cd "$ARTICLE_ROOT"
    git add \
      artifacts/he2_publication_freeze \
      tables/generated_tex \
      figures/manuscript
    git commit -m "Refresh HE2 tables for promoted exAL keep specs"
  )

  (
    cd "$CORRECTIONS_ROOT"
    git add tables/generated_tex
    git commit -m "Sync HE2 response tables with promoted exAL keep specs"
  )

  git push
  git -C "$ARTICLE_ROOT" push
  git -C "$CORRECTIONS_ROOT" push
}

cmd="${1:-}"
case "$cmd" in
  preflight) preflight ;;
  pause-screen) pause_screen ;;
  launch-clean) launch_clean ;;
  wait-clean) wait_clean ;;
  promote-clean) promote_clean ;;
  sync-articles) sync_articles ;;
  validate) validate_all ;;
  commit) commit_all ;;
  all)
    preflight
    pause_screen
    launch_clean
    wait_clean
    promote_clean
    sync_articles
    validate_all
    commit_all
    ;;
  -h|--help|help|"") usage ;;
  *) usage; exit 2 ;;
esac

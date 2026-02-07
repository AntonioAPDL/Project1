#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p logs/latex tmp/latex

# Main entrypoints detected in this repository.
DOCS=(
  "article.txt"
  "Manuscript_Revision_Tracker.txt"
)

build_with_pdflatex_fallback() {
  local doc="$1"
  local stem="$2"

  pdflatex -interaction=nonstopmode -halt-on-error -jobname="$stem" -output-directory=tmp/latex "$doc" || return 1
}

status=0

for doc in "${DOCS[@]}"; do
  if [[ ! -f "$doc" ]]; then
    echo "[skip] Missing document: $doc"
    status=1
    continue
  fi

  stem="$(basename "${doc%.*}")"
  log="logs/latex/${stem}.log"

  rm -f \
    "tmp/latex/${stem}.aux" \
    "tmp/latex/${stem}.bbl" \
    "tmp/latex/${stem}.blg" \
    "tmp/latex/${stem}.fdb_latexmk" \
    "tmp/latex/${stem}.fls" \
    "tmp/latex/${stem}.log" \
    "tmp/latex/${stem}.out" \
    "tmp/latex/${stem}.pdf" \
    "tmp/latex/${stem}.toc"

  {
    echo "[build] $doc"
    echo "[info] start: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

    if command -v latexmk >/dev/null 2>&1; then
      latexmk -pdf -interaction=nonstopmode -halt-on-error -jobname="$stem" -outdir=tmp/latex "$doc" || exit 1
    else
      echo "[info] latexmk not found; using deterministic pdflatex+bibtex fallback"
      build_with_pdflatex_fallback "$doc" "$stem" || exit 1
    fi

    if [[ ! -f "tmp/latex/${stem}.pdf" ]]; then
      echo "[error] missing output PDF: tmp/latex/${stem}.pdf"
      exit 1
    fi

    echo "[info] done: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "[info] pdf: tmp/latex/${stem}.pdf"
  } >"$log" 2>&1 || {
    status=1
    echo "[fail] $doc (see $log)"
    continue
  }

  echo "[ok] $doc"
 done

exit "$status"

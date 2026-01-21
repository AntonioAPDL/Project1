#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${1:-$(pwd)}"
cd "$ROOT"

LOGDIR="${ROOT}/_audit_logs"
mkdir -p "$LOGDIR"

TS="$(date +%Y%m%d_%H%M%S)"
OUTDIR="${LOGDIR}/audit_${TS}"
mkdir -p "$OUTDIR"

REPORT="${OUTDIR}/audit_report_${TS}.txt"
FREEZE="${OUTDIR}/pip_freeze_${TS}.txt"
BIGTSV="${OUTDIR}/biggest_files_${TS}.tsv"
DIRTSV="${OUTDIR}/top_level_du_${TS}.tsv"

# Print both to terminal and to report
exec > >(tee -a "$REPORT") 2>&1

hr() { printf '\n%s\n' "================================================================================"; }
sec() { hr; printf '%s\n' "$1"; hr; }

cmd() {
  printf '\n$ %s\n' "$*"
  "$@"
}

note() { printf '\n[NOTE] %s\n' "$1"; }

sec "AUDIT START"
cmd date
cmd hostname
cmd whoami
note "Project root: $(pwd)"
note "Script output directory: $OUTDIR"

sec "ENVIRONMENT (active Python env snapshot)"
if command -v python >/dev/null 2>&1; then
  cmd which python
  cmd python -V
  cmd python -c "import sys; print('executable:', sys.executable); print('prefix:', sys.prefix)"
  cmd python -m pip --version || true
  note "Writing full pip freeze to: $FREEZE"
  python -m pip freeze > "$FREEZE" 2>/dev/null || true
  note "First 80 lines of pip freeze:"
  head -n 80 "$FREEZE" 2>/dev/null || true
else
  note "python not found on PATH in this shell."
fi

sec "STEP 1B: TOP-LEVEL LISTING"
cmd ls -lah

sec "STEP 1B: DIRECTORY TREE (2 levels, compact)"
if command -v tree >/dev/null 2>&1; then
  cmd tree -L 2 -a
else
  note "tree not installed; using find."
  cmd bash -lc "find . -maxdepth 2 -mindepth 1 -type d -print | sed 's|^\\./||' | sort | head -n 400"
fi

sec "STEP 1B: TOP-LEVEL SIZES (du --max-depth=1)"
note "Writing TSV to: $DIRTSV"
# TSV: size_in_bytes<TAB>path
bash -lc "find . -maxdepth 1 -mindepth 1 -print0 | xargs -0 -I{} du -sb {} 2>/dev/null | sort -nr | tee '$DIRTSV' | head -n 200"
note "Human-readable (top 60):"
cmd bash -lc "du -h --max-depth=1 2>/dev/null | sort -hr | head -n 60"

sec "STEP 1B: BIGGEST FILES (top 80)"
note "Writing TSV to: $BIGTSV"
cmd bash -lc "find . -type f -printf '%s\t%p\n' 2>/dev/null | sort -nr | head -n 80 | tee '$BIGTSV'"

sec "STEP 1C: FILE EXTENSION COUNTS (top 50)"
cmd bash -lc "find . -type f 2>/dev/null | sed 's/.*\\.//' | awk '{print tolower(\$0)}' | sort | uniq -c | sort -nr | head -n 50"

sec "STEP 1C: LIKELY DATA/OUTPUT DIRECTORIES (maxdepth=4, compact)"
cmd bash -lc "find . -maxdepth 4 -type d \\( -iname '*data*' -o -iname '*results*' -o -iname '*output*' -o -iname '*models*' -o -iname '*fig*' -o -iname '*cache*' -o -iname '*checkpoint*' \\) 2>/dev/null | sed 's|^\\./||' | sort | head -n 300"

sec "STEP 1D: CODE FILE COUNTS (py/R/jl/sh/tex/yaml)"
cmd bash -lc "find . -type f \\( -name '*.py' -o -name '*.R' -o -name '*.jl' -o -name '*.sh' -o -name '*.tex' -o -name '*.yaml' -o -name '*.yml' \\) -printf '%f\n' 2>/dev/null | sed 's/.*\\.//' | awk '{print tolower(\$0)}' | sort | uniq -c | sort -nr"

sec "STEP 1D: LIKELY ENTRYPOINTS (maxdepth=3, first 300)"
cmd bash -lc "find . -maxdepth 3 -type f \\( -name 'Makefile' -o -name '*.sh' -o -name '*.py' \\) 2>/dev/null | sed 's|^\\./||' | sort | head -n 300"

sec "AUDIT END"
note "Report: $REPORT"
note "Full pip freeze: $FREEZE"
note "Big files TSV: $BIGTSV"
note "Top-level du TSV: $DIRTSV"

# Create tarball and stable symlink for scp
TARBALL="${LOGDIR}/audit_${TS}.tar.gz"
note "Creating tarball: $TARBALL"
tar -czf "$TARBALL" -C "$LOGDIR" "audit_${TS}" >/dev/null 2>&1 || true
ln -sf "$(basename "$TARBALL")" "${LOGDIR}/audit_latest.tar.gz"

note "Stable download target:"
note "${LOGDIR}/audit_latest.tar.gz"

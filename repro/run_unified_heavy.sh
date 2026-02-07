#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

BASE_CONFIG="config/unified_runs/heavy_site11160500_cutoff20221225.yaml"
PARAMETERS_PATH="/data/muscat_data/jaguir26/projects/Project/Input/exAL/parameters/parameters.txt"
RETROS_PATH="retros_2022-12-25.csv"
NWS_PATH="nws_forecast.csv"
GLOFAS_PATH="weighted_time_series.csv"

FORECATS="${FORECATS:-0}"
RUN_TWICE="${RUN_TWICE:-0}"

log() {
  printf '[heavy-run] %s\n' "$*"
}

die() {
  printf '[heavy-run] ERROR: %s\n' "$*" >&2
  exit 1
}

find_unified_entrypoint() {
  if [[ -f "${REPO_ROOT}/unified_run.R" ]]; then
    printf '%s\n' "${REPO_ROOT}/unified_run.R"
    return 0
  fi
  if [[ -f "${REPO_ROOT}/scripts/unified_run.R" ]]; then
    printf '%s\n' "${REPO_ROOT}/scripts/unified_run.R"
    return 0
  fi
  return 1
}

require_file() {
  local p="$1"
  [[ -f "$p" ]] || die "required file not found: $p"
}

detect_forecats_bundle() {
  local cutoff_root="data/forecats_inputs/site=11160500/cutoff_date=2022-12-25"
  if [[ ! -d "$cutoff_root" ]]; then
    return 1
  fi

  local latest
  latest="$(find "$cutoff_root" -mindepth 1 -maxdepth 1 -type d -name 'run_id=*' -printf '%T@ %p\n' | sort -nr | head -n 1 | cut -d' ' -f2-)"
  if [[ -n "${latest}" && -d "${latest}" ]]; then
    printf '%s\n' "${latest}"
    return 0
  fi

  return 1
}

write_resolved_config() {
  local run_id="$1"
  local canonical_run_id="$2"
  local resolved_cfg="$3"
  local forecats_enabled="$4"
  local forecats_bundle_path="$5"
  local resolved_retros_path="$6"
  local resolved_nws_path="$7"
  local resolved_glofas_path="$8"

  Rscript --vanilla - "$BASE_CONFIG" "$resolved_cfg" "$run_id" "$canonical_run_id" "$forecats_enabled" "$forecats_bundle_path" "$resolved_retros_path" "$resolved_nws_path" "$resolved_glofas_path" <<'RS'
args <- commandArgs(trailingOnly = TRUE)
base_cfg_path <- args[[1]]
resolved_cfg_path <- args[[2]]
run_id <- args[[3]]
canonical_run_id <- args[[4]]
forecats_enabled <- args[[5]]
forecats_bundle_path <- args[[6]]
resolved_retros_path <- args[[7]]
resolved_nws_path <- args[[8]]
resolved_glofas_path <- args[[9]]

if (!requireNamespace("yaml", quietly = TRUE)) {
  stop("Package 'yaml' is required to write resolved heavy config")
}

cfg <- yaml::read_yaml(base_cfg_path)
if (is.null(cfg) || !is.list(cfg)) {
  stop("Base heavy config could not be read: ", base_cfg_path)
}

cfg$run$run_id <- run_id
cfg$run$overwrite <- TRUE
cfg$run$dry_run <- FALSE
cfg$inputs$fit$retros_path <- resolved_retros_path
cfg$inputs$fit$nws_forecast_path <- resolved_nws_path
cfg$inputs$fit$glofas_forecast_path <- resolved_glofas_path

if (!is.na(canonical_run_id) && nzchar(canonical_run_id)) {
  cfg$validation$canonical_run_id <- canonical_run_id
} else {
  cfg$validation$canonical_run_id <- NULL
}

if (identical(forecats_enabled, "1")) {
  cfg$stages$forecats <- TRUE
  cfg$inputs$forecats$mode <- "use_existing"
  cfg$inputs$forecats$existing_bundle_path <- forecats_bundle_path
} else {
  cfg$stages$forecats <- FALSE
  cfg$inputs$forecats$existing_bundle_path <- NULL
}

yaml::write_yaml(cfg, resolved_cfg_path)
RS
}

prepare_csv_for_adapter() {
  local src="$1"
  local dst="$2"
  local label="$3"

  local prep_out
  prep_out="$(Rscript --vanilla - "$src" "$dst" "$label" <<'RS'
args <- commandArgs(trailingOnly = TRUE)
src <- args[[1]]
dst <- args[[2]]
label <- args[[3]]

dat <- utils::read.csv(src, check.names = FALSE, stringsAsFactors = FALSE)
num_cols <- names(dat)[vapply(dat, is.numeric, logical(1))]
if (length(num_cols) == 0) {
  stop(sprintf("%s has no numeric columns to adapt", src))
}

replacements <- 0L
for (nm in num_cols) {
  x <- dat[[nm]]
  bad <- which(!is.finite(x))
  if (length(bad) == 0) next
  good <- which(is.finite(x))
  if (length(good) == 0) {
    stop(sprintf("%s:%s has no finite values; cannot repair non-finite entries", label, nm))
  }
  for (b in bad) {
    nearest <- good[which.min(abs(good - b))]
    x[[b]] <- x[[nearest]]
  }
  dat[[nm]] <- x
  replacements <- replacements + length(bad)
}

dir.create(dirname(dst), recursive = TRUE, showWarnings = FALSE)
utils::write.csv(dat, dst, row.names = FALSE)
cat(sprintf("label=%s src=%s dst=%s nonfinite_replacements=%d", label, src, dst, replacements))
RS
)"
  log "$prep_out"
}

append_forecats_skip_note() {
  local run_root="$1"
  local reason="$2"
  local summary_md="${run_root}/report/summary.md"
  local summary_json="${run_root}/report/summary.json"

  if [[ -f "$summary_md" ]]; then
    {
      printf '\n## Forecats\n'
      printf -- '- skipped: `true`\n'
      printf -- '- reason: `%s`\n' "$reason"
    } >> "$summary_md"
  fi

  if [[ -f "$summary_json" ]]; then
    python3 - "$summary_json" "$reason" <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
reason = sys.argv[2]

try:
    payload = json.loads(summary_path.read_text())
except Exception:
    sys.exit(0)

payload["forecats_skipped"] = True
payload["forecats_skip_reason"] = reason
summary_path.write_text(json.dumps(payload, indent=2) + "\n")
PY
  fi
}

print_paths() {
  local run_id="$1"
  local run_root="repro/runs/${run_id}"
  log "run_id=${run_id}"
  log "run_root=${run_root}"
  log "manifest=${run_root}/run_manifest.yaml"
  log "compare_report=${run_root}/validate/compare_report.json"
  log "write_audit_dir=${run_root}/validate/write_audit"
  log "write_audit_report_stage_diff=${run_root}/validate/write_audit/report/fs_diff.patch"
  log "summary_md=${run_root}/report/summary.md"
  log "summary_json=${run_root}/report/summary.json"
  log "log_file=${run_root}/logs/heavy_run.log"
}

run_single() {
  local run_id="$1"
  local canonical_run_id="$2"
  local forecats_enabled="$3"
  local forecats_bundle_path="$4"
  local forecats_skip_reason="$5"

  local run_root="repro/runs/${run_id}"
  local logs_dir="${run_root}/logs"
  local inputs_dir="${run_root}/inputs"
  local resolved_cfg="${run_root}/resolved_config.yaml"
  local run_log="${logs_dir}/heavy_run.log"
  local resolved_retros="${inputs_dir}/retros_2022-12-25.csv"
  local resolved_nws="${inputs_dir}/nws_forecast.csv"
  local resolved_glofas="${inputs_dir}/weighted_time_series.csv"

  mkdir -p "$logs_dir" "$inputs_dir"

  prepare_csv_for_adapter "$RETROS_PATH" "$resolved_retros" "retros"
  prepare_csv_for_adapter "$NWS_PATH" "$resolved_nws" "nws_forecast"
  prepare_csv_for_adapter "$GLOFAS_PATH" "$resolved_glofas" "glofas_forecast"

  log "preparing resolved config for run_id=${run_id}"
  write_resolved_config "$run_id" "$canonical_run_id" "$resolved_cfg" "$forecats_enabled" "$forecats_bundle_path" "$resolved_retros" "$resolved_nws" "$resolved_glofas"

  log "launching unified workflow: ${UNIFIED_ENTRYPOINT}"
  log "config: ${resolved_cfg}"
  Rscript --vanilla "$UNIFIED_ENTRYPOINT" --config "$resolved_cfg" 2>&1 | tee "$run_log"

  if [[ "$forecats_skip_reason" != "" ]]; then
    append_forecats_skip_note "$run_root" "$forecats_skip_reason"
  fi

  print_paths "$run_id"
}

UNIFIED_ENTRYPOINT="$(find_unified_entrypoint || true)"
[[ -n "$UNIFIED_ENTRYPOINT" ]] || die "unified entrypoint not found (expected ./unified_run.R or ./scripts/unified_run.R)"

require_file "$BASE_CONFIG"
require_file "$PARAMETERS_PATH"
require_file "$RETROS_PATH"
require_file "$NWS_PATH"
require_file "$GLOFAS_PATH"

# Validate committed heavy config as shipped.
log "validating committed heavy config with dry-run"
Rscript --vanilla - "$BASE_CONFIG" <<'RS'
args <- commandArgs(trailingOnly = TRUE)
cfg_path <- args[[1]]
repo_root <- normalizePath(getwd(), mustWork = TRUE)
source(file.path(repo_root, "R", "unified", "config.R"))
cfg <- unified_load_config(cfg_path, repo_root = repo_root)
invisible(cfg)
RS

forecats_enabled="0"
forecats_bundle_path=""
forecats_skip_reason=""

if [[ "$FORECATS" == "1" ]]; then
  if bundle_path="$(detect_forecats_bundle || true)"; then
    if [[ -n "$bundle_path" ]]; then
      forecats_enabled="1"
      forecats_bundle_path="$bundle_path"
      log "forecats enabled with existing bundle: $forecats_bundle_path"
    else
      forecats_skip_reason="FORECATS=1 but no matching bundle found under data/forecats_inputs/site=11160500/cutoff_date=2022-12-25"
      log "$forecats_skip_reason"
    fi
  else
    forecats_skip_reason="FORECATS=1 but no matching bundle found under data/forecats_inputs/site=11160500/cutoff_date=2022-12-25"
    log "$forecats_skip_reason"
  fi
else
  log "forecats disabled (default). Set FORECATS=1 to auto-detect and enable existing bundle mode."
fi

stamp="$(date -u +%Y%m%d_%H%M%S)"

if [[ "$RUN_TWICE" == "1" ]]; then
  run_id_a="heavy_${stamp}_A"
  run_id_b="heavy_${stamp}_B"

  log "RUN_TWICE=1 -> running A then B (B compares against A)"
  run_single "$run_id_a" "" "$forecats_enabled" "$forecats_bundle_path" "$forecats_skip_reason"
  run_single "$run_id_b" "$run_id_a" "$forecats_enabled" "$forecats_bundle_path" "$forecats_skip_reason"

  log "completed two-run strict reproducibility sequence"
  log "run_a=${run_id_a}"
  log "run_b=${run_id_b}"
else
  run_id="heavy_${stamp}"
  run_single "$run_id" "" "$forecats_enabled" "$forecats_bundle_path" "$forecats_skip_reason"
  log "completed single heavy run"
fi

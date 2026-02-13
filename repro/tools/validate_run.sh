#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash repro/tools/validate_run.sh <RUN_ID> [--profile production|production_proof|smoke|auto] [--exit-nonzero]
  RUN_ID=<RUN_ID> bash repro/tools/validate_run.sh [--profile production|production_proof|smoke|auto] [--exit-nonzero]

Production profile (default) strict success checklist:
1) All 7 quantile outputs exist:
   DISC_variables_{5,20,35,50,65,80,95}_exAL_synth_DISC.RData
   (canonical production gate; this is enforced regardless of fit.quantiles)
2) post outputs exist under post/outputs/<RUN_ID> with at least one file
3) validate/compare_report.json exists
4) validate/write_audit/.../fs_diff.patch exists
5) report/summary.md exists
6) report/summary.json exists
7) run_manifest.yaml exists
8) run_manifest timestamps.finished_at_utc is non-null
9) run_manifest validation.status == pass

Smoke profile checklist:
1) run_manifest exists and finished_at_utc is non-null
2) run_manifest validation.status == pass
3) expected family artifacts exist for enabled models and requested quantiles
4) post/validate/report artifacts exist
5) write_audit fs_diff.patch exists and all detected patches are empty

Production-proof profile checklist:
1) same gates as production for manifest/post/validate/report/family artifacts
2) expected quantiles are derived from run resolved_config.yaml fit.quantiles
3) default expected quantile is q=50 only if fit.quantiles is absent

--exit-nonzero:
  When provided, exits 1 on RESULT=FAIL (default behavior remains exit 0).
EOF
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

norm_null() {
  local v="${1:-}"
  case "$v" in
    ""|"~"|"null"|"NULL"|"None"|"<nil>")
      echo ""
      ;;
    *)
      echo "$v"
      ;;
  esac
}

join_by() {
  local sep="$1"
  shift || true
  local out=""
  local first=1
  local x
  for x in "$@"; do
    if [[ $first -eq 1 ]]; then
      out="$x"
      first=0
    else
      out="${out}${sep}${x}"
    fi
  done
  echo "$out"
}

bool_word() {
  if [[ "$1" == "true" ]]; then
    echo "PASS"
  else
    echo "FAIL"
  fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

PROFILE="production"
PROFILE_EXPLICIT="false"
EXIT_NONZERO="false"
RUN_ID_ARG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      [[ $# -ge 2 ]] || die "--profile requires an argument"
      PROFILE="$2"
      PROFILE_EXPLICIT="true"
      shift 2
      ;;
    --exit-nonzero)
      EXIT_NONZERO="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      die "Unknown option: $1"
      ;;
    *)
      if [[ -z "${RUN_ID_ARG}" ]]; then
        RUN_ID_ARG="$1"
      else
        die "Unexpected extra argument: $1"
      fi
      shift
      ;;
  esac
done

RUN_ID="${RUN_ID_ARG:-${RUN_ID:-}}"
[[ -n "${RUN_ID}" ]] || {
  usage
  exit 1
}

RUN_ROOT="${REPO_ROOT}/repro/runs/${RUN_ID}"
[[ -d "${RUN_ROOT}" ]] || die "Run root not found: ${RUN_ROOT}"

MANIFEST_PATH="${RUN_ROOT}/run_manifest.yaml"
POST_DIR="${RUN_ROOT}/post"
POST_OUTPUTS_DIR="${RUN_ROOT}/post/outputs/${RUN_ID}"
COMPARE_REPORT_PATH="${RUN_ROOT}/validate/compare_report.json"
REPORT_MD_PATH="${RUN_ROOT}/report/summary.md"
REPORT_JSON_PATH="${RUN_ROOT}/report/summary.json"
WRITE_AUDIT_PRIMARY="${RUN_ROOT}/validate/write_audit/fs_diff.patch"
RESOLVED_CONFIG_PATH="${RUN_ROOT}/resolved_config.yaml"
SHARED_SOURCE_MAP_PATH="${RUN_ROOT}/inputs/shared/source_map.txt"
SNAPSHOT_SOURCE_MAP_PATH="${RUN_ROOT}/inputs/shared/forecats_bundle/snapshot_source_map.txt"
FIT_SHARED_SOURCE_LOG="${RUN_ROOT}/fit/logs/shared_input_source_map.log"
POST_SHARED_SOURCE_LOG="${RUN_ROOT}/post/logs/shared_input_source_map.log"

validation_profile_from_config=""
validation_profile_from_manifest=""
profile_resolution_source="cli"
cfg_quantile_nums_csv=""
cfg_quantile_labels_csv=""
cfg_run_exdqlm_multivar="true"
cfg_run_exdqlm_univar="false"
cfg_run_ndlm_main="false"
cfg_contract_checks_enabled="false"
cfg_diagnostics_enabled="false"
[[ -f "${RESOLVED_CONFIG_PATH}" ]] || die "resolved_config.yaml not found: ${RESOLVED_CONFIG_PATH}"
if mapfile -t cfg_vals < <(python3 - "${RESOLVED_CONFIG_PATH}" <<'PY'
import sys
try:
    import yaml
except Exception as exc:
    print(f"ERROR: PyYAML unavailable (import yaml failed): {exc}", file=sys.stderr)
    raise SystemExit(2)

path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
except Exception as exc:
    print(f"ERROR: Failed to parse YAML at {path}: {exc}", file=sys.stderr)
    raise

validation = doc.get("validation") or {}
models = doc.get("models") or {}
fit = doc.get("fit") or {}
raw_quantiles = fit.get("quantiles")
if isinstance(raw_quantiles, (list, tuple)):
    quantiles = list(raw_quantiles)
elif raw_quantiles is None:
    quantiles = []
else:
    quantiles = [raw_quantiles]

q_nums = []
q_labels = []
for q in quantiles:
    try:
        q_num = int(round(float(q) * 100))
    except Exception:
        continue
    q_nums.append(str(q_num))
    q_labels.append(f"{q_num:02d}")

def as_bool_word(val, default=False):
    if val is None:
        val = default
    return "true" if bool(val) else "false"

print(str(validation.get("profile") or ""))
print(",".join(q_nums))
print(",".join(q_labels))
print(as_bool_word(models.get("run_exdqlm_multivar"), default=True))
print(as_bool_word(models.get("run_exdqlm_univar"), default=False))
print(as_bool_word(models.get("run_ndlm_main"), default=False))
print(as_bool_word((fit.get("contract_checks") or {}).get("enabled"), default=False))
print(as_bool_word((fit.get("diagnostics") or {}).get("enabled"), default=False))
PY
); then
  validation_profile_from_config="${cfg_vals[0]:-}"
  cfg_quantile_nums_csv="${cfg_vals[1]:-}"
  cfg_quantile_labels_csv="${cfg_vals[2]:-}"
  cfg_run_exdqlm_multivar="${cfg_vals[3]:-true}"
  cfg_run_exdqlm_univar="${cfg_vals[4]:-false}"
  cfg_run_ndlm_main="${cfg_vals[5]:-false}"
  cfg_contract_checks_enabled="${cfg_vals[6]:-false}"
  cfg_diagnostics_enabled="${cfg_vals[7]:-false}"
else
  die "Failed to parse ${RESOLVED_CONFIG_PATH} (ensure valid YAML and PyYAML import 'yaml' is available)"
fi

PROFILE_EFFECTIVE="${PROFILE}"
if [[ "${PROFILE}" == "auto" ]]; then
  if [[ -f "${MANIFEST_PATH}" ]]; then
    if mapfile -t manifest_vals < <(python3 - "${MANIFEST_PATH}" <<'PY'
import sys
try:
    import yaml
except Exception as exc:
    print(f"ERROR: PyYAML unavailable (import yaml failed): {exc}", file=sys.stderr)
    raise SystemExit(2)

path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
except Exception as exc:
    print(f"ERROR: Failed to parse YAML at {path}: {exc}", file=sys.stderr)
    raise

validation = doc.get("validation") or {}
print(str(validation.get("validator_profile") or ""))
PY
    ); then
      validation_profile_from_manifest="${manifest_vals[0]:-}"
    else
      die "Failed to parse ${MANIFEST_PATH} while resolving --profile auto (ensure valid YAML and PyYAML import 'yaml' is available)"
    fi
  fi

  if [[ -n "${validation_profile_from_manifest}" ]]; then
    PROFILE_EFFECTIVE="${validation_profile_from_manifest}"
    profile_resolution_source="manifest"
  elif [[ -n "${validation_profile_from_config}" ]]; then
    PROFILE_EFFECTIVE="${validation_profile_from_config}"
    profile_resolution_source="resolved_config"
  else
    PROFILE_EFFECTIVE="production"
    profile_resolution_source="default"
  fi
fi
if [[ "${PROFILE_EFFECTIVE}" != "production" && "${PROFILE_EFFECTIVE}" != "production_proof" && "${PROFILE_EFFECTIVE}" != "smoke" ]]; then
  die "Unsupported validation profile: ${PROFILE_EFFECTIVE} (allowed: production, production_proof, smoke, auto)"
fi

require_multivar="${cfg_run_exdqlm_multivar}"
require_univar="${cfg_run_exdqlm_univar}"
require_ndlm="${cfg_run_ndlm_main}"
declare -a EXPECTED_QUANTILES=()
declare -a EXPECTED_Q_LABELS=()
quantile_rule_desc=""
if [[ "${PROFILE_EFFECTIVE}" == "production" ]]; then
  # Production remains strict: always enforce canonical 7 quantiles.
  EXPECTED_QUANTILES=(5 20 35 50 65 80 95)
  EXPECTED_Q_LABELS=(05 20 35 50 65 80 95)
  quantile_rule_desc="canonical_7_quantiles_enforced"
else
  # Smoke and production_proof follow requested quantiles from resolved_config; default q=50 when absent.
  if [[ -n "${cfg_quantile_nums_csv}" ]]; then
    IFS=',' read -r -a EXPECTED_QUANTILES <<< "${cfg_quantile_nums_csv}"
  else
    EXPECTED_QUANTILES=(50)
  fi
  if [[ -n "${cfg_quantile_labels_csv}" ]]; then
    IFS=',' read -r -a EXPECTED_Q_LABELS <<< "${cfg_quantile_labels_csv}"
  fi
  if [[ "${#EXPECTED_Q_LABELS[@]}" -ne "${#EXPECTED_QUANTILES[@]}" ]]; then
    EXPECTED_Q_LABELS=()
    for q in "${EXPECTED_QUANTILES[@]}"; do
      EXPECTED_Q_LABELS+=("$(printf "%02d" "${q}")")
    done
  fi
  if [[ "${PROFILE_EFFECTIVE}" == "production_proof" ]]; then
    quantile_rule_desc="config_declared_quantiles_enforced"
  else
    quantile_rule_desc="quantiles_from_resolved_config_or_default_50"
  fi
fi

present_quantiles=()
missing_quantiles=()
if [[ "${require_multivar}" == "true" ]]; then
  for q in "${EXPECTED_QUANTILES[@]}"; do
    found="$(find "${RUN_ROOT}/fit" -type f -name "DISC_variables_${q}_exAL_synth_DISC.RData" -print -quit 2>/dev/null || true)"
    if [[ -n "${found}" ]]; then
      present_quantiles+=("${q}")
    else
      missing_quantiles+=("${q}")
    fi
  done
fi
quantile_count="${#present_quantiles[@]}"

present_univar_quantiles=()
missing_univar_quantiles=()
if [[ "${require_univar}" == "true" ]]; then
  for qlab in "${EXPECTED_Q_LABELS[@]}"; do
    qnum_no_lead="$((10#${qlab}))"
    found="$(
      find "${RUN_ROOT}/fit/exdqlm_univar/q=${qlab}/outputs" -type f \
        \( -name "variables_${qlab}_exAL_synth_DISC_uni.RData" -o -name "variables_${qnum_no_lead}_exAL_synth_DISC_uni.RData" \) \
        -print -quit 2>/dev/null || true
    )"
    if [[ -n "${found}" ]]; then
      present_univar_quantiles+=("${qlab}")
    else
      missing_univar_quantiles+=("${qlab}")
    fi
  done
fi

ndlm_output_path=""
declare -a NDLM_ACCEPTED_FILENAMES=(
  "DISC_variables_50_NDLM_synth_DISC.RData"
  "ndlm_main_state.RData"
  "ndlm_main_*.RData"
)
if [[ "${require_ndlm}" == "true" ]]; then
  ndlm_find_expr=()
  for ndlm_name in "${NDLM_ACCEPTED_FILENAMES[@]}"; do
    if [[ "${#ndlm_find_expr[@]}" -gt 0 ]]; then
      ndlm_find_expr+=(-o)
    fi
    ndlm_find_expr+=(-name "${ndlm_name}")
  done
  ndlm_output_path="$(
    find "${RUN_ROOT}/fit/ndlm_main/outputs" -type f \
      \( "${ndlm_find_expr[@]}" \) \
      -print -quit 2>/dev/null || true
  )"
fi

contract_univar_reports=()
missing_contract_univar=()
if [[ "${cfg_contract_checks_enabled}" == "true" && "${require_univar}" == "true" ]]; then
  for qlab in "${EXPECTED_Q_LABELS[@]}"; do
    found="$(find "${RUN_ROOT}/fit/contract_checks/exdqlm_univar/q=${qlab}" -type f -name '*.json' -print -quit 2>/dev/null || true)"
    if [[ -n "${found}" ]]; then
      contract_univar_reports+=("${found}")
    else
      missing_contract_univar+=("fit/contract_checks/exdqlm_univar/q=${qlab}/*.json")
    fi
  done
fi

contract_ndlm_report=""
if [[ "${cfg_contract_checks_enabled}" == "true" && "${require_ndlm}" == "true" ]]; then
  contract_ndlm_report="$(find "${RUN_ROOT}/fit/contract_checks/ndlm_main" -type f -name '*.json' -print -quit 2>/dev/null || true)"
fi

diag_univar_reports=()
missing_diag_univar=()
if [[ "${cfg_diagnostics_enabled}" == "true" && "${require_univar}" == "true" ]]; then
  for qlab in "${EXPECTED_Q_LABELS[@]}"; do
    found="$(find "${RUN_ROOT}/fit/diagnostics/exdqlm_univar/q=${qlab}" -type f -name '*.json' -print -quit 2>/dev/null || true)"
    if [[ -n "${found}" ]]; then
      diag_univar_reports+=("${found}")
    else
      missing_diag_univar+=("fit/diagnostics/exdqlm_univar/q=${qlab}/*.json")
    fi
  done
fi

diag_ndlm_report=""
if [[ "${cfg_diagnostics_enabled}" == "true" && "${require_ndlm}" == "true" ]]; then
  diag_ndlm_report="$(find "${RUN_ROOT}/fit/diagnostics/ndlm_main" -type f -name '*.json' -print -quit 2>/dev/null || true)"
fi

mapfile -t WRITE_AUDIT_PATCHES < <(find "${RUN_ROOT}/validate/write_audit" -type f -name 'fs_diff.patch' 2>/dev/null | sort)
if [[ -f "${WRITE_AUDIT_PRIMARY}" ]]; then
  WRITE_AUDIT_PATH="${WRITE_AUDIT_PRIMARY}"
elif [[ "${#WRITE_AUDIT_PATCHES[@]}" -gt 0 ]]; then
  WRITE_AUDIT_PATH="${WRITE_AUDIT_PATCHES[0]}"
else
  WRITE_AUDIT_PATH=""
fi

write_audit_nonempty=()
for patch_path in "${WRITE_AUDIT_PATCHES[@]:-}"; do
  if [[ -f "${patch_path}" ]]; then
    patch_size="$(wc -c < "${patch_path}" | tr -d '[:space:]')"
    if [[ "${patch_size}" != "0" ]]; then
      write_audit_nonempty+=("${patch_path}:${patch_size}")
    fi
  fi
done

post_file_count=0
if [[ -d "${POST_OUTPUTS_DIR}" ]]; then
  post_file_count="$(find "${POST_OUTPUTS_DIR}" -type f | wc -l | tr -d '[:space:]')"
fi

manifest_finished_at=""
manifest_validation_status=""
manifest_git_dirty=""

if [[ -f "${MANIFEST_PATH}" ]]; then
  if python3 - <<'PY' >/dev/null 2>&1
import yaml
PY
  then
    mapfile -t manifest_vals < <(python3 - "${MANIFEST_PATH}" <<'PY'
import sys
import yaml

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    doc = yaml.safe_load(f) or {}

def get(path):
    cur = doc
    for key in path:
        if not isinstance(cur, dict):
            return ""
        cur = cur.get(key)
    if cur is None:
        return ""
    return str(cur)

print(get(["timestamps", "finished_at_utc"]))
print(get(["validation", "status"]))
print(get(["git", "dirty"]))
PY
)
    manifest_finished_at="${manifest_vals[0]:-}"
    manifest_validation_status="${manifest_vals[1]:-}"
    manifest_git_dirty="${manifest_vals[2]:-}"
  else
    manifest_finished_at="$(awk '/^[[:space:]]*finished_at_utc:/ {print $2; exit}' "${MANIFEST_PATH}")"
    manifest_validation_status="$(awk '
      /^validation:/ {inv=1; next}
      inv && /^[^[:space:]]/ {inv=0}
      inv && /^[[:space:]]+status:/ {print $2; exit}
    ' "${MANIFEST_PATH}")"
    manifest_git_dirty="$(awk '
      /^git:/ {ing=1; next}
      ing && /^[^[:space:]]/ {ing=0}
      ing && /^[[:space:]]+dirty:/ {print $2; exit}
    ' "${MANIFEST_PATH}")"
  fi
fi

manifest_finished_at="$(norm_null "${manifest_finished_at}")"
manifest_validation_status="$(norm_null "${manifest_validation_status}")"
manifest_git_dirty="$(norm_null "${manifest_git_dirty}")"

repo_git_porcelain="$(git -C "${REPO_ROOT}" status --porcelain=v1 || true)"
if [[ -n "${repo_git_porcelain}" ]]; then
  repo_dirty="true"
else
  repo_dirty="false"
fi

chk_manifest_exists="false"
[[ -f "${MANIFEST_PATH}" ]] && chk_manifest_exists="true"

chk_finished_at="false"
[[ -n "${manifest_finished_at}" ]] && chk_finished_at="true"

chk_quantiles="false"
if [[ "${require_multivar}" != "true" ]]; then
  chk_quantiles="true"
elif [[ "${PROFILE_EFFECTIVE}" == "production" ]]; then
  [[ "${quantile_count}" -eq 7 ]] && chk_quantiles="true"
elif [[ "${PROFILE_EFFECTIVE}" == "production_proof" ]]; then
  [[ "${quantile_count}" -eq "${#EXPECTED_QUANTILES[@]}" && "${#missing_quantiles[@]}" -eq 0 ]] && chk_quantiles="true"
else
  [[ "${#missing_quantiles[@]}" -eq 0 ]] && chk_quantiles="true"
fi

chk_univar_outputs="true"
if [[ "${require_univar}" == "true" ]]; then
  [[ "${#missing_univar_quantiles[@]}" -eq 0 ]] || chk_univar_outputs="false"
fi

chk_ndlm_outputs="true"
if [[ "${require_ndlm}" == "true" ]]; then
  if [[ -z "${ndlm_output_path}" ]]; then
    chk_ndlm_outputs="false"
  fi
fi

chk_contract_univar="true"
if [[ "${cfg_contract_checks_enabled}" == "true" && "${require_univar}" == "true" ]]; then
  [[ "${#missing_contract_univar[@]}" -eq 0 ]] || chk_contract_univar="false"
fi

chk_contract_ndlm="true"
if [[ "${cfg_contract_checks_enabled}" == "true" && "${require_ndlm}" == "true" ]]; then
  [[ -n "${contract_ndlm_report}" ]] || chk_contract_ndlm="false"
fi

chk_diag_univar="true"
if [[ "${cfg_diagnostics_enabled}" == "true" && "${require_univar}" == "true" ]]; then
  [[ "${#missing_diag_univar[@]}" -eq 0 ]] || chk_diag_univar="false"
fi

chk_diag_ndlm="true"
if [[ "${cfg_diagnostics_enabled}" == "true" && "${require_ndlm}" == "true" ]]; then
  [[ -n "${diag_ndlm_report}" ]] || chk_diag_ndlm="false"
fi

chk_post_outputs="false"
if [[ -d "${POST_OUTPUTS_DIR}" && "${post_file_count}" -gt 0 ]]; then
  chk_post_outputs="true"
fi

chk_compare_report="false"
[[ -f "${COMPARE_REPORT_PATH}" ]] && chk_compare_report="true"

chk_write_audit_patch="false"
[[ -n "${WRITE_AUDIT_PATH}" && -f "${WRITE_AUDIT_PATH}" ]] && chk_write_audit_patch="true"

chk_write_audit_clean="true"
if [[ "${PROFILE_EFFECTIVE}" == "smoke" ]]; then
  if [[ "${#WRITE_AUDIT_PATCHES[@]}" -eq 0 ]]; then
    chk_write_audit_clean="false"
  elif [[ "${#write_audit_nonempty[@]}" -gt 0 ]]; then
    chk_write_audit_clean="false"
  fi
fi

chk_report_md="false"
[[ -f "${REPORT_MD_PATH}" ]] && chk_report_md="true"

chk_report_json="false"
[[ -f "${REPORT_JSON_PATH}" ]] && chk_report_json="true"

chk_validation_pass="false"
if [[ "${manifest_validation_status}" == "pass" ]]; then
  chk_validation_pass="true"
fi

overall_pass="false"
if [[ "${PROFILE_EFFECTIVE}" == "production" || "${PROFILE_EFFECTIVE}" == "production_proof" ]]; then
  if [[ "${chk_manifest_exists}" == "true" && \
        "${chk_finished_at}" == "true" && \
        "${chk_quantiles}" == "true" && \
        "${chk_univar_outputs}" == "true" && \
        "${chk_ndlm_outputs}" == "true" && \
        "${chk_contract_univar}" == "true" && \
        "${chk_contract_ndlm}" == "true" && \
        "${chk_diag_univar}" == "true" && \
        "${chk_diag_ndlm}" == "true" && \
        "${chk_post_outputs}" == "true" && \
        "${chk_compare_report}" == "true" && \
        "${chk_write_audit_patch}" == "true" && \
        "${chk_report_md}" == "true" && \
        "${chk_report_json}" == "true" && \
        "${chk_validation_pass}" == "true" ]]; then
    overall_pass="true"
  fi
else
  if [[ "${chk_manifest_exists}" == "true" && \
        "${chk_finished_at}" == "true" && \
        "${chk_quantiles}" == "true" && \
        "${chk_univar_outputs}" == "true" && \
        "${chk_ndlm_outputs}" == "true" && \
        "${chk_contract_univar}" == "true" && \
        "${chk_contract_ndlm}" == "true" && \
        "${chk_diag_univar}" == "true" && \
        "${chk_diag_ndlm}" == "true" && \
        "${chk_post_outputs}" == "true" && \
        "${chk_compare_report}" == "true" && \
        "${chk_write_audit_patch}" == "true" && \
        "${chk_write_audit_clean}" == "true" && \
        "${chk_report_md}" == "true" && \
        "${chk_report_json}" == "true" && \
        "${chk_validation_pass}" == "true" ]]; then
    overall_pass="true"
  fi
fi

missing_q_csv="$(join_by "," "${missing_quantiles[@]:-}")"
present_q_csv="$(join_by "," "${present_quantiles[@]:-}")"
[[ -n "${missing_q_csv}" ]] || missing_q_csv="none"
[[ -n "${present_q_csv}" ]] || present_q_csv="none"
missing_univar_q_csv="$(join_by "," "${missing_univar_quantiles[@]:-}")"
present_univar_q_csv="$(join_by "," "${present_univar_quantiles[@]:-}")"
[[ -n "${missing_univar_q_csv}" ]] || missing_univar_q_csv="none"
[[ -n "${present_univar_q_csv}" ]] || present_univar_q_csv="none"
missing_contract_univar_csv="$(join_by "," "${missing_contract_univar[@]:-}")"
[[ -n "${missing_contract_univar_csv}" ]] || missing_contract_univar_csv="none"
missing_diag_univar_csv="$(join_by "," "${missing_diag_univar[@]:-}")"
[[ -n "${missing_diag_univar_csv}" ]] || missing_diag_univar_csv="none"
contract_ndlm_report_out="${contract_ndlm_report:-none}"
diag_ndlm_report_out="${diag_ndlm_report:-none}"
write_audit_nonempty_csv="$(join_by "," "${write_audit_nonempty[@]:-}")"
[[ -n "${write_audit_nonempty_csv}" ]] || write_audit_nonempty_csv="none"
if [[ "${require_multivar}" == "true" ]]; then
  quantile_target="${#EXPECTED_QUANTILES[@]}"
else
  quantile_target="0"
fi

largest10="$(
  find "${RUN_ROOT}" -type f -printf '%s\t%P\n' 2>/dev/null \
    | sort -nr \
    | head -n 10 \
    | while IFS=$'\t' read -r sz rel; do
        hs="$(numfmt --to=iec-i --suffix=B "${sz}" 2>/dev/null || echo "${sz}B")"
        printf '%s\t%s\t%s\n' "${hs}" "${sz}" "${rel}"
      done
)"

artifact_index="$(
  find "${RUN_ROOT}" -maxdepth 6 -type f -printf '%P\t%s\n' 2>/dev/null | sort
)"

where_stopped="n/a"
if [[ "${overall_pass}" != "true" ]]; then
  if [[ "${chk_quantiles}" != "true" ]]; then
    if [[ "${#present_quantiles[@]}" -eq 0 ]]; then
      where_stopped="fit (no completed quantiles)"
    else
      last_idx=$(( ${#present_quantiles[@]} - 1 ))
      where_stopped="fit (completed q=${present_quantiles[$last_idx]}, next missing q=${missing_quantiles[0]:-unknown})"
    fi
  elif [[ "${chk_univar_outputs}" != "true" || "${chk_ndlm_outputs}" != "true" || \
          "${chk_contract_univar}" != "true" || "${chk_contract_ndlm}" != "true" || \
          "${chk_diag_univar}" != "true" || "${chk_diag_ndlm}" != "true" ]]; then
    where_stopped="fit (family artifact/contract/diagnostics checks)"
  elif [[ "${chk_post_outputs}" != "true" ]]; then
    where_stopped="post"
  elif [[ "${chk_compare_report}" != "true" || "${chk_write_audit_patch}" != "true" || "${chk_validation_pass}" != "true" ]]; then
    where_stopped="validate"
  elif [[ "${chk_report_md}" != "true" || "${chk_report_json}" != "true" ]]; then
    where_stopped="report"
  else
    where_stopped="unknown"
  fi
fi

heavy_log_path="${RUN_ROOT}/logs/heavy_run.log"
heavy_log_tail="$(tail -n 120 "${heavy_log_path}" 2>/dev/null || true)"

latest_fit_log="$(
  find "${RUN_ROOT}/fit" -type f -path '*/q=*/logs/fit.log' 2>/dev/null \
    | sed -E 's#.*q=([0-9]{2})/logs/fit.log#\1\t&#' \
    | sort -n \
    | tail -n 1 \
    | cut -f2-
)"

latest_fit_tail=""
if [[ -n "${latest_fit_log}" && -f "${latest_fit_log}" ]]; then
  latest_fit_tail="$(tail -n 120 "${latest_fit_log}" 2>/dev/null || true)"
fi

error_hits="$(rg -n '(Error|Execution halted|Killed|SIGKILL|SIGTERM|segfault|OOM|No space left|cannot allocate|std::bad_alloc)' "${RUN_ROOT}" 2>/dev/null || true)"
exit_evidence="$(tail -n 30 "${REPO_ROOT}/repro/last_heavy_exit.txt" 2>/dev/null || true)"

ranked_causes="1) Process interruption (parent shell/session stop)\n"
ranked_causes+="   Evidence: no explicit crash markers in run logs, abrupt stage boundary stop.\n"
ranked_causes+="2) Runtime failure in child process before log flush\n"
ranked_causes+="   Evidence: missing q-level log for expected next quantile.\n"
ranked_causes+="3) Resource/event outside captured logs (external signal)\n"
ranked_causes+="   Evidence: no run-local SIG/OOM trace captured.\n"

if echo "${error_hits}" | grep -Eqi 'No space left'; then
  ranked_causes="1) Disk full\n   Evidence: 'No space left' marker found.\n2) Process interruption\n3) Child runtime failure"
elif echo "${error_hits}" | grep -Eqi 'OOM|cannot allocate|std::bad_alloc|Killed'; then
  ranked_causes="1) Memory pressure / OOM\n   Evidence: OOM/alloc markers found.\n2) Process interruption\n3) Child runtime failure"
elif echo "${error_hits}" | grep -Eqi 'Execution halted|Error'; then
  ranked_causes="1) Child runtime error\n   Evidence: explicit error markers found.\n2) Process interruption\n3) External resource failure"
fi

minimal_fix="Keep stage/model logic unchanged. Re-run via tmux detached session and preserve parent exit evidence (already in harness). If failed again, inspect q-specific fit.log + compare_report path before any code change."

if [[ "${overall_pass}" == "true" ]]; then
  report_path="${RUN_ROOT}/COMPLETION_REPORT.md"
  cat > "${report_path}" <<EOF
# COMPLETION REPORT: ${RUN_ID}

Result: PASS

## Strict Checklist
- profile: \`${PROFILE_EFFECTIVE}\`
- [$(bool_word "${chk_manifest_exists}")] run_manifest.yaml exists
- [$(bool_word "${chk_finished_at}")] manifest timestamps.finished_at_utc is non-null
- [$(bool_word "${chk_quantiles}")] expected multivar quantile outputs present
- [$(bool_word "${chk_univar_outputs}")] expected univar outputs present (when enabled)
- [$(bool_word "${chk_ndlm_outputs}")] expected NDLM outputs present (when enabled)
- [$(bool_word "${chk_contract_univar}")] expected univar contract-check reports present (when enabled)
- [$(bool_word "${chk_contract_ndlm}")] expected NDLM contract-check reports present (when enabled)
- [$(bool_word "${chk_diag_univar}")] expected univar diagnostics reports present (when enabled)
- [$(bool_word "${chk_diag_ndlm}")] expected NDLM diagnostics reports present (when enabled)
- [$(bool_word "${chk_post_outputs}")] post outputs exist under post/outputs/${RUN_ID}
- [$(bool_word "${chk_compare_report}")] validate/compare_report.json exists
- [$(bool_word "${chk_write_audit_patch}")] validate/write_audit fs_diff.patch exists
- [$(bool_word "${chk_write_audit_clean}")] all detected write_audit fs_diff.patch files are empty (smoke profile)
- [$(bool_word "${chk_report_md}")] report/summary.md exists
- [$(bool_word "${chk_report_json}")] report/summary.json exists
- [$(bool_word "${chk_validation_pass}")] manifest validation.status == pass

## Manifest + Git
- manifest.finished_at_utc: \`${manifest_finished_at}\`
- manifest.validation.status: \`${manifest_validation_status}\`
- manifest.git.dirty: \`${manifest_git_dirty}\`
- current_repo_dirty: \`${repo_dirty}\`

## Quantile Outputs
- completed_count: \`${quantile_count}/${quantile_target}\`
- present_quantiles: \`${present_q_csv}\`
- missing_quantiles: \`${missing_q_csv}\`
- present_univar_quantiles: \`${present_univar_q_csv}\`
- missing_univar_quantiles: \`${missing_univar_q_csv}\`
- ndlm_output_path: \`${ndlm_output_path:-<not-required-or-missing>}\`
- missing_contract_univar_reports: \`${missing_contract_univar_csv}\`
- contract_ndlm_report: \`${contract_ndlm_report_out}\`
- missing_diag_univar_reports: \`${missing_diag_univar_csv}\`
- diag_ndlm_report: \`${diag_ndlm_report_out}\`
- write_audit_nonempty_patches: \`${write_audit_nonempty_csv}\`

## Top 10 Largest Files (human_size, bytes, path)
\`\`\`text
${largest10}
\`\`\`

## Artifact Index (path, size_bytes)
\`\`\`text
${artifact_index}
\`\`\`
EOF
else
  report_path="${RUN_ROOT}/FAILURE_REPORT.md"
  cat > "${report_path}" <<EOF
# FAILURE REPORT: ${RUN_ID}

Result: FAIL

## Where It Stopped
- inferred_stop_point: \`${where_stopped}\`
- completed_quantiles: \`${present_q_csv}\`
- missing_quantiles: \`${missing_q_csv}\`

## Strict Checklist
- profile: \`${PROFILE_EFFECTIVE}\`
- [$(bool_word "${chk_manifest_exists}")] run_manifest.yaml exists
- [$(bool_word "${chk_finished_at}")] manifest timestamps.finished_at_utc is non-null
- [$(bool_word "${chk_quantiles}")] expected multivar quantile outputs present
- [$(bool_word "${chk_univar_outputs}")] expected univar outputs present (when enabled)
- [$(bool_word "${chk_ndlm_outputs}")] expected NDLM outputs present (when enabled)
- [$(bool_word "${chk_contract_univar}")] expected univar contract-check reports present (when enabled)
- [$(bool_word "${chk_contract_ndlm}")] expected NDLM contract-check reports present (when enabled)
- [$(bool_word "${chk_diag_univar}")] expected univar diagnostics reports present (when enabled)
- [$(bool_word "${chk_diag_ndlm}")] expected NDLM diagnostics reports present (when enabled)
- [$(bool_word "${chk_post_outputs}")] post outputs exist under post/outputs/${RUN_ID}
- [$(bool_word "${chk_compare_report}")] validate/compare_report.json exists
- [$(bool_word "${chk_write_audit_patch}")] validate/write_audit fs_diff.patch exists
- [$(bool_word "${chk_write_audit_clean}")] all detected write_audit fs_diff.patch files are empty (smoke profile)
- [$(bool_word "${chk_report_md}")] report/summary.md exists
- [$(bool_word "${chk_report_json}")] report/summary.json exists
- [$(bool_word "${chk_validation_pass}")] manifest validation.status == pass

## Manifest + Git
- manifest.finished_at_utc: \`${manifest_finished_at:-<null>}\`
- manifest.validation.status: \`${manifest_validation_status:-<null>}\`
- manifest.git.dirty: \`${manifest_git_dirty:-<null>}\`
- current_repo_dirty: \`${repo_dirty}\`

## Error / Exit Evidence
- heavy_run_log: \`${heavy_log_path}\`
- latest_fit_log: \`${latest_fit_log:-<none>}\`
- write_audit_patch_detected: \`${WRITE_AUDIT_PATH:-<none>}\`

### Key Lines (run log tail)
\`\`\`text
${heavy_log_tail}
\`\`\`

### Key Lines (latest fit log tail)
\`\`\`text
${latest_fit_tail}
\`\`\`

### Error Marker Grep Hits
\`\`\`text
${error_hits}
\`\`\`

### Exit Code Evidence (repro/last_heavy_exit.txt tail)
\`\`\`text
${exit_evidence}
\`\`\`

## Ranked Likely Causes
\`\`\`text
${ranked_causes}
\`\`\`

## Minimal Operational Fix (No Stage/Model Edits)
${minimal_fix}

## Top 10 Largest Files (human_size, bytes, path)
\`\`\`text
${largest10}
\`\`\`
EOF
fi

echo "RUN_ID=${RUN_ID}"
echo "profile=${PROFILE_EFFECTIVE}"
echo "profile_resolved=${PROFILE_EFFECTIVE}"
echo "profile_source=${profile_resolution_source}"
echo "quantile_rule=${quantile_rule_desc}"
echo "RESULT=$([[ "${overall_pass}" == "true" ]] && echo PASS || echo FAIL)"
echo "quantile_outputs=${quantile_count}/${quantile_target}"
echo "present_quantiles=${present_q_csv}"
echo "missing_quantiles=${missing_q_csv}"
echo "present_univar_quantiles=${present_univar_q_csv}"
echo "missing_univar_quantiles=${missing_univar_q_csv}"
echo "ndlm_output_path=${ndlm_output_path:-<not-required-or-missing>}"
echo "ndlm_accepted_output_names=$(join_by "," "${NDLM_ACCEPTED_FILENAMES[@]}")"
echo "require_multivar=${require_multivar}"
echo "require_univar=${require_univar}"
echo "require_ndlm=${require_ndlm}"
echo "fit.contract_checks.enabled=${cfg_contract_checks_enabled}"
echo "fit.diagnostics.enabled=${cfg_diagnostics_enabled}"
echo "family_check.multivar=$(bool_word "${chk_quantiles}")"
echo "family_check.univar_outputs=$(bool_word "${chk_univar_outputs}")"
echo "family_check.ndlm_output=$(bool_word "${chk_ndlm_outputs}")"
echo "family_check.univar_contract_reports=$(bool_word "${chk_contract_univar}")"
echo "family_check.ndlm_contract_report=$(bool_word "${chk_contract_ndlm}")"
echo "family_check.univar_diagnostics_reports=$(bool_word "${chk_diag_univar}")"
echo "family_check.ndlm_diagnostics_report=$(bool_word "${chk_diag_ndlm}")"
echo "missing_contract_univar_reports=${missing_contract_univar_csv}"
echo "contract_ndlm_report=${contract_ndlm_report_out}"
echo "missing_diag_univar_reports=${missing_diag_univar_csv}"
echo "diag_ndlm_report=${diag_ndlm_report_out}"
echo "post_outputs_dir=${POST_OUTPUTS_DIR}"
echo "post_outputs_file_count=${post_file_count}"
echo "compare_report_exists=${chk_compare_report}"
echo "write_audit_patch_path=${WRITE_AUDIT_PATH:-<none>}"
echo "write_audit_all_patches=$(join_by "," "${WRITE_AUDIT_PATCHES[@]:-}")"
echo "write_audit_nonempty_patches=${write_audit_nonempty_csv}"
echo "shared_source_map_path=${SHARED_SOURCE_MAP_PATH}"
echo "shared_source_map_exists=$([[ -f "${SHARED_SOURCE_MAP_PATH}" ]] && echo true || echo false)"
echo "snapshot_source_map_path=${SNAPSHOT_SOURCE_MAP_PATH}"
echo "snapshot_source_map_exists=$([[ -f "${SNAPSHOT_SOURCE_MAP_PATH}" ]] && echo true || echo false)"
echo "fit_shared_source_log=${FIT_SHARED_SOURCE_LOG}"
echo "fit_shared_source_log_exists=$([[ -f "${FIT_SHARED_SOURCE_LOG}" ]] && echo true || echo false)"
echo "post_shared_source_log=${POST_SHARED_SOURCE_LOG}"
echo "post_shared_source_log_exists=$([[ -f "${POST_SHARED_SOURCE_LOG}" ]] && echo true || echo false)"
echo "report_summary_md_exists=${chk_report_md}"
echo "report_summary_json_exists=${chk_report_json}"
echo "manifest_path=${MANIFEST_PATH}"
echo "manifest.finished_at_utc=${manifest_finished_at:-<null>}"
echo "manifest.validation.status=${manifest_validation_status:-<null>}"
echo "manifest.git.dirty=${manifest_git_dirty:-<null>}"
echo "repo.git.dirty=${repo_dirty}"
echo "report_written=${report_path}"
echo "top_10_largest_files:"
echo "${largest10}"

if [[ "${EXIT_NONZERO}" == "true" && "${overall_pass}" != "true" ]]; then
  exit 1
fi

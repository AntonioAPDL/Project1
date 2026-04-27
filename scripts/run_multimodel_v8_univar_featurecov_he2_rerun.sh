#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CONFIG="${MULTIMODEL_V8_UNIVAR_FEATURECOV_HE2_CONFIG:-$ROOT/config/multimodel_v8_univar_featurecov_he2_rerun_20260422.template.yaml}"

bash scripts/run_multimodel_v8_all9_feature_campaign.sh --config "$CONFIG" "$@"

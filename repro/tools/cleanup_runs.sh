#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

exec python3 "${ROOT_DIR}/repro/tools/cleanup_policy.py" --repo-root "${ROOT_DIR}" "$@"

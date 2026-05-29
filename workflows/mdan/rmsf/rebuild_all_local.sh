#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)
cd "$ROOT"

python workflows/mdan/rmsf/overlay.py

echo
echo "RMSF overlay composite rebuilt under:"
echo "  ${VARMDYN_RUN_ROOT:-$ROOT/runs}/mdan/rmsf/"

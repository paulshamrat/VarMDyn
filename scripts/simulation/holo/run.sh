#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PYTHON_BIN="${PYTHON:-python}"

cd "$ROOT"
"$PYTHON_BIN" scripts/simulation/holo/run.py "$@"

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKFLOW_PARENT="$ROOT/workflows"
OUTDIR="${OUTDIR:-${VARMDYN_RUN_ROOT:-$ROOT/data}/varmodel}"
PYTHON_BIN="${PYTHON:-python}"

mkdir -p "$OUTDIR"
cd "$WORKFLOW_PARENT"

"$PYTHON_BIN" varmodel/run.py \
  --config varmodel/config.yaml \
  --out-root "$OUTDIR" \
  "$@"

echo "[OK] varmodel outputs: $OUTDIR"

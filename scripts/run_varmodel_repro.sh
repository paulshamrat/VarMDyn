#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKFLOW_PARENT="$ROOT/workflows"
OUTDIR="${OUTDIR:-${VARMDYN_RUN_ROOT:-$ROOT/runs}/varmodel}"
RUN_NAME="${RUN_NAME:-reviewer_smoke}"

mkdir -p "$OUTDIR"
cd "$WORKFLOW_PARENT"

python varmodel/run.py \
  --config varmodel/config.yaml \
  --out-root "$OUTDIR" \
  --run-name "$RUN_NAME" \
  "$@"

echo "[OK] varmodel outputs: $OUTDIR"

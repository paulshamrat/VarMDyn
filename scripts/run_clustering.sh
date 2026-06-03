#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKFLOW="$ROOT/workflows/clustering"
OUTDIR="${OUTDIR:-${VARMDYN_RUN_ROOT:-$ROOT/data}/clustering}"
PYTHON_BIN="${PYTHON:-python}"

mkdir -p "$OUTDIR"
cd "$WORKFLOW"

"$PYTHON_BIN" -m pytest -q
MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/varmdyn-matplotlib}" \
  "$PYTHON_BIN" -m distcluster.cli run all \
    --config config.yaml \
    --outdir "$OUTDIR"

"$PYTHON_BIN" "$ROOT/scripts/compare_clustering_outputs.py" "$OUTDIR"

echo "[OK] clustering outputs: $OUTDIR"

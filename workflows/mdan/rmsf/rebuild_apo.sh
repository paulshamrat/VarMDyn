#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)
cd "$ROOT"

# Canonical apo rebuild path: use the replay wrapper that stages legacy inputs
# via LEGACY_BASE and regenerates a run-stamped apo RMSF analysis directory.
LEGACY_BASE=${LEGACY_BASE:-${VARMDYN_MD_LEGACY_ROOT:-}}
if [[ -z "${LEGACY_BASE}" ]]; then
  echo "Set VARMDYN_MD_LEGACY_ROOT or LEGACY_BASE to the MD input root." >&2
  exit 2
fi

REQS=("$LEGACY_BASE/03_mdsim")

missing=0
for p in "${REQS[@]}"; do
  if [[ ! -e "$p" ]]; then
    echo "[ERR] Missing required apo replay input: $p"
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  echo
  echo "Set LEGACY_BASE to the mounted legacy simulation root, then rerun."
  echo "Example:"
  echo "  LEGACY_BASE=/path/to/250922_sim bash workflows/mdan/rmsf/rebuild_apo.sh"
  exit 1
fi

VARMDYN_RMSF_APO_INPUT_ROOT="$LEGACY_BASE" \
VARMDYN_RMSF_APO_OUT_DIR="${VARMDYN_RUN_ROOT:-$ROOT/runs}/mdan/rmsf/apo" \
  bash workflows/mdan/rmsf/rebuild_apo_local.sh

echo
echo "Replay outputs are written under:"
echo "  ${VARMDYN_RUN_ROOT:-$ROOT/runs}/mdan/rmsf/"

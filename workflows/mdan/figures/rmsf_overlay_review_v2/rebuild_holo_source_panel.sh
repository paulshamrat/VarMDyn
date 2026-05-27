#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)
cd "$ROOT"

LEGACY_BASE=${LEGACY_BASE:-${VARMDYN_MD_LEGACY_ROOT:-}}
if [[ -z "${LEGACY_BASE}" ]]; then
  echo "Set VARMDYN_MD_LEGACY_ROOT or LEGACY_BASE to the private legacy simulation root." >&2
  exit 2
fi

REQS=(
  "$LEGACY_BASE/05_cdkl5atpmg/analysis/rmsf"
)

missing=0
for p in "${REQS[@]}"; do
  if [[ ! -e "$p" ]]; then
    echo "[ERR] Missing required holo replay input: $p"
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  echo
  echo "Set LEGACY_BASE to the mounted legacy simulation root, then rerun."
  echo "Example:"
  echo "  LEGACY_BASE=/path/to/250922_sim bash manuscript/assets/main_candidates/rmsf_overlay_review_v2/rebuild_holo_source_panel.sh"
  exit 1
fi

bash 03_md/run/rebuild_holo_rmsf_same_style.sh

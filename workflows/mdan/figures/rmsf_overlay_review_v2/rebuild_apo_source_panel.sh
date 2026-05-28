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

REQS=(
  "$LEGACY_BASE/00_scripts/run_rmsf_all.sh"
  "$LEGACY_BASE/00_scripts/plot_rmsf_all.py"
  "$LEGACY_BASE/03_mdsim"
)

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
  echo "  LEGACY_BASE=/path/to/250922_sim bash manuscript/assets/main_candidates/rmsf_overlay_review_v2/rebuild_apo_source_panel.sh"
  exit 1
fi

bash 03_md/analysis_repro/scripts/03_replay_rmsf_cdlsim.sh

echo
echo "Canonical manuscript apo panel path:"
echo "  manuscript/modules/03_md/figs/rmsf/rmsf_variant_means_overlay_range.png"
echo
echo "Replay outputs are written under:"
echo "  03_md/analysis_repro/results/replay/apo/rmsf_replay_<timestamp>/analysis/rmsf/"

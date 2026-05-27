#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)
cd "$ROOT"

bash manuscript/assets/main_candidates/rmsf_overlay_review_v2/rebuild_apo_source_panel_local.sh
bash manuscript/assets/main_candidates/rmsf_overlay_review_v2/rebuild_holo_source_panel_local.sh
python manuscript/assets/main_candidates/rmsf_overlay_review_v2/build_rmsf_overlay_review_v2.py

echo
echo "Local source-backed RMSF review figure rebuilt at:"
echo "  manuscript/assets/main_candidates/rmsf_overlay_review_v2/rmsf_overlay_apo_holo_panelAB_preview_v2.png"

#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)
cd "$ROOT"

PLOTTER="$ROOT/251008_simulation/00_scripts/plot_rmsf_all_variants_replicas_range_mean.py"
INPUT_ROOT="$ROOT/manuscript/assets/main_candidates/rmsf_overlay_review_v2/source_inputs/apo_root"
OUT_DIR="$ROOT/manuscript/modules/03_md/figs/rmsf"

if [[ ! -f "$PLOTTER" ]]; then
  echo "[ERR] Missing canonical plotter: $PLOTTER"
  exit 1
fi

count=$(find "$INPUT_ROOT/03_mdsim" -path '*/com/cr*/rmsf/rmsf.byresidue.agr' | wc -l | tr -d ' ')
if [[ "$count" -ne 18 ]]; then
  echo "[ERR] Expected 18 apo replica-level RMSF inputs under:"
  echo "  $INPUT_ROOT/03_mdsim"
  echo "Found: $count"
  exit 1
fi

python "$PLOTTER" \
  --root "$INPUT_ROOT" \
  --out-stem "$OUT_DIR/rmsf_all_variants_range_mean" \
  --overlay-stem "$OUT_DIR/rmsf_variant_means_overlay_range" \
  --res-start 1 --res-end 300 --xpad 2 \
  --ylim-min 0 --ylim-max 5.5 \
  --overlay-w 6.0 --overlay-h 1.75 \
  --overlay-wt-line-w 3.0 --overlay-var-line-w 1.8 \
  --overlay-ncols 6 \
  --overlay-legend-mode none \
  --overlay-save-bbox standard \
  --title-font 6 --label-font 6 --tick-font 6 --legend-font 5 --overlay-title-font 6 \
  --overlay-hide-title --overlay-hide-x-label --overlay-hide-x-tick-labels \
  --highlight-regions "20-60,46-56,151-191,169-171,171-171" \
  --highlight-colors "#F2D66B,#E9AE47,#CFEFF4,#7FD3DF,#2AA7B8" \
  --highlight-alphas "0.34,0.48,0.32,0.44,0.58" \
  --annotate-residues "42:K42,60:E60,135:D135,153:D153,171:Y171" \
  --annotate-line-color "#4d4d4d" \
  --annotate-text-color "#333333" \
  --annotate-line-style ":" \
  --annotate-line-width 0.8 \
  --annotate-font-size 5 \
  --annotate-alpha 0.75

echo
echo "Local apo source panel regenerated at:"
echo "  $OUT_DIR/rmsf_variant_means_overlay_range.png"

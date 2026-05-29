#!/usr/bin/env bash
set -Eeuo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../../.." && pwd)
cd "$ROOT"

PLOTTER="${VARMDYN_RMSF_PLOTTER:-$ROOT/workflows/mdan/rmsf/plot_rmsf_all_variants_replicas_range_mean.py}"
RAW_DIR="${VARMDYN_RMSF_HOLO_RAW_DIR:-${VARMDYN_DATA_ROOT:-$ROOT/data}/rmsf/holo_raw}"
OUT_DIR="${VARMDYN_RMSF_HOLO_OUT_DIR:-${VARMDYN_RUN_ROOT:-$ROOT/runs}/mdan/rmsf/holo}"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/rmsf_holo_local_XXXXXX")
trap 'rm -rf "$TMP"' EXIT

if [[ ! -f "$PLOTTER" ]]; then
  echo "[ERR] Missing canonical plotter: $PLOTTER"
  exit 1
fi

count=$(find "$RAW_DIR" -maxdepth 1 -type f -name '*_rmsf.byresidue.agr' | wc -l | tr -d ' ')
if [[ "$count" -ne 18 ]]; then
  echo "[ERR] Expected 18 holo raw RMSF inputs under:"
  echo "  $RAW_DIR"
  echo "Found: $count"
  exit 1
fi

for src in "$RAW_DIR"/*_rmsf.byresidue.agr; do
  base=$(basename "$src" _rmsf.byresidue.agr)
  replica=${base##*_}
  variant=${base%_"$replica"}
  dst="$TMP/03_mdsim/$variant/04.ptraj/com/$replica/rmsf/rmsf.byresidue.agr"
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
done

python "$PLOTTER" \
  --root "$TMP" \
  --out-stem "$OUT_DIR/rmsf_all_variants_range_mean_atpmg" \
  --overlay-stem "$OUT_DIR/rmsf_variant_means_overlay_range_atpmg" \
  --res-start 1 --res-end 300 --xpad 2 \
  --ylim-min 0 --ylim-max 5.5 \
  --overlay-w 6.0 --overlay-h 1.75 \
  --overlay-wt-line-w 3.0 --overlay-var-line-w 1.8 \
  --overlay-ncols 3 \
  --overlay-legend-mode none \
  --overlay-save-bbox standard \
  --title-font 6 --label-font 6 --tick-font 6 --legend-font 6 --overlay-title-font 6 \
  --overlay-hide-title \
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
echo "Local holo source panel regenerated at:"
echo "  $OUT_DIR/rmsf_variant_means_overlay_range_atpmg.png"

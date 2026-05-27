#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
OUT_DIR="$ROOT_DIR/modules/03_md/figs/combined"
mkdir -p "$OUT_DIR"

APO_FULL="$ROOT_DIR/modules/03_md/figs/rmsf/rmsf_all_variants_range_mean.png"
HOLO_FULL="$ROOT_DIR/modules/03_md/figs/holo_rmsf_replay_same_style/rmsf_all_variants_range_mean_atpmg.png"
S4_OUT="$OUT_DIR/supp_s4_rmsf_grid_apo_holo.png"
S6_OUT="$OUT_DIR/supp_s6_rmsf_segments_apo_holo.png"
S3_OUT="$OUT_DIR/supp_s3_rmsd_apo_holo.png"
S7_OUT="$OUT_DIR/supp_s7_dendrogram_apo_holo.png"
APO_RMSD="$ROOT_DIR/modules/03_md/figs/rmsd_apo_holo/rmsd_apo_all_variants.png"
HOLO_RMSD="$ROOT_DIR/modules/03_md/figs/rmsd_apo_holo/rmsd_atpmg_all_variants.png"
APO_DENDRO="$ROOT_DIR/modules/03_md/figs/quant/variant_dendrogram_including_WT.png"
HOLO_DENDRO="$ROOT_DIR/modules/03_md/figs/quant/variant_dendrogram_including_WT_holo.png"

ffmpeg -y \
  -i "$APO_RMSD" \
  -i "$HOLO_RMSD" \
  -filter_complex "\
    [0:v]scale=1680:-1[a]; \
    [1:v]scale=1680:-1[b]; \
    [a][b]hstack=inputs=2[stack]; \
    [stack]drawtext=text='A':x=18:y=18:fontsize=64:fontcolor=black, \
          drawtext=text='B':x=1698:y=18:fontsize=64:fontcolor=black[out]" \
  -map "[out]" \
  -frames:v 1 \
  -update 1 \
  "$S3_OUT"

python "$OUT_DIR/build_supp_s4_rmsf_premium.py"

ffmpeg -y \
  -i "$ROOT_DIR/modules/03_md/figs/rmsf/segments/020-060/rmsf_variant_means_overlay_range_020-060.png" \
  -i "$ROOT_DIR/modules/03_md/figs/rmsf/segments/075-120/rmsf_variant_means_overlay_range_075-120.png" \
  -i "$ROOT_DIR/modules/03_md/figs/rmsf/segments/091-115/rmsf_variant_means_overlay_range_091-115.png" \
  -i "$ROOT_DIR/modules/03_md/figs/rmsf/segments/160-225/rmsf_variant_means_overlay_range_160-225.png" \
  -i "$ROOT_DIR/modules/03_md/figs/rmsf/segments/240-295/rmsf_variant_means_overlay_range_240-295.png" \
  -i "$ROOT_DIR/modules/03_md/figs/holo_rmsf_replay_same_style/segments/020-060/rmsf_variant_means_overlay_range_020-060.png" \
  -i "$ROOT_DIR/modules/03_md/figs/holo_rmsf_replay_same_style/segments/075-120/rmsf_variant_means_overlay_range_075-120.png" \
  -i "$ROOT_DIR/modules/03_md/figs/holo_rmsf_replay_same_style/segments/091-115/rmsf_variant_means_overlay_range_091-115.png" \
  -i "$ROOT_DIR/modules/03_md/figs/holo_rmsf_replay_same_style/segments/160-225/rmsf_variant_means_overlay_range_160-225.png" \
  -i "$ROOT_DIR/modules/03_md/figs/holo_rmsf_replay_same_style/segments/240-295/rmsf_variant_means_overlay_range_240-295.png" \
  -filter_complex "\
    xstack=inputs=10:layout=0_70|1274_70|2548_70|0_1044|1274_1044|0_2088|1274_2088|2548_2088|0_3062|1274_3062:fill=white, \
    drawtext=text='A':x=24:y=12:fontsize=72:fontcolor=black, \
    drawtext=text='B':x=24:y=2006:fontsize=72:fontcolor=black[out]" \
  -map "[out]" \
  -frames:v 1 \
  -update 1 \
  "$S6_OUT"

ffmpeg -y \
  -i "$APO_DENDRO" \
  -i "$HOLO_DENDRO" \
  -filter_complex "\
    [0:v]scale=1680:-1[a]; \
    [1:v]scale=1680:-1[b]; \
    [a][b]hstack=inputs=2[stack]; \
    [stack]drawtext=text='A':x=18:y=18:fontsize=64:fontcolor=black, \
          drawtext=text='B':x=1698:y=18:fontsize=64:fontcolor=black[out]" \
  -map "[out]" \
  -frames:v 1 \
  -update 1 \
  "$S7_OUT"

printf 'Wrote %s\n' "$S3_OUT"
printf 'Wrote %s\n' "$S4_OUT"
printf 'Wrote %s\n' "$S6_OUT"
printf 'Wrote %s\n' "$S7_OUT"

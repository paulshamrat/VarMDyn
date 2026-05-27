#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../../../.." && pwd)"

if [[ -n "${CONDA_SH:-}" ]]; then
  # shellcheck source=/dev/null
  source "${CONDA_SH}"
fi
if command -v conda >/dev/null 2>&1; then
  conda activate "${VARMDYN_PYMOL_ENV:-pymol-viz}" >/dev/null 2>&1 || true
fi

/snap/bin/inkscape \
  "$HERE/fig2_variant_context_calpha_com_review_mod.svg" \
  --export-type=pdf \
  --export-filename="${OUT_PDF:-$ROOT/runs/clustering_figures/fig2_variant_context_calpha_com_review_mod.pdf}"

echo "${OUT_PDF:-$ROOT/runs/clustering_figures/fig2_variant_context_calpha_com_review_mod.pdf}"

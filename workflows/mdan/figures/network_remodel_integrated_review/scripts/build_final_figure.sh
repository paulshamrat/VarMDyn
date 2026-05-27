#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
RENDER_DIR="${SCRIPT_DIR}/render"
POSTPROCESS_DIR="${SCRIPT_DIR}/postprocess"
ASSEMBLE_DIR="${SCRIPT_DIR}/assemble"

mkdir -p "${WORKSPACE_DIR}/pymol"
mkdir -p "${WORKSPACE_DIR}/chimerax"
mkdir -p "${WORKSPACE_DIR}/state_paired"

cd "${WORKSPACE_DIR}/../../../../../.."

if [[ -n "${CONDA_SH:-}" ]]; then
  # shellcheck source=/dev/null
  source "${CONDA_SH}"
elif [[ -n "${CONDA_PREFIX:-}" && -f "${CONDA_PREFIX}/../etc/profile.d/conda.sh" ]]; then
  # shellcheck source=/dev/null
  source "${CONDA_PREFIX}/../etc/profile.d/conda.sh"
fi
if command -v conda >/dev/null 2>&1; then
  conda activate "${VARMDYN_CONDA_ENV:-varmdyn_env}" || true
fi

pymol -cq "${RENDER_DIR}/render_figure9_apo_holo_no_surface_exact.py"
python "${POSTPROCESS_DIR}/crop_exact_panels.py"
python "${ASSEMBLE_DIR}/build_exact_review_svg.py"
/snap/bin/inkscape "${WORKSPACE_DIR}/pymol/network_remodel_pymol_exact_review.svg" \
  --export-type=png \
  --export-filename="${WORKSPACE_DIR}/pymol/network_remodel_pymol_exact_review_preview.png"

XDG_DATA_HOME=/tmp/chimerax-data \
XDG_CONFIG_HOME=/tmp/chimerax-config \
XDG_CACHE_HOME=/tmp/chimerax-cache \
HOME=/tmp/chimerax-home \
chimerax --nogui --offscreen --silent "${RENDER_DIR}/apo_surface.cxc"

XDG_DATA_HOME=/tmp/chimerax-data \
XDG_CONFIG_HOME=/tmp/chimerax-config \
XDG_CACHE_HOME=/tmp/chimerax-cache \
HOME=/tmp/chimerax-home \
chimerax --nogui --offscreen --silent "${RENDER_DIR}/atp_mg_surface.cxc"

python "${POSTPROCESS_DIR}/crop_surface_panels.py"
python "${ASSEMBLE_DIR}/build_review_svg.py"
/snap/bin/inkscape "${WORKSPACE_DIR}/chimerax/network_remodel_surface_companion_review.svg" \
  --export-type=png \
  --export-filename="${WORKSPACE_DIR}/chimerax/network_remodel_surface_companion_review_preview.png"

python "${ASSEMBLE_DIR}/build_state_paired_review_svg.py"
/snap/bin/inkscape "${WORKSPACE_DIR}/state_paired/network_remodel_state_paired_review.svg" \
  --export-type=png \
  --export-filename="${WORKSPACE_DIR}/state_paired/network_remodel_state_paired_review_preview.png"

cp "${WORKSPACE_DIR}/state_paired/network_remodel_state_paired_review.svg" \
  "${WORKSPACE_DIR}/network_remodel_final.svg"
cp "${WORKSPACE_DIR}/state_paired/network_remodel_state_paired_review_preview.png" \
  "${WORKSPACE_DIR}/network_remodel_final_preview.png"

echo "${WORKSPACE_DIR}/network_remodel_final.svg"

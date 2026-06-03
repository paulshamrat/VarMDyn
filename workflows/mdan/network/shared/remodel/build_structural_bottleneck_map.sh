#!/usr/bin/env bash
# remodel.sh
# Coordinates cartoon and surface network rendering/assembly for the state-paired figure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DATA_ROOT="${VARMDYN_DATA_ROOT:-${REPO_ROOT}/data}"
RUN_ROOT="${VARMDYN_RUN_ROOT:-${REPO_ROOT}/data}"
WORKSPACE_DIR="${VARMDYN_NETWORK_FIGURE_WORKSPACE:-${DATA_ROOT}/network/full/render}"

mkdir -p "${WORKSPACE_DIR}/pymol"
mkdir -p "${WORKSPACE_DIR}/chimerax"
mkdir -p "${WORKSPACE_DIR}/state_paired"

VARMDYN_NETWORK_APO_PDB="${VARMDYN_NETWORK_APO_PDB:-${DATA_ROOT}/network/full/prepared/apo/01_WT/01_WT.pdb}"
VARMDYN_NETWORK_HOLO_PDB="${VARMDYN_NETWORK_HOLO_PDB:-${DATA_ROOT}/network/full/prepared/holo/01_WT/01_WT_with_ligands.pdb}"

if [[ ! -f "${VARMDYN_NETWORK_APO_PDB}" ]]; then
  echo "[ERROR] VARMDYN_NETWORK_APO_PDB is not readable: ${VARMDYN_NETWORK_APO_PDB}" >&2
  exit 2
fi
if [[ ! -f "${VARMDYN_NETWORK_HOLO_PDB}" ]]; then
  echo "[ERROR] VARMDYN_NETWORK_HOLO_PDB is not readable: ${VARMDYN_NETWORK_HOLO_PDB}" >&2
  exit 2
fi

export VARMDYN_NETWORK_FIGURE_WORKSPACE="${WORKSPACE_DIR}"
export VARMDYN_NETWORK_APO_PDB
export VARMDYN_NETWORK_HOLO_PDB

cd "${WORKSPACE_DIR}"

# Relying on the user's active environment (e.g., varmdyn_pymol) instead of hardcoding.

# 1. Render PyMOL cartoons
pymol -cq "${SCRIPT_DIR}/render_cartoon.py"

# 2. Crop cartoons
python "${SCRIPT_DIR}/crop.py"

# 3. Assemble cartoon row SVG
python "${SCRIPT_DIR}/assemble.py"

# 4. Render ChimeraX surfaces (using aligned apo structure)
sed \
  -e "s|@VARMDYN_NETWORK_APO_PDB@|${WORKSPACE_DIR}/pymol/apo_aligned.pdb|g" \
  -e "s|@VARMDYN_CHIMERAX_APO_OUT@|${WORKSPACE_DIR}/chimerax/apo_surface.png|g" \
  "${SCRIPT_DIR}/apo_surface.cxc" > "${WORKSPACE_DIR}/chimerax/apo_surface.runtime.cxc"

sed \
  -e "s|@VARMDYN_NETWORK_HOLO_PDB@|${VARMDYN_NETWORK_HOLO_PDB}|g" \
  -e "s|@VARMDYN_CHIMERAX_HOLO_OUT@|${WORKSPACE_DIR}/chimerax/atp_mg_surface.png|g" \
  "${SCRIPT_DIR}/holo_surface.cxc" > "${WORKSPACE_DIR}/chimerax/holo_surface.runtime.cxc"

XDG_DATA_HOME=/tmp/chimerax-data \
XDG_CONFIG_HOME=/tmp/chimerax-config \
XDG_CACHE_HOME=/tmp/chimerax-cache \
HOME=/tmp/chimerax-home \
chimerax --nogui --offscreen --silent "${WORKSPACE_DIR}/chimerax/apo_surface.runtime.cxc"

XDG_DATA_HOME=/tmp/chimerax-data \
XDG_CONFIG_HOME=/tmp/chimerax-config \
XDG_CACHE_HOME=/tmp/chimerax-cache \
HOME=/tmp/chimerax-home \
chimerax --nogui --offscreen --silent "${WORKSPACE_DIR}/chimerax/holo_surface.runtime.cxc"

# 5. Crop surfaces
python "${SCRIPT_DIR}/crop.py"

# 6. Assemble everything
python "${SCRIPT_DIR}/assemble.py"

# 7. Convert SVGs to PNGs
/snap/bin/inkscape "${WORKSPACE_DIR}/pymol/network_remodel_pymol_exact_review.svg" \
  --export-area-page \
  --export-type=png \
  --export-filename="${WORKSPACE_DIR}/pymol/network_remodel_pymol_exact_review_preview.png"

/snap/bin/inkscape "${WORKSPACE_DIR}/chimerax/network_remodel_surface_companion_review.svg" \
  --export-area-page \
  --export-type=png \
  --export-filename="${WORKSPACE_DIR}/chimerax/network_remodel_surface_companion_review_preview.png"

/snap/bin/inkscape "${WORKSPACE_DIR}/state_paired/network_remodel_state_paired_review.svg" \
  --export-area-page \
  --export-type=png \
  --export-filename="${WORKSPACE_DIR}/state_paired/network_remodel_state_paired_review_preview.png"

# 8. Copy final outputs
cp "${WORKSPACE_DIR}/state_paired/network_remodel_state_paired_review.svg" \
  "${WORKSPACE_DIR}/structural_bottleneck_remodeling_map.svg"
cp "${WORKSPACE_DIR}/state_paired/network_remodel_state_paired_review_preview.png" \
  "${WORKSPACE_DIR}/structural_bottleneck_remodeling_map.png"

echo "State-paired composite generated successfully at: ${WORKSPACE_DIR}/structural_bottleneck_remodeling_map.png"

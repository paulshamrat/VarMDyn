#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"
CODE_WORKFLOW_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_ROOT="${VARMDYN_DATA_ROOT:-${REPO_ROOT}/data}"
RUN_ROOT="${VARMDYN_RUN_ROOT:-${REPO_ROOT}/runs}"
WORKSPACE_DIR="${VARMDYN_NETWORK_FIGURE_WORKSPACE:-${RUN_ROOT}/mdan/figures/network_remodel_integrated_review}"
RENDER_DIR="${SCRIPT_DIR}/render"
POSTPROCESS_DIR="${SCRIPT_DIR}/postprocess"
ASSEMBLE_DIR="${SCRIPT_DIR}/assemble"

mkdir -p "${WORKSPACE_DIR}/pymol"
mkdir -p "${WORKSPACE_DIR}/chimerax"
mkdir -p "${WORKSPACE_DIR}/state_paired"

VARMDYN_NETWORK_APO_PDB="${VARMDYN_NETWORK_APO_PDB:-${DATA_ROOT}/structures/apo/01_WT.apo.pdb}"
VARMDYN_NETWORK_HOLO_PDB="${VARMDYN_NETWORK_HOLO_PDB:-${DATA_ROOT}/structures/holo_atpmg/01_WT.keepATPmg.pdb}"
if [[ ! -f "${VARMDYN_NETWORK_APO_PDB}" ]]; then
  echo "[ERROR] VARMDYN_NETWORK_APO_PDB is not readable: ${VARMDYN_NETWORK_APO_PDB}" >&2
  echo "[FIX] Put the apo PDB at ${DATA_ROOT}/structures/apo/01_WT.apo.pdb or set VARMDYN_NETWORK_APO_PDB." >&2
  echo "[FIX] To create the data folders, run: python scripts/init_data_layout.py" >&2
  exit 2
fi
if [[ ! -f "${VARMDYN_NETWORK_HOLO_PDB}" ]]; then
  echo "[ERROR] VARMDYN_NETWORK_HOLO_PDB is not readable: ${VARMDYN_NETWORK_HOLO_PDB}" >&2
  echo "[FIX] Put the holo/ATP-Mg PDB at ${DATA_ROOT}/structures/holo_atpmg/01_WT.keepATPmg.pdb or set VARMDYN_NETWORK_HOLO_PDB." >&2
  echo "[FIX] To create the data folders, run: python scripts/init_data_layout.py" >&2
  exit 2
fi
export VARMDYN_NETWORK_FIGURE_WORKSPACE="${WORKSPACE_DIR}"
export VARMDYN_NETWORK_APO_PDB
export VARMDYN_NETWORK_HOLO_PDB

cd "${WORKSPACE_DIR}"

if [[ -n "${CONDA_SH:-}" && -f "${CONDA_SH}" ]]; then
  # shellcheck source=/dev/null
  source "${CONDA_SH}"
elif [[ -n "${CONDA_EXE:-}" ]]; then
  CONDA_ROOT="$(cd "$(dirname "${CONDA_EXE}")/.." && pwd)"
  if [[ -f "${CONDA_ROOT}/etc/profile.d/conda.sh" ]]; then
    # shellcheck source=/dev/null
    source "${CONDA_ROOT}/etc/profile.d/conda.sh"
  fi
elif [[ -f "${HOME}/miniforge3/etc/profile.d/conda.sh" ]]; then
  # shellcheck source=/dev/null
  source "${HOME}/miniforge3/etc/profile.d/conda.sh"
fi
if declare -F conda >/dev/null 2>&1; then
  conda activate "${VARMDYN_CONDA_ENV:-varmdyn_env}" || true
fi

pymol -cq "${RENDER_DIR}/render_figure9_apo_holo_no_surface_exact.py"
python "${POSTPROCESS_DIR}/crop_exact_panels.py"
python "${ASSEMBLE_DIR}/build_exact_review_svg.py"
/snap/bin/inkscape "${WORKSPACE_DIR}/pymol/network_remodel_pymol_exact_review.svg" \
  --export-type=png \
  --export-filename="${WORKSPACE_DIR}/pymol/network_remodel_pymol_exact_review_preview.png"

sed \
  -e "s|@VARMDYN_NETWORK_APO_PDB@|${VARMDYN_NETWORK_APO_PDB}|g" \
  -e "s|@VARMDYN_CHIMERAX_APO_OUT@|${WORKSPACE_DIR}/chimerax/apo_surface.png|g" \
  "${RENDER_DIR}/apo_surface.cxc" > "${WORKSPACE_DIR}/chimerax/apo_surface.runtime.cxc"
sed \
  -e "s|@VARMDYN_NETWORK_HOLO_PDB@|${VARMDYN_NETWORK_HOLO_PDB}|g" \
  -e "s|@VARMDYN_CHIMERAX_HOLO_OUT@|${WORKSPACE_DIR}/chimerax/atp_mg_surface.png|g" \
  "${RENDER_DIR}/atp_mg_surface.cxc" > "${WORKSPACE_DIR}/chimerax/atp_mg_surface.runtime.cxc"

XDG_DATA_HOME=/tmp/chimerax-data \
XDG_CONFIG_HOME=/tmp/chimerax-config \
XDG_CACHE_HOME=/tmp/chimerax-cache \
HOME=/tmp/chimerax-home \
chimerax --nogui --offscreen --silent "${WORKSPACE_DIR}/chimerax/apo_surface.runtime.cxc"

XDG_DATA_HOME=/tmp/chimerax-data \
XDG_CONFIG_HOME=/tmp/chimerax-config \
XDG_CACHE_HOME=/tmp/chimerax-cache \
HOME=/tmp/chimerax-home \
chimerax --nogui --offscreen --silent "${WORKSPACE_DIR}/chimerax/atp_mg_surface.runtime.cxc"

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

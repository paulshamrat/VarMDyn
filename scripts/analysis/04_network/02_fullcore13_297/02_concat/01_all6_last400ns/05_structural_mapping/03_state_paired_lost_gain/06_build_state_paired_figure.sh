#!/usr/bin/env bash
set -Eeuo pipefail
STATE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${STATE_DIR}/../00_settings.sh"
"${STATE_DIR}/../01_prepared_inputs/02_prepare_network_structure_maps.sh"
QT_QPA_PLATFORM=offscreen pymol -cq -r "${STATE_DIR}/01_render_state_paired_cartoons.py" -- "${STRUCTURAL_MAPPING_ROOT}"
python3 "${STATE_DIR}/03_render_state_surfaces.py" "${STRUCTURAL_MAPPING_ROOT}"
for cxc in "${STRUCTURAL_MAPPING_ROOT}/03_state_paired_lost_gain/raw_apo_surface.cxc" "${STRUCTURAL_MAPPING_ROOT}/03_state_paired_lost_gain/raw_holo_surface.cxc"; do
  XDG_DATA_HOME=/tmp/cdkl5-chimerax-data XDG_CONFIG_HOME=/tmp/cdkl5-chimerax-config XDG_CACHE_HOME=/tmp/cdkl5-chimerax-cache HOME=/tmp/cdkl5-chimerax-home chimerax --nogui --offscreen --silent "$cxc"
done
python3 "${STATE_DIR}/04_crop_state_paired_panels.py" "${STRUCTURAL_MAPPING_ROOT}"
python3 "${STATE_DIR}/05_assemble_state_paired_figure.py" "${STRUCTURAL_MAPPING_ROOT}"

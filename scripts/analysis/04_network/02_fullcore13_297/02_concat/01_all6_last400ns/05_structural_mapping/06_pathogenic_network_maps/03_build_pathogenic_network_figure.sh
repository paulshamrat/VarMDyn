#!/usr/bin/env bash
set -Eeuo pipefail
FIGURE_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${FIGURE_DIR}/../00_settings.sh"
"${FIGURE_DIR}/../01_prepared_inputs/02_prepare_network_structure_maps.sh"
QT_QPA_PLATFORM=offscreen pymol -cq -r "${FIGURE_DIR}/01_render_pathogenic_network_maps.py" -- "${STRUCTURAL_MAPPING_ROOT}"
python3 "${FIGURE_DIR}/02_assemble_pathogenic_network_figure.py" "${STRUCTURAL_MAPPING_ROOT}"

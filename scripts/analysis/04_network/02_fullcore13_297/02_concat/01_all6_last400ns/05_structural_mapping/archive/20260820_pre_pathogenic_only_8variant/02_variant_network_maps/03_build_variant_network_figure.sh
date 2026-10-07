#!/usr/bin/env bash
set -Eeuo pipefail
VARIANT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${VARIANT_DIR}/../00_settings.sh"
"${VARIANT_DIR}/../01_prepared_inputs/02_prepare_network_structure_maps.sh"
QT_QPA_PLATFORM=offscreen pymol -cq -r "${VARIANT_DIR}/01_render_variant_network_maps.py" -- "${STRUCTURAL_MAPPING_ROOT}"
python3 "${VARIANT_DIR}/02_assemble_variant_network_figure.py" "${STRUCTURAL_MAPPING_ROOT}"

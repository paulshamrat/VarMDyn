#!/usr/bin/env bash
set -Eeuo pipefail
PREP_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${PREP_DIR}/../00_settings.sh"
python3 "${PREP_DIR}/01_prepare_network_structure_maps.py" \
  --reference-root "${REFERENCE_ROOT}" \
  --coordinate-root "${COORDINATE_ROOT}" \
  --apo-pdb "${MANUSCRIPT_APO_PDB}" \
  --holo-pdb "${MANUSCRIPT_HOLO_PDB}" \
  --output-root "${STRUCTURAL_MAPPING_ROOT}" \
  --min-recurrence "${MIN_RECURRENCE_COUNT}"
python3 "${PREP_DIR}/03_check_network_structure_maps.py" "${STRUCTURAL_MAPPING_ROOT}"

#!/usr/bin/env bash
# Build the recurrent pathogenic reference and test WT/S240T/H254R controls.
set -Eeuo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../00_settings.sh"
METHOD=$(network_method_tag)
RESULT_ROOT="${NETWORK_ROOT}/data/analysis/04_network/02_fullcore13_297/02_concat/01_all6_last400ns"
COORDINATE_ROOT="${RESULT_ROOT}/04_emergent/02_control_equilibrium_coordinates"
CONTROLS=(01_WT 07_S240T 08_H254R)

for STATE in apo holo; do
  if [[ "${STATE}" == "apo" ]]; then BRANCH="03_mdsim"; EQUILIBRIUM_PDB="cdl.com.gas.equib.pdb"; else BRANCH="05_cdkl5atpmg"; EQUILIBRIUM_PDB="cdl.com.striped_v2.equib.pdb"; fi
  for CONTROL in "${CONTROLS[@]}"; do
    TARGET="${COORDINATE_ROOT}/${STATE}/${CONTROL}/01_equilibrium.pdb"
    [[ -f "${TARGET}" ]] && continue
    [[ -n "${MD_DATA_ROOT}" ]] || { echo "ERROR: missing ${TARGET}; run on the host with MD_DATA_ROOT." >&2; exit 1; }
    SOURCE="${MD_DATA_ROOT}/${BRANCH}/${CONTROL}/02.leap/com/${EQUILIBRIUM_PDB}"
    [[ -f "${SOURCE}" ]] || { echo "ERROR: missing equilibrated PDB: ${SOURCE}" >&2; exit 1; }
    mkdir -p "$(dirname "${TARGET}")"; cp "${SOURCE}" "${TARGET}"
  done
done

python3 "${SCRIPT_DIR}/03_build_recurrent_pathogenic_reference.py" \
  --network-root "${RESULT_ROOT}/02_network/${METHOD}" \
  --recurrence-summary "${RESULT_ROOT}/04_emergent/01_pathogenic_candidates/01_site_comparison/04_pathogenic_recurrence_summary.tsv" \
  --coordinate-root "${COORDINATE_ROOT}" \
  --output-root "${RESULT_ROOT}/04_emergent/02_recurrent_pathogenic_reference" \
  --tolerance-a "${SPATIAL_TOLERANCE_A}"

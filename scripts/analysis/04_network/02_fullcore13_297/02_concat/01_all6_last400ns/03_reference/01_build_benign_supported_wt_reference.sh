#!/usr/bin/env bash
# Reuse the validated reference-builder logic with this full-core concat input.
set -Eeuo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../00_settings.sh"
METHOD=$(network_method_tag)
RESULT_ROOT="${NETWORK_ROOT}/data/analysis/04_network/02_fullcore13_297/02_concat/01_all6_last400ns"
BUILDER="${NETWORK_ROOT}/scripts/analysis/04_network/03_stablecore13_297/02_concat/01_selected_triplet/08_build_concat_pi_reference.py"
COORDINATE_ROOT="${RESULT_ROOT}/03_reference/00_reference_coordinates"
mkdir -p "${COORDINATE_ROOT}"
for STATE in apo holo; do
    REFERENCE="${COORDINATE_ROOT}/${STATE}_WT_equib.pdb"
    # A regular file here is the fixed coordinate reference for this analysis.
    # Replace older host-specific symlinks once, then use the same PDB on every host.
    [[ -f "${REFERENCE}" && ! -L "${REFERENCE}" ]] && continue
    SOURCE="${RESULT_ROOT}/01_inputs/${STATE}/01_WT/03_reference.pdb"
    [[ -f "${SOURCE}" ]] || { echo "ERROR: missing ${STATE} WT reference PDB" >&2; exit 1; }
    rm -f "${REFERENCE}"
    cp "${SOURCE}" "${REFERENCE}"
done
python3 "${BUILDER}" --network-root "${RESULT_ROOT}/02_network/${METHOD}" --coordinate-root "${COORDINATE_ROOT}" --output-root "${RESULT_ROOT}/03_reference/01_benign_supported_wt_reference" --tolerance-a "${SPATIAL_TOLERANCE_A}" --method-label "all-six-replica concatenated DyNetAn analysis" --trajectory-description "CR1--CR6; 100--500 ns; 500 frames/replica; 3000 concatenated frames"

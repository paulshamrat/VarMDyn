#!/usr/bin/env bash
# Stage 1 only: mutation-aware pathogenic recurrence; no WT/benign comparison.
set -Eeuo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../00_settings.sh"
METHOD=$(network_method_tag)
RESULT_ROOT="${NETWORK_ROOT}/data/analysis/04_network/02_fullcore13_297/02_concat/01_all6_last400ns"
COORDINATE_ROOT="${RESULT_ROOT}/04_emergent/00_variant_equilibrium_coordinates"
PATHOGENIC=(02_L119R 03_D193H 04_G202E 05_Q219K 06_C291Y)

# The 5-A fallback must use the equilibrated structure of the target variant.
# Stage these ten immutable PDB inputs once on the analysis host.  They are
# copied rather than linked so a later review sync remains self-contained.
for STATE in apo holo; do
  if [[ "${STATE}" == "apo" ]]; then
    BRANCH="03_mdsim"
    EQUILIBRIUM_PDB="cdl.com.gas.equib.pdb"
  else
    BRANCH="05_cdkl5atpmg"
    EQUILIBRIUM_PDB="cdl.com.striped_v2.equib.pdb"
  fi
  for VARIANT in "${PATHOGENIC[@]}"; do
    TARGET="${COORDINATE_ROOT}/${STATE}/${VARIANT}/01_equilibrium.pdb"
    [[ -f "${TARGET}" ]] && continue
    [[ -n "${MD_DATA_ROOT}" ]] || {
      echo "ERROR: missing ${TARGET}; run on the host with MD_DATA_ROOT to stage variant equilibrium PDBs." >&2
      exit 1
    }
    SOURCE="${MD_DATA_ROOT}/${BRANCH}/${VARIANT}/02.leap/com/${EQUILIBRIUM_PDB}"
    [[ -f "${SOURCE}" ]] || { echo "ERROR: missing equilibrated PDB: ${SOURCE}" >&2; exit 1; }
    mkdir -p "$(dirname "${TARGET}")"
    cp "${SOURCE}" "${TARGET}"
  done
done

python3 "${SCRIPT_DIR}/01_build_direct_pathogenic_candidates.py" \
  --network-root "${RESULT_ROOT}/02_network/${METHOD}" \
  --coordinate-root "${COORDINATE_ROOT}" \
  --output-root "${RESULT_ROOT}/04_emergent/01_pathogenic_candidates" \
  --tolerance-a "${SPATIAL_TOLERANCE_A}"

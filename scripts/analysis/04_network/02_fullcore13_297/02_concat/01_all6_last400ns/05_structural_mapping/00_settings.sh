#!/usr/bin/env bash
# Settings for structural projection of finalized reference-centered network calls.
set -Eeuo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# Portable runtime paths. Source config/paths.sh or export these variables first.
_vmd_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while [[ ! -f "${_vmd_root}/AGENTS.md" || ! -d "${_vmd_root}/scripts" ]]; do
    [[ "${_vmd_root}" != / ]] || { echo "Cannot locate VarMDyn root" >&2; return 2; }
    _vmd_root="$(dirname "${_vmd_root}")"
done
REPO="${VARMDYN_ROOT:-${_vmd_root}}"
NETWORK_ROOT="${REPO}"
MD_DATA_ROOT="${VARMDYN_MD_SOURCE_ROOT:-}"
SIM_ROOT="${MD_DATA_ROOT}"
DATA_LOCATION=external
DYNETAN_PYTHON="${VARMDYN_DYNETAN_PYTHON:-python3}"
RESULT_ROOT="${NETWORK_ROOT}/data/analysis/04_network/02_fullcore13_297/02_concat/01_all6_last400ns"
REFERENCE_ROOT="${RESULT_ROOT}/03_reference/01_benign_supported_wt_reference"
COORDINATE_ROOT="${RESULT_ROOT}/03_reference/00_reference_coordinates"
STRUCTURAL_MAPPING_ROOT="${RESULT_ROOT}/05_structural_mapping"

# Manuscript-canonical coordinate frames used for visual consistency in the
# review structural figures. Network event calls remain sourced from the
# current all-six/last-400-ns analysis outputs.
MANUSCRIPT_APO_PDB="${NETWORK_ROOT}/data/analysis/replay/network/holo_legacy_support/pymol/cdl.com.gas.leap.pdb"
MANUSCRIPT_HOLO_PDB="${NETWORK_ROOT}/251008_simulation/04_cdkl5atp/01_WT/02.leap/com/cdl.com.gas.leap.pdb"

# A site is recurrent for the state-paired figure when it occurs in at least
# two of the five pathogenic variant comparisons.  The per-variant figure does
# not apply this filter.
MIN_RECURRENCE_COUNT=2
PATHOGENIC_VARIANTS=(L119R D193H G202E Q219K C291Y)

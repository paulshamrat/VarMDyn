#!/usr/bin/env bash
# SETTINGS -- full-core, all-six-replica concatenated DyNetAn analysis.
# Edit this file only when the data location or scientific method changes.

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

# Six independent trajectories are concatenated in CR1--CR6 order.
REPLICAS=(cr1 cr2 cr3 cr4 cr5 cr6)
ANALYSIS_START_NS=100
ANALYSIS_END_NS=500
FRAMES_PER_REPLICA=500
NUM_WINDOWS=1
CONTACT_CUTOFF_A=4.5
CONTACT_PERSISTENCE=0.75
SPATIAL_TOLERANCE_A=5.0
NODE_SELECTION='segid PROT and resid 13:297 and not (name H* or name [123]H*)'

network_method_tag() {
    printf 't%s-%s_w%s_f%s_c%s_p%s_core13-297\n' \
        "$ANALYSIS_START_NS" "$ANALYSIS_END_NS" "$NUM_WINDOWS" \
        "$((FRAMES_PER_REPLICA * ${#REPLICAS[@]}))" "${CONTACT_CUTOFF_A/./p}" "${CONTACT_PERSISTENCE#0.}"
}

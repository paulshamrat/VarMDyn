#!/usr/bin/env bash
# Shared settings for the CDKL5 MD post-processing workflow.
# Edit SIM_ROOT only when the active simulation tree moves from scratch to
# persistent project storage. The directory layout below this root is fixed.

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
RESULT_ROOT="${REPO}/data/analysis/01_postprocess"

VARIANTS=(01_WT 02_L119R 03_D193H 04_G202E 05_Q219K 06_C291Y 07_S240T 08_H254R)
REPLICAS=(cr1 cr2 cr3 cr4 cr5 cr6)
PRODUCTION_STAGES=(25 26 27 28 29)

state_branch() {
    case "$1" in
        apo) printf '03_mdsim' ;;
        holo) printf '05_cdkl5atpmg' ;;
        *) echo "Unknown state: $1" >&2; return 2 ;;
    esac
}

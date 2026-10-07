#!/usr/bin/env bash
# Shared settings for the core13-297 structural-metrics workflow.
# Change DATA_LOCATION only when the active MD data move.

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

RESULT_ROOT="${REPO}/data/analysis/02_metrics/02_fullcore13_297"
CPPTRAJ_BIN="cpptraj"

VARIANTS=(01_WT 02_L119R 03_D193H 04_G202E 05_Q219K 06_C291Y 07_S240T 08_H254R)
REPLICAS=(cr1 cr2 cr3 cr4 cr5 cr6)

# Same 400-ps sampling as the validated whole-protein workflow.
SOURCE_FRAMES=5000
TRAJIN_STRIDE=4
OUTPUT_FRAMES=1250

# The CDKL5 kinase domain only.
RMSD_MASK=':13-297@CA,C,N'
RMSF_MASK=':13-297@C,CA,N'
RG_MASK=':13-297&!@H='
RMSF_RESIDUES=285

state_branch() {
    case "$1" in
        apo) printf '03_mdsim' ;;
        holo) printf '05_cdkl5atpmg' ;;
        *) echo "Unknown state: $1" >&2; return 2 ;;
    esac
}

state_inputs() {
    case "$1" in
        apo) printf 'striped\tcdl.com.gas.equib.prmtop\n' ;;
        holo) printf 'striped_v2\tcdl.com.striped_v2.equib.prmtop\n' ;;
        *) echo "Unknown state: $1" >&2; return 2 ;;
    esac
}

#!/usr/bin/env bash
# Settings for full kinase-core (residues 13--297), all-replica dynamics.
# Change DATA_LOCATION only when the active MD-data location changes.

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

ANALYSIS_ROOT="${REPO}/data/analysis"
RESULT_ROOT="${ANALYSIS_ROOT}/03_dynamics/02_fullcore13_297/03_windows/02_last400ns_100_500"
DYNAMICS_LOG_ROOT="${REPO}/logs/analysis/03_dynamics"

# 0--500 ns standardized trajectories contain 5,000 frames at 100 ps/frame.
WINDOW_START_NS=100
WINDOW_END_NS=500
SOURCE_FRAMES=5000
FRAME_INTERVAL_PS=100
WINDOW_SOURCE_FIRST_FRAME=1001
WINDOW_SOURCE_LAST_FRAME=5000
WINDOW_FRAMES=4000
KINASE_START_RESIDUE=13
KINASE_END_RESIDUE=297
VARIANTS=(01_WT 02_L119R 03_D193H 04_G202E 05_Q219K 06_C291Y 07_S240T 08_H254R)
REPLICAS=(cr1 cr2 cr3 cr4 cr5 cr6)
STATES=(apo holo)

state_branch() {
    case "$1" in apo) printf '03_mdsim' ;; holo) printf '05_cdkl5atpmg' ;; *) return 2 ;; esac
}
state_inputs() {
    case "$1" in
        apo) printf 'striped\tcdl.com.gas.equib.prmtop\tcdl.com.gas.equib.pdb\n' ;;
        holo) printf 'striped_v2\tcdl.com.striped_v2.equib.prmtop\tcdl.com.striped_v2.equib.pdb\n' ;;
        *) return 2 ;;
    esac
}
source_paths() {
    local state=$1 variant=$2 replica=$3 branch representation topology equilibrium_structure system
    branch=$(state_branch "${state}")
    IFS=$'\t' read -r representation topology equilibrium_structure < <(state_inputs "${state}")
    system="${MD_DATA_ROOT}/${branch}/${variant}"
    printf '%s\t%s\t%s\n' \
        "${system}/02.leap/com/${topology}" \
        "${system}/04.ptraj/com/${replica}/traj-proc/production-25-to-29-500ns.${replica}.${representation}.sampled-5.mdcrd.nc" \
        "${system}/02.leap/com/${equilibrium_structure}"
}

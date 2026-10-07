#!/usr/bin/env bash
# Calculate RMSF over 100-500 ns only, for kinase residues 13-297.
# Run on Insurgent or HPC.  Edit only the SETTINGS block.
set -Eeuo pipefail
umask 002

###############################################################################
RUN_SCOPE="${RUN_SCOPE:-test}"  # test = apo/01_WT/cr1; all = all 96 cases
EXECUTE="${EXECUTE:-no}"        # no = show plan; yes = calculate missing cases
MAX_WORKERS="${MAX_WORKERS:-6}"
###############################################################################

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../../00_settings.sh"
WINDOW_ROOT="${RESULT_ROOT}/03_windows/02_last400ns_100_500/01_window_metrics"
FIRST_SOURCE_FRAME=1001
WINDOW_FRAMES=1000

source_paths() {
    local state=$1 variant=$2 replica=$3 branch representation topology_name system
    branch=$(state_branch "${state}")
    IFS=$'\t' read -r representation topology_name < <(state_inputs "${state}")
    system="${SIM_ROOT}/${branch}/${variant}"
    printf '%s\t%s\n' "${system}/02.leap/com/${topology_name}" \
        "${system}/04.ptraj/com/${replica}/traj-proc/production-25-to-29-500ns.${replica}.${representation}.sampled-5.mdcrd.nc"
}

run_case() {
    local state=$1 variant=$2 replica=$3 topology trajectory target action rmsf_n
    IFS=$'\t' read -r topology trajectory < <(source_paths "${state}" "${variant}" "${replica}")
    target="${WINDOW_ROOT}/${state}/${variant}/${replica}"
    action=READY_TO_CALCULATE
    [[ -s "${target}/qc.tsv" && -s "${target}/rmsf_core13_297_100_500ns_byres.agr" ]] && action=ALREADY_PRESENT
    [[ -s "${topology}" && -s "${trajectory}" ]] || action=SOURCE_INCOMPLETE
    printf 'state=%s variant=%s replica=%s action=%s\n' "${state}" "${variant}" "${replica}" "${action}"
    [[ ${EXECUTE} == yes && ${action} == READY_TO_CALCULATE ]] || return 0
    mkdir -p "${target}"
    cat > "${target}/calculate_rmsf_100_500ns.in" <<EOF
parm ${topology}
trajin ${trajectory} ${FIRST_SOURCE_FRAME} last ${TRAJIN_STRIDE}
rms first ${RMSD_MASK}
average crdset Core13_297_100_500_Avg
run
rms ref Core13_297_100_500_Avg ${RMSD_MASK}
atomicfluct out ${target}/rmsf_core13_297_100_500ns_byres.agr ${RMSF_MASK} byres
run
quit
EOF
    "${CPPTRAJ_BIN}" -i "${target}/calculate_rmsf_100_500ns.in" > "${target}/calculate_rmsf_100_500ns.log" 2>&1
    rmsf_n=$(awk '!/^[@#]/ && NF >= 2 {n++} END {print n+0}' "${target}/rmsf_core13_297_100_500ns_byres.agr")
    [[ ${rmsf_n} -eq ${RMSF_RESIDUES} ]] || { echo "ERROR: expected ${RMSF_RESIDUES} RMSF residues, found ${rmsf_n}" >&2; return 1; }
    printf 'state\tvariant\treplica\ttopology\ttrajectory\tresidue_range\twindow_ns\tframe_interval_ps\tframes\trmsf_residues\tstatus\n%s\t%s\t%s\t%s\t%s\t13-297\t100-500\t400\t%s\t%s\tPASS\n' \
        "${state}" "${variant}" "${replica}" "${topology}" "${trajectory}" "${WINDOW_FRAMES}" "${RMSF_RESIDUES}" > "${target}/qc.tsv"
}

case "${RUN_SCOPE}" in
    test) CASES=("apo 01_WT cr1") ;;
    all) CASES=(); for state in apo holo; do for variant in "${VARIANTS[@]}"; do for replica in "${REPLICAS[@]}"; do CASES+=("${state} ${variant} ${replica}"); done; done; done ;;
    *) echo "Unknown RUN_SCOPE: ${RUN_SCOPE}" >&2; exit 2 ;;
esac
if [[ ${EXECUTE} == yes ]]; then
    command -v "${CPPTRAJ_BIN}" >/dev/null || { echo 'ERROR: cpptraj is unavailable.' >&2; exit 1; }
fi
printf 'Location: %s\nSimulation root: %s\nWindow: 100-500 ns\nScope: %s (%s cases)\nExecute: %s\n' "${DATA_LOCATION}" "${SIM_ROOT}" "${RUN_SCOPE}" "${#CASES[@]}" "${EXECUTE}"
[[ ${EXECUTE} == yes ]] && { mkdir -p "${RESULT_ROOT}/00_logs"; exec > >(tee -a "${RESULT_ROOT}/00_logs/core13_297_last400_${RUN_SCOPE}_$(date +%Y%m%d_%H%M%S).log") 2>&1; }
[[ ${MAX_WORKERS} =~ ^[1-9][0-9]*$ ]] || { echo "Invalid MAX_WORKERS: ${MAX_WORKERS}" >&2; exit 2; }
if [[ ${EXECUTE} == no || ${MAX_WORKERS} -eq 1 ]]; then
    for entry in "${CASES[@]}"; do read -r state variant replica <<< "${entry}"; run_case "${state}" "${variant}" "${replica}"; done
else
    active=0; failures=0
    for entry in "${CASES[@]}"; do
        read -r state variant replica <<< "${entry}"
        run_case "${state}" "${variant}" "${replica}" &
        active=$((active + 1))
        if (( active >= MAX_WORKERS )); then wait -n || failures=1; active=$((active - 1)); fi
    done
    while (( active > 0 )); do wait -n || failures=1; active=$((active - 1)); done
    (( failures == 0 )) || { echo 'ERROR: one or more RMSF cases failed.' >&2; exit 1; }
fi
[[ ${EXECUTE} == yes ]] || echo 'DRY RUN COMPLETE: set EXECUTE="yes" to calculate the planned case(s).'

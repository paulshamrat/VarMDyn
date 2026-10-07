#!/usr/bin/env bash
# Extract 100--500 ns displacement for all full-core CR1--CR6 trajectories.
# On Insurgent, first run with DRY_RUN=yes. Then set DRY_RUN=no.
set -Eeuo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../../../00_settings.sh"

###############################################################################
# SETTINGS — edit these lines only.
DRY_RUN="${DRY_RUN:-yes}"              # yes = show 96-case plan; no = calculate
MAX_PARALLEL="${MAX_PARALLEL:-4}"       # Insurgent: modest concurrent USB reads
CASE_FILTER="${CASE_FILTER:-all}"       # e.g. apo/01_WT/cr1, or all
FORCE="${FORCE:-no}"                    # no = retain a verified completed case
###############################################################################

VMD_STRIDE=4
WINDOW_FIRST_FRAME_ZERO=$((WINDOW_SOURCE_FIRST_FRAME - 1))
WINDOW_LAST_FRAME_ZERO=$((WINDOW_SOURCE_LAST_FRAME - 1))
EXPECTED_FRAMES=$(((WINDOW_LAST_FRAME_ZERO - WINDOW_FIRST_FRAME_ZERO) / VMD_STRIDE + 1))
RAW_ROOT="${RESULT_ROOT}/01_displacement_raw"; LOG_ROOT="${DYNAMICS_LOG_ROOT}"
TCL="${SCRIPT_DIR}/01_perres_displacement.tcl"
[[ -n "${MD_DATA_ROOT}" ]] || { echo "MD_DATA_ROOT is empty for ${DATA_LOCATION}." >&2; exit 2; }
command -v vmd >/dev/null || { echo "vmd is required but not found." >&2; exit 2; }
[[ -f "${TCL}" ]] || { echo "Missing Tcl script: ${TCL}" >&2; exit 2; }
[[ "${DRY_RUN}" == yes || "${DRY_RUN}" == no ]] || { echo "DRY_RUN must be yes or no." >&2; exit 2; }
[[ "${FORCE}" == yes || "${FORCE}" == no ]] || { echo "FORCE must be yes or no." >&2; exit 2; }
[[ "${MAX_PARALLEL}" =~ ^[1-9][0-9]*$ ]] || { echo "MAX_PARALLEL must be a positive integer." >&2; exit 2; }

mkdir -p "${LOG_ROOT}"; RUN_ID=$(date +%Y%m%d_%H%M%S); HOST_TAG=$(hostname -s)
RUN_LOG="${LOG_ROOT}/fullcore13_297_displacement_${HOST_TAG}_${RUN_ID}.log"
MANIFEST="${RAW_ROOT}/00_run_manifest.tsv"

run_case() {
    local state=$1 variant=$2 replica=$3 topology trajectory equilibrium_structure state_dir target qc file lines
    IFS=$'\t' read -r topology trajectory equilibrium_structure < <(source_paths "${state}" "${variant}" "${replica}")
    state_dir=$(printf '%s' "${state}" | sed 's/^apo$/01_apo/; s/^holo$/02_holo/')
    target="${RAW_ROOT}/${state_dir}/${variant}/${replica}"; qc="${target}/03_qc.tsv"
    if [[ "${FORCE}" == no && -s "${qc}" ]] && tail -n 1 "${qc}" | grep -q $'\tPASS$'; then echo "SKIP verified ${state}/${variant}/${replica}"; return 0; fi
    [[ -s "${topology}" ]] || { echo "Missing topology: ${topology}" >&2; return 1; }
    [[ -s "${trajectory}" ]] || { echo "Missing trajectory: ${trajectory}" >&2; return 1; }
    [[ -s "${equilibrium_structure}" ]] || { echo "Missing equilibrium structure: ${equilibrium_structure}" >&2; return 1; }
    mkdir -p "${target}"; rm -f "${target}/01_displacement_res13-56.tsv" "${target}/02_displacement_res151-191.tsv" "${qc}"
    echo "RUN ${state}/${variant}/${replica}"
    vmd -dispdev text -e "${TCL}" -args "${topology}" "${trajectory}" "${equilibrium_structure}" "${target}" 13 56 "${WINDOW_FIRST_FRAME_ZERO}" "${WINDOW_LAST_FRAME_ZERO}" "${VMD_STRIDE}" 01_displacement_res13-56.tsv
    vmd -dispdev text -e "${TCL}" -args "${topology}" "${trajectory}" "${equilibrium_structure}" "${target}" 151 191 "${WINDOW_FIRST_FRAME_ZERO}" "${WINDOW_LAST_FRAME_ZERO}" "${VMD_STRIDE}" 02_displacement_res151-191.tsv
    for file in "${target}/01_displacement_res13-56.tsv" "${target}/02_displacement_res151-191.tsv"; do
        lines=$(wc -l < "${file}"); [[ "${lines}" -eq $((EXPECTED_FRAMES + 1)) ]] || { echo "Unexpected row count in ${file}: ${lines}" >&2; return 1; }
    done
    printf 'state\tvariant\treplica\ttopology\ttrajectory\tequilibrium_structure\twindow_ns\tinput_frame_interval_ps\tread_stride\toutput_frame_interval_ps\tframes\tstatus\n%s\t%s\t%s\t%s\t%s\t%s\t%s-%s\t100\t%s\t%s\t%s\tPASS\n' \
        "${state}" "${variant}" "${replica}" "${topology}" "${trajectory}" "${equilibrium_structure}" "${WINDOW_START_NS}" "${WINDOW_END_NS}" "${VMD_STRIDE}" "$((FRAME_INTERVAL_PS * VMD_STRIDE))" "${EXPECTED_FRAMES}" > "${qc}"
    echo "OK ${state}/${variant}/${replica}"
}

cases=()
for state in "${STATES[@]}"; do for variant in "${VARIANTS[@]}"; do for replica in "${REPLICAS[@]}"; do
    case_name="${state}/${variant}/${replica}"; [[ "${CASE_FILTER}" == all || "${CASE_FILTER}" == "${case_name}" ]] && cases+=("${case_name}")
done; done; done
printf 'Run: %s\nData: %s\nScope: core %s-%s; all CR1--CR6\nWindow: %s--%s ns (source frames %s--%s; VMD stride %s; %s output frames)\nCases: %d\nLog: %s\n' \
    "${RUN_ID}" "${DATA_LOCATION}" "${KINASE_START_RESIDUE}" "${KINASE_END_RESIDUE}" "${WINDOW_START_NS}" "${WINDOW_END_NS}" "${WINDOW_FIRST_FRAME_ZERO}" "${WINDOW_LAST_FRAME_ZERO}" "${VMD_STRIDE}" "${EXPECTED_FRAMES}" "${#cases[@]}" "${RUN_LOG}" | tee -a "${RUN_LOG}"
printf '%s\n' "${cases[@]}" | tee -a "${RUN_LOG}"
[[ "${DRY_RUN}" == yes ]] && { echo "DRY RUN: no trajectories read and no displacement files written." | tee -a "${RUN_LOG}"; exit 0; }
mkdir -p "${RAW_ROOT}"
printf 'run_id\thost\tdata_location\tkinase_residue_range\treplica_set\twindow_ns\tsource_frame_range_zero_based\tvmd_stride\texpected_frames\tmax_parallel\texecution_log\n%s\t%s\t%s\t%s-%s\tcr1-cr6\t%s-%s\t%s-%s\t%s\t%s\t%s\t%s\n' \
    "${RUN_ID}" "${HOST_TAG}" "${DATA_LOCATION}" "${KINASE_START_RESIDUE}" "${KINASE_END_RESIDUE}" "${WINDOW_START_NS}" "${WINDOW_END_NS}" "${WINDOW_FIRST_FRAME_ZERO}" "${WINDOW_LAST_FRAME_ZERO}" "${VMD_STRIDE}" "${EXPECTED_FRAMES}" "${MAX_PARALLEL}" "${RUN_LOG}" > "${MANIFEST}"
declare -a pids=(); failures=0
reap_one() { local pid=${pids[0]}; wait "${pid}" || failures=$((failures + 1)); pids=("${pids[@]:1}"); }
for case_name in "${cases[@]}"; do
    IFS=/ read -r state variant replica <<< "${case_name}"
    (run_case "${state}" "${variant}" "${replica}") >> "${RUN_LOG}" 2>&1 &
    pids+=("$!")
    [[ ${#pids[@]} -ge ${MAX_PARALLEL} ]] && reap_one
done
while [[ ${#pids[@]} -gt 0 ]]; do reap_one; done
printf 'Completed with %d failed case(s).\n' "${failures}" | tee -a "${RUN_LOG}"; [[ ${failures} -eq 0 ]]

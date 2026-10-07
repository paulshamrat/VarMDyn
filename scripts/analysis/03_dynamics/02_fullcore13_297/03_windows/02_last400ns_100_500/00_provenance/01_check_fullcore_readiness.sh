#!/usr/bin/env bash
# Read-only audit for every full-core 100--500 ns state/variant/replica case.
set -Eeuo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../../../00_settings.sh"

[[ -n "${MD_DATA_ROOT}" ]] || { echo "MD_DATA_ROOT is empty for ${DATA_LOCATION}." >&2; exit 2; }
command -v cpptraj >/dev/null || { echo "cpptraj is required." >&2; exit 2; }
OUT_DIR="${RESULT_ROOT}/00_provenance"; OUT="${OUT_DIR}/01_fullcore_readiness.tsv"
mkdir -p "${OUT_DIR}"
printf 'state\tvariant\treplica\tsource_frames\twindow_frames_100_500ns\ttopology\ttrajectory\tequilibrium_structure\tstatus\n' > "${OUT}"
failures=0; cases=0
for state in "${STATES[@]}"; do for variant in "${VARIANTS[@]}"; do for replica in "${REPLICAS[@]}"; do
    IFS=$'\t' read -r topology trajectory equilibrium_structure < <(source_paths "${state}" "${variant}" "${replica}")
    status=READY; source_frames=NA; window_frames=NA
    [[ -f "${topology}" ]] || status=MISSING_TOPOLOGY
    [[ -f "${trajectory}" ]] || status=MISSING_TRAJECTORY
    [[ -f "${equilibrium_structure}" ]] || status=MISSING_EQUILIBRIUM_STRUCTURE
    if [[ "${status}" == READY ]]; then
        cpptraj_log=$(printf 'trajin %q\nrun\n' "${trajectory}" | cpptraj -p "${topology}" 2>&1) || status=CPPTRAJ_FAILED
        if [[ "${status}" == READY ]]; then
            source_frames=$(sed -n 's/.*Read \([0-9][0-9]*\) frames and processed.*/\1/p' <<< "${cpptraj_log}" | tail -n 1)
            [[ "${source_frames}" == "${SOURCE_FRAMES}" ]] || status="UNEXPECTED_SOURCE_FRAMES_${source_frames:-UNKNOWN}"
            window_frames=$((WINDOW_SOURCE_LAST_FRAME - WINDOW_SOURCE_FIRST_FRAME + 1))
            [[ ${window_frames} -eq ${WINDOW_FRAMES} ]] || status=INVALID_WINDOW_FRAME_COUNT
        fi
    fi
    [[ "${status}" == READY ]] || failures=$((failures + 1))
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "${state}" "${variant}" "${replica}" "${source_frames}" "${window_frames}" "${topology}" "${trajectory}" "${equilibrium_structure}" "${status}" >> "${OUT}"
    cases=$((cases + 1))
done; done; done
printf 'Readiness table: %s\nCases: %d; failed: %d\n' "${OUT}" "${cases}" "${failures}"
[[ ${failures} -eq 0 ]]

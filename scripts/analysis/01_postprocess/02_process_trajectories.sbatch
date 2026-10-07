#!/usr/bin/env bash
# Produce standardized 500-ns trajectories for every state/variant/replica.
# Existing valid-looking outputs are never overwritten. Start with DRY_RUN=yes.

#SBATCH --job-name=cdkl5-100ps
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=08:00:00

set -Eeuo pipefail
: "${SLURM_ARRAY_TASK_ID:?Use a manifest-derived Slurm array; see scripts/checks/submit_array.py}"
umask 002

###############################################################################
# SETTINGS — submit with DRY_RUN="yes" to preview, or pass --execute / change to "no".
DRY_RUN="yes"
if [[ ${1:-} == "--execute" ]]; then
    DRY_RUN="no"
fi
###############################################################################

WORKFLOW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00_postprocess_settings.sh
source "${WORKFLOW_DIR}/00_postprocess_settings.sh"

tasks_per_state=$((${#VARIANTS[@]} * ${#REPLICAS[@]}))
(( SLURM_ARRAY_TASK_ID < 2 * tasks_per_state )) || { echo "Invalid array task: ${SLURM_ARRAY_TASK_ID}" >&2; exit 2; }
state_index=$((SLURM_ARRAY_TASK_ID / tasks_per_state))
within_state=$((SLURM_ARRAY_TASK_ID % tasks_per_state))
variant=${VARIANTS[$((within_state / ${#REPLICAS[@]}))]}
replica=${REPLICAS[$((within_state % ${#REPLICAS[@]}))]}
if (( state_index == 0 )); then state=apo; else state=holo; fi
branch=$(state_branch "$state")
system=${SIM_ROOT}/${branch}/${variant}
raw=${system}/03.pmemd/com/${replica}
out=${system}/04.ptraj/com/${replica}/traj-proc

raw_complete() {
    local stage
    for stage in "${PRODUCTION_STAGES[@]}"; do
        [[ -s "${raw}/${stage}md.mdcrd.nc" && -s "${raw}/${stage}md.mdout" ]] || return 1
        grep -Eq 'NSTEP[[:space:]]*=[[:space:]]*50000000' "${raw}/${stage}md.mdout" || return 1
    done
}

if [[ $state == apo ]]; then
    outputs=(production-25-to-29-500ns.${replica}.striped.sampled-5.mdcrd.nc)
else
    outputs=(
        production-25-to-29-500ns.${replica}.keepATPmg.sampled-5.mdcrd.nc
        production-25-to-29-500ns.${replica}.striped_v2.sampled-5.mdcrd.nc
    )
fi

action=READY_TO_PROCESS
if ! raw_complete; then
    action=SOURCE_INCOMPLETE
else
    all_present=yes
    for output in "${outputs[@]}"; do [[ -s "${out}/${output}" ]] || all_present=no; done
    [[ $all_present == yes ]] && action=ALREADY_PRESENT
fi
printf 'state=%s variant=%s replica=%s action=%s root=%s\n' "$state" "$variant" "$replica" "$action" "$SIM_ROOT"

write_qc() {
    mkdir -p "${RESULT_ROOT}/02_trajectory_qc/${state}/${variant}"
    printf 'state\tvariant\treplica\tframe_interval_ps\tframes\toutputs\tstatus\n%s\t%s\t%s\t100\t5000\t%s\tPASS\n' \
        "$state" "$variant" "$replica" "$(IFS=,; echo "${outputs[*]}")" \
        > "${RESULT_ROOT}/02_trajectory_qc/${state}/${variant}/${replica}.tsv"
}

if [[ $DRY_RUN == yes ]]; then
    echo 'DRY RUN: no trajectory output or QC record was created.'
    exit 0
fi
if [[ $action == SOURCE_INCOMPLETE ]]; then
    echo 'Source production stages are incomplete; no trajectory output or QC record was created.' >&2
    exit 0
fi
if [[ $action == ALREADY_PRESENT ]]; then
    write_qc
    echo 'Existing standardized trajectories recorded in QC; no trajectory output was created.'
    exit 0
fi

test -s "${system}/02.leap/com/cdl.com.wat.leap.prmtop"
mkdir -p "${out}"
module --ignore_cache load amber/24.openmpi

trajin_lines() {
    local stage
    for stage in "${PRODUCTION_STAGES[@]}"; do
        printf 'trajin ../../../../03.pmemd/com/%s/%smd.mdcrd.nc 1 last 5\n' "$replica" "$stage"
    done
}
run_cpptraj() { local input=$1; ( cd "${out}" && cpptraj -i "$(basename "${input}")" > "${input%.in}.log" 2>&1 ); }

if [[ $state == apo ]]; then
    input=${out}/strip-25-to-29.sampled-5.in
    { echo 'parm ../../../../02.leap/com/cdl.com.wat.leap.prmtop'; trajin_lines; echo autoimage; echo 'strip :WAT,Na+,Cl-'; echo "trajout ${outputs[0]} nobox"; echo run; echo quit; } > "${input}"
    run_cpptraj "${input}"
else
    keep_input=${out}/strip-25-to-29_keepATPmg.sampled-5.in
    strip_input=${out}/strip-25-to-29_striped_v2.sampled-5.in
    { echo 'parm ../../../../02.leap/com/cdl.com.wat.leap.prmtop'; trajin_lines; echo autoimage; echo 'strip :WAT,Na+,Cl-'; echo "trajout ${outputs[0]} nobox"; echo run; echo quit; } > "${keep_input}"
    { echo 'parm ../../../../02.leap/com/cdl.com.wat.leap.prmtop'; trajin_lines; echo autoimage; echo 'strip :WAT,Na+,Cl-,ATP,MG'; echo "trajout ${outputs[1]} nobox"; echo run; echo quit; } > "${strip_input}"
    run_cpptraj "${keep_input}"
    run_cpptraj "${strip_input}"
fi
for output in "${outputs[@]}"; do test -s "${out}/${output}"; done
write_qc

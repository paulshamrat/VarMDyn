#!/usr/bin/env bash
# Create missing equilibrium-reference topologies for every state/variant.
# Start with DRY_RUN=yes. Existing reference files are never overwritten.

#SBATCH --job-name=cdkl5-equib
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00

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

if (( SLURM_ARRAY_TASK_ID < ${#VARIANTS[@]} )); then
    state=apo
    variant=${VARIANTS[$SLURM_ARRAY_TASK_ID]}
else
    state=holo
    variant=${VARIANTS[$((SLURM_ARRAY_TASK_ID - ${#VARIANTS[@]}))]}
fi
branch=$(state_branch "$state")
system=${SIM_ROOT}/${branch}/${variant}
leap=${system}/02.leap
restart=${system}/03.pmemd/com/cr1/24md.restrt
wat_topology=${leap}/com/cdl.com.wat.leap.prmtop

if [[ $state == apo ]]; then
    outputs=(com/cdl.com.gas.equib.prmtop com/cdl.com.gas.equib.pdb)
else
    outputs=(
        com/cdl.com.keepATPmg.equib.prmtop com/cdl.com.keepATPmg.equib.pdb
        com/cdl.com.striped_v2.equib.prmtop com/cdl.com.striped_v2.equib.pdb
    )
fi
all_present=yes
for output in "${outputs[@]}"; do [[ -s "${leap}/${output}" ]] || all_present=no; done
if [[ $all_present == yes ]]; then action=ALREADY_PRESENT; else action=READY_TO_BUILD; fi
printf 'state=%s variant=%s action=%s root=%s\n' "$state" "$variant" "$action" "$SIM_ROOT"
write_qc() {
    mkdir -p "${RESULT_ROOT}/01_equib_qc/${state}"
    printf 'state\tvariant\trestart\toutputs\tstatus\n%s\t%s\t%s\t%s\tPASS\n' \
        "$state" "$variant" "$restart" "$(IFS=,; echo "${outputs[*]}")" \
        > "${RESULT_ROOT}/01_equib_qc/${state}/${variant}.tsv"
}

if [[ $DRY_RUN == yes ]]; then
    [[ $DRY_RUN == yes ]] && echo 'DRY RUN: no topology output was created.'
    exit 0
fi

if [[ $action == ALREADY_PRESENT ]]; then
    write_qc
    echo 'Existing topology references recorded in QC; no topology output was created.'
    exit 0
fi

test -s "${restart}"
test -s "${wat_topology}"
mkdir -p "${RESULT_ROOT}/01_equib_qc/${state}"
module --ignore_cache load amber/24.openmpi

if [[ $state == apo ]]; then
    input=${leap}/tleap.com.equib.in
    cat > "${input}" <<EOF
# Final CR1 equilibration restart; retain protein only.
parm com/cdl.com.wat.leap.prmtop
trajin ../03.pmemd/com/cr1/24md.restrt
strip :WAT,Na+,Cl- parmout com/cdl.com.gas.equib.prmtop
trajout com/cdl.com.gas.equib.pdb
run
quit
EOF
    ( cd "${leap}" && cpptraj -i "$(basename "${input}")" )
else
    keep_input=${leap}/tleap.com.equib.keepATPmg.in
    strip_input=${leap}/tleap.com.equib.striped_v2.in
    cat > "${keep_input}" <<EOF
# Final CR1 equilibration restart; retain protein, ATP, and Mg.
parm com/cdl.com.wat.leap.prmtop
trajin ../03.pmemd/com/cr1/24md.restrt
strip :WAT,Na+,Cl- parmout com/cdl.com.keepATPmg.equib.prmtop
trajout com/cdl.com.keepATPmg.equib.pdb
run
quit
EOF
    cat > "${strip_input}" <<EOF
# Final CR1 equilibration restart; retain protein only.
parm com/cdl.com.wat.leap.prmtop
trajin ../03.pmemd/com/cr1/24md.restrt
strip :WAT,Na+,Cl-,ATP,MG parmout com/cdl.com.striped_v2.equib.prmtop
trajout com/cdl.com.striped_v2.equib.pdb
run
quit
EOF
    ( cd "${leap}" && cpptraj -i "$(basename "${keep_input}")" && cpptraj -i "$(basename "${strip_input}")" )
fi
for output in "${outputs[@]}"; do test -s "${leap}/${output}"; done
write_qc

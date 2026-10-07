#!/usr/bin/env bash
# Read-only topology/trajectory audit for every standardized CR1--CR6 output.
# Start with DRY_RUN=yes to list the audit plan without writing QC TSV files.

#SBATCH --job-name=cdkl5-postprocess-audit
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00

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
traj_dir=${system}/04.ptraj/com/${replica}/traj-proc

if [[ $state == apo ]]; then
    checks=("striped|${system}/02.leap/com/cdl.com.gas.equib.prmtop|${traj_dir}/production-25-to-29-500ns.${replica}.striped.sampled-5.mdcrd.nc")
else
    checks=(
        "keepATPmg|${system}/02.leap/com/cdl.com.keepATPmg.equib.prmtop|${traj_dir}/production-25-to-29-500ns.${replica}.keepATPmg.sampled-5.mdcrd.nc"
        "striped_v2|${system}/02.leap/com/cdl.com.striped_v2.equib.prmtop|${traj_dir}/production-25-to-29-500ns.${replica}.striped_v2.sampled-5.mdcrd.nc"
    )
fi

available=0
for check in "${checks[@]}"; do
    IFS='|' read -r _ topology trajectory <<< "${check}"
    [[ -s $topology && -s $trajectory ]] && ((available += 1))
done
printf 'state=%s variant=%s replica=%s representations=%s/%s root=%s\n' "$state" "$variant" "$replica" "$available" "${#checks[@]}" "$SIM_ROOT"
if [[ $DRY_RUN == yes ]]; then
    echo 'DRY RUN: no audit QC file was created.'
    exit 0
fi

qc_dir=${RESULT_ROOT}/03_audit_qc/${state}/${variant}
mkdir -p "${qc_dir}"
printf 'state\tvariant\treplica\trepresentation\ttopology\ttrajectory\tframes\tstatus\n' > "${qc_dir}/${replica}.tsv"
if (( available != ${#checks[@]} )); then
    for check in "${checks[@]}"; do
        IFS='|' read -r representation topology trajectory <<< "${check}"
        status=NOT_PROCESSED
        [[ -s $topology && -s $trajectory ]] && status=NOT_AUDITED
        printf '%s\t%s\t%s\t%s\t%s\t%s\t—\t%s\n' "$state" "$variant" "$replica" "$representation" "$topology" "$trajectory" "$status" >> "${qc_dir}/${replica}.tsv"
    done
    exit 0
fi

module --ignore_cache load amber/24.openmpi
for check in "${checks[@]}"; do
    IFS='|' read -r representation topology trajectory <<< "${check}"
    log=$(mktemp)
    printf 'parm %s\ntrajin %s\nrun\nquit\n' "$topology" "$trajectory" | cpptraj > "${log}" 2>&1
    grep -q 'Read 5000 frames and processed 5000 frames' "${log}"
    rm -f "${log}"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t5000\tPASS\n' "$state" "$variant" "$replica" "$representation" "$topology" "$trajectory" >> "${qc_dir}/${replica}.tsv"
done

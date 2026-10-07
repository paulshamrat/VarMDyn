#!/usr/bin/env bash
# Calculate corrected replica RMSD, RMSF, and protein radius of gyration.
#
# One array task processes one state / variant / replica. It reads the validated
# protein-only trajectories sampled every 100 ps, then keeps every fourth frame
# (400 ps) to match the sampling of the manuscript-facing legacy analysis.
# This script never changes simulation trajectories or topologies.
#
# Submit on Palmetto after reviewing the default dry run:
#   sbatch 01_run_metrics.sbatch
#
# Results:
#   .../results/02_metrics/01_metrics/<state>/<variant>/<replica>/

#SBATCH --job-name=cdkl5-corrected-metrics
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00

set -Eeuo pipefail
: "${SLURM_ARRAY_TASK_ID:?Use a manifest-derived Slurm array; see scripts/checks/submit_array.py}"
umask 002

###############################################################################
# SETTINGS — default is a safe dry run. Submit with --execute to calculate a
# missing metric set. Existing PASS metrics are never overwritten.
DRY_RUN=yes
[[ ${1:-} == --execute ]] && DRY_RUN=no
###############################################################################

WORKFLOW_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${WORKFLOW_ROOT}/00_shared/00_structural_metrics_settings.sh"

tasks_per_state=$((${#VARIANTS[@]} * ${#REPLICAS[@]}))
(( SLURM_ARRAY_TASK_ID < 2 * tasks_per_state )) || { echo "Invalid array task: ${SLURM_ARRAY_TASK_ID}" >&2; exit 2; }
state_index=$((SLURM_ARRAY_TASK_ID / tasks_per_state))
remainder=$((SLURM_ARRAY_TASK_ID % tasks_per_state))
variant=${VARIANTS[$((remainder / ${#REPLICAS[@]}))]}
replica=${REPLICAS[$((remainder % ${#REPLICAS[@]}))]}

if [[ ${state_index} -eq 0 ]]; then
    state=apo
    branch=$(state_branch apo)
    representation=striped
    topology_name=cdl.com.gas.equib.prmtop
else
    state=holo
    branch=$(state_branch holo)
    representation=striped_v2
    topology_name=cdl.com.striped_v2.equib.prmtop
fi

system=${SIM_ROOT}/${branch}/${variant}
topology=${system}/02.leap/com/${topology_name}
trajectory=${system}/04.ptraj/com/${replica}/traj-proc/production-25-to-29-500ns.${replica}.${representation}.sampled-5.mdcrd.nc
target=${RESULT_ROOT}/01_metrics/${state}/${variant}/${replica}

action=READY_TO_CALCULATE
if [[ -s ${target}/qc.tsv && $(tail -n 1 "${target}/qc.tsv" | awk -F '\t' '{print $NF}') == PASS ]]; then
    action=ALREADY_PRESENT
elif [[ ! -s ${topology} || ! -s ${trajectory} ]]; then
    action=SOURCE_INCOMPLETE
fi
printf 'state=%s variant=%s replica=%s action=%s root=%s\n' "$state" "$variant" "$replica" "$action" "$SIM_ROOT"
if [[ $DRY_RUN == yes ]]; then
    echo 'DRY RUN: no metric output was created.'
    exit 0
fi
if [[ $action == ALREADY_PRESENT ]]; then
    echo 'Existing PASS metric output retained.'
    exit 0
fi
if [[ $action == SOURCE_INCOMPLETE ]]; then
    echo 'Required topology or standardized trajectory is missing.' >&2
    exit 1
fi

mkdir -p "${target}" "${RESULT_ROOT}/00_logs"

[[ -s ${topology} ]] || { echo "Missing topology: ${topology}" >&2; exit 1; }
[[ -s ${trajectory} ]] || { echo "Missing trajectory: ${trajectory}" >&2; exit 1; }

module --ignore_cache load amber/24.openmpi

cat > "${target}/calculate_metrics.in" <<EOF
parm ${topology}
trajin ${trajectory} 1 last 4

# Backbone RMSD after fitting residues 1--303 to the first frame.
rms first :1-303@CA,C,N out ${target}/rmsd_backbone.dat
run

# RMSF after fitting to the first frame, then to the average structure.
rms first
average crdset MyAvg
run
rms ref MyAvg
atomicfluct out ${target}/rmsf_backbone_byres.agr @C,CA,N byres
run

# Protein heavy-atom radius of gyration.
radgyr Rgyr :1-303&!@H= out ${target}/rgyr_protein_heavy.dat
run
quit
EOF

cpptraj -i "${target}/calculate_metrics.in" > "${target}/calculate_metrics.log" 2>&1

rmsd_n=$(awk '!/^#/ && NF >= 2 {n++} END {print n+0}' "${target}/rmsd_backbone.dat")
rmsf_n=$(awk '!/^[@#]/ && NF >= 2 {n++} END {print n+0}' "${target}/rmsf_backbone_byres.agr")
rg_n=$(awk '!/^#/ && NF >= 2 {n++} END {print n+0}' "${target}/rgyr_protein_heavy.dat")
[[ ${rmsd_n} -eq 1250 && ${rmsf_n} -eq 303 && ${rg_n} -eq 1250 ]] || {
    echo "Unexpected output lengths: RMSD=${rmsd_n}, RMSF=${rmsf_n}, Rg=${rg_n}" >&2
    exit 1
}
grep -q 'Read 1250 frames and processed 1250 frames.' "${target}/calculate_metrics.log"

printf 'state\tvariant\treplica\ttopology\ttrajectory\tframe_interval_ps\tframes\trmsf_residues\tstatus\n%s\t%s\t%s\t%s\t%s\t400\t1250\t303\tPASS\n' \
    "${state}" "${variant}" "${replica}" "${topology}" "${trajectory}" \
    > "${target}/qc.tsv"
echo "[OK] ${state}/${variant}/${replica}: 1,250 frames; 303 residues"

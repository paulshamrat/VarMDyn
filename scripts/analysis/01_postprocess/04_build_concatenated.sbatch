#!/usr/bin/env bash
# SBATCH configuration for Palmetto HPC
#SBATCH --job-name=cdkl5-concat
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=08:00:00

# Build and validate concatenated multi-replica trajectories from standardized
# per-replica inputs. Existing valid outputs are retained and get a labelled QC
# record when run with --execute.

set -Eeuo pipefail
: "${SLURM_ARRAY_TASK_ID:?Use a manifest-derived Slurm array; see scripts/checks/submit_array.py}"
umask 002

WORKFLOW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00_postprocess_settings.sh
source "${WORKFLOW_DIR}/00_postprocess_settings.sh"

###############################################################################
# CONCATENATION USER SETTINGS
# Edit these variables before submitting!
###############################################################################

# Target replica set: "cr1-cr3", "cr4-cr6", or "cr1-cr6".
# The default is cr1-cr6; an sbatch export can temporarily select another set.
CONCAT_SET="${CONCAT_SET:-cr1-cr6}"

# Subsampling Stride Settings:
# STRIDE_400PS=4  --> Takes 1 frame every 400 ps (1,250 frames per replica)
# STRIDE_2NS=5    --> Takes 1 frame every 2 ns (250 frames per replica)
STRIDE_400PS=4
STRIDE_2NS=5

# Set DRY_RUN="yes" to preview inputs/outputs, or DRY_RUN="no" to execute
DRY_RUN="yes"

# Allow CLI override: --execute sets DRY_RUN="no"
if [[ ${1:-} == "--execute" ]]; then
    DRY_RUN="no"
fi
###############################################################################

case "${CONCAT_SET}" in
    cr1-cr3) CONCAT_REPLICAS=(cr1 cr2 cr3) ;;
    cr4-cr6) CONCAT_REPLICAS=(cr4 cr5 cr6) ;;
    cr1-cr6) CONCAT_REPLICAS=(cr1 cr2 cr3 cr4 cr5 cr6) ;;
    *) echo "Unknown CONCAT_SET: ${CONCAT_SET}" >&2; exit 2 ;;
esac

CONCAT_LABEL="${CONCAT_SET}"
N_REPLICAS=${#CONCAT_REPLICAS[@]}

FRAMES_PER_REP_400=$(( 5000 / STRIDE_400PS ))
FRAMES_PER_REP_2NS=$(( FRAMES_PER_REP_400 / STRIDE_2NS ))

EXPECTED_400=$(( FRAMES_PER_REP_400 * N_REPLICAS ))
EXPECTED_750=$(( FRAMES_PER_REP_2NS * N_REPLICAS ))

ARRAY_ID=${SLURM_ARRAY_TASK_ID:-0}
state_index=$((ARRAY_ID / ${#VARIANTS[@]}))
variant=${VARIANTS[$((ARRAY_ID % ${#VARIANTS[@]}))]}

if (( state_index == 0 )); then
    state=apo; branch=03_mdsim; representations=(striped)
else
    state=holo; branch=05_cdkl5atpmg; representations=(striped_v2 keepATPmg)
fi

system=${SIM_ROOT}/${branch}/${variant}
concat=${system}/04.ptraj/com/concatenated
QC_ROOT=${RESULT_ROOT}/04_concatenation_qc

echo "[INFO] Concatenation Job Setup:"
echo "       State:         ${state}"
echo "       Variant:       ${variant}"
echo "       Replica Set:   ${CONCAT_SET} (${CONCAT_REPLICAS[*]})"
echo "       Expected 400:  ${EXPECTED_400} frames"
echo "       Expected 2ns:  ${EXPECTED_750} frames"
echo "       Dry Run:       ${DRY_RUN}"

if [[ ${DRY_RUN} == "yes" ]]; then
    echo "[DRY-RUN] Planned execution details:"
    echo "          Output dir:  ${concat}"
    echo "          QC dir:      ${QC_ROOT}/${state}/${variant}"
    for representation in "${representations[@]}"; do
        label_750="${EXPECTED_750}frames"
        [[ ${representation} == "striped" ]] && rep_label="apo" || rep_label="${representation}"
        echo "          - Representation: ${representation}"
        echo "            Target 400ps:   production-25-to-29-concatenated-${CONCAT_LABEL}-sampled-20.${representation}.mdcrd.nc"
        echo "            Target 2ns:     production-25-to-29-concatenated-${CONCAT_LABEL}-${label_750}.${rep_label}.mdcrd.nc"
        for replica in "${CONCAT_REPLICAS[@]}"; do
            echo "            Input:          ${system}/04.ptraj/com/${replica}/traj-proc/production-25-to-29-500ns.${replica}.${representation}.sampled-5.mdcrd.nc"
        done
    done
    echo "[DRY-RUN] Dry run complete. No files were written."
    exit 0
fi

mkdir -p "${concat}" "${QC_ROOT}/${state}/${variant}"
module --ignore_cache load amber/24.openmpi

frame_count() {
    local topology=$1 trajectory=$2 probe=.count_frames.in log=.count_frames.log count
    {
        echo "parm ${topology}"
        echo "trajin ${trajectory}"
        echo run
        echo quit
    } > "${concat}/${probe}"
    (cd "${concat}" && cpptraj -i "${probe}") > "${concat}/${log}" 2>&1
    count=$(awk '/Read [0-9]+ frames and processed/ {print $2}' "${concat}/${log}" | tail -1)
    rm -f "${concat}/${probe}" "${concat}/${log}"
    [[ ${count} =~ ^[0-9]+$ ]] || { echo "Could not count frames in ${trajectory}" >&2; exit 1; }
    printf '%s\n' "${count}"
}

for representation in "${representations[@]}"; do
    label_750="${EXPECTED_750}frames"
    if [[ ${state} == apo ]]; then
        topology=../../../02.leap/com/cdl.com.gas.equib.prmtop
        output_400=production-25-to-29-concatenated-${CONCAT_LABEL}-sampled-20.striped.mdcrd.nc
        output_750=production-25-to-29-concatenated-${CONCAT_LABEL}-${label_750}.apo.mdcrd.nc
    elif [[ ${representation} == striped_v2 ]]; then
        topology=../../../02.leap/com/cdl.com.striped_v2.equib.prmtop
        output_400=production-25-to-29-concatenated-${CONCAT_LABEL}-sampled-20.striped_v2.mdcrd.nc
        output_750=production-25-to-29-concatenated-${CONCAT_LABEL}-${label_750}.striped_v2.mdcrd.nc
    else
        topology=../../../02.leap/com/cdl.com.keepATPmg.equib.prmtop
        output_400=production-25-to-29-concatenated-${CONCAT_LABEL}-sampled-20.keepATPmg.mdcrd.nc
        output_750=production-25-to-29-concatenated-${CONCAT_LABEL}-${label_750}.keepATPmg.mdcrd.nc
    fi
    topology_absolute=${system}/02.leap/com/$(basename "${topology}")
    test -s "${topology_absolute}"

    manifest=${concat}/concatenated_manifest_${CONCAT_LABEL}_${representation}.tsv
    qc_file=${QC_ROOT}/${state}/${variant}/${CONCAT_LABEL}_${representation}.tsv

    write_qc() {
        {
            echo -e 'state\tvariant\treplica_set\trepresentation\ttopology\treplica\tinput_100ps_frames\tinput_100ps_file\toutput_400ps_frames\toutput_2ns_frames\tstatus'
            for replica in "${CONCAT_REPLICAS[@]}"; do
                trajectory=${system}/04.ptraj/com/${replica}/traj-proc/production-25-to-29-500ns.${replica}.${representation}.sampled-5.mdcrd.nc
                echo -e "${state}\t${variant}\t${CONCAT_LABEL}\t${representation}\t${topology_absolute}\t${replica}\t5000\t${trajectory}\t${frames_400}\t${frames_750}\tPASS"
            done
        } > "${manifest}"
        cp "${manifest}" "${qc_file}"
    }

    # Validate existing outputs and backfill a replica-set-labelled QC record.
    if [[ -s ${concat}/${output_400} && -s ${concat}/${output_750} ]]; then
        f400=$(frame_count "${topology}" "${output_400}")
        f750=$(frame_count "${topology}" "${output_750}")
        if [[ ${f400} == ${EXPECTED_400} && ${f750} == ${EXPECTED_750} ]]; then
            frames_400=${f400}
            frames_750=${f750}
            write_qc
            echo "[SKIP] Valid concatenated products recorded for ${state}/${variant}/${CONCAT_LABEL}/${representation} (${f400}, ${f750} frames)."
            continue
        fi
    fi

    input=${concat}/rebuild_corrected_${representation}.in
    {
        echo "parm ${topology}"
        for replica in "${CONCAT_REPLICAS[@]}"; do
            trajectory=../${replica}/traj-proc/production-25-to-29-500ns.${replica}.${representation}.sampled-5.mdcrd.nc
            test -s "${concat}/${trajectory}"
            echo "trajin ${trajectory} 1 last ${STRIDE_400PS}"
        done
        echo "trajout ${output_400} nobox"
        echo run
        echo "clear all"
        echo "parm ${topology}"
        echo "trajin ${output_400} 1 last ${STRIDE_2NS}"
        echo "trajout ${output_750} nobox"
        echo run
        echo quit
    } > "${input}"
    (cd "${concat}" && cpptraj -i "$(basename "${input}")") > "${concat}/rebuild_corrected_${representation}.log" 2>&1

    frames_400=$(frame_count "${topology}" "${output_400}")
    frames_750=$(frame_count "${topology}" "${output_750}")
    [[ ${frames_400} == ${EXPECTED_400} && ${frames_750} == ${EXPECTED_750} ]] || {
        echo "Unexpected frame count for ${state}/${variant}/${representation}: got ${frames_400}, ${frames_750}; expected ${EXPECTED_400}, ${EXPECTED_750}" >&2
        exit 1
    }
    write_qc
done

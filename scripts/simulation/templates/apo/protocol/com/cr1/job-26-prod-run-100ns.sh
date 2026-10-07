#!/bin/bash
#SBATCH --job-name 26cr1
#SBATCH --nodes 1
#SBATCH --tasks-per-node 1
#SBATCH --cpus-per-task 2
#SBATCH --gpus a100
#SBATCH --mem 16gb
#SBATCH --time 48:00:00

set -euo pipefail
SCRIPT_DIR="$(pwd)"
cd "${SCRIPT_DIR}"
BASE="$(cd ../../.. && pwd)"
export OMPI_MCA_btl_vader_single_copy_mechanism=none
export OMPI_MCA_smsc=^knem

module --ignore_cache load amber/24.gpu_mpi

export PMEMD=`which pmemd.cuda_SPFP`

CMD="$PMEMD "

PDB="cdl"
STATE="com"
RUNNO="cr1"

PROTOCOL="${BASE}/protocol/${STATE}/${RUNNO}"
TRAJDIR="${BASE}/03.pmemd/${STATE}/${RUNNO}"
LEAPDIR="${BASE}/02.leap/${STATE}"
mkdir -p "${TRAJDIR}"
cd "${TRAJDIR}"


echo "Job-26 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/26md.in \
-o      ${TRAJDIR}/26md.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/25md.restrt \
-ref    ${TRAJDIR}/14mi.restrt \
-x      ${TRAJDIR}/26md.mdcrd.nc \
-inf    ${TRAJDIR}/26md.info \
-r      ${TRAJDIR}/26md.restrt

echo "All job done on: `date`"



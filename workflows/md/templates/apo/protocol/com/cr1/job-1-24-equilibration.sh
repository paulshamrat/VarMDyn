#!/bin/bash
#SBATCH --job-name eq1-24
#SBATCH --nodes 1
#SBATCH --tasks-per-node 32
#SBATCH --cpus-per-task 1
#SBATCH --mem 64gb
#SBATCH --time 48:00:00

set -euo pipefail
SCRIPT_DIR="$(pwd)"
cd "${SCRIPT_DIR}"
BASE="$(cd ../../.. && pwd)"
export OMPI_MCA_btl_vader_single_copy_mechanism=none
export OMPI_MCA_smsc=^knem

module --ignore_cache load amber/24.openmpi

export PMEMD=`which pmemd.MPI`
NTASKS="${SLURM_NTASKS:-32}"

CMD="mpirun -np ${NTASKS} $PMEMD "


PDB="cdl"
STATE="com"
RUNNO="cr1"

PROTOCOL="${BASE}/protocol/${STATE}/${RUNNO}"
TRAJDIR="${BASE}/03.pmemd/${STATE}/${RUNNO}"
LEAPDIR="${BASE}/02.leap/${STATE}"
mkdir -p "${TRAJDIR}"
cd "${TRAJDIR}"


echo "Job-01 minimization of non-crystal water started on: `date`"
echo $CMD
$CMD -O -i  ${PROTOCOL}/01mi.in \
-o      ${TRAJDIR}/01mi.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.inpcrd \
-ref    ${LEAPDIR}/${PDB}.${STATE}.wat.leap.inpcrd \
-x      ${TRAJDIR}/01mi.mdcrd.nc \
-inf    ${TRAJDIR}/01mi.info \
-r      ${TRAJDIR}/01mi.restrt 


echo "Job-02 minimization of all solvent water started on: `date`"
$CMD -O -i  ${PROTOCOL}/02mi.in \
-o      ${TRAJDIR}/02mi.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/01mi.restrt \
-ref    ${TRAJDIR}/01mi.restrt \
-x      ${TRAJDIR}/02mi.mdcrd.nc \
-inf    ${TRAJDIR}/02mi.info \
-r      ${TRAJDIR}/02mi.restrt 

echo "Job-03 minimization of of solute and solvent started on: `date`"
$CMD -O -i  ${PROTOCOL}/03mi.in \
-o      ${TRAJDIR}/03mi.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/02mi.restrt \
-ref    ${TRAJDIR}/02mi.restrt \
-x      ${TRAJDIR}/03mi.mdcrd.nc \
-inf    ${TRAJDIR}/03mi.info \
-r      ${TRAJDIR}/03mi.restrt 


echo "Heating of system has started on `date` heating from 0K to 300K is to be done in 6-steps 50K in incerements"
echo "Job-04 started on: `date`"
$CMD -O -i  ${PROTOCOL}/04mh.in \
-o      ${TRAJDIR}/04mh.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/03mi.restrt \
-ref    ${TRAJDIR}/03mi.restrt \
-x      ${TRAJDIR}/04mh.mdcrd.nc \
-inf    ${TRAJDIR}/04mh.info \
-r      ${TRAJDIR}/04mh.restrt 

echo "Job-05 started on: `date`"
$CMD -O -i  ${PROTOCOL}/05mh.in \
-o      ${TRAJDIR}/05mh.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/04mh.restrt \
-ref    ${TRAJDIR}/04mh.restrt \
-x      ${TRAJDIR}/05mh.mdcrd.nc \
-inf    ${TRAJDIR}/05mh.info \
-r      ${TRAJDIR}/05mh.restrt 

echo "Job-06 started on: `date`"
$CMD -O -i  ${PROTOCOL}/06mh.in \
-o      ${TRAJDIR}/06mh.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/05mh.restrt \
-ref    ${TRAJDIR}/05mh.restrt \
-x      ${TRAJDIR}/06mh.mdcrd.nc \
-inf    ${TRAJDIR}/06mh.info \
-r      ${TRAJDIR}/06mh.restrt 


echo "Job-07 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/07mh.in \
-o      ${TRAJDIR}/07mh.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/06mh.restrt \
-ref    ${TRAJDIR}/06mh.restrt \
-x      ${TRAJDIR}/07mh.mdcrd.nc \
-inf    ${TRAJDIR}/07mh.info \
-r      ${TRAJDIR}/07mh.restrt 


echo "Job-08 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/08mh.in \
-o      ${TRAJDIR}/08mh.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/07mh.restrt \
-ref    ${TRAJDIR}/07mh.restrt \
-x      ${TRAJDIR}/08mh.mdcrd.nc \
-inf    ${TRAJDIR}/08mh.info \
-r      ${TRAJDIR}/08mh.restrt 

echo "Job-09 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/09mh.in \
-o      ${TRAJDIR}/09mh.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/08mh.restrt \
-ref    ${TRAJDIR}/08mh.restrt \
-x      ${TRAJDIR}/09mh.mdcrd.nc \
-inf    ${TRAJDIR}/09mh.info \
-r      ${TRAJDIR}/09mh.restrt 

echo "Heating of system has finished on `date` heating from 0K to 300K is done in 6-steps 50K in incerements"
echo "Second phase of system minimization has started on `date` this minimization is done in 5-steps"
echo "restraints on non-H atoms of solute is decreased in each step it is kept restraint_wt =25, 10, 5, 2, 1"
echo "No-SHAKE in (N,V,E)"
echo "Job-10 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/10mi.in \
-o      ${TRAJDIR}/10mi.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/09mh.restrt \
-ref    ${TRAJDIR}/09mh.restrt \
-x      ${TRAJDIR}/10mi.mdcrd.nc \
-inf    ${TRAJDIR}/10mi.info \
-r      ${TRAJDIR}/10mi.restrt 

echo "Job-11 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/11mi.in \
-o      ${TRAJDIR}/11mi.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/10mi.restrt \
-ref    ${TRAJDIR}/10mi.restrt \
-x      ${TRAJDIR}/11mi.mdcrd.nc \
-inf    ${TRAJDIR}/11mi.info \
-r      ${TRAJDIR}/11mi.restrt 

echo "Job-12 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/12mi.in \
-o      ${TRAJDIR}/12mi.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/11mi.restrt \
-ref    ${TRAJDIR}/11mi.restrt \
-x      ${TRAJDIR}/12mi.mdcrd.nc \
-inf    ${TRAJDIR}/12mi.info \
-r      ${TRAJDIR}/12mi.restrt 

echo "Job-13 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/13mi.in \
-o      ${TRAJDIR}/13mi.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/12mi.restrt \
-ref    ${TRAJDIR}/12mi.restrt \
-x      ${TRAJDIR}/13mi.mdcrd.nc \
-inf    ${TRAJDIR}/13mi.info \
-r      ${TRAJDIR}/13mi.restrt 

echo "Job-14 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/14mi.in \
-o      ${TRAJDIR}/14mi.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/13mi.restrt \
-ref    ${TRAJDIR}/13mi.restrt \
-x      ${TRAJDIR}/14mi.mdcrd.nc \
-inf    ${TRAJDIR}/14mi.info \
-r      ${TRAJDIR}/14mi.restrt 

echo "Job-15 NVT started on: `date`"
${CMD} -O -i  ${PROTOCOL}/15md.in \
-o      ${TRAJDIR}/15md.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/14mi.restrt \
-ref    ${TRAJDIR}/14mi.restrt \
-x      ${TRAJDIR}/15md.mdcrd.nc \
-inf    ${TRAJDIR}/15md.info \
-r      ${TRAJDIR}/15md.restrt 

echo "Job-16 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/16md.in \
-o      ${TRAJDIR}/16md.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/15md.restrt \
-ref    ${TRAJDIR}/14mi.restrt \
-x      ${TRAJDIR}/16md.mdcrd.nc \
-inf    ${TRAJDIR}/16md.info \
-r      ${TRAJDIR}/16md.restrt 

echo "Job-17 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/17md.in \
-o      ${TRAJDIR}/17md.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/16md.restrt \
-ref    ${TRAJDIR}/14mi.restrt \
-x      ${TRAJDIR}/17md.mdcrd.nc \
-inf    ${TRAJDIR}/17md.info \
-r      ${TRAJDIR}/17md.restrt 

echo "Job-18 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/18md.in \
-o      ${TRAJDIR}/18md.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/17md.restrt \
-ref    ${TRAJDIR}/14mi.restrt \
-x      ${TRAJDIR}/18md.mdcrd.nc \
-inf    ${TRAJDIR}/18md.info \
-r      ${TRAJDIR}/18md.restrt 

echo "Job-19 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/19md.in \
-o      ${TRAJDIR}/19md.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/18md.restrt \
-ref    ${TRAJDIR}/14mi.restrt \
-x      ${TRAJDIR}/19md.mdcrd.nc \
-inf    ${TRAJDIR}/19md.info \
-r      ${TRAJDIR}/19md.restrt

echo "Job-20 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/20md.in \
-o      ${TRAJDIR}/20md.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/19md.restrt \
-ref    ${TRAJDIR}/14mi.restrt \
-x      ${TRAJDIR}/20md.mdcrd.nc \
-inf    ${TRAJDIR}/20md.info \
-r      ${TRAJDIR}/20md.restrt 

echo "Job-21 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/21md.in \
-o      ${TRAJDIR}/21md.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/20md.restrt \
-ref    ${TRAJDIR}/14mi.restrt \
-x      ${TRAJDIR}/21md.mdcrd.nc \
-inf    ${TRAJDIR}/21md.info \
-r      ${TRAJDIR}/21md.restrt 

echo "Job-22 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/22md.in \
-o      ${TRAJDIR}/22md.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/21md.restrt \
-ref    ${TRAJDIR}/14mi.restrt \
-x      ${TRAJDIR}/22md.mdcrd.nc \
-inf    ${TRAJDIR}/22md.info \
-r      ${TRAJDIR}/22md.restrt 


echo "Job-23 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/23md.in \
-o      ${TRAJDIR}/23md.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/22md.restrt \
-ref    ${TRAJDIR}/14mi.restrt \
-x      ${TRAJDIR}/23md.mdcrd.nc \
-inf    ${TRAJDIR}/23md.info \
-r      ${TRAJDIR}/23md.restrt

echo "Job-24 started on: `date`"
${CMD} -O -i  ${PROTOCOL}/24md.in \
-o      ${TRAJDIR}/24md.mdout \
-p      ${LEAPDIR}/${PDB}.${STATE}.wat.leap.prmtop \
-c      ${TRAJDIR}/23md.restrt \
-ref    ${TRAJDIR}/14mi.restrt \
-x      ${TRAJDIR}/24md.mdcrd.nc \
-inf    ${TRAJDIR}/24md.info \
-r      ${TRAJDIR}/24md.restrt

echo "All jobs finished on: `date`" 

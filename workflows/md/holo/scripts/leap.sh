#!/usr/bin/env bash
set -euo pipefail

ROOT="${VARMDYN_MD_GENERATION_ROOT:-${PWD}/data/md}"
STATE_ROOT="${ROOT%/}/holo"
RUN_DIR="${STATE_ROOT}/${VARMDYN_MD_RUN_DIR:-.}"
SUBMIT=0
DIRECT_VARIANT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --submit) SUBMIT=1; shift ;;
    --variant) DIRECT_VARIANT="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--submit] [--variant WT]"
      exit 0
      ;;
    *) echo "[ERROR] unknown argument: $1"; exit 2 ;;
  esac
done

echo "[INFO] holo Hu2024 LEaP root: ${STATE_ROOT}"
test -d "${RUN_DIR}" || { echo "[ERROR] missing ${RUN_DIR}; run prepare first"; exit 2; }

source workflows/md/scripts/modules.sh
varmdyn_load_amber_modules

if [[ "${SUBMIT}" -eq 1 ]]; then
  mapfile -t variants < <(find "${RUN_DIR}" -maxdepth 1 -mindepth 1 -type d ! -name variants ! -name logs -printf '%f\n' | sort)
  (( ${#variants[@]} > 0 )) || { echo "[ERROR] no variants under ${RUN_DIR}"; exit 1; }
  logs="${STATE_ROOT}/logs/leap"
  mkdir -p "${logs}"
  script="${logs}/run_leap_array.slurm"
  {
    echo '#!/bin/bash'
    echo '#SBATCH --job-name=varmdyn-holo-leap'
    echo '#SBATCH --nodes=1'
    echo '#SBATCH --tasks-per-node=1'
    echo '#SBATCH --cpus-per-task=1'
    echo '#SBATCH --mem=16gb'
    echo '#SBATCH --time=02:00:00'
    echo "#SBATCH --array=0-$((${#variants[@]} - 1))"
    echo "#SBATCH --output=${logs}/leap-%A_%a.out"
    echo "#SBATCH --error=${logs}/leap-%A_%a.err"
    echo 'set -euo pipefail'
    echo 'source workflows/md/scripts/modules.sh'
    echo 'varmdyn_load_amber_modules'
    printf 'VARIANTS=(%s)\n' "${variants[*]}"
    printf 'cd %q\n' "$(pwd)"
    printf 'export VARMDYN_MD_GENERATION_ROOT=%q\n' "${ROOT}"
    printf 'bash workflows/md/holo/scripts/leap.sh --variant "${VARIANTS[$SLURM_ARRAY_TASK_ID]}"\n'
  } > "${script}"
  chmod 755 "${script}"
  echo "[SUBMIT] sbatch ${script}"
  sbatch "${script}"
  exit 0
fi

command -v tleap >/dev/null 2>&1 || { echo "[ERROR] tleap not found; load AmberTools/Amber first"; exit 2; }

for variant_dir in "${RUN_DIR}"/*; do
  test -d "${variant_dir}" || continue
  case "$(basename "${variant_dir}")" in variants|logs) continue ;; esac
  if [[ -n "${DIRECT_VARIANT}" && "$(basename "${variant_dir}")" != "${DIRECT_VARIANT}" ]]; then
    continue
  fi
  leap_dir="${variant_dir}/02.leap"
  com_dir="${leap_dir}/com"
  for required in \
    "${variant_dir}/01.prep/cdl.prot.noH.pdb" \
    "${variant_dir}/01.prep/ligand-only-from-complex-atponly.pdb" \
    "${variant_dir}/01.prep/mg-only-from-complex-mgonly.pdb" \
    "${variant_dir}/ligprep/hu2024/ATP-B3.prepi" \
    "${variant_dir}/ligprep/hu2024/ATP-B3.frcmod" \
    "${leap_dir}/tleap.com.hu24.in"; do
    test -s "${required}" || { echo "[ERROR] missing ${required}"; exit 1; }
  done

  echo "[LEAP] $(basename "${variant_dir}") Hu2024 ATP/Mg"
  cat > "${leap_dir}/charge_probe.in" <<'EOF'
addAtomTypes {{"O3" "O" "sp2"}}
addAtomTypes {{"O2" "O" "sp2"}}
addAtomTypes {{"O"  "O" "sp2"}}
addAtomTypes {{"OW" "O" "sp3"}}
addAtomTypes {{"OY" "O" "sp3"}}
source leaprc.protein.ff19SB
source leaprc.water.opc
loadamberparams frcmod.opc
loadamberparams frcmod.ionslm_126_opc
loadamberparams frcmod.ionslm_1264_opc
loadAmberPrep   ../ligprep/hu2024/ATP-B3.prepi
loadAmberParams ../ligprep/hu2024/ATP-B3.frcmod
REC = loadpdb ../01.prep/cdl.prot.noH.pdb
LIG = loadpdb ../01.prep/ligand-only-from-complex-atponly.pdb
MG  = loadpdb ../01.prep/mg-only-from-complex-mgonly.pdb
COM2 = combine { REC LIG MG }
charge COM2
quit
EOF
  (cd "${leap_dir}" && tleap -s -f charge_probe.in > charge_probe.log)
  python workflows/md/leap_neutralize.py \
    --template "${leap_dir}/tleap.com.hu24.in" \
    --charge-log "${leap_dir}/charge_probe.log" \
    --out "${leap_dir}/tleap.com.hu24.varmdyn.in" \
    --report "${leap_dir}/neutralization_plan.txt"
  (cd "${leap_dir}" && tleap -s -f tleap.com.hu24.varmdyn.in > leap.log)
  python workflows/md/ion_report.py \
    --state holo \
    --variant "$(basename "${variant_dir}")" \
    --log "${leap_dir}/leap.log" \
    --pdb "${leap_dir}/cdl.hu_atpmg.opc.pdb" \
    --out "${leap_dir}/ion_report.txt"
  mkdir -p "${com_dir}"
  cp -f "${leap_dir}/cdl.hu_atpmg.opc.prmtop" "${com_dir}/cdl.com.wat.leap.prmtop"
  cp -f "${leap_dir}/cdl.hu_atpmg.opc.inpcrd" "${com_dir}/cdl.com.wat.leap.inpcrd"
  cp -f "${leap_dir}/cdl.hu_atpmg.opc.pdb" "${com_dir}/cdl.com.wat.leap.pdb"
  cp -f "${leap_dir}/cdl.hu_atpmg.opc_gas.prmtop" "${com_dir}/cdl.com.gas.leap.prmtop"
  cp -f "${leap_dir}/cdl.hu_atpmg.opc_gas.inpcrd" "${com_dir}/cdl.com.gas.leap.inpcrd"
  cp -f "${leap_dir}/cdl.hu_atpmg.opc_gas.pdb" "${com_dir}/cdl.com.gas.leap.pdb"
  test -s "${com_dir}/cdl.com.wat.leap.prmtop" || { echo "[ERROR] missing holo wat topology"; exit 1; }
  test -s "${com_dir}/cdl.com.wat.leap.inpcrd" || { echo "[ERROR] missing holo wat coordinates"; exit 1; }
done

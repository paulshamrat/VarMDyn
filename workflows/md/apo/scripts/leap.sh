#!/usr/bin/env bash
set -euo pipefail

ROOT="${VARMDYN_MD_GENERATION_ROOT:-${PWD}/data/md}"
STATE_ROOT="${ROOT%/}/apo"
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

echo "[INFO] apo LEaP root: ${STATE_ROOT}"
test -d "${RUN_DIR}" || { echo "[ERROR] missing ${RUN_DIR}; run prep first"; exit 2; }

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
    echo '#SBATCH --job-name=varmdyn-apo-leap'
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
    printf 'bash workflows/md/apo/scripts/leap.sh --variant "${VARIANTS[$SLURM_ARRAY_TASK_ID]}"\n'
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
  prep="${variant_dir}/01.prep/cdl.prot.noH.pdb"
  leap_dir="${variant_dir}/02.leap"
  com_dir="${leap_dir}/com"
  test -s "${prep}" || { echo "[ERROR] missing ${prep}; run prep first"; exit 1; }
  test -s "${leap_dir}/tleap.com.in" || { echo "[ERROR] missing ${leap_dir}/tleap.com.in"; exit 1; }

  echo "[LEAP] $(basename "${variant_dir}")"
  cat > "${leap_dir}/charge_probe.in" <<'EOF'
set default PBradii mbondi3
source leaprc.protein.ff19SB
WAT = OPC
source leaprc.water.opc
loadoff solvents.lib
loadoff atomic_ions.lib
REC = loadpdb ../01.prep/cdl.prot.noH.pdb
COM2 = REC
charge COM2
quit
EOF
  (cd "${leap_dir}" && tleap -s -f charge_probe.in > charge_probe.log)
  python workflows/md/leap/neutralize.py \
    --template "${leap_dir}/tleap.com.in" \
    --charge-log "${leap_dir}/charge_probe.log" \
    --out "${leap_dir}/tleap.com.varmdyn.in" \
    --report "${leap_dir}/neutralization_plan.txt"
  (cd "${leap_dir}" && tleap -s -f tleap.com.varmdyn.in > leap.log)
  python workflows/md/leap/ion_report.py \
    --state apo \
    --variant "$(basename "${variant_dir}")" \
    --log "${leap_dir}/leap.log" \
    --pdb "${leap_dir}/cdl.com.wat.leap.pdb" \
    --out "${leap_dir}/ion_report.txt"
  mkdir -p "${com_dir}"
  cp -f "${leap_dir}"/cdl.com.*.leap.* "${com_dir}/"
  for required in \
    cdl.com.gas.leap.prmtop cdl.com.gas.leap.inpcrd \
    cdl.com.wat.leap.prmtop cdl.com.wat.leap.inpcrd; do
    test -s "${com_dir}/${required}" || { echo "[ERROR] missing ${com_dir}/${required}"; exit 1; }
  done
done

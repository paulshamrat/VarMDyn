#!/usr/bin/env bash
set -euo pipefail

ROOT="${VARMDYN_MD_GENERATION_ROOT:-${PWD}/data/md}"
STATE_ROOT="${ROOT%/}/holo"
RUN_DIR="${STATE_ROOT}/${VARMDYN_MD_RUN_DIR:-.}"
TEMPLATE_ROOT="${VARMDYN_MD_HOLO_TEMPLATE_ROOT:-workflows/md/templates/holo}"

source workflows/md/scripts/modules.sh
varmdyn_load_amber_modules

echo "[INFO] holo stage-1 prepare root: ${STATE_ROOT}"
test -d "${RUN_DIR}" || { echo "[ERROR] missing ${RUN_DIR}; run seed/transfer first"; exit 2; }
test -d "${TEMPLATE_ROOT}" || { echo "[ERROR] missing templates: ${TEMPLATE_ROOT}"; exit 2; }

strip_hydrogens() {
  awk '
  /^ATOM|^HETATM/ {
    an=$3
    el=$0
    sub(/^.{76}/,"",el)
    sub(/^[[:space:]]+/,"",el)
    if (substr(an,1,1)=="H" || el=="H") next
  }
  {print $0}
  ' "$1" > "$2"
}

for variant_dir in "${RUN_DIR}"/*; do
  test -d "${variant_dir}" || continue
  case "$(basename "${variant_dir}")" in variants|logs) continue ;; esac
  ligprep="${variant_dir}/ligprep"
  prep="${variant_dir}/01.prep"
  mkdir -p "${prep}" "${variant_dir}/02.leap/com" \
    "${variant_dir}/03.pmemd/com/cr1" "${variant_dir}/03.pmemd/com/cr2" \
    "${variant_dir}/03.pmemd/com/cr3"
  rsync -a "${TEMPLATE_ROOT}/02.leap/" "${variant_dir}/02.leap/"
  rsync -a "${TEMPLATE_ROOT}/04.ptraj/" "${variant_dir}/04.ptraj/"
  rsync -a "${TEMPLATE_ROOT}/protocol/" "${variant_dir}/protocol/"
  mkdir -p "${variant_dir}/ligprep/hu2024"
  rsync -a "${TEMPLATE_ROOT}/ligprep/hu2024/" "${variant_dir}/ligprep/hu2024/"

  receptor="${ligprep}/receptor_from_varmodel.pdb"
  ligand="${ligprep}/ligand-only-from-complex-atponly.pdb"
  mg="${ligprep}/mg-only-from-complex-mgonly.pdb"
  test -s "${receptor}" || { echo "[ERROR] missing ${receptor}; run seed first"; exit 1; }
  test -s "${ligand}" || { echo "[ERROR] missing ${ligand}; run ATP transfer first"; exit 1; }
  test -s "${mg}" || { echo "[ERROR] missing ${mg}; run ATP/Mg transfer first"; exit 1; }

  strip_hydrogens "${receptor}" "${prep}/cdl.prot.noH.pdb"
  cp -f "${ligand}" "${prep}/ligand-only-from-complex-atponly.pdb"
  cp -f "${mg}" "${prep}/mg-only-from-complex-mgonly.pdb"
  echo "[PREP] $(basename "${variant_dir}"): staged Hu2024 inputs and protocol layout"
done

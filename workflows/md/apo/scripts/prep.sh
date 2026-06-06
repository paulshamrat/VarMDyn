#!/usr/bin/env bash
set -euo pipefail

ROOT="${VARMDYN_MD_GENERATION_ROOT:-${PWD}/data/md}"
STATE_ROOT="${ROOT%/}/apo"
RUN_DIR="${STATE_ROOT}/${VARMDYN_MD_RUN_DIR:-.}"
VARIANTS_DIR="${STATE_ROOT}/${VARMDYN_MD_VARIANTS_DIR:-variants}"
TEMPLATE_ROOT="${VARMDYN_MD_APO_TEMPLATE_ROOT:-workflows/md/templates/apo}"
PH="${VARMDYN_MD_PREP_PH:-7.4}"

source workflows/md/scripts/modules.sh
varmdyn_load_amber_modules

echo "[INFO] apo prep root: ${STATE_ROOT}"
test -d "${VARIANTS_DIR}" || { echo "[ERROR] missing ${VARIANTS_DIR}; run handoff first"; exit 2; }
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

stage_layout() {
  local variant_dir="$1"
  mkdir -p "${variant_dir}/01.prep" "${variant_dir}/02.leap/com" \
    "${variant_dir}/03.pmemd/com/cr1" "${variant_dir}/03.pmemd/com/cr2" \
    "${variant_dir}/03.pmemd/com/cr3"
  rsync -a "${TEMPLATE_ROOT}/02.leap/" "${variant_dir}/02.leap/"
  rsync -a "${TEMPLATE_ROOT}/04.ptraj/" "${variant_dir}/04.ptraj/"
  rsync -a "${TEMPLATE_ROOT}/protocol/" "${variant_dir}/protocol/"
}

for pdb in "${VARIANTS_DIR}"/*.pdb; do
  variant="$(basename "${pdb}" .pdb)"
  variant_dir="${RUN_DIR}/${variant}"
  out="${variant_dir}/01.prep"
  stage_layout "${variant_dir}"
  cp -f "${pdb}" "${out}/input_from_varmodel.pdb"

  if command -v pdb4amber >/dev/null 2>&1 && command -v pdb2pqr >/dev/null 2>&1; then
    echo "[PREP] ${variant}: pdb4amber + pdb2pqr pH ${PH}"
    pdb4amber -i "${pdb}" -o "${out}/cdl_out.pdb" -y -d > "${out}/pdb4amber.log" 2>&1
    pdb2pqr \
      --ff=AMBER --ffout=AMBER \
      --titration-state-method=propka --with-ph="${PH}" \
      --drop-water \
      --pdb-output "${out}/cdl_out_prot.pdb" \
      "${pdb}" "${out}/cdl_out_prot.pqr" > "${out}/pdb2pqr.log" 2>&1
    strip_hydrogens "${out}/cdl_out_prot.pdb" "${out}/cdl.prot.noH.pdb"
  else
    echo "[WARN] pdb4amber or pdb2pqr not found; staging input without protonation for ${variant}"
    strip_hydrogens "${pdb}" "${out}/cdl.prot.noH.pdb"
  fi

  test -s "${out}/cdl.prot.noH.pdb" || { echo "[ERROR] failed to create ${out}/cdl.prot.noH.pdb"; exit 1; }
  echo "[PREP] ${variant}: staged legacy layout and cdl.prot.noH.pdb"
done

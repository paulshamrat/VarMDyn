#!/usr/bin/env bash
set -euo pipefail

ROOT="${VARMDYN_MD_GENERATION_ROOT:-${PWD}/data/md}"
STATE_ROOT="${ROOT%/}/holo"
RUN_DIR="${STATE_ROOT}/${VARMDYN_MD_RUN_DIR:-.}"
VARIANTS_DIR="${STATE_ROOT}/${VARMDYN_MD_VARIANTS_DIR:-variants}"
APO_RUN_ROOT="${VARMDYN_MD_APO_RUN_ROOT:-}"

echo "[INFO] holo seed root: ${STATE_ROOT}"
test -d "${VARIANTS_DIR}" || { echo "[ERROR] missing ${VARIANTS_DIR}; run handoff first"; exit 2; }
for pdb in "${VARIANTS_DIR}"/*.pdb; do
  variant="$(basename "${pdb}" .pdb)"
  out="${RUN_DIR}/${variant}/ligprep"
  mkdir -p "${out}"
  src="${pdb}"
  if [[ -n "${APO_RUN_ROOT}" ]]; then
    for candidate in \
      "${APO_RUN_ROOT}/${variant}/01.prep/cdl.prot.noH.pdb" \
      "${APO_RUN_ROOT}/systems/${variant}/01.prep/cdl.prot.noH.pdb" \
      "${APO_RUN_ROOT}/${variant}/01.prep/cdl.prot.noH.pdb" \
      "${APO_RUN_ROOT}/03_mdsim/${variant}/01.prep/cdl.prot.noH.pdb"; do
      if [[ -s "${candidate}" ]]; then
        src="${candidate}"
        break
      fi
    done
  fi
  cp -f "${src}" "${out}/receptor_from_varmodel.pdb"
  cp -f "${src}" "${out}/cdl.prot.noH.pdb"
  echo "[SEED] ${variant}: staged receptor from ${src}"
done

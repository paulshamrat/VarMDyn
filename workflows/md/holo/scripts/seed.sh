#!/usr/bin/env bash
set -euo pipefail

ROOT="${VARMDYN_MD_GENERATION_ROOT:-${PWD}/data/md}"
STATE_ROOT="${ROOT%/}/holo"
RUN_DIR="${STATE_ROOT}/${VARMDYN_MD_RUN_DIR:-systems}"
VARIANTS_DIR="${STATE_ROOT}/01_variants"

echo "[INFO] holo seed root: ${STATE_ROOT}"
test -d "${VARIANTS_DIR}" || { echo "[ERROR] missing ${VARIANTS_DIR}; run handoff first"; exit 2; }
for pdb in "${VARIANTS_DIR}"/*.pdb; do
  variant="$(basename "${pdb}" .pdb)"
  out="${RUN_DIR}/${variant}/ligprep"
  mkdir -p "${out}"
  cp -f "${pdb}" "${out}/receptor_from_varmodel.pdb"
  echo "[SEED] ${variant}: staged receptor_from_varmodel.pdb"
done
echo "[WARN] ATP/Mg transfer is not implemented in this script yet."

#!/usr/bin/env bash
set -euo pipefail

ROOT="${VARMDYN_MD_GENERATION_ROOT:-${PWD}/data/md}"
STATE_ROOT="${ROOT%/}/apo"
RUN_DIR="${STATE_ROOT}/${VARMDYN_MD_RUN_DIR:-systems}"
VARIANTS_DIR="${STATE_ROOT}/01_variants"

echo "[INFO] apo prep root: ${STATE_ROOT}"
test -d "${VARIANTS_DIR}" || { echo "[ERROR] missing ${VARIANTS_DIR}; run handoff first"; exit 2; }

for pdb in "${VARIANTS_DIR}"/*.pdb; do
  variant="$(basename "${pdb}" .pdb)"
  out="${RUN_DIR}/${variant}/01.prep"
  mkdir -p "${out}"
  cp -f "${pdb}" "${out}/input_from_varmodel.pdb"
  echo "[PREP] ${variant}: staged input_from_varmodel.pdb"
done

echo "[WARN] AMBER pdb4amber/pdb2pqr cleaning is not implemented in this public script yet."
echo "[WARN] Next parity step: port validated prep commands into this module-owned script."

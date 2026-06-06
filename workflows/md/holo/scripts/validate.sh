#!/usr/bin/env bash
set -euo pipefail

ROOT="${VARMDYN_MD_GENERATION_ROOT:-${PWD}/data/md}"
STATE_ROOT="${ROOT%/}/holo"
RUN_DIR="${STATE_ROOT}/${VARMDYN_MD_RUN_DIR:-.}"

echo "[INFO] holo coordinate validation root: ${STATE_ROOT}"
test -d "${RUN_DIR}" || { echo "[ERROR] missing ${RUN_DIR}; run transfer first"; exit 2; }

failures=0
for variant_dir in "${RUN_DIR}"/*; do
  test -d "${variant_dir}" || continue
  case "$(basename "${variant_dir}")" in variants|logs) continue ;; esac
  for required in \
    ligprep/cdl.prot.noH.pdb \
    ligprep/8FP5.pdb \
    ligprep/ligand-only-from-complex-atponly.pdb \
    ligprep/mg-only-from-complex-mgonly.pdb \
    ligprep/cdl.prot.noH_atpmg_from8fp5.pdb \
    ligprep/transfer_kinase_context.png \
    ligprep/transfer_ligand_zoom.png \
    ligprep/transfer_core_30_220_overlay.png; do
    path="${variant_dir}/${required}"
    if [[ -s "${path}" ]]; then
      echo "[OK] $(basename "${variant_dir}") ${required}"
    else
      echo "[MISSING] $(basename "${variant_dir}") ${required}"
      failures=$((failures + 1))
    fi
  done
done

exit "${failures}"

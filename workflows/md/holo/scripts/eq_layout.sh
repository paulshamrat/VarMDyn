#!/usr/bin/env bash
set -euo pipefail

ROOT="${VARMDYN_MD_GENERATION_ROOT:-${PWD}/data/md}"
STATE_ROOT="${ROOT%/}/holo"
RUN_DIR="${STATE_ROOT}/${VARMDYN_MD_RUN_DIR:-.}"
TEMPLATE_ROOT="${VARMDYN_MD_HOLO_TEMPLATE_ROOT:-workflows/md/templates/holo}"

echo "[INFO] holo equilibration layout root: ${STATE_ROOT}"
test -d "${RUN_DIR}" || { echo "[ERROR] missing ${RUN_DIR}; run prepare first"; exit 2; }
test -d "${TEMPLATE_ROOT}" || { echo "[ERROR] missing templates: ${TEMPLATE_ROOT}"; exit 2; }

for variant_dir in "${RUN_DIR}"/*; do
  test -d "${variant_dir}" || continue
  case "$(basename "${variant_dir}")" in variants|logs) continue ;; esac
  mkdir -p "${variant_dir}/03.pmemd/com/cr1" "${variant_dir}/03.pmemd/com/cr2" \
    "${variant_dir}/03.pmemd/com/cr3"
  rsync -a "${TEMPLATE_ROOT}/protocol/" "${variant_dir}/protocol/"
  rsync -a "${TEMPLATE_ROOT}/04.ptraj/" "${variant_dir}/04.ptraj/"
  echo "[LAYOUT] $(basename "${variant_dir}"): protocol/com and 03.pmemd/com replicas ready"
done

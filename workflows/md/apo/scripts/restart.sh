#!/usr/bin/env bash
set -euo pipefail

ROOT="${VARMDYN_MD_GENERATION_ROOT:-${PWD}/data/md}"
STATE_ROOT="${ROOT%/}/apo"
RUN_DIR="${STATE_ROOT}/${VARMDYN_MD_RUN_DIR:-.}"

source workflows/md/scripts/modules.sh
varmdyn_load_amber_modules

echo "[INFO] apo restart propagation root: ${STATE_ROOT}"
test -d "${RUN_DIR}" || { echo "[ERROR] missing ${RUN_DIR}; run equilibration first"; exit 2; }
python workflows/md/stages/restart.py --run-root "${RUN_DIR}" "${@}"

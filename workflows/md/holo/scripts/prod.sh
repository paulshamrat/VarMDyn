#!/usr/bin/env bash
set -euo pipefail
ROOT="${VARMDYN_MD_GENERATION_ROOT:-${PWD}/data/md}"
STATE_ROOT="${ROOT%/}/holo"
RUN_DIR="${STATE_ROOT}/${VARMDYN_MD_RUN_DIR:-.}"

source workflows/md/scripts/modules.sh
varmdyn_load_amber_modules

echo "[INFO] holo production root: ${STATE_ROOT}"
test -d "${RUN_DIR}" || { echo "[ERROR] missing ${RUN_DIR}; run earlier stages first"; exit 2; }
START="${VARMDYN_MD_PROD_START:-25}"
END="${VARMDYN_MD_PROD_END:-29}"
python workflows/md/submit.py --mode prod --array --run-root "${RUN_DIR}" --start "${START}" --end "${END}" "${@}"

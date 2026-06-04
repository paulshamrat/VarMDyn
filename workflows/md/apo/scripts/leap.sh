#!/usr/bin/env bash
set -euo pipefail

ROOT="${VARMDYN_MD_GENERATION_ROOT:-${PWD}/data/md}"
STATE_ROOT="${ROOT%/}/apo"
RUN_DIR="${STATE_ROOT}/${VARMDYN_MD_RUN_DIR:-systems}"

echo "[INFO] apo LEaP root: ${STATE_ROOT}"
test -d "${RUN_DIR}" || { echo "[ERROR] missing ${RUN_DIR}; run prep first"; exit 2; }
echo "[WARN] AMBER tleap generation is not implemented in this public script yet."
echo "[WARN] Next parity step: port ff19SB/OPC LEaP template into workflows/md/apo/templates/."

#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${SCRIPT_DIR}/env.sh.example"

if [[ "${VARMDYN_HPC_HOST}" == "user@login.example.edu" ]]; then
  echo "[FAIL] Set VARMDYN_HPC_HOST=user@login.example.edu" >&2
  exit 2
fi
if [[ "${VARMDYN_HPC_REPO}" == "/path/to/hpc/network_shared" ]]; then
  echo "[FAIL] Set VARMDYN_HPC_REPO=/path/to/hpc/network_shared" >&2
  exit 2
fi

mkdir -p "${VARMDYN_NETWORK_DATA_ROOT}"

rsync -av \
  -e "${VARMDYN_RSYNC_SSH}" \
  --include='*/' --include='*.csv' --include='*.txt' --exclude='*' \
  "${VARMDYN_HPC_HOST}:${VARMDYN_HPC_NETWORK_DATA_ROOT}/dynetan/" \
  "${VARMDYN_NETWORK_DATA_ROOT}/dynetan/"

rsync -av \
  -e "${VARMDYN_RSYNC_SSH}" \
  --include='*/' --include='*.csv' --exclude='*' \
  "${VARMDYN_HPC_HOST}:${VARMDYN_HPC_NETWORK_DATA_ROOT}/compare/" \
  "${VARMDYN_NETWORK_DATA_ROOT}/compare/"

rsync -av \
  -e "${VARMDYN_RSYNC_SSH}" \
  --include='*/' --include='*.pdb' --include='bottleneck_nodes_top25.csv' --exclude='*' \
  "${VARMDYN_HPC_HOST}:${VARMDYN_HPC_NETWORK_DATA_ROOT}/prepared/" \
  "${VARMDYN_NETWORK_DATA_ROOT}/prepared/"

echo "[OK] fetched lightweight network results into ${VARMDYN_NETWORK_DATA_ROOT}"

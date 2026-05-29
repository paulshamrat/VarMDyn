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

mkdir -p "${SCRIPT_DIR}/data/network/full"

rsync -av \
  -e "${VARMDYN_RSYNC_SSH}" \
  --include='*/' --include='*.csv' --include='*.txt' --exclude='*' \
  "${VARMDYN_HPC_HOST}:${VARMDYN_HPC_REPO}/data/network/full/dynetan/" \
  "${SCRIPT_DIR}/data/network/full/dynetan/"

rsync -av \
  -e "${VARMDYN_RSYNC_SSH}" \
  --include='*/' --include='*.csv' --exclude='*' \
  "${VARMDYN_HPC_HOST}:${VARMDYN_HPC_REPO}/data/network/full/compare/" \
  "${SCRIPT_DIR}/data/network/full/compare/"

rsync -av \
  -e "${VARMDYN_RSYNC_SSH}" \
  --include='*/' --include='*.pdb' --exclude='*' \
  "${VARMDYN_HPC_HOST}:${VARMDYN_HPC_REPO}/data/network/full/prepared/" \
  "${SCRIPT_DIR}/data/network/full/prepared/"

echo "[OK] fetched lightweight network results into ${SCRIPT_DIR}/data/network/full"

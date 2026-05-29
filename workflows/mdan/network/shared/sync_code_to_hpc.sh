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

"${VARMDYN_SSH_COMMAND}" "${VARMDYN_HPC_HOST}" "mkdir -p '${VARMDYN_HPC_REPO}'"

rsync -av \
  -e "${VARMDYN_RSYNC_SSH}" \
  --exclude='.git/' \
  --exclude='data/' \
  --exclude='runs/' \
  --exclude='site/' \
  --exclude='.local_docs/' \
  --exclude='CHECKPOINT.md' \
  --exclude='mkdocs.local.yml' \
  "${SCRIPT_DIR}/" "${VARMDYN_HPC_HOST}:${VARMDYN_HPC_REPO}/"

echo "[OK] synced code to ${VARMDYN_HPC_HOST}:${VARMDYN_HPC_REPO}"

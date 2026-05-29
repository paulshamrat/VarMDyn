#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

source "${SCRIPT_DIR}/env.sh.example"

if [[ "${VARMDYN_HPC_HOST}" == "user@login.example.edu" ]]; then
  echo "[FAIL] Set VARMDYN_HPC_HOST=user@login.example.edu" >&2
  exit 2
fi
if [[ "${VARMDYN_HPC_REPO}" == "/path/to/hpc/varmdyn" ]]; then
  echo "[FAIL] Set VARMDYN_HPC_REPO=/path/to/hpc/varmdyn" >&2
  exit 2
fi

mkdir -p "${REPO_ROOT}/data/network/full"

rsync -av \
  --include='*/' --include='*.csv' --include='*.txt' --exclude='*' \
  "${VARMDYN_HPC_HOST}:${VARMDYN_HPC_REPO}/data/network/full/dynetan/" \
  "${REPO_ROOT}/data/network/full/dynetan/"

rsync -av \
  --include='*/' --include='*.csv' --exclude='*' \
  "${VARMDYN_HPC_HOST}:${VARMDYN_HPC_REPO}/data/network/full/compare/" \
  "${REPO_ROOT}/data/network/full/compare/"

rsync -av \
  --include='*/' --include='*.pdb' --exclude='*' \
  "${VARMDYN_HPC_HOST}:${VARMDYN_HPC_REPO}/data/network/full/prepared/" \
  "${REPO_ROOT}/data/network/full/prepared/"

echo "[OK] fetched lightweight network results into ${REPO_ROOT}/data/network/full"

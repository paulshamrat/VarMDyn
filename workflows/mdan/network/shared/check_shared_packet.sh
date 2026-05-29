#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

required=(
  "${SCRIPT_DIR}/README.md"
  "${SCRIPT_DIR}/env.sh.example"
  "${SCRIPT_DIR}/sync_code_to_hpc.sh"
  "${SCRIPT_DIR}/submit_network_array.sh"
  "${SCRIPT_DIR}/fetch_network_results.sh"
  "${SCRIPT_DIR}/check_shared_packet.sh"
  "${REPO_ROOT}/workflows/mdan/network/network.py"
  "${REPO_ROOT}/workflows/mdan/network/run_network_array.slurm"
  "${REPO_ROOT}/workflows/mdan/network/create_dynetan_env.sh"
)

missing=0
for path in "${required[@]}"; do
  if [[ -e "${path}" ]]; then
    echo "[OK] ${path#${REPO_ROOT}/}"
  else
    echo "[MISSING] ${path#${REPO_ROOT}/}" >&2
    missing=1
  fi
done

exit "${missing}"

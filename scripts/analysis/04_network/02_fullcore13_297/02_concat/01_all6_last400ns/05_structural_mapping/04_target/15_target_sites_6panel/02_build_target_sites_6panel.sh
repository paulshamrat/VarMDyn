#!/usr/bin/env bash
# Build the independent red target-site six-panel Apo/Holo figure.
set -Eeuo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
python3 "${SCRIPT_DIR}/01_build_target_sites_6panel.py"

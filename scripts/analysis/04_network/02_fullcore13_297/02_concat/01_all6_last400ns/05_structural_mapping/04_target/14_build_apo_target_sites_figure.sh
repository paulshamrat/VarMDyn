#!/usr/bin/env bash
# Build the independent three-panel apo target-site figure.
set -Eeuo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
python3 "${SCRIPT_DIR}/12_render_apo_target_sites.py"
python3 "${SCRIPT_DIR}/13_assemble_apo_target_sites_figure.py"

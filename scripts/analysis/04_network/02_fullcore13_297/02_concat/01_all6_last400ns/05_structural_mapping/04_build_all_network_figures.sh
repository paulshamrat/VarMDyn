#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
"${SCRIPT_DIR}/06_pathogenic_network_maps/03_build_pathogenic_network_figure.sh"
"${SCRIPT_DIR}/03_state_paired_lost_gain/06_build_state_paired_figure.sh"

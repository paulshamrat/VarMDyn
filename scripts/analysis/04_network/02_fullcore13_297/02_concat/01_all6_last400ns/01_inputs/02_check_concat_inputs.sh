#!/usr/bin/env bash
set -Eeuo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../00_settings.sh"
RESULT_ROOT="${NETWORK_ROOT}/data/analysis/04_network/02_fullcore13_297/02_concat/01_all6_last400ns"
[[ -d ${MD_DATA_ROOT} && -x ${DYNETAN_PYTHON} ]] || { echo "ERROR: run this on Insurgent after activating the DyNetAn environment." >&2; exit 2; }
"${DYNETAN_PYTHON}" "${SCRIPT_DIR}/01_check_concat_inputs.py" --md-data-root "${MD_DATA_ROOT}" --output "${RESULT_ROOT}/01_inputs/01_concat_input_qc.tsv"

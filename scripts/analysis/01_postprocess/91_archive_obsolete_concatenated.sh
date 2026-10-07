#!/usr/bin/env bash
# Archive explicitly named obsolete concatenated products on scratch.
# It cannot select anything until you add exact obsolete basenames below.
# Current CR1--CR3 and CR1--CR6 outputs are therefore protected by default.

set -Eeuo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/00_postprocess_settings.sh"

ARCHIVE_NAME=archive_prestandardized_20260731
# Add only exact, reviewed basenames here. Leave empty for a safe no-op.
OBSOLETE_BASENAMES=()
execute=false

if [[ ${1:-} == "--execute" ]]; then
    execute=true
elif [[ $# -ne 0 ]]; then
    echo "Usage: $0 [--execute]" >&2
    exit 2
fi

echo "[INFO] Maintenance Tool 91: Archive Obsolete Concatenated Trajectories"
echo "       Scratch Root: ${SIM_ROOT}"
echo "       Execute:      ${execute}"

if (( ${#OBSOLETE_BASENAMES[@]} == 0 )); then
    echo "No explicitly approved obsolete basenames are configured; nothing will be moved."
    exit 0
fi

for branch in 03_mdsim 05_cdkl5atpmg; do
    for variant_dir in "${SIM_ROOT}/${branch}"/0[1-8]_*; do
        concat=${variant_dir}/04.ptraj/com/concatenated
        [[ -d ${concat} ]] || continue
        archive=${concat}/${ARCHIVE_NAME}
        for basename in "${OBSOLETE_BASENAMES[@]}"; do
            item=${concat}/${basename}
            [[ -e ${item} ]] || continue
            if [[ ${execute} == true ]]; then
                mkdir -p "${archive}"
                [[ ! -e ${archive}/$(basename "${item}") ]] || {
                    echo "Refusing to overwrite existing archive item: ${archive}/$(basename "${item}")" >&2
                    exit 1
                }
                mv -- "${item}" "${archive}/"
                printf 'ARCHIVED\t%s\n' "${item}"
            else
                printf 'WOULD_ARCHIVE\t%s\n' "${item}"
            fi
        done
    done
done

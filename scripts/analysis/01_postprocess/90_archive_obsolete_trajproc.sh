#!/usr/bin/env bash
# Archive older derived trajectory-processing artifacts on shared scratch.
# Maintenance tool only (numbered 90). Dry-run by default.
# Raw MD output under 03.pmemd, LEaP input, and current *.sampled-5 products
# are never moved. Pass --execute to run planned moves.

set -Eeuo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/00_postprocess_settings.sh"

ARCHIVE_NAME=archive_prestandardized_20260731
execute=false

if [[ ${1:-} == "--execute" ]]; then
    execute=true
elif [[ $# -ne 0 ]]; then
    echo "Usage: $0 [--execute]" >&2
    exit 2
fi

echo "[INFO] Maintenance Tool 90: Archive Obsolete Trajectory Processing"
echo "       Scratch Root: ${SIM_ROOT}"
echo "       Execute:      ${execute}"

is_current_apo() {
    case $1 in
        production-25-to-29-500ns.cr*.striped.sampled-5.mdcrd.nc|strip-25-to-29.sampled-5.in|strip-25-to-29.sampled-5.log) return 0 ;;
        *) return 1 ;;
    esac
}

is_current_holo() {
    case $1 in
        production-25-to-29-500ns.cr*.keepATPmg.sampled-5.mdcrd.nc|production-25-to-29-500ns.cr*.striped_v2.sampled-5.mdcrd.nc|strip-25-to-29_keepATPmg.sampled-5.in|strip-25-to-29_keepATPmg.sampled-5.log|strip-25-to-29_striped_v2.sampled-5.in|strip-25-to-29_striped_v2.sampled-5.log) return 0 ;;
        *) return 1 ;;
    esac
}

archive_directory() {
    local state=$1 directory=$2 file archive
    [[ -d $directory ]] || return 0
    archive=${directory}/${ARCHIVE_NAME}

    while IFS= read -r -d '' file; do
        # NFS temporary files can be held open by another process; leave them alone.
        [[ $(basename "$file") == .nfs* ]] && continue
        if [[ $state == apo ]]; then
            is_current_apo "$(basename "$file")" && continue
        else
            is_current_holo "$(basename "$file")" && continue
        fi

        if [[ $execute == true ]]; then
            mkdir -p "$archive"
            mv -- "$file" "$archive/"
            printf 'ARCHIVED\t%s\n' "$file"
        else
            printf 'WOULD_ARCHIVE\t%s\n' "$file"
        fi
    done < <(find "$directory" -maxdepth 1 -type f -print0)
}

for root_state in apo holo; do
    if [[ $root_state == apo ]]; then
        root=${SIM_ROOT}/03_mdsim
    else
        root=${SIM_ROOT}/05_cdkl5atpmg
    fi

    for variant_dir in "$root"/0[1-8]_*; do
        [[ -d $variant_dir ]] || continue
        for replica_dir in "$variant_dir"/04.ptraj/com/cr*; do
            archive_directory "$root_state" "$replica_dir/traj-proc"
        done
    done
done

#!/usr/bin/env bash
# Read-only readiness check for standardized trajectory processing.
# Run on the Palmetto login node:
#   bash 00_check_postprocess_readiness.sh

set -Eeuo pipefail

WORKFLOW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00_postprocess_settings.sh
source "${WORKFLOW_DIR}/00_postprocess_settings.sh"

[[ -d $SIM_ROOT ]] || { echo "SIM_ROOT does not exist: $SIM_ROOT" >&2; exit 2; }
module --ignore_cache load amber/24.openmpi >/dev/null 2>&1
command -v ncdump >/dev/null || { echo 'ncdump is unavailable after loading Amber 24.' >&2; exit 2; }

frame_count() {
    ncdump -h "$1" 2>/dev/null | sed -n 's/^[[:space:]]*frame = UNLIMITED ; \/\/ (\([0-9][0-9]*\) currently).*/\1/p' | head -n 1
}

stage_ready() {
    local raw=$1 stage=$2
    [[ -s "${raw}/${stage}md.mdcrd.nc" && -s "${raw}/${stage}md.mdout" && -s "${raw}/${stage}md.restrt" ]] || return 1
    grep -Eq 'NSTEP[[:space:]]*=[[:space:]]*50000000' "${raw}/${stage}md.mdout"
}

expected_outputs() {
    local state=$1 replica=$2 output_dir=$3
    if [[ $state == apo ]]; then
        printf '%s\n' "${output_dir}/production-25-to-29-500ns.${replica}.striped.sampled-5.mdcrd.nc"
    else
        printf '%s\n' \
            "${output_dir}/production-25-to-29-500ns.${replica}.keepATPmg.sampled-5.mdcrd.nc" \
            "${output_dir}/production-25-to-29-500ns.${replica}.striped_v2.sampled-5.mdcrd.nc"
    fi
}

audit_topology_status() {
    local state=$1 leap=$2
    if [[ $state == apo ]]; then
        [[ -s "${leap}/com/cdl.com.gas.equib.prmtop" ]] && printf PASS || printf MISSING
    elif [[ -s "${leap}/com/cdl.com.keepATPmg.equib.prmtop" && -s "${leap}/com/cdl.com.striped_v2.equib.prmtop" ]]; then
        printf PASS
    else
        printf MISSING
    fi
}

{
    printf 'State\tVariant\tReplica\tStages\tStage completion\tRaw frames\tWater topology\tOutput status\tAudit topology\tReadiness\n'
    for state in apo holo; do
        branch=$(state_branch "$state")
        for variant in "${VARIANTS[@]}"; do
            system="${SIM_ROOT}/${branch}/${variant}"
            leap="${system}/02.leap"
            water_topology="${leap}/com/cdl.com.wat.leap.prmtop"
            for replica in "${REPLICAS[@]}"; do
                raw="${system}/03.pmemd/com/${replica}"
                output_dir="${system}/04.ptraj/com/${replica}/traj-proc"
                stage_files=0
                stage_complete=0
                raw_frames=0
                netcdf_ok=yes
                for stage in "${PRODUCTION_STAGES[@]}"; do
                    trajectory="${raw}/${stage}md.mdcrd.nc"
                    [[ -s $trajectory ]] && ((stage_files += 1))
                    stage_ready "$raw" "$stage" && ((stage_complete += 1)) || true
                    frames=$(frame_count "$trajectory" || true)
                    [[ $frames == 5000 ]] && ((raw_frames += frames)) || netcdf_ok=no
                done
                topology_status=MISSING
                [[ -s $water_topology ]] && topology_status=PASS
                outputs_present=0
                outputs_expected=0
                output_frames_ok=yes
                while read -r output; do
                    ((outputs_expected += 1))
                    if [[ -s $output ]]; then
                        ((outputs_present += 1))
                        [[ $(frame_count "$output" || true) == 5000 ]] || output_frames_ok=no
                    fi
                done < <(expected_outputs "$state" "$replica" "$output_dir")
                if (( outputs_present == 0 )); then
                    output_status=MISSING
                elif (( outputs_present == outputs_expected )) && [[ $output_frames_ok == yes ]]; then
                    output_status=PRESENT_5000
                else
                    output_status=PARTIAL_OR_INVALID
                fi
                audit_status=$(audit_topology_status "$state" "$leap")
                readiness=READY_TO_PROCESS
                if (( stage_files != 5 || stage_complete != 5 )); then
                    readiness=RAW_INCOMPLETE
                elif [[ $netcdf_ok != yes || $raw_frames != 25000 ]]; then
                    readiness=RAW_FRAMES_OR_NETCDF_INVALID
                elif [[ $topology_status != PASS ]]; then
                    readiness=MISSING_WATER_TOPOLOGY
                elif [[ ! -w $system ]]; then
                    readiness=OUTPUT_LOCATION_NOT_WRITABLE
                elif [[ $output_status == PRESENT_5000 ]]; then
                    if [[ $audit_status == PASS ]]; then readiness=ALREADY_PRESENT_NEEDS_AUDIT; else readiness=ALREADY_PRESENT_MISSING_AUDIT_TOPOLOGY; fi
                elif [[ $output_status == PARTIAL_OR_INVALID ]]; then
                    readiness=OUTPUT_PARTIAL_REPROCESS
                fi
                printf '%s\t%s\t%s\t%s/5\t%s/5\t%s/25000\t%s\t%s\t%s\t%s\n' \
                    "${state^}" "$variant" "${replica^^}" "$stage_files" "$stage_complete" "$raw_frames" \
                    "$topology_status" "$output_status" "$audit_status" "$readiness"
            done
        done
    done
} | awk -F $'\t' 'BEGIN { OFS = FS }
    NR == 1 { print; next }
    { state = $1; variant = $2; if (state == previous_state && variant == previous_variant) { $1 = ""; $2 = "" }; print; previous_state = state; previous_variant = variant }
' | column -ts $'\t'

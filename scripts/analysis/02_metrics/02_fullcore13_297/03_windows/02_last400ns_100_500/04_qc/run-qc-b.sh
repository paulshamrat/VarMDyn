#!/usr/bin/env bash
set -Eeuo pipefail

die() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

selected_state="all"
results_root="${VARMDYN_DATA_ROOT:?Set VARMDYN_DATA_ROOT}/analysis/02_metrics/qc"
block_ns="50"
cutoffs="0,25,50,75,100,125,150,175,200"
min_tail_ns="250"
overwrite=0

while (( $# > 0 )); do
    case "$1" in
        --state) selected_state="$2"; shift 2 ;;
        --state=*) selected_state="${1#*=}"; shift ;;
        --input-root|--output-root) results_root="$2"; shift 2 ;;
        --input-root=*|--output-root=*) results_root="${1#*=}"; shift ;;
        --block-ns) block_ns="$2"; shift 2 ;;
        --block-ns=*) block_ns="${1#*=}"; shift ;;
        --cutoffs) cutoffs="$2"; shift 2 ;;
        --cutoffs=*) cutoffs="${1#*=}"; shift ;;
        --min-tail-ns) min_tail_ns="$2"; shift 2 ;;
        --min-tail-ns=*) min_tail_ns="${1#*=}"; shift ;;
        --overwrite) overwrite=1; shift ;;
        -h|--help)
            cat <<'EOF'
Usage:
  qc/run-qc-b.sh --state apo|holo|all [OPTIONS]

State-first inputs:
  qc/results/<state>/qc-a/

State-first outputs:
  qc/results/<state>/qc-b/
EOF
            exit 0
            ;;
        *) die "Unknown option: $1" ;;
    esac
done

case "${selected_state}" in
    apo|holo|all) ;;
    *) die "--state must be apo, holo, or all" ;;
esac

analysis_py="${script_dir}/analyze_equilibration.py"
[[ -f "${analysis_py}" ]] || die "Missing analysis script: ${analysis_py}"

run_state() {
    local state
    local qca
    local out
    local whole
    local core
    local rg

    state="$1"
    qca="${results_root}/${state}/qc-a"
    out="${results_root}/${state}/qc-b"

    whole="${qca}/rmsd/rmsd.whole.all.tsv"
    core="${qca}/rmsd/rmsd.core.all.tsv"
    rg="${qca}/rg/rg.all.tsv"

    [[ -f "${whole}" ]] || die "Missing ${state} QC-A whole RMSD: ${whole}"
    [[ -f "${core}" ]] || die "Missing ${state} QC-A core RMSD: ${core}"
    [[ -f "${rg}" ]] || die "Missing ${state} QC-A Rg: ${rg}"

    if (( overwrite == 0 )) && [[ -s "${out}/cutoff.summary.tsv" ]]; then
        die "QC-B already exists for ${state}: ${out} (use --overwrite)"
    fi

    python "${analysis_py}"         --state "${state}"         --whole "${whole}"         --core "${core}"         --rg "${rg}"         --output-root "${out}"         --block-ns "${block_ns}"         --cutoffs "${cutoffs}"         --min-tail-ns "${min_tail_ns}"
}

if [[ "${selected_state}" == "apo" || "${selected_state}" == "all" ]]; then
    run_state apo
fi

if [[ "${selected_state}" == "holo" || "${selected_state}" == "all" ]]; then
    run_state holo
fi

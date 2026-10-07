#!/usr/bin/env bash
set -Eeuo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
state="all"; jobs=1; overwrite=0; extra=()
while (( $# )); do
 case "$1" in
  --state) state="$2"; shift 2;;
  --jobs) jobs="$2"; shift 2;;
  --overwrite) overwrite=1; shift;;
  -h|--help)
   cat <<'EOF'
QC-C wrapper for finalized workflows only:
  1. regional RMSD
  2. dedicated ensemble RMSF

Per-replica RMSF from the legacy QC-C script is intentionally retired.
EOF
   exit 0;;
  *) extra+=("$1"); shift;;
 esac
done
ow=(); ((overwrite==1))&&ow=(--overwrite)
bash "${script_dir}/run-regional-rmsd.sh" --state "$state" --jobs "$jobs" "${ow[@]}" "${extra[@]}"
bash "${script_dir}/run-ensemble-rmsf.sh" --state "$state" "${ow[@]}" "${extra[@]}"

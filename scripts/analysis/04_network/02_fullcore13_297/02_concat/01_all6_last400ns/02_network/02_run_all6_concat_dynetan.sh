#!/usr/bin/env bash
# Run a pilot or all 16 full-core CR1--CR6 concatenated networks on Insurgent.
set -Eeuo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/../00_settings.sh"
###############################################################################
# SETTINGS -- edit only these lines for execution.
RUN_MODE="${RUN_MODE_OVERRIDE:-audit}"       # audit = print plan; run = execute incomplete cases
RUN_SCOPE="${RUN_SCOPE_OVERRIDE:-pilot}"     # pilot = WT apo+holo; all = all 16 state/variant systems
MAX_PARALLEL="${MAX_PARALLEL_OVERRIDE:-2}"   # each system uses 4 CPU cores
###############################################################################
METHOD=$(network_method_tag)
RESULT_ROOT="${NETWORK_ROOT}/data/analysis/04_network/02_fullcore13_297/02_concat/01_all6_last400ns"
INPUT_ROOT="${RESULT_ROOT}/01_inputs"; NETWORK_OUT="${RESULT_ROOT}/02_network/${METHOD}"; LOG_ROOT="${RESULT_ROOT}/logs/${METHOD}"
RUNNER="${SCRIPT_DIR}/01_run_all6_concat_dynetan.py"; EXPORTER="${NETWORK_ROOT}/scripts/analysis/04_network/02_fullcore13_297/01_replica/02_network/02_run_replica_dynetan.py"
[[ ${RUN_MODE} == audit || ${RUN_MODE} == run ]] || { echo "ERROR: RUN_MODE must be audit or run" >&2; exit 2; }
[[ ${RUN_SCOPE} == pilot || ${RUN_SCOPE} == all ]] || { echo "ERROR: RUN_SCOPE must be pilot or all" >&2; exit 2; }
[[ -d ${MD_DATA_ROOT} && -x ${DYNETAN_PYTHON} && -s ${EXPORTER} ]] || { echo "ERROR: run on Insurgent with the DyNetAn environment available" >&2; exit 2; }
states=(apo holo); variants=(01_WT 02_L119R 03_D193H 04_G202E 05_Q219K 06_C291Y 07_S240T 08_H254R); cases=()
complete(){ local b="$NETWORK_OUT/$1/$2"; [[ -s "$b/01_network_qc.tsv" && -s "$b/02_all6_concat.dcd" && -s "$b/03_dynetan_native/dnaData.hf" && -s "$b/04_project_exports/bottleneck_centrality_all_nodes.csv" ]] && grep -q $'^status\tPASS$' "$b/01_network_qc.tsv"; }
for s in "${states[@]}"; do for v in "${variants[@]}"; do [[ ${RUN_SCOPE} == all || $v == 01_WT ]] && complete "$s" "$v" || { [[ ${RUN_SCOPE} == all || $v == 01_WT ]] && cases+=("$s" "$v"); }; done; done
echo "Method: ${METHOD}"; echo "Input: CR1--CR6; 100--500 ns; 500 frames/replica = 3000 frames/system"; echo "Scope: ${RUN_SCOPE}; incomplete systems: $((${#cases[@]}/2))"; echo "Output: ${NETWORK_OUT}"; echo "Logs: ${LOG_ROOT}"; echo "Concurrency: ${MAX_PARALLEL} systems x 4 CPU cores"
[[ ${RUN_MODE} == run ]] || { echo "AUDIT only. Change RUN_MODE to run after reviewing this plan."; exit 0; }; ((${#cases[@]})) || { echo "All requested systems already PASS."; exit 0; }; mkdir -p "$LOG_ROOT"
run_case(){
    local s=$1
    local v=$2
    local log="$LOG_ROOT/${s}_${v}.log"
    echo "START $s/$v $(date --iso-8601=seconds)" | tee -a "$log"
    "$DYNETAN_PYTHON" "$RUNNER" --md-data-root "$MD_DATA_ROOT" --input-root "$INPUT_ROOT" --network-root "$NETWORK_OUT" --replica-runner "$EXPORTER" --state "$s" --variant "$v" --analysis-start-ns "$ANALYSIS_START_NS" --analysis-end-ns "$ANALYSIS_END_NS" --frames-per-replica "$FRAMES_PER_REPLICA" --contact-cutoff-a "$CONTACT_CUTOFF_A" --contact-persistence "$CONTACT_PERSISTENCE" --node-selection "$NODE_SELECTION" --ncores 4 >> "$log" 2>&1
    echo "PASS $s/$v $(date --iso-8601=seconds)" | tee -a "$log"
}
export -f run_case; export DYNETAN_PYTHON RUNNER MD_DATA_ROOT INPUT_ROOT NETWORK_OUT EXPORTER LOG_ROOT ANALYSIS_START_NS ANALYSIS_END_NS FRAMES_PER_REPLICA CONTACT_CUTOFF_A CONTACT_PERSISTENCE NODE_SELECTION
printf '%s\n' "${cases[@]}" | xargs -n 2 -P "$MAX_PARALLEL" bash -c 'run_case "$@"' _

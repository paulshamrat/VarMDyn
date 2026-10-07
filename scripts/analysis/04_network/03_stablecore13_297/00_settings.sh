#!/usr/bin/env bash
# SETTINGS -- stable-core network analyses only.
# This branch reuses the finalized stable-core triplet selection. DyNetAn uses
# 300--500 ns from each selected replica unless a sensitivity script states
# otherwise.

# Portable runtime paths. Source config/paths.sh or export these variables first.
_vmd_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while [[ ! -f "${_vmd_root}/AGENTS.md" || ! -d "${_vmd_root}/scripts" ]]; do
    [[ "${_vmd_root}" != / ]] || { echo "Cannot locate VarMDyn root" >&2; return 2; }
    _vmd_root="$(dirname "${_vmd_root}")"
done
REPO="${VARMDYN_ROOT:-${_vmd_root}}"
NETWORK_ROOT="${REPO}"
MD_DATA_ROOT="${VARMDYN_MD_SOURCE_ROOT:-}"
SIM_ROOT="${MD_DATA_ROOT}"
DATA_LOCATION=external
DYNETAN_PYTHON="${VARMDYN_DYNETAN_PYTHON:-python3}"

# Authoritative 300--500 ns stable-core selection; do not edit triplets here.
SELECTION_REGISTER="${NETWORK_ROOT}/data/analysis/02_metrics/03_stablecore13_297/03_triplet_selection/03_primary_selection/03_primary_triplet_selection.tsv"

# Completed all-six, 0--500 ns replica-level DyNetAn exports used solely to
# prototype the selected-triplet table layout before a new late-window run.
METHOD="t0-500_w1_f500_c4p5_p75_core13-297"
ALL_REPLICA_NODE_TABLE="${NETWORK_ROOT}/data/analysis/04_network/02_fullcore13_297/01_replica/03_tables/${METHOD}/01_replica_network_tables/01_all_replica_metrics/01_bottleneck_centrality_all_replicas.tsv"
COMPLETED_CASES_TABLE="${NETWORK_ROOT}/data/analysis/04_network/02_fullcore13_297/01_replica/03_tables/${METHOD}/01_replica_network_tables/01_all_replica_metrics/00_completed_cases.tsv"

STABLECORE_NETWORK_RESULT_ROOT="${NETWORK_ROOT}/data/analysis/04_network/03_stablecore13_297"
ALL6_REPLICA_RESULT_ROOT="${STABLECORE_NETWORK_RESULT_ROOT}/01_all6_replica_networks"
SELECTED_TRIPLET_RESULT_ROOT="${STABLECORE_NETWORK_RESULT_ROOT}/02_selected_triplet_concat"
SENSITIVITY_RESULT_ROOT="${STABLECORE_NETWORK_RESULT_ROOT}/03_sensitivity"
EXPLORATORY_RESULT_ROOT="${STABLECORE_NETWORK_RESULT_ROOT}/04_exploratory_metrics"

# Primary settings for the real selected-triplet exploration.
ANALYSIS_START_NS=300
ANALYSIS_END_NS=500
FRAMES_PER_REPLICA=500
NUM_WINDOWS=1
CONTACT_CUTOFF_A=4.5
CONTACT_PERSISTENCE=0.75
SPATIAL_TOLERANCE_A=5.0
REPLICAS_PER_SYSTEM=3
SYSTEM_SUPPORT_MIN=2

# Protein-heavy-atom nodes in the kinase domain. This exactly matches the
# completed all-six core13-297 replica workflow.
NODE_SELECTION='segid PROT and resid 13:297 and not (name H* or name [123]H*)'

# Insurgent-only execution locations. The authoritative code remains in the
# repository; only this mirrored copy performs the local calculation.
# Portable runtime paths. Source config/paths.sh or export these variables first.
_vmd_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while [[ ! -f "${_vmd_root}/AGENTS.md" || ! -d "${_vmd_root}/scripts" ]]; do
    [[ "${_vmd_root}" != / ]] || { echo "Cannot locate VarMDyn root" >&2; return 2; }
    _vmd_root="$(dirname "${_vmd_root}")"
done
REPO="${VARMDYN_ROOT:-${_vmd_root}}"
NETWORK_ROOT="${REPO}"
MD_DATA_ROOT="${VARMDYN_MD_SOURCE_ROOT:-}"
SIM_ROOT="${MD_DATA_ROOT}"
DATA_LOCATION=external
DYNETAN_PYTHON="${VARMDYN_DYNETAN_PYTHON:-python3}"

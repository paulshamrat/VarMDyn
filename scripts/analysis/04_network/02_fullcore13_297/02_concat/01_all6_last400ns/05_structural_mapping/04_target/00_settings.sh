#!/usr/bin/env bash
# Settings for 04_target: 100% ChimeraX 6-Panel State-Paired Target Figure
set -Eeuo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
STRUCTURAL_MAPPING_SCRIPTS=$(cd "${SCRIPT_DIR}/.." && pwd)
ANALYSIS_REPRO_ROOT=$(cd "${STRUCTURAL_MAPPING_SCRIPTS}/../../../../../../" && pwd)
RESULTS_ROOT="${ANALYSIS_REPRO_ROOT}/results/04_network/02_fullcore13_297/02_concat/01_all6_last400ns/05_structural_mapping"
STRUCTURAL_MAPPING_INPUTS="${RESULTS_ROOT}/01_prepared_inputs"
TARGET_OUTPUT_ROOT="${RESULTS_ROOT}/04_target"

# Reused canonical equilibrium structures from 01_prepared_inputs
APO_EQUILIBRIUM_PDB="${STRUCTURAL_MAPPING_INPUTS}/04_apo_wt_equilibrium.pdb"
HOLO_EQUILIBRIUM_PDB="${STRUCTURAL_MAPPING_INPUTS}/05_holo_wt_equilibrium.pdb"

# Target active site residues & color groupings
# Gain / dark orange: 93 (E93), 143 (I143)
# Lost / blue: 170 (E170), 188 (Y188), 190 (K190)
# Green: ATP/Mg2+ (Residues 304/305 in the Holo PDB)
TARGET_RESIDUES="93,143,170,188,190"
BLUE_RESIDUES="170,188,190"
ORANGE_RESIDUES="93,143"

# Canonical locked kinase camera view matrix (shared across all six panels)
CAMERA_MATRIX="-0.31169,0.79727,0.51692,212.61,-0.87489,-0.028557,-0.48348,-118.97,-0.37071,-0.60294,0.70642,283.72 models #1,1,0,0,0,0,1,0,0,0,0,1,0"
CAMERA_ZOOM="0.75"

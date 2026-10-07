#!/usr/bin/env bash
# Build pipeline for 04_target: 100% ChimeraX 6-Panel State-Paired Figure
set -Eeuo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "${SCRIPT_DIR}/00_settings.sh"

echo "============================================================"
echo " STEP 1: Rendering All 6 Panels via ChimeraX..."
echo "============================================================"
python3 "${SCRIPT_DIR}/05_render_all_panels.py"

echo ""
echo "============================================================"
echo " STEP 2: Assembling 7.00-inch 300 DPI Composite Figure..."
echo "============================================================"
python3 "${SCRIPT_DIR}/06_assemble_target_figure.py"

echo ""
echo "============================================================"
echo " SUCCESS: All deliverables built in ${TARGET_OUTPUT_ROOT}"
echo "============================================================"
ls -lh "${TARGET_OUTPUT_ROOT}"

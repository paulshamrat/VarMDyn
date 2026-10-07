#!/usr/bin/env python3
"""Regenerate the validated legacy A--B structure panels for stable-core C--F."""

from __future__ import annotations

import importlib.util
import os
import base64
import re
from pathlib import Path


ANALYSIS_ROOT = (
    Path(
        __import__("os").environ.get(
            "VARMDYN_DATA_ROOT",
            str(
                next(
                    p
                    for p in Path(__file__).resolve().parents
                    if (p / "AGENTS.md").is_file()
                )
                / "data"
            ),
        )
    )
    / "analysis"
)
LEGACY = (
    next(p for p in Path(__file__).resolve().parents if (p / "AGENTS.md").is_file())
    / "scripts"
    / "analysis"
    / "03_dynamics"
    / "00_legacy_cr1_cr3"
    / "03_structure_panels"
    / "01_build_structure_panels.py"
)
OUT_DIR = ANALYSIS_ROOT / "03_dynamics" / "03_stablecore13_297" / "03_structure_panels"


def add_benign_sites(module) -> None:
    """Extend only the stable-core copy of the legacy structural context."""
    module.VARIANT_RESI = "119+193+202+219+240+254+291"
    module.FIG2B_BASE_STYLE += """
set_color stable_s240, [0.090, 0.745, 0.810]
set_color stable_h254, [0.737, 0.741, 0.133]
"""
    module.VARIANT_COLORS_PYMOL.update({"240": "stable_s240", "254": "stable_h254"})
    module.VARIANT_SITE_COLORS.update(
        {
            "S240": (23, 190, 207),
            "H254": (188, 189, 34),
        }
    )
    module.SITE_COLORS.update(module.VARIANT_SITE_COLORS)

    # Projected source locations in the validated Figure-1B camera. The text
    # and leader paths below are initial placements and remain editable in SVG.
    for state in ("apo", "holo"):
        module.SOURCE_POINTS_APPROX["context"][state].update(
            {
                "S240": (800, 920),
                "H254": (622, 1071),
            }
        )
        module.CALLOUT_LAYOUT["context"][state].update(
            {
                "S240": {"text_pos": (760, 790), "line_start": (820, 790)},
                "H254": {"text_pos": (350, 1100), "line_start": (500, 1100)},
            }
        )

    module.MASTER_SHARED_CALLOUTS.update(
        {
            "S240": (790.0, 690.0),
            "H254": (350.0, 980.0),
        }
    )
    module.MASTER_SHARED_LEADER_PATHS.extend(
        [
            "M 850,700 L 835,697",
            "M 520,950 L 650,810",
        ]
    )


def assemble_from_exact_legacy_svg(module) -> None:
    """Keep legacy content fixed while making room for the lower benign H254 site."""
    legacy_svg = (
        ANALYSIS_ROOT
        / "03_dynamics"
        / "00_legacy_cr1_cr3"
        / "03_structure_panels"
        / "02_structure_context_panels.svg"
    )
    text = legacy_svg.read_text(encoding="utf-8")
    payloads = [
        module.RAW_PNGS[("context", "apo")],
        module.RAW_PNGS[("context", "holo")],
    ]
    encoded = [base64.b64encode(path.read_bytes()).decode("ascii") for path in payloads]
    image_index = 0

    def replace_image(match: re.Match[str]) -> str:
        nonlocal image_index
        if image_index >= len(encoded):
            raise RuntimeError(
                "Legacy SVG has more embedded structural images than expected"
            )
        replacement = match.group(1) + encoded[image_index]
        image_index += 1
        return replacement

    text, replacements = re.subn(
        r'(xlink:href="data:image/png;base64,)[^"]+', replace_image, text
    )
    if replacements != 2 or image_index != 2:
        raise RuntimeError(
            f"Expected two legacy structural images, replaced {replacements}"
        )

    # H254 is lower in the rendered stable-core structure than any legacy
    # pathogenic site.  The legacy panel clips each structural image at y=1228,
    # which truncates that benign stick.  Extend only this stable-core canvas
    # and its two image clips by 100 SVG units; all inherited legacy elements
    # retain their original coordinates and styling.
    text, canvas_replacements = re.subn(
        r'<svg width="3920" height="1252" viewBox="0 0 3920 1252"',
        '<svg width="3920" height="1352" viewBox="0 0 3920 1352"',
        text,
        count=1,
    )
    text, clip_replacements = re.subn(
        r'(<rect x="(?:0|1960)" y="28" width="1960" height=")1200(" />)',
        r"\g<1>1300\g<2>",
        text,
    )
    if canvas_replacements != 1 or clip_replacements != 2:
        raise RuntimeError(
            "Could not extend the stable-core benign H254 crop region "
            f"(canvas={canvas_replacements}, clips={clip_replacements})"
        )

    # These are the only new SVG elements. Existing legacy text and leaders
    # are untouched byte-for-byte. The new elements remain editable.
    benign = """  <text x=\"790.0\" y=\"690.0\" font-family=\"Arial\" font-size=\"64\" fill=\"black\">S240</text>
  <text x=\"2750.0\" y=\"690.0\" font-family=\"Arial\" font-size=\"64\" fill=\"black\">S240</text>
  <text x=\"350.0\" y=\"980.0\" font-family=\"Arial\" font-size=\"64\" fill=\"black\">H254</text>
  <text x=\"2310.0\" y=\"980.0\" font-family=\"Arial\" font-size=\"64\" fill=\"black\">H254</text>
  <path style=\"fill:none;stroke:#000000;stroke-width:3.77953\" d=\"M 850,700 L 835,697\"/>
  <path style=\"fill:none;stroke:#000000;stroke-width:3.77953\" d=\"M 850,700 L 835,697\" transform=\"translate(1960,0)\"/>
  <path style=\"fill:none;stroke:#000000;stroke-width:3.77953\" d=\"M 520,950 L 650,810\"/>
  <path style=\"fill:none;stroke:#000000;stroke-width:3.77953\" d=\"M 520,950 L 650,810\" transform=\"translate(1960,0)\"/>
"""
    module.SVG_OUT.write_text(
        text.replace("</svg>", benign + "</svg>"), encoding="utf-8"
    )


def main() -> None:
    spec = importlib.util.spec_from_file_location("legacy_structure_panels", LEGACY)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load legacy structure builder: {LEGACY}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Preserve the proven scene, labels, editable SVG construction, and export
    # settings exactly; only redirect generated files to the stable-core branch.
    module.ANALYSIS_ROOT = ANALYSIS_ROOT
    module.FIGURE_DIR = ANALYSIS_ROOT
    module.INPUT_DIR = ANALYSIS_ROOT / "inputs" / "03_dynamics" / "00_shared"
    module.STRUCTURE_PDB = (
        module.INPUT_DIR / "01_source_structure" / "cdl.com.wat.leap.pdb"
    )
    module.OUT_DIR = OUT_DIR
    module.SOURCE_PANEL_DIR = OUT_DIR / "01_source_renders"
    module.WORK_DIR = module.SOURCE_PANEL_DIR
    module.SVG_OUT = OUT_DIR / "02_structure_context_panels.svg"
    module.PNG_OUT = OUT_DIR / "03_structure_context_panels.png"
    module.PDF_OUT = OUT_DIR / "04_structure_context_panels.pdf"
    module.RAW_PNGS = {
        ("context", "apo"): module.WORK_DIR / "01_panel_apo_context_raw.png",
        ("context", "holo"): module.WORK_DIR / "02_panel_holo_context_raw.png",
    }
    add_benign_sites(module)
    # Retain legacy raw rendering, but use the exact legacy SVG as the fixed
    # layout source. Existing valid source renders are reused unless forced.
    force_render = os.environ.get("FORCE_RENDER", "no").lower() == "yes"
    reuse_raw = not force_render and all(
        path.exists() for path in module.RAW_PNGS.values()
    )
    if not reuse_raw:
        module.render_raw_panels()
    assemble_from_exact_legacy_svg(module)
    module.export_svg()
    module.verify_exports()


if __name__ == "__main__":
    main()

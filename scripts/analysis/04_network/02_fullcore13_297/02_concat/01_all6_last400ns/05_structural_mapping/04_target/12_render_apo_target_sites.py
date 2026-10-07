#!/usr/bin/env python3
"""Render the three apo target-site-only molecular panels in ChimeraX."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CXC_FILES = (
    "09_render_apo_target_sites_cartoon.cxc",
    "10_render_apo_target_sites_surface.cxc",
    "11_render_apo_target_sites_surface_back.cxc",
)


def main() -> None:
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":0")
    env.setdefault("WAYLAND_DISPLAY", "wayland-0")
    env.setdefault("XDG_RUNTIME_DIR", "/run/user/1000")
    chimerax = Path("/usr/bin/chimerax")
    if not chimerax.exists():
        raise FileNotFoundError(f"ChimeraX executable not found: {chimerax}")
    for name in CXC_FILES:
        result = subprocess.run(
            [str(chimerax), "--exit", str(SCRIPT_DIR / name)], env=env
        )
        if result.returncode:
            sys.exit(result.returncode)


if __name__ == "__main__":
    main()

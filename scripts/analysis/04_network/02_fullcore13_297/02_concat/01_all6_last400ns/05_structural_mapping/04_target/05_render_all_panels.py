#!/usr/bin/env python3
"""Execute all 6 ChimeraX target rendering scripts with OpenGL hardware display context."""

from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CXC_FILES = [
    "01_render_apo_cartoon.cxc",
    "02_render_apo_surface.cxc",
    "03_render_holo_cartoon.cxc",
    "04_render_holo_surface.cxc",
    "05_render_apo_surface_back.cxc",
    "06_render_holo_surface_back.cxc",
]


def main() -> None:
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":0")
    env.setdefault("WAYLAND_DISPLAY", "wayland-0")
    env.setdefault("XDG_RUNTIME_DIR", "/run/user/1000")

    chimerax_bin = "/usr/bin/chimerax"
    if not Path(chimerax_bin).exists():
        raise FileNotFoundError(f"ChimeraX executable not found at {chimerax_bin}")

    for cxc_name in CXC_FILES:
        cxc_path = SCRIPT_DIR / cxc_name
        print(f"--> Rendering {cxc_name} via ChimeraX...")
        cmd = [chimerax_bin, "--exit", str(cxc_path)]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERROR rendering {cxc_name}:\n{result.stderr}\n{result.stdout}")
            sys.exit(result.returncode)
        print(f"    SUCCESS: Rendered {cxc_name}")


if __name__ == "__main__":
    main()

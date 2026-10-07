#!/usr/bin/env python3
"""Render a LEaP input with charge-aware neutralization commands."""

from __future__ import annotations

import argparse
import math
import re
from pathlib import Path


CHARGE_RE = re.compile(r"Total unperturbed charge:\s*([-+0-9.eE]+)")
ION_LINE_RE = re.compile(r"^\s*addIons2\s+COM2\s+(Na\+|Cl-)\s+0\s*$")
PLACEHOLDER = "# VARMDYN_ION_COMMANDS"


def parse_charge(path: Path) -> float:
    text = path.read_text(encoding="utf-8", errors="ignore")
    matches = CHARGE_RE.findall(text)
    if not matches:
        raise SystemExit(f"no LEaP charge line found in {path}")
    return float(matches[-1])


def ion_commands(charge: float) -> list[str]:
    rounded = int(round(charge))
    if not math.isclose(charge, rounded, abs_tol=0.01):
        raise SystemExit(f"system charge is not near an integer: {charge:.6f}")
    if rounded > 0:
        return [f"addIons2 COM2 Cl- {rounded}"]
    if rounded < 0:
        return [f"addIons2 COM2 Na+ {abs(rounded)}"]
    return ["# VARMDYN: no neutralizing ions required; system charge is 0"]


def render_template(template: Path, out: Path, commands: list[str]) -> None:
    lines = template.read_text(encoding="utf-8").splitlines()
    rendered: list[str] = []
    inserted = False
    for line in lines:
        if PLACEHOLDER in line:
            rendered.extend(commands)
            inserted = True
            continue
        if ION_LINE_RE.match(line):
            if not inserted:
                rendered.extend(commands)
                inserted = True
            continue
        rendered.append(line)
    if not inserted:
        raise SystemExit(
            f"no {PLACEHOLDER!r} placeholder or neutralization addIons2 lines found in {template}"
        )
    out.write_text("\n".join(rendered) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--charge-log", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    charge = parse_charge(args.charge_log)
    commands = ion_commands(charge)
    render_template(args.template, args.out, commands)
    args.report.write_text(
        "\n".join(
            [
                f"charge: {charge:.6f}",
                "neutralization_commands:",
                *(f"  - {command}" for command in commands),
                "",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

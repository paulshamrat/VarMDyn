#!/usr/bin/env python3
"""Summarize LEaP neutralization for an MD system."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path


COMMAND_RE = re.compile(r"\baddIons2\s+\S+\s+(\S+)\s+(\S+)")
ADDING_RE = re.compile(r"Adding\s+(\d+)\s+counter ions?", re.IGNORECASE)
UNPERTURBED_RE = re.compile(
    r"The unperturbed charge of the unit\s+\(([-+0-9.eE]+)\)\s+is not zero"
)
SOLUTE_RE = re.compile(r"Total solute charge:\s*([-+0-9.eE]+)")
TOTAL_UNPERTURBED_RE = re.compile(r"Total unperturbed charge:\s*([-+0-9.eE]+)")
CHARGE_WORD_RE = re.compile(r"\bcharge\b", re.IGNORECASE)

ION_NAMES = {
    "NA": "Na+",
    "Na": "Na+",
    "Na+": "Na+",
    "CL": "Cl-",
    "Cl": "Cl-",
    "Cl-": "Cl-",
}
ION_CHARGE = {"Na+": 1.0, "Cl-": -1.0}


def normalize_ion(name: str) -> str:
    return ION_NAMES.get(name.strip(), name.strip())


def parse_log(path: Path) -> tuple[list[float], list[dict[str, str | int]]]:
    charges: list[float] = []
    additions: list[dict[str, str | int]] = []
    current: dict[str, str | int] | None = None

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if match := UNPERTURBED_RE.search(line):
            charges.append(float(match.group(1)))
        if match := TOTAL_UNPERTURBED_RE.search(line):
            charges.append(float(match.group(1)))
        if match := SOLUTE_RE.search(line):
            charges.append(float(match.group(1)))
        if match := COMMAND_RE.search(line):
            current = {
                "ion": normalize_ion(match.group(1)),
                "requested": match.group(2),
                "added": "unknown",
            }
            additions.append(current)
            continue
        if current is not None and (match := ADDING_RE.search(line)):
            current["added"] = int(match.group(1))
            current = None

    return charges, additions


def count_pdb_ions(path: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    residues: set[tuple[str, str, str]] = set()
    if not path.is_file():
        return counts
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        resname = normalize_ion(line[17:20].strip())
        if resname not in ION_CHARGE:
            continue
        chain = line[21:22].strip()
        resid = line[22:26].strip()
        icode = line[26:27].strip()
        residues.add((resname, chain, resid + icode))
    for resname, _chain, _resid in residues:
        counts[resname] += 1
    return counts


def estimate_final_charge(start_charge: float | None, ion_counts: Counter[str]) -> float | None:
    if start_charge is None:
        return None
    return start_charge + sum(ION_CHARGE[ion] * count for ion, count in ion_counts.items())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--pdb", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--state", default="unknown")
    parser.add_argument("--variant", default="unknown")
    args = parser.parse_args()

    charges, additions = parse_log(args.log)
    pdb_counts = count_pdb_ions(args.pdb)
    start_charge = charges[0] if charges else None
    last_reported_charge = charges[-1] if charges else None
    estimated_final = estimate_final_charge(start_charge, pdb_counts)

    lines = [
        f"state: {args.state}",
        f"variant: {args.variant}",
        f"log: {args.log}",
        f"pdb: {args.pdb}",
        "",
        "reported_charges:",
    ]
    if charges:
        lines.extend(f"  - {value:.6f}" for value in charges)
    else:
        lines.append("  - not found")

    lines.extend(["", "addIons2_commands:"])
    if additions:
        for item in additions:
            lines.append(
                f"  - ion: {item['ion']}; requested: {item['requested']}; added: {item['added']}"
            )
    else:
        lines.append("  - not found")

    lines.extend(["", "ions_in_final_pdb:"])
    if pdb_counts:
        for ion in sorted(pdb_counts):
            lines.append(f"  - {ion}: {pdb_counts[ion]}")
    else:
        lines.append("  - none detected")

    lines.extend(
        [
            "",
            "sanity:",
            f"  first_reported_charge: {start_charge:.6f}" if start_charge is not None else "  first_reported_charge: not found",
            f"  last_reported_charge: {last_reported_charge:.6f}" if last_reported_charge is not None else "  last_reported_charge: not found",
            f"  estimated_final_charge_from_pdb_ions: {estimated_final:.6f}" if estimated_final is not None else "  estimated_final_charge_from_pdb_ions: not available",
        ]
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

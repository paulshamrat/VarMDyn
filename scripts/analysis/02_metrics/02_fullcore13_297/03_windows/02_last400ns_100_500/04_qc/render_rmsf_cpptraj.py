#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(
        description="Render PASS1 or PASS2 CPPTRAJ input for ensemble RMSF."
    )
    p.add_argument("--template", required=True, type=Path)
    p.add_argument(
        "--pass", dest="pass_name", required=True, choices=["pass1", "pass2"]
    )
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--reference", type=Path)
    p.add_argument("--average-pdb", required=True, type=Path)
    p.add_argument("--fit-mask", required=True)
    p.add_argument("--rmsf-mask")
    p.add_argument("--fit-rmsd", type=Path)
    p.add_argument("--rmsf-dat", type=Path)
    p.add_argument(
        "--trajin-file",
        required=True,
        type=Path,
        help="Text file containing one or more fully rendered trajin lines.",
    )
    return p.parse_args()


def extract_pass(text: str, pass_name: str) -> str:
    marker = "# === PASS2 ==="
    if marker not in text:
        raise ValueError(f"Missing required marker: {marker}")

    pass1, pass2 = text.split(marker, 1)
    if pass_name == "pass1":
        return pass1
    return pass2


def require(value, name):
    if value is None:
        raise ValueError(f"{name} is required for this pass.")
    return value


def main():
    a = parse_args()

    text = a.template.read_text()
    text = extract_pass(text, a.pass_name)

    trajin = a.trajin_file.read_text().rstrip()

    replacements = {
        "{{TRAJIN}}": trajin,
        "{{FIT_MASK}}": a.fit_mask,
        "{{AVERAGE_PDB}}": str(a.average_pdb),
    }

    if a.pass_name == "pass1":
        replacements["{{REFERENCE}}"] = str(require(a.reference, "--reference"))
    else:
        replacements["{{FIT_RMSD}}"] = str(require(a.fit_rmsd, "--fit-rmsd"))
        replacements["{{RMSF_DAT}}"] = str(require(a.rmsf_dat, "--rmsf-dat"))
        replacements["{{RMSF_MASK}}"] = require(a.rmsf_mask, "--rmsf-mask")

    for key, value in replacements.items():
        text = text.replace(key, value)

    # Guard against accidentally emitting unresolved placeholders or shell syntax.
    if "{{" in text or "}}" in text:
        raise ValueError(
            "Unresolved template placeholder remains in rendered CPPTRAJ input."
        )
    if (
        "FIT_MASK=" in text
        or "RMSF_MASK=" in text
        or "${FIT_MASK}" in text
        or "${RMSF_MASK}" in text
    ):
        raise ValueError("Shell-style mask assignment leaked into CPPTRAJ input.")

    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(text.rstrip() + "\n")


if __name__ == "__main__":
    main()

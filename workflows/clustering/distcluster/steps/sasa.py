#!/usr/bin/env python3
"""Run PyMOL headless and export residue-level relative SASA."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional

SASA_LINE_RE = re.compile(r"^/[^\s]+\s+\d{1,3}%")


def _which_or_fail(executable: Optional[str] = None) -> str:
    name = executable or "pymol"
    if "/" in name:
        path = Path(name)
        if not path.exists():
            raise RuntimeError(f"Configured PyMOL executable does not exist: '{name}'")
        return str(path)
    # Prefer the PyMOL binary from the active Python environment.
    if executable is None:
        env_candidate = Path(sys.executable).resolve().parent / "pymol"
        if env_candidate.exists():
            return str(env_candidate)

    path = shutil.which(name)
    if not path:
        raise RuntimeError(
            f"Required executable not found on PATH: '{name}'. "
            "Activate the environment where PyMOL is installed."
        )
    return path


def build_pml(
    pdb_path: Path,
    chain: Optional[str],
    selection: Optional[str],
    legacy_mode: bool = False,
) -> str:
    """Return a temporary PML script for `get_sasa_relative`."""
    if selection:
        sel = selection
    elif legacy_mode:
        # Legacy workflow used: get_sasa_relative polymer
        sel = "polymer"
    elif chain:
        sel = f"(polymer.protein) and chain {chain}"
    else:
        sel = "polymer.protein"

    return "\n".join(
        [
            "reinitialize",
            f"load {pdb_path.resolve()}, target",
            "remove solvent",
            f"select target_sel, {sel}",
            "get_sasa_relative target_sel",
            "quit",
            "",
        ]
    )


def extract_sasa_lines(pymol_stdout: str) -> list[str]:
    """Extract table lines emitted by PyMOL `get_sasa_relative`."""
    lines: list[str] = []
    for raw in pymol_stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("/") and SASA_LINE_RE.match(line):
            lines.append(line)
    return lines



def _run_sasa_via_pymol_python(pdb: Path, selection: str, python_executable: str) -> tuple[int, str, str]:
    """Return residue-level SASA lines using the PyMOL Python API."""
    script = """
from pymol import cmd

pdb = {pdb_path!r}
selection = {selection!r}
cmd.reinitialize()
cmd.load(pdb, "target")
cmd.remove("solvent")
cmd.select("target_sel", selection)
values = cmd.get_sasa_relative("target_sel", var="b", quiet=1)
resn_by_key = {{}}
for atom in cmd.get_model("target_sel and name CA").atom:
    resn_by_key[(atom.chain, atom.resi)] = atom.resn
for atom in cmd.get_model("target_sel").atom:
    resn_by_key.setdefault((atom.chain, atom.resi), atom.resn)

def sort_key(item):
    (_model, _segi, chain, resi), _value = item
    try:
        num = int(str(resi).strip())
    except ValueError:
        num = 10**9
    return (chain, num, str(resi))

for (_model, _segi, chain, resi), value in sorted(values.items(), key=sort_key):
    resn = resn_by_key.get((chain, resi), "UNK")
    pct = round(float(value) * 100.0)
    print(f"/target//{{chain}}/{{resn}}`{{resi:<5}} {{pct:3.0f}}% |")
""".format(pdb_path=str(pdb.resolve()), selection=selection)
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "sasa_api.py"
        script_path.write_text(script, encoding="utf-8")
        proc = subprocess.run([python_executable, str(script_path)], capture_output=True, text=True, check=False)
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def run_sasa(
    pdb: Path,
    out_txt: Path,
    chain: Optional[str] = None,
    selection: Optional[str] = None,
    legacy_mode: bool = False,
    pymol_executable: Optional[str] = None,
    min_lines: int = 10,
    dry_run: bool = False,
    log: Callable[[str], None] = print,
) -> Path:
    """Run PyMOL and write a residue-level relative SASA text file."""
    pdb = Path(pdb)
    out_txt = Path(out_txt)
    out_txt.parent.mkdir(parents=True, exist_ok=True)
    pml_text = build_pml(pdb_path=pdb, chain=chain, selection=selection, legacy_mode=legacy_mode)

    if selection:
        sel = selection
    elif legacy_mode:
        sel = "polymer"
    elif chain:
        sel = f"(polymer.protein) and chain {chain}"
    else:
        sel = "polymer.protein"

    if dry_run:
        pymol_path = pymol_executable or sys.executable
        log(f"[DRY-RUN] Would run PyMOL SASA through: {pymol_path}")
        log(f"[DRY-RUN] Would read PDB: {pdb}")
        log(f"[DRY-RUN] Would write SASA file: {out_txt}")
        return out_txt

    if not pdb.exists():
        raise FileNotFoundError(f"Missing input PDB: {pdb}")

    if pymol_executable is None:
        log(f"[INFO] Running PyMOL Python API with: {sys.executable}")
        returncode, stdout, stderr = _run_sasa_via_pymol_python(
            pdb=pdb,
            selection=sel,
            python_executable=sys.executable,
        )
        if returncode != 0:
            raise RuntimeError(
                "PyMOL Python API failed while computing SASA.\n"
                f"Return code: {returncode}\n"
                f"STDOUT (first 500 chars):\n{stdout[:500]}\n"
                f"STDERR (first 500 chars):\n{stderr[:500]}"
            )
        sasa_lines = extract_sasa_lines(stdout)
    else:
        pymol = _which_or_fail(pymol_executable)
        with tempfile.TemporaryDirectory() as tmpdir:
            pml_path = Path(tmpdir) / "run_sasa.pml"
            pml_path.write_text(pml_text, encoding="utf-8")
            cmd = [pymol, "-cq", str(pml_path)]
            log(f"[INFO] Running headless PyMOL: {' '.join(cmd)}")
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                raise RuntimeError(
                    "PyMOL failed while computing SASA.\n"
                    f"Return code: {proc.returncode}\n"
                    f"STDOUT (first 500 chars):\n{(proc.stdout or '')[:500]}\n"
                    f"STDERR (first 500 chars):\n{(proc.stderr or '')[:500]}"
                )
        sasa_lines = extract_sasa_lines(proc.stdout or "")

    out_txt.write_text(
        "# PyMOL get_sasa_relative output\n" + "\n".join(sasa_lines) + "\n",
        encoding="utf-8",
    )

    if len(sasa_lines) < min_lines:
        raise RuntimeError(
            f"SASA output has too few residue lines ({len(sasa_lines)} < {min_lines}). "
            "Check selection/chain and input structure."
        )

    log(f"[OK] Wrote SASA file: {out_txt}")
    log(f"[OK] Residue lines captured: {len(sasa_lines)}")
    log("[INFO] First 10 lines:")
    for line in sasa_lines[:10]:
        log(f"  {line}")

    return out_txt

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compute residue-level relative SASA with headless PyMOL."
    )
    parser.add_argument("--pdb", required=True, help="Input PDB file path")
    parser.add_argument("--out", required=True, help="Output SASA text file path")
    parser.add_argument("--chain", default=None, help="Optional chain ID (e.g. A)")
    parser.add_argument(
        "--selection",
        default=None,
        help="Optional explicit PyMOL selection; overrides --chain",
    )
    parser.add_argument(
        "--legacy-mode",
        action="store_true",
        help="Use legacy-style PyMOL selection (get_sasa_relative polymer).",
    )
    parser.add_argument(
        "--pymol-executable",
        default=None,
        help="Optional explicit PyMOL executable path/name.",
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=10,
        help="Minimum residue lines required for a successful run",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without running")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    run_sasa(
        pdb=Path(args.pdb),
        out_txt=Path(args.out),
        chain=args.chain,
        selection=args.selection,
        legacy_mode=args.legacy_mode,
        pymol_executable=args.pymol_executable,
        min_lines=args.min_lines,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Legacy-friendly headless SASA text generation using the refactored engine.

This writes a PyMOL SASA text file in the same residue-line style expected by
legacy SASA parser, while running fully headless from command line.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow execution from either repo root or clustering/ directory.
THIS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = THIS_DIR.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from distcluster.steps.sasa import run_sasa


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate PyMOL SASA text (legacy parser compatible) in headless mode."
    )
    parser.add_argument("--pdb", required=True, help="Input PDB path")
    parser.add_argument("--out", required=True, help="Output SASA text file path")
    parser.add_argument("--chain", default="A", help="Chain ID (default: A)")
    parser.add_argument(
        "--selection",
        default=None,
        help="Optional explicit PyMOL selection; overrides --chain",
    )
    parser.add_argument(
        "--min-lines",
        type=int,
        default=10,
        help="Minimum residue lines required for success",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    run_sasa(
        pdb=Path(args.pdb),
        out_txt=Path(args.out),
        chain=args.chain,
        selection=args.selection,
        min_lines=args.min_lines,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

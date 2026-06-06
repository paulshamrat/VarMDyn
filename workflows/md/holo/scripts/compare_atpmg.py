#!/usr/bin/env python3
"""Compare transferred ATP/Mg coordinates against a validated source tree."""

from __future__ import annotations

import argparse
import math
from collections import defaultdict
from pathlib import Path

Atom = tuple[str, str, str, float, float, float]


def read_atoms(path: Path) -> list[Atom]:
    atoms: list[Atom] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith(("ATOM", "HETATM")):
            atoms.append(
                (
                    line[12:16].strip(),
                    line[17:20].strip(),
                    line[22:26].strip(),
                    float(line[30:38]),
                    float(line[38:46]),
                    float(line[46:54]),
                )
            )
    return atoms


def read_mg_fallback(path: Path) -> list[Atom]:
    atoms: list[Atom] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("HETATM") and line[17:20].strip() == "MG":
            atoms.append(
                (
                    line[12:16].strip(),
                    line[17:20].strip(),
                    line[22:26].strip(),
                    float(line[30:38]),
                    float(line[38:46]),
                    float(line[46:54]),
                )
            )
    return atoms


def metric(legacy: list[Atom], new: list[Atom]) -> tuple[float, float, int, bool]:
    legacy_by_key: dict[tuple[str, str, str], list[tuple[float, float, float]]] = defaultdict(list)
    new_by_key: dict[tuple[str, str, str], list[tuple[float, float, float]]] = defaultdict(list)
    for atom in legacy:
        legacy_by_key[atom[:3]].append(atom[3:])
    for atom in new:
        new_by_key[atom[:3]].append(atom[3:])

    max_dist = 0.0
    sum_sq = 0.0
    count = 0
    ok = True
    for key in sorted(set(legacy_by_key) | set(new_by_key)):
        legacy_coords = legacy_by_key.get(key, [])
        new_coords = new_by_key.get(key, [])
        if len(legacy_coords) != len(new_coords):
            ok = False
            continue
        for left, right in zip(legacy_coords, new_coords):
            dist = math.dist(left, right)
            max_dist = max(max_dist, dist)
            sum_sq += dist * dist
            count += 1
    rms = math.sqrt(sum_sq / count) if count else float("inf")
    return max_dist, rms, count, ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--variants", default="WT")
    parser.add_argument(
        "--legacy-map",
        default="WT=01_WT L119R=02_L119R D193H=03_D193H G202E=04_G202E Q219K=05_Q219K C291Y=06_C291Y",
        help="Optional run=legacy folder mapping for private parity checks.",
    )
    parser.add_argument("--atp-max-thresh", type=float, default=0.50)
    parser.add_argument("--mg-max-thresh", type=float, default=0.30)
    args = parser.parse_args()

    print("variant,atp_maxA,atp_rmsA,mg_maxA,mg_rmsA,status,notes")
    failed = False
    legacy_map = dict(item.split("=", 1) for item in args.legacy_map.split() if "=" in item)
    for variant in args.variants.split():
        legacy_variant = legacy_map.get(variant, variant)
        legacy_dir = args.legacy_root / legacy_variant / "ligprep"
        run_dir = args.run_root / variant / "ligprep"
        legacy_atp_file = legacy_dir / "ligand-only-from-complex.pdb"
        legacy_mg_file = legacy_dir / "mg-only-from-complex.pdb"
        legacy_mg_h_file = legacy_dir / "mg-only-from-complex-H.pdb"
        new_atp_file = run_dir / "ligand-only-from-complex-atponly.pdb"
        new_mg_file = run_dir / "mg-only-from-complex-mgonly.pdb"

        notes: list[str] = []
        if not legacy_atp_file.exists() or not new_atp_file.exists() or not new_mg_file.exists():
            print(f"{variant},inf,inf,inf,inf,FAIL,missing_required_files")
            failed = True
            continue
        legacy_atp = read_atoms(legacy_atp_file)
        if legacy_mg_file.exists():
            legacy_mg = read_atoms(legacy_mg_file)
        elif legacy_mg_h_file.exists():
            legacy_mg = read_mg_fallback(legacy_mg_h_file)
            notes.append("mg_from_mg-only-from-complex-H.pdb")
        else:
            print(f"{variant},inf,inf,inf,inf,FAIL,missing_legacy_mg")
            failed = True
            continue

        atp_max, atp_rms, _atp_n, atp_ok = metric(legacy_atp, read_atoms(new_atp_file))
        mg_max, mg_rms, _mg_n, mg_ok = metric(legacy_mg, read_atoms(new_mg_file))
        status = "PASS"
        if not atp_ok or not mg_ok or atp_max > args.atp_max_thresh or mg_max > args.mg_max_thresh:
            status = "FAIL"
            failed = True
            if not atp_ok:
                notes.append("atp_atom_mismatch")
            if not mg_ok:
                notes.append("mg_atom_mismatch")
            if atp_max > args.atp_max_thresh:
                notes.append(f"atp_max>{args.atp_max_thresh:.2f}")
            if mg_max > args.mg_max_thresh:
                notes.append(f"mg_max>{args.mg_max_thresh:.2f}")
        print(
            f"{variant},{atp_max:.6f},{atp_rms:.6f},{mg_max:.6f},{mg_rms:.6f},"
            f"{status},{';'.join(notes) if notes else 'ok'}"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
from pathlib import Path

FILES = [
    "rmsd.Stable_core.fit.dat",
    "rmsd.N_lobe.corefit.dat",
    "rmsd.C_lobe.corefit.dat",
    "rmsd.C_lobe_no_Aloop.corefit.dat",
    "rmsd.Hinge.corefit.dat",
    "rmsd.Activation_loop.corefit.dat",
]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    return p.parse_args()


def meta(path):
    d = {}
    with path.open() as h:
        r = csv.reader(h, delimiter="\t")
        next(r)
        for row in r:
            if len(row) >= 2:
                d[row[0]] = row[1]
    return d


def read_series(path):
    vals = []
    with path.open() as h:
        for line in h:
            if not line.strip() or line.startswith("#"):
                continue
            f = line.split()
            if len(f) >= 2:
                try:
                    vals.append(float(f[1]))
                except ValueError:
                    pass
    return vals


def ident(m):
    return f"{m['state']}_{m['system']}_{m['replicate']}"


def main():
    a = parse_args()
    rec = []
    for mp in sorted((a.root / "per-replica").glob("*/*/*/meta.tsv")):
        rec.append((meta(mp), mp.parent))
    if not rec:
        raise SystemExit("No regional metadata found")

    outdir = a.root / "rmsd"
    outdir.mkdir(parents=True, exist_ok=True)

    for fn in FILES:
        data = [(m, read_series(d / fn)) for m, d in rec]
        lens = {len(v) for _, v in data}
        if len(lens) != 1:
            raise ValueError(f"Frame mismatch: {fn}")
        n = next(iter(lens))
        f0 = {int(m["first_frame"]) for m, _ in data}
        st = {int(m["stride"]) for m, _ in data}
        dt = {float(m["frame_dt_ns"]) for m, _ in data}
        if len(f0) != 1 or len(st) != 1 or len(dt) != 1:
            raise ValueError(f"Sampling mismatch: {fn}")
        f0 = next(iter(f0))
        st = next(iter(st))
        dt = next(iter(dt))
        out = outdir / (fn.replace(".dat", ".all.tsv"))
        with out.open("w", newline="") as h:
            w = csv.writer(h, delimiter="\t")
            w.writerow(["time_ns"] + [ident(m) for m, _ in data])
            for i in range(n):
                t = ((f0 - 1) + i * st) * dt
                w.writerow([f"{t:.6f}"] + [f"{v[i]:.6f}" for _, v in data])
        print("Wrote", out)


if __name__ == "__main__":
    main()

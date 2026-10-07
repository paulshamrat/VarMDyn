#!/usr/bin/env python3
from __future__ import annotations
import argparse
import csv
from pathlib import Path
import pandas as pd


def args():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--state", required=True, choices=["apo", "holo"])
    p.add_argument("--output", required=True, type=Path)
    return p.parse_args()


def main():
    a = args()
    rows = []
    seen = {}
    for mp in sorted(a.root.glob("*/*/meta.tsv")):
        d = {}
        with mp.open() as h:
            r = csv.reader(h, delimiter="\t")
            next(r)
            for row in r:
                if len(row) >= 2:
                    d[row[0]] = row[1]
        if d.get("state") != a.state:
            raise ValueError(f"Foreign state in {mp}")
        p = Path(d["trajectory"])
        real = str(p.resolve())
        st = p.stat()
        ident = f"{d['state']}_{d['system']}_{d['replicate']}"
        dup = seen.get(real, ".")
        seen.setdefault(real, ident)
        rows.append(
            dict(
                trajectory_id=ident,
                state=d["state"],
                system=d["system"],
                replicate=d["replicate"],
                trajectory=str(p),
                realpath=real,
                size_bytes=st.st_size,
                mtime_ns=st.st_mtime_ns,
                duplicate_of=dup,
            )
        )
    df = pd.DataFrame(rows)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.output, sep="\t", index=False)
    if len(df) != 48:
        raise SystemExit(f"ERROR: expected 48 trajectories, found {len(df)}")
    dup = df[df.duplicate_of != "."]
    if len(dup):
        print(dup.to_string(index=False))
        raise SystemExit("ERROR: duplicate trajectories")
    print(f"PASS: 48 unique {a.state} trajectories")


if __name__ == "__main__":
    main()

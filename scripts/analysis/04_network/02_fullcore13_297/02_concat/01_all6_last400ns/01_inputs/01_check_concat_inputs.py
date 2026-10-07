#!/usr/bin/env python3
"""Read-only audit of the 16 full-core all-six concatenated inputs."""

from __future__ import annotations
import argparse
import csv
from pathlib import Path
import MDAnalysis as mda

STATES = {
    "apo": (
        "03_mdsim",
        "cdl.com.gas.equib.prmtop",
        "production-25-to-29-500ns.{replica}.striped.sampled-5.mdcrd.nc",
    ),
    "holo": (
        "05_cdkl5atpmg",
        "cdl.com.striped_v2.equib.prmtop",
        "production-25-to-29-500ns.{replica}.striped_v2.sampled-5.mdcrd.nc",
    ),
}
VARIANTS = (
    "01_WT",
    "02_L119R",
    "03_D193H",
    "04_G202E",
    "05_Q219K",
    "06_C291Y",
    "07_S240T",
    "08_H254R",
)
REPLICAS = tuple(f"cr{i}" for i in range(1, 7))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--md-data-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    rows = []
    for state, (branch, top_name, template) in STATES.items():
        for variant in VARIANTS:
            base = a.md_data_root / branch / variant
            top = base / "02.leap" / "com" / top_name
            status = "PASS"
            detail = []
            atoms = ""
            if not top.is_file():
                status = "FAIL"
                detail.append("missing topology")
            trajectories = []
            for replica in REPLICAS:
                traj = (
                    base
                    / "04.ptraj"
                    / "com"
                    / replica
                    / "traj-proc"
                    / template.format(replica=replica)
                )
                trajectories.append(str(traj))
                if not traj.is_file():
                    status = "FAIL"
                    detail.append(f"missing {replica}")
                    continue
                try:
                    u = mda.Universe(str(top), str(traj))
                    atoms = str(u.atoms.n_atoms)
                    if len(u.trajectory) != 5000:
                        status = "FAIL"
                        detail.append(f"{replica} has {len(u.trajectory)} frames")
                except Exception as exc:
                    status = "FAIL"
                    detail.append(f"{replica}: {type(exc).__name__}")
            rows.append(
                {
                    "state": state,
                    "variant": variant,
                    "replicas": ";".join(REPLICAS),
                    "topology": str(top),
                    "trajectories": ";".join(trajectories),
                    "source_frames_per_replica": 5000,
                    "analysis_ns": "100-500",
                    "frames_per_replica": 500,
                    "concatenated_frames": 3000,
                    "atom_count": atoms,
                    "status": status,
                    "detail": "; ".join(detail) or "validated",
                }
            )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("w", newline="") as h:
        f = list(rows[0])
        w = csv.DictWriter(h, fieldnames=f, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    failed = [r for r in rows if r["status"] != "PASS"]
    print(
        f"{'FAIL' if failed else 'PASS'}: {len(rows) - len(failed)}/{len(rows)} systems ready; {a.output}"
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

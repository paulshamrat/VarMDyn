#!/usr/bin/env python3
"""Build and analyse one CR1--CR6 100--500 ns concatenated DyNetAn system."""

from __future__ import annotations
import argparse
import csv
import importlib.util
from pathlib import Path
import MDAnalysis as mda
from MDAnalysis.coordinates.DCD import DCDWriter
import parmed as pmd

REPLICAS = tuple(f"cr{i}" for i in range(1, 7))
SOURCE_FRAMES = 5000
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


def die(m):
    raise SystemExit(f"ERROR: {m}")


def load(path):
    s = importlib.util.spec_from_file_location("replica_runner", path)
    if not s or not s.loader:
        die(f"cannot import {path}")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def source(root, state, variant, replica):
    b, t, q = STATES[state]
    base = root / b / variant
    return (
        base / "02.leap" / "com" / t,
        base / "04.ptraj" / "com" / replica / "traj-proc" / q.format(replica=replica),
    )


def write(path, fields, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=fields, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerow(row)


def complete(out):
    q = out / "01_network_qc.tsv"
    required = (
        q,
        out / "02_all6_concat.dcd",
        out / "03_dynetan_native" / "dnaData.hf",
        out / "03_dynetan_native" / "dnaData_btws.npy",
        out / "03_dynetan_native" / "dnaData_nxGraphs.pickle",
        out / "04_project_exports" / "bottleneck_centrality_all_nodes.csv",
    )
    return (
        all(x.is_file() and x.stat().st_size for x in required)
        and "status\tPASS" in q.read_text()
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("md-data-root", "input-root", "network-root", "replica-runner"):
        p.add_argument(f"--{n}", type=Path, required=True)
    p.add_argument("--state", choices=STATES, required=True)
    p.add_argument("--variant", required=True)
    p.add_argument("--analysis-start-ns", type=int, required=True)
    p.add_argument("--analysis-end-ns", type=int, required=True)
    p.add_argument("--frames-per-replica", type=int, required=True)
    p.add_argument("--contact-cutoff-a", type=float, required=True)
    p.add_argument("--contact-persistence", type=float, required=True)
    p.add_argument("--node-selection", required=True)
    p.add_argument("--ncores", type=int, default=4)
    a = p.parse_args()
    if (a.analysis_start_ns, a.analysis_end_ns, a.frames_per_replica) != (
        100,
        500,
        500,
    ):
        die("this workflow is fixed to 100--500 ns and 500 frames/replica")
    runner = load(a.replica_runner)
    top, first = source(a.md_data_root, a.state, a.variant, REPLICAS[0])
    trajs = [source(a.md_data_root, a.state, a.variant, r)[1] for r in REPLICAS]
    out = a.network_root / a.state / a.variant
    if complete(out):
        print(f"PASS existing {a.state}/{a.variant}")
        return
    if not top.is_file() or any(not x.is_file() for x in trajs):
        die("missing topology or source trajectory")
    atoms = len(pmd.load_file(str(top)).atoms)
    idx = range(1000, 5000, 8)
    if len(idx) != 500:
        die("invalid sampling")
    psf, pdb = runner.prepare_reference(top, first, a.input_root / a.state / a.variant)
    out.mkdir(parents=True, exist_ok=True)
    dcd = out / "02_all6_concat.dcd"
    if not dcd.exists():
        tmp = dcd.with_name("02_all6_concat.tmp.dcd")
        if tmp.exists():
            die(f"stale temporary DCD: {tmp}")
        with DCDWriter(str(tmp), atoms) as w:
            for traj in trajs:
                u = mda.Universe(str(top), str(traj))
                if len(u.trajectory) != SOURCE_FRAMES or u.atoms.n_atoms != atoms:
                    die(f"invalid source {traj}")
                for i in idx:
                    u.trajectory[i]
                    w.write(u.atoms)
        u = mda.Universe(str(top), str(tmp))
        if len(u.trajectory) != 3000 or u.atoms.n_atoms != atoms:
            die("concatenated DCD validation failed")
        tmp.replace(dcd)
    else:
        u = mda.Universe(str(top), str(dcd))
        if len(u.trajectory) != 3000 or u.atoms.n_atoms != atoms:
            die(f"invalid existing DCD {dcd}")
    write(
        out / "00_run_manifest.tsv",
        [
            "state",
            "variant",
            "replicas",
            "analysis_ns",
            "source_frames_per_replica",
            "frames_per_replica",
            "concatenated_frames",
            "source_first_frame_0based",
            "source_last_frame_0based",
            "sampling_stride_frames",
            "contact_cutoff_A",
            "contact_persistence",
            "node_selection",
            "topology",
            "trajectories",
            "sampled_dcd",
        ],
        {
            "state": a.state,
            "variant": a.variant,
            "replicas": ";".join(REPLICAS),
            "analysis_ns": "100-500",
            "source_frames_per_replica": 5000,
            "frames_per_replica": 500,
            "concatenated_frames": 3000,
            "source_first_frame_0based": 1000,
            "source_last_frame_0based": 4992,
            "sampling_stride_frames": 8,
            "contact_cutoff_A": a.contact_cutoff_a,
            "contact_persistence": a.contact_persistence,
            "node_selection": a.node_selection,
            "topology": top,
            "trajectories": ";".join(map(str, trajs)),
            "sampled_dcd": dcd,
        },
    )
    runner.run_network(
        psf,
        dcd,
        out / "03_dynetan_native",
        out / "04_project_exports",
        out / "01_network_qc.tsv",
        a.ncores,
        3000,
        a.contact_cutoff_a,
        a.contact_persistence,
        a.node_selection,
    )
    print(f"PASS {a.state}/{a.variant}: 3000 concatenated frames")


if __name__ == "__main__":
    main()

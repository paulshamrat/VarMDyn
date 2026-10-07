#!/usr/bin/env python3
"""Run one balanced all-six-replica concatenated late-window DyNetAn network."""

from __future__ import annotations
import argparse
import csv
import importlib.util
from pathlib import Path
import MDAnalysis as mda
from MDAnalysis.coordinates.DCD import DCDWriter
import numpy as np
import parmed as pmd
import dynetan as dna

REPLICAS = tuple(f"cr{i}" for i in range(1, 7))
SOURCE_FRAMES = 5000
INTERVAL_PS = 100
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
    spec = importlib.util.spec_from_file_location("replica_runner", path)
    if not spec or not spec.loader:
        die(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source(root, state, variant, replica):
    branch, top, traj = STATES[state]
    base = root / branch / variant
    return (
        base / "02.leap" / "com" / top,
        base
        / "04.ptraj"
        / "com"
        / replica
        / "traj-proc"
        / traj.format(replica=replica),
    )


def indices(start, end, n):
    s, e = round(start * 1000 / INTERVAL_PS), round(end * 1000 / INTERVAL_PS)
    if not (0 <= s < e <= SOURCE_FRAMES) or (e - s) % n:
        die("range must be valid and evenly sampleable")
    return list(range(s, e, (e - s) // n))


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


def reference(top, traj, folder):
    psf, pdb = folder / "02_reference.psf", folder / "03_reference.pdb"
    if psf.is_file() and pdb.is_file():
        return psf, pdb
    folder.mkdir(parents=True, exist_ok=True)
    structure = pmd.load_file(str(top))
    for residue in structure.residues:
        residue.segid = "PROT"
    structure.save(str(psf), overwrite=True)
    u = mda.Universe(str(top), str(traj))
    u.trajectory[0]
    u.atoms.write(str(pdb))
    return psf, pdb


def dcd(top, trajs, idx, path, atoms):
    expected = len(trajs) * len(idx)
    if path.is_file():
        u = mda.Universe(str(top), str(path))
        if len(u.trajectory) == expected and u.atoms.n_atoms == atoms:
            return
        die(f"invalid existing DCD {path}")
    tmp = path.with_name(path.stem + ".tmp.dcd")
    if tmp.exists():
        die(f"stale temporary {tmp}")
    with DCDWriter(str(tmp), atoms) as w:
        for traj in trajs:
            u = mda.Universe(str(top), str(traj))
            if len(u.trajectory) != SOURCE_FRAMES or u.atoms.n_atoms != atoms:
                die(f"invalid source {traj}")
            for i in idx:
                u.trajectory[i]
                w.write(u.atoms)
    check = mda.Universe(str(top), str(tmp))
    if len(check.trajectory) != expected:
        die("DCD validation failed")
    tmp.replace(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--md-data-root", type=Path, required=True)
    p.add_argument("--input-root", type=Path, required=True)
    p.add_argument("--network-root", type=Path, required=True)
    p.add_argument("--replica-runner", type=Path, required=True)
    p.add_argument("--state", choices=STATES, required=True)
    p.add_argument("--variant", required=True)
    p.add_argument("--analysis-start-ns", type=float, required=True)
    p.add_argument("--analysis-end-ns", type=float, required=True)
    p.add_argument("--frames-per-replica", type=int, required=True)
    p.add_argument("--contact-cutoff-a", type=float, required=True)
    p.add_argument("--contact-persistence", type=float, required=True)
    p.add_argument("--node-selection", required=True)
    p.add_argument("--ncores", type=int, default=4)
    a = p.parse_args()
    runner = load(a.replica_runner)
    top, first = source(a.md_data_root, a.state, a.variant, REPLICAS[0])
    trajs = [source(a.md_data_root, a.state, a.variant, r)[1] for r in REPLICAS]
    if not top.is_file() or any(not x.is_file() for x in trajs):
        die("matched topology or source trajectory missing")
    out = a.network_root / a.state / a.variant
    if complete(out):
        print(f"PASS existing {a.state}/{a.variant}")
        return
    atom_count = len(pmd.load_file(str(top)).atoms)
    idx = indices(a.analysis_start_ns, a.analysis_end_ns, a.frames_per_replica)
    psf, pdb = reference(top, first, a.input_root / a.state / a.variant)
    out.mkdir(parents=True, exist_ok=True)
    sampled = out / "02_all6_concat.dcd"
    dcd(top, trajs, idx, sampled, atom_count)
    write(
        out / "00_run_manifest.tsv",
        [
            "state",
            "variant",
            "replicas",
            "analysis_start_ns",
            "analysis_end_ns",
            "frames_per_replica",
            "concatenated_frames",
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
            "replicas": ",".join(REPLICAS),
            "analysis_start_ns": a.analysis_start_ns,
            "analysis_end_ns": a.analysis_end_ns,
            "frames_per_replica": a.frames_per_replica,
            "concatenated_frames": len(REPLICAS) * len(idx),
            "contact_cutoff_A": a.contact_cutoff_a,
            "contact_persistence": a.contact_persistence,
            "node_selection": a.node_selection,
            "topology": top,
            "trajectories": ";".join(map(str, trajs)),
            "sampled_dcd": sampled,
        },
    )
    native, exports = out / "03_dynetan_native", out / "04_project_exports"
    native.mkdir(parents=True, exist_ok=True)
    n = dna.proctraj.DNAproc()
    n.setNumWinds(1)
    n.setNumSampledFrames(len(REPLICAS) * len(idx))
    n.setCutoffDist(a.contact_cutoff_a)
    n.setContactPersistence(a.contact_persistence)
    n.setSegIDs(["PROT"])
    n.setSolvNames(["WAT", "TIP3", "HOH", "OPC"])
    n.loadSystem(str(psf), [str(sampled)])
    n.checkSystem()
    n.selectSystem(withSolvent=False, inputSelStr=a.node_selection)
    n.prepareNetwork()
    n.alignTraj(inMemory=True)
    n.findContacts(stride=1)
    n.filterContacts(notSameRes=True, notConsecutiveRes=True, removeIsolatedNodes=True)
    n.calcCor(ncores=a.ncores)
    n.calcCartesian(backend="openmp")
    n.calcGraphInfo()
    n.calcBetween(ncores=a.ncores)
    n.calcEigenCentral()
    n.calcCommunities()
    if getattr(n, "distsAll", None) is None:
        n.distsAll = np.zeros((1, 1), dtype=np.float64)
    n.saveData(str(native / "dnaData"))
    n.saveReducedTraj(str(native / "dnaData"))
    runner.write_project_exports(n, exports)
    write(
        out / "01_network_qc.tsv",
        ["setting", "value"],
        {"setting": "status", "value": "PASS"},
    )
    with (out / "01_network_qc.tsv").open("a") as h:
        h.write(
            f"sampled_frames\t{len(REPLICAS) * len(idx)}\nreplicas\t{','.join(REPLICAS)}\nnodes\t{len(n.nxGraphs[0].nodes)}\nedges\t{len(n.nxGraphs[0].edges)}\n"
        )
    print(f"PASS {a.state}/{a.variant}: {len(REPLICAS) * len(idx)} frames")


if __name__ == "__main__":
    main()

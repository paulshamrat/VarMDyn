#!/usr/bin/env python3
"""Run one independent-replica DyNetAn calculation from a 500-ns trajectory."""

from __future__ import annotations

import argparse
import csv
from operator import itemgetter
from pathlib import Path
import sys
import warnings

import MDAnalysis as mda
from MDAnalysis.coordinates.DCD import DCDWriter
import numpy as np
import parmed as pmd
import pandas as pd
import dynetan as dna


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
REPLICAS = tuple(f"cr{number}" for number in range(1, 7))
SOURCE_FRAMES = 5000
INPUT_INTERVAL_PS = 100
TOTAL_NS = SOURCE_FRAMES * INPUT_INTERVAL_PS / 1000
STATE_LAYOUT = {
    "apo": {
        "branch": "03_mdsim",
        "topology": "cdl.com.gas.equib.prmtop",
        "trajectory_template": "production-25-to-29-500ns.{replica}.striped.sampled-5.mdcrd.nc",
    },
    "holo": {
        "branch": "05_cdkl5atpmg",
        "topology": "cdl.com.striped_v2.equib.prmtop",
        "trajectory_template": "production-25-to-29-500ns.{replica}.striped_v2.sampled-5.mdcrd.nc",
    },
}


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def source_paths(
    root: Path, state: str, variant: str, replica: str
) -> tuple[Path, Path]:
    layout = STATE_LAYOUT[state]
    system = root / layout["branch"] / variant
    topology = system / "02.leap" / "com" / layout["topology"]
    trajectory = (
        system
        / "04.ptraj"
        / "com"
        / replica
        / "traj-proc"
        / layout["trajectory_template"].format(replica=replica)
    )
    return topology, trajectory


def selected_indices(
    start_ns: float, end_ns: float, frame_count: int
) -> tuple[int, int, int]:
    """Return uniformly spaced source-frame indices for one DyNetAn window."""
    if start_ns < 0 or end_ns > TOTAL_NS or start_ns >= end_ns:
        fail(
            f"analysis range must lie within 0--{TOTAL_NS:g} ns and have positive width"
        )
    start_raw = start_ns * 1000 / INPUT_INTERVAL_PS
    end_raw = end_ns * 1000 / INPUT_INTERVAL_PS
    start, end = round(start_raw), round(end_raw)
    if not np.isclose(start_raw, start) or not np.isclose(end_raw, end):
        fail(
            "analysis bounds must align to the 100-ps standardized trajectory interval"
        )
    if end > frame_count:
        fail(f"analysis end frame {end} exceeds trajectory length {frame_count}")
    available = end - start
    if available < 1:
        fail("analysis range has no trajectory frames")
    return start, end, available


def evenly_sampled_indices(start: int, end: int, frames_per_window: int) -> list[int]:
    available = end - start
    if frames_per_window <= 0:
        fail("frames per window must be positive")
    if available < frames_per_window:
        fail(
            f"requested {frames_per_window} frames from only {available} source frames"
        )
    if available % frames_per_window:
        fail(
            f"{available} source frames cannot be sampled at a constant stride into "
            f"{frames_per_window} frames"
        )
    stride = available // frames_per_window
    return list(range(start, end, stride))


def write_tsv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def prepare_reference(
    topology: Path, trajectory: Path, input_dir: Path
) -> tuple[Path, Path]:
    psf, pdb = input_dir / "02_reference.psf", input_dir / "03_reference.pdb"
    if psf.is_file() and pdb.is_file():
        return psf, pdb
    if psf.exists() or pdb.exists():
        fail(f"incomplete reference pair in {input_dir}; inspect before rerunning")
    input_dir.mkdir(parents=True, exist_ok=True)
    psf_tmp = psf.with_name("02_reference.tmp.psf")
    pdb_tmp = pdb.with_name("03_reference.tmp.pdb")
    if psf_tmp.exists() or pdb_tmp.exists():
        fail(f"stale reference temporary file in {input_dir}; inspect before rerunning")
    structure = pmd.load_file(str(topology))
    for residue in structure.residues:
        residue.segid = "PROT"
    structure.save(str(psf_tmp), overwrite=True)
    universe = mda.Universe(str(topology), str(trajectory))
    universe.trajectory[0]
    universe.atoms.write(str(pdb_tmp))
    psf_tmp.replace(psf)
    pdb_tmp.replace(pdb)
    return psf, pdb


def build_sampled_dcd(
    topology: Path,
    trajectory: Path,
    dcd: Path,
    indices: list[int],
    atom_count: int,
) -> None:
    if dcd.is_file():
        existing = mda.Universe(str(topology), str(dcd))
        if (
            len(existing.trajectory) == len(indices)
            and existing.atoms.n_atoms == atom_count
        ):
            return
        fail(f"existing sampled DCD is invalid: {dcd}; inspect before rerunning")
    tmp = dcd.with_name("02_sampled_trajectory.tmp.dcd")
    if tmp.exists():
        fail(
            f"stale sampled-DCD temporary file exists: {tmp}; inspect before rerunning"
        )
    universe = mda.Universe(str(topology), str(trajectory))
    if len(universe.trajectory) != SOURCE_FRAMES:
        fail(
            f"{trajectory}: expected {SOURCE_FRAMES} frames, found {len(universe.trajectory)}"
        )
    if universe.atoms.n_atoms != atom_count:
        fail(f"{trajectory}: atom count differs from topology")
    with DCDWriter(str(tmp), atom_count) as writer:
        for index in indices:
            universe.trajectory[index]
            writer.write(universe.atoms)
    check = mda.Universe(str(topology), str(tmp))
    if len(check.trajectory) != len(indices) or check.atoms.n_atoms != atom_count:
        fail(f"sampled DCD failed validation: {tmp}")
    tmp.replace(dcd)


def write_project_exports(network: dna.proctraj.DNAproc, export_dir: Path) -> None:
    """Write readable diagnostics from the native DyNetAn objects.

    These exports retain the categories used in the older concatenated
    workflow.  They are conveniences for inspection; the native ``dnaData``
    files remain the authoritative DyNetAn output.
    """
    export_dir.mkdir(parents=True, exist_ok=True)
    graph = network.nxGraphs[0]
    scores = {node: 0.0 for node in graph.nodes}
    for (left, right), value in network.btws[0].items():
        scores[left] += float(value)
        scores[right] += float(value)
    rows = []
    for rank, (node, score) in enumerate(
        sorted(scores.items(), key=itemgetter(1), reverse=True), 1
    ):
        atom = network.nodesAtmSel[node]
        rows.append(
            {
                "node": node,
                "rank": rank,
                "residue_name": atom.resname,
                "residue_id": int(atom.resid),
                "bottleneck_centrality": score,
                "degree": graph.nodes[node].get("degree"),
                "eigenvector_centrality": graph.nodes[node].get("eigenvector"),
                "community": graph.nodes[node].get("modularity"),
            }
        )
    table = pd.DataFrame(rows)
    table.to_csv(export_dir / "bottleneck_centrality_all_nodes.csv", index=False)
    table.iloc[:25].to_csv(export_dir / "bottleneck_nodes_top25.csv", index=False)
    table.iloc[:25].to_csv(
        export_dir / "bottleneck_nodes_top25.txt", sep="\t", index=False
    )
    degree = table.sort_values(["degree", "node"], ascending=[False, True])
    degree.iloc[:25].to_csv(export_dir / "top_degree_nodes_top25.csv", index=False)
    eigen = table.sort_values(
        ["eigenvector_centrality", "node"], ascending=[False, True]
    )
    eigen.iloc[:25].to_csv(export_dir / "top_eigenvector_nodes_top25.csv", index=False)
    edge_rows = []
    for (left, right), value in network.btws[0].items():
        left_atom, right_atom = network.nodesAtmSel[left], network.nodesAtmSel[right]
        edge_rows.append(
            {
                "node_left": left,
                "residue_left_name": left_atom.resname,
                "residue_left_id": int(left_atom.resid),
                "node_right": right,
                "residue_right_name": right_atom.resname,
                "residue_right_id": int(right_atom.resid),
                "edge_betweenness": float(value),
                "edge_weight": graph.edges[left, right].get("weight"),
                "communication_distance": graph.edges[left, right].get("dist"),
            }
        )
    edge_table = pd.DataFrame(edge_rows).sort_values(
        "edge_betweenness", ascending=False
    )
    edge_table.iloc[:100].to_csv(
        export_dir / "top_edges_betweenness_top100.csv", index=False
    )
    (export_dir / "network_report.txt").write_text(
        f"nodes\t{graph.number_of_nodes()}\n"
        f"edges\t{graph.number_of_edges()}\n"
        f"bottleneck_definition\tsum of native edge-betweenness over edges incident on each node\n"
    )
    if len(table.iloc[:25]) != 25 or table.iloc[:25]["residue_id"].nunique() != 25:
        fail("top-25 bottleneck table is invalid")


def run_network(
    psf: Path,
    dcd: Path,
    native_dir: Path,
    export_dir: Path,
    qc_path: Path,
    ncores: int,
    sampled_frames: int,
    cutoff: float,
    persistence: float,
    node_selection: str,
) -> None:
    warnings.filterwarnings("ignore", category=UserWarning)
    native_dir.mkdir(parents=True, exist_ok=True)
    network = dna.proctraj.DNAproc()
    network.setNumWinds(1)
    network.setNumSampledFrames(sampled_frames)
    network.setCutoffDist(cutoff)
    network.setContactPersistence(persistence)
    network.setSegIDs(["PROT"])
    network.setSolvNames(["WAT", "TIP3", "HOH", "OPC"])
    network.loadSystem(str(psf), [str(dcd)])
    network.checkSystem()
    # Empty selection preserves the validated full-protein workflow.  A supplied
    # selection is an explicit, heavy-atom protein-core network definition.
    network.selectSystem(withSolvent=False, inputSelStr=node_selection)
    network.prepareNetwork()
    network.alignTraj(inMemory=True)
    network.findContacts(stride=1)
    network.filterContacts(
        notSameRes=True, notConsecutiveRes=True, removeIsolatedNodes=True
    )
    network.calcCor(ncores=ncores)
    network.calcCartesian(backend="openmp")
    network.calcGraphInfo()
    network.calcBetween(ncores=ncores)
    network.calcEigenCentral()
    network.calcCommunities()
    if getattr(network, "distsAll", None) is None:
        network.distsAll = np.zeros((1, 1), dtype=np.float64)
    # Omit the optional root argument so the default native DyNetAn base name
    # remains dnaData; only its parent directory is chosen by this workflow.
    network.saveData(str(native_dir / "dnaData"))
    network.saveReducedTraj(str(native_dir / "dnaData"))
    write_project_exports(network, export_dir)
    qc_path.write_text(
        "setting\tvalue\n"
        f"sampled_frames\t{sampled_frames}\n"
        f"contact_cutoff_A\t{cutoff}\n"
        f"contact_persistence\t{persistence}\n"
        f"node_selection\t{node_selection or 'automatic_full_PROT_selection'}\n"
        "same_residue_contacts_excluded\ttrue\n"
        "consecutive_residue_contacts_excluded\ttrue\n"
        f"nodes\t{len(network.nxGraphs[0].nodes)}\n"
        f"edges\t{len(network.nxGraphs[0].edges)}\n"
        "status\tPASS\n"
    )


def network_outputs_complete(out_dir: Path) -> bool:
    required = (
        out_dir / "01_network_qc.tsv",
        out_dir / "03_dynetan_native" / "dnaData.hf",
        out_dir / "03_dynetan_native" / "dnaData_btws.npy",
        out_dir / "03_dynetan_native" / "dnaData_nxGraphs.pickle",
        out_dir / "04_project_exports" / "bottleneck_centrality_all_nodes.csv",
    )
    qc = out_dir / "01_network_qc.tsv"
    return all(path.is_file() for path in required) and "status\tPASS" in qc.read_text()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md-data-root", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--network-root", type=Path, required=True)
    parser.add_argument("--state", choices=tuple(STATE_LAYOUT), required=True)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--replica", choices=REPLICAS, required=True)
    parser.add_argument("--analysis-start-ns", type=float, required=True)
    parser.add_argument("--analysis-end-ns", type=float, required=True)
    parser.add_argument("--frames-per-window", type=int, required=True)
    parser.add_argument("--num-windows", type=int, required=True)
    parser.add_argument("--contact-cutoff-a", type=float, required=True)
    parser.add_argument("--contact-persistence", type=float, required=True)
    parser.add_argument("--node-selection", default="")
    parser.add_argument("--ncores", type=int, default=8)
    args = parser.parse_args()
    if args.num_windows != 1:
        fail("this initial independent-replica method supports NUM_WINDOWS=1 only")
    if args.ncores < 1:
        fail("--ncores must be positive")

    topology, trajectory = source_paths(
        args.md_data_root, args.state, args.variant, args.replica
    )
    if not topology.is_file() or not trajectory.is_file():
        fail("matched topology or trajectory is missing; run input QC first")
    topology_atoms = len(pmd.load_file(str(topology)).atoms)
    source = mda.Universe(str(topology), str(trajectory))
    source_frames = len(source.trajectory)
    if source_frames != SOURCE_FRAMES:
        fail(f"{trajectory}: expected {SOURCE_FRAMES} frames, found {source_frames}")
    if source.atoms.n_atoms != topology_atoms:
        fail("topology/trajectory atom-count mismatch")
    start, end, available = selected_indices(
        args.analysis_start_ns, args.analysis_end_ns, source_frames
    )
    indices = evenly_sampled_indices(start, end, args.frames_per_window)

    input_dir = args.input_root / args.state / args.variant / args.replica
    out_dir = args.network_root / args.state / args.variant / args.replica
    native_dir = out_dir / "03_dynetan_native"
    export_dir = out_dir / "04_project_exports"
    dcd = out_dir / "02_sampled_trajectory.dcd"
    if network_outputs_complete(out_dir):
        print(
            f"PASS existing {args.state}/{args.variant}/{args.replica}: network outputs already complete"
        )
        return 0
    psf, pdb = prepare_reference(topology, trajectory, input_dir)
    write_tsv(
        input_dir / "01_input_manifest.tsv",
        [
            {
                "state": args.state,
                "variant": args.variant,
                "replica": args.replica,
                "source_root": args.md_data_root,
                "topology": topology,
                "trajectory": trajectory,
                "topology_atoms": topology_atoms,
                "source_frames": source_frames,
                "source_interval_ps": INPUT_INTERVAL_PS,
                "status": "PASS",
            }
        ],
        [
            "state",
            "variant",
            "replica",
            "source_root",
            "topology",
            "trajectory",
            "topology_atoms",
            "source_frames",
            "source_interval_ps",
            "status",
        ],
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    build_sampled_dcd(topology, trajectory, dcd, indices, topology_atoms)
    write_tsv(
        out_dir / "00_run_manifest.tsv",
        [
            {
                "state": args.state,
                "variant": args.variant,
                "replica": args.replica,
                "analysis_start_ns": args.analysis_start_ns,
                "analysis_end_ns": args.analysis_end_ns,
                "source_first_frame": indices[0],
                "source_last_frame": indices[-1],
                "source_frames_in_range": available,
                "sampling_stride_frames": available // len(indices),
                "sampled_frames": len(indices),
                "num_windows": args.num_windows,
                "contact_cutoff_A": args.contact_cutoff_a,
                "contact_persistence": args.contact_persistence,
                "node_selection": args.node_selection
                or "automatic_full_PROT_selection",
                "reference_psf": psf,
                "reference_pdb": pdb,
                "sampled_dcd": dcd,
            }
        ],
        [
            "state",
            "variant",
            "replica",
            "analysis_start_ns",
            "analysis_end_ns",
            "source_first_frame",
            "source_last_frame",
            "source_frames_in_range",
            "sampling_stride_frames",
            "sampled_frames",
            "num_windows",
            "contact_cutoff_A",
            "contact_persistence",
            "node_selection",
            "reference_psf",
            "reference_pdb",
            "sampled_dcd",
        ],
    )
    run_network(
        psf,
        dcd,
        native_dir,
        export_dir,
        out_dir / "01_network_qc.tsv",
        args.ncores,
        len(indices),
        args.contact_cutoff_a,
        args.contact_persistence,
        args.node_selection,
    )
    print(f"PASS {args.state}/{args.variant}/{args.replica}: {len(indices)} frames")
    return 0


if __name__ == "__main__":
    sys.exit(main())

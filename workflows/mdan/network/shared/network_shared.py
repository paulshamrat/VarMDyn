#!/usr/bin/env python3
"""Standalone DyNetAn network workflow packet.

This script keeps the VarMDyn dynamic network workflow in one portable CLI:

  prepare  -> build stripped topology, sampled NetCDF, PDB, PSF, and DCD
  run      -> run DyNetAn and write top-node/top-edge tables
  compare  -> compare variant top-25 bottleneck residues against WT
  render   -> render one WT-vs-variant comparison with PyMOL
  full     -> run prepare, run, compare, and optional render
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import time
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR
DATA_ROOT = Path(
    os.environ.get("VARMDYN_NETWORK_DATA_ROOT", REPO_ROOT / "data" / "mdan" / "network" / "full")
).expanduser()
RUN_ROOT = Path(
    os.environ.get("VARMDYN_NETWORK_RUN_ROOT", REPO_ROOT / "data" / "mdan" / "network" / "runs")
).expanduser()
os.environ.setdefault("NUMBA_CACHE_DIR", str(RUN_ROOT / "numba_cache"))
LEGACY_REPLAY_SBATCH = SCRIPT_DIR / "dynetan_replay_validation_apo.sh"
LAST_HPC_JOB_FILE = REPO_ROOT / ".last_network_hpc_job_id"

AA3_TO_1 = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLU": "E",
    "GLN": "Q",
    "GLY": "G",
    "HIS": "H",
    "HID": "H",
    "HIE": "H",
    "HIP": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
}


def run_command(cmd: list[str], log: Path | None = None) -> None:
    if log is None:
        subprocess.run(cmd, check=True)
        return
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(cmd, stdout=handle, stderr=handle)
    if proc.returncode:
        raise SystemExit(f"command failed; see {log}: {' '.join(cmd)}")


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def split_variants(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def discover_variants(root: Path, wt: str) -> list[str]:
    variants = sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir() and re.match(r"^\d{2}_[A-Za-z0-9]+$", path.name)
    )
    if wt in variants:
        variants = [wt] + [variant for variant in variants if variant != wt]
    return variants


def resolve_variants(args: argparse.Namespace) -> list[str]:
    if args.variants:
        return split_variants(args.variants)
    root = Path(args.root).expanduser()
    variants = discover_variants(root, args.wt)
    variants = [variant for variant in variants if variant_has_required_input(args, root, variant)]
    if not variants:
        raise SystemExit(f"no variant folders found in {args.root}")
    return variants


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def prepared_paths(args: argparse.Namespace, src: Path) -> tuple[Path, Path, Path | None]:
    topo = src / args.prepared_topology_suffix
    traj = src / args.prepared_traj_suffix
    ref = src / args.prepared_ref_traj_suffix if args.prepared_ref_traj_suffix else None
    return topo, traj, ref


def raw_topology_path(args: argparse.Namespace, src: Path) -> Path:
    return src / args.topology_suffix


def variant_has_required_input(args: argparse.Namespace, root: Path, variant: str) -> bool:
    src = root / variant
    input_mode = getattr(args, "input_mode", "auto")
    if input_mode in {"auto", "prepared"}:
        topo, traj, _ref = prepared_paths(args, src)
        if topo.exists() and traj.exists():
            return True
    if input_mode in {"auto", "raw"}:
        return raw_topology_path(args, src).exists()
    return False


def resolve_input_mode(args: argparse.Namespace, src: Path, variant: str) -> str:
    input_mode = args.input_mode
    if input_mode in {"auto", "prepared"}:
        topo, traj, _ref = prepared_paths(args, src)
        if topo.exists() and traj.exists():
            return "prepared"
        if input_mode == "prepared":
            raise SystemExit(
                f"missing prepared inputs for {variant}: topology={topo}, trajectory={traj}"
            )
    if input_mode in {"auto", "raw"}:
        topo = raw_topology_path(args, src)
        if topo.exists():
            return "raw"
        if input_mode == "raw":
            raise SystemExit(f"missing raw topology for {variant}: {topo}")
    raise SystemExit(f"could not resolve input mode for {variant} under {src}")


def prepare_variant(args: argparse.Namespace, variant: str) -> None:
    try:
        import MDAnalysis as mda
        import parmed as pmd
        from MDAnalysis.coordinates.DCD import DCDWriter
    except ImportError as exc:
        raise SystemExit(
            "Missing MD preparation dependency. Activate varmdyn_dynetan first. "
            f"Original error: {exc}"
        ) from exc

    src = Path(args.root).expanduser() / variant
    input_mode = resolve_input_mode(args, src, variant)

    out = DATA_ROOT / "prepared" / args.state / variant
    work = RUN_ROOT / "cpptraj" / args.state / variant
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    keep = args.state == "holo"
    tag = "striped_v2" if input_mode == "prepared" else ("keepATPmg" if keep else "striped")
    topo_out = out / f"{variant}.{tag}.prmtop"
    nc_out = out / f"{variant}.concatenated_750frames.{tag}.nc"
    pdb_out = out / f"{variant}.pdb"
    psf_out = out / f"{variant}.psf"
    dcd_out = out / f"{variant}.dcd"
    ligands_pdb_out = out / f"{variant}_with_ligands.pdb"
    manifest_out = out / "prepare_manifest.txt"
    manifest_lines = [f"state={args.state}", f"variant={variant}", f"input_mode={input_mode}"]

    if input_mode == "prepared":
        topo, prepared_nc, ref_nc = prepared_paths(args, src)
        manifest_lines += [
            f"topology={topo}",
            f"trajectory={prepared_nc}",
            f"reference_trajectory={ref_nc or ''}",
        ]
        if not topo_out.exists() or args.force:
            run_command(["cp", str(topo), str(topo_out)])
        if not nc_out.exists() or args.force:
            run_command(["cp", str(prepared_nc), str(nc_out)])
        if keep and ref_nc and ref_nc.exists() and (not ligands_pdb_out.exists() or args.force):
            inp = work / "extract_ligands_pdb.in"
            write_text(
                inp,
                f"parm {topo}\ntrajin {ref_nc} 1 1\nautoimage\nstrip ':WAT,Na+,Cl-'\ntrajout {ligands_pdb_out} pdb\ngo\nquit\n",
            )
            run_command(["cpptraj", "-i", str(inp)], work / "extract_ligands_pdb.log")
    else:
        topo = raw_topology_path(args, src)
        strip_mask = args.holo_strip_mask if keep else args.apo_strip_mask
        manifest_lines += [
            f"topology={topo}",
            f"trajectory_template={args.traj_template}",
            f"replicas={args.replicas}",
            f"chunks={args.chunks}",
            f"stride={args.stride}",
            f"strip_mask={strip_mask}",
        ]
        if not topo_out.exists() or args.force:
            inp = work / "strip_topology.in"
            write_text(
                inp,
                f"parm {topo}\nparmstrip '{strip_mask}'\nparmwrite out {topo_out}\ngo\nquit\n",
            )
            run_command(["cpptraj", "-i", str(inp)], work / "strip_topology.log")

        trajin_lines: list[str] = []
        for rep in split_variants(args.replicas):
            for chunk in split_variants(args.chunks):
                nc = src / args.traj_template.format(replica=rep, chunk=chunk)
                if nc.exists():
                    trajin_lines.append(f"trajin {nc} 1 last {args.stride}")
                elif args.strict:
                    raise SystemExit(f"missing trajectory chunk for {variant}: {nc}")
                else:
                    print(f"[WARN] missing trajectory chunk for {variant}: {nc}")
        if not trajin_lines:
            raise SystemExit(f"no trajectory chunks found for {variant}")

        # Generate an extra PDB for PyMOL rendering that keeps ATP and Mg.
        if keep and (not ligands_pdb_out.exists() or args.force):
            first_chunk_path = trajin_lines[0].split()[1]
            inp = work / "extract_ligands_pdb.in"
            write_text(
                inp,
                f"parm {topo}\ntrajin {first_chunk_path} 1 1\nautoimage\nstrip ':WAT,Na+,Cl-'\ntrajout {ligands_pdb_out} pdb\ngo\nquit\n",
            )
            run_command(["cpptraj", "-i", str(inp)], work / "extract_ligands_pdb.log")

        if not nc_out.exists() or args.force:
            inp = work / "concat_sample.in"
            write_text(
                inp,
                "parm {topo}\n{trajin}\nautoimage\nstrip '{strip}'\ntrajout {out} netcdf\ngo\nquit\n".format(
                    topo=topo,
                    trajin="\n".join(trajin_lines),
                    strip=strip_mask,
                    out=nc_out,
                ),
            )
            run_command(["cpptraj", "-i", str(inp)], work / "concat_sample.log")

    manifest_text = "\n".join(manifest_lines) + "\n"
    manifest_changed = not manifest_out.exists() or manifest_out.read_text(encoding="utf-8") != manifest_text

    if manifest_changed:
        for stale in [psf_out, pdb_out, dcd_out]:
            if stale.exists():
                stale.unlink()

    if not psf_out.exists() or args.force:
        st = pmd.load_file(str(topo_out))
        for residue in st.residues:
            residue.segid = "PROT"
        st.save(str(psf_out), overwrite=True)

    if not pdb_out.exists() or not dcd_out.exists() or args.force:
        u = mda.Universe(str(topo_out), str(nc_out))
        if not pdb_out.exists() or args.force:
            u.trajectory[0]
            u.atoms.write(str(pdb_out))
        if not dcd_out.exists() or args.force:
            with DCDWriter(str(dcd_out), u.atoms.n_atoms) as writer:
                for _ts in u.trajectory:
                    writer.write(u.atoms)

    write_text(manifest_out, manifest_text)
    print(f"[OK] prepared {args.state}/{variant} ({input_mode} inputs): {out}")


def selection_label(node: int, nodes_atm_sel) -> str:
    atom = nodes_atm_sel[node]
    return f"resname {atom.resname} and resid {atom.resid}"


def run_dynetan_variant(args: argparse.Namespace, variant: str) -> None:
    try:
        import dynetan as dna
        import networkx as nx
    except ImportError as exc:
        raise SystemExit(f"Missing dynetan. Activate varmdyn_dynetan first. Original error: {exc}") from exc

    stage_tag = args.stage_tag or f"varmdyn_full_{args.state}"
    prepared = DATA_ROOT / "prepared" / args.state / variant
    psf = prepared / f"{variant}.psf"
    dcd = prepared / f"{variant}.dcd"
    if not psf.exists() or not dcd.exists():
        raise SystemExit(f"missing prepared inputs for {args.state}/{variant}: {prepared}")

    out = DATA_ROOT / "dynetan" / args.state / variant
    done = out / f"bottleneck_nodes_top{args.top_nodes}_{stage_tag}.csv"
    if done.exists() and not args.force:
        print(f"[OK] DyNetAn already complete: {args.state}/{variant} ({done})")
        return
    out.mkdir(parents=True, exist_ok=True)

    dnap = dna.proctraj.DNAproc()
    dnap.setNumWinds(args.num_winds)
    dnap.setNumSampledFrames(args.num_sampled_frames)
    dnap.setCutoffDist(args.cutoff)
    dnap.setContactPersistence(args.contact_persistence)
    dnap.setSegIDs(["PROT"])
    if hasattr(dnap, "setSolvNames"):
        dnap.setSolvNames(["WAT", "TIP3", "HOH", "OPC"])
    else:
        dnap.h2oName = ["WAT", "TIP3", "HOH", "OPC"]

    dnap.loadSystem(str(psf), [str(dcd)])
    dnap.checkSystem()
    if not getattr(dnap, "notSelSegidSet", None):
        dnap.notSelSegidSet = ["__VARMDYN_NO_NONSELECTED_SEGID__"]
    dnap.selectSystem(withSolvent=False)
    dnap.prepareNetwork()
    dnap.alignTraj(inMemory=True)
    dnap.findContacts(stride=1)
    dnap.filterContacts(notSameRes=True, notConsecutiveRes=True, removeIsolatedNodes=True)
    dnap.calcCor(ncores=args.ncores)
    dnap.calcCartesian(backend=args.cartesian_backend)
    dnap.calcGraphInfo()
    dnap.calcOptPaths(ncores=args.ncores)
    dnap.calcBetween(ncores=args.ncores)
    dnap.calcEigenCentral()
    dnap.calcCommunities()
    dnap.saveData(str(out / f"dnaData_{stage_tag}"))

    graph = dnap.nxGraphs[0]
    node_rows = [
        {
            "Node": node,
            "Degree": graph.nodes[node].get("degree", None),
            "Eigenvector": graph.nodes[node].get("eigenvector", None),
            "Selection": selection_label(node, dnap.nodesAtmSel),
        }
        for node in graph.nodes
    ]
    degree_rows = sorted(node_rows, key=lambda row: float(row["Degree"] or 0.0), reverse=True)[
        : args.top_nodes
    ]
    eigen_rows = sorted(node_rows, key=lambda row: float(row["Eigenvector"] or 0.0), reverse=True)[
        : args.top_nodes
    ]
    write_csv(out / f"top_degree_nodes_top{args.top_nodes}_{stage_tag}.csv", degree_rows, ["Node", "Degree", "Eigenvector", "Selection"])
    write_csv(out / "top_degree_nodes_top25.csv", degree_rows, ["Node", "Degree", "Eigenvector", "Selection"])
    write_csv(out / f"top_eigenvector_nodes_top{args.top_nodes}_{stage_tag}.csv", eigen_rows, ["Node", "Degree", "Eigenvector", "Selection"])

    node_betweenness = {node: 0.0 for node in graph.nodes}
    for (i, j), value in dnap.btws[0].items():
        node_betweenness[i] = node_betweenness.get(i, 0.0) + float(value)
        node_betweenness[j] = node_betweenness.get(j, 0.0) + float(value)
    top_bottleneck = sorted(node_betweenness.items(), key=lambda item: item[1], reverse=True)[
        : args.top_nodes
    ]
    bottleneck_rows = [
        {
            "Node": node,
            "BottleneckScore_sumEdgeBetw": f"{score:.8f}",
            "Degree": graph.nodes[node].get("degree", None),
            "Eigenvector": graph.nodes[node].get("eigenvector", None),
            "Selection": selection_label(node, dnap.nodesAtmSel),
        }
        for node, score in top_bottleneck
    ]
    write_csv(out / f"bottleneck_nodes_top{args.top_nodes}_{stage_tag}.csv", bottleneck_rows, ["Node", "BottleneckScore_sumEdgeBetw", "Degree", "Eigenvector", "Selection"])
    write_csv(out / "bottleneck_nodes_top25.csv", bottleneck_rows, ["Node", "BottleneckScore_sumEdgeBetw", "Degree", "Eigenvector", "Selection"])

    with (out / f"bottleneck_nodes_top{args.top_nodes}_{stage_tag}.txt").open("w", encoding="utf-8") as handle:
        handle.write(f"Top {args.top_nodes} Bottleneck Nodes (sum of incident edge betweenness)\n")
        handle.write(f"Stage: {stage_tag}\n")
        handle.write("Rank\tNode\tBottleneckScore\tDegree\tEigenvector\tSelection\n")
        for rank, (node, score) in enumerate(top_bottleneck, start=1):
            handle.write(
                f"{rank}\t{node}\t{score}\t{graph.nodes[node].get('degree', None)}\t"
                f"{graph.nodes[node].get('eigenvector', None)}\t{selection_label(node, dnap.nodesAtmSel)}\n"
            )

    edge_rows = [
        {
            "Edge_i": i,
            "Edge_j": j,
            "EdgeBetweenness": f"{float(value):.8f}",
            "Correlation": f"{float(dnap.corrMatAll[0, i, j]):.8f}",
            "Sel_i": selection_label(i, dnap.nodesAtmSel),
            "Sel_j": selection_label(j, dnap.nodesAtmSel),
        }
        for (i, j), value in dnap.btws[0].items()
    ]
    edge_rows = sorted(edge_rows, key=lambda row: float(row["EdgeBetweenness"]), reverse=True)[
        : args.top_edges
    ]
    write_csv(out / f"top_edges_betweenness_top{args.top_edges}_{stage_tag}.csv", edge_rows, ["Edge_i", "Edge_j", "EdgeBetweenness", "Correlation", "Sel_i", "Sel_j"])

    with (out / f"network_report_{stage_tag}.txt").open("w", encoding="utf-8") as handle:
        handle.write("CDKL5 DyNetAn Network Report\n")
        handle.write("========================================\n\n")
        handle.write(f"Variant: {variant}\nMode   : concatenated\nStage  : {stage_tag}\n\n")
        handle.write(f"Nodes: {len(graph.nodes)}\nEdges: {len(graph.edges)}\n")
        handle.write(f"Density: {nx.density(graph):.4f}\n")
        handle.write(f"Transitivity: {nx.transitivity(graph):.4f}\n")
        handle.write(f"Connected components: {nx.number_connected_components(graph)}\n")
        handle.write(f"Largest component size: {len(max(nx.connected_components(graph), key=len))}\n")
    print(f"[OK] DyNetAn complete: {out}")


def residue_label(selection: str) -> str:
    match = re.search(r"\bresname\s+(\S+)\s+and\s+resid\s+(\d+)\b", selection)
    if not match:
        raise ValueError(f"could not parse selection: {selection}")
    resname, resid = match.group(1), int(match.group(2))
    return f"{AA3_TO_1.get(resname.upper(), resname[0].upper())}{resid}"


def residue_number(label: str) -> int:
    match = re.search(r"(\d+)$", label)
    if not match:
        raise ValueError(f"could not parse residue number: {label}")
    return int(match.group(1))


def compare_top25(args: argparse.Namespace) -> None:
    stage_tag = args.stage_tag or f"varmdyn_full_{args.state}"
    variants = resolve_variants(args)
    sets: dict[str, set[str]] = {}
    for variant in variants:
        folder = DATA_ROOT / "dynetan" / args.state / variant
        path = folder / f"bottleneck_nodes_top25_{stage_tag}.csv"
        if not path.exists():
            path = folder / "bottleneck_nodes_top25.csv"
        sets[variant] = {residue_label(row["Selection"]) for row in csv_rows(path)}

    wt_set = sets[args.wt]
    out = DATA_ROOT / "compare" / args.state
    overlap_rows = []
    transition_rows = []
    frequency = {"wt_lost": Counter(), "gained": Counter()}
    mutant_variants = [variant for variant in variants if variant != args.wt]

    for variant in mutant_variants:
        residues = sets[variant]
        shared = wt_set & residues
        wt_lost = wt_set - residues
        gained = residues - wt_set
        overlap_rows.append(
            {
                "variant": variant,
                "wt_top_total": len(wt_set),
                "shared": len(shared),
                "shared_fraction": f"{len(shared) / len(wt_set):.4f}",
                "wt_lost": len(wt_lost),
                "gained": len(gained),
            }
        )
        for klass, labels in [("shared", shared), ("wt_lost", wt_lost), ("gained", gained)]:
            for label in sorted(labels, key=residue_number):
                transition_rows.append(
                    {
                        "state": args.state,
                        "variant": variant,
                        "transition_class": klass,
                        "residue": label,
                        "residue_number": residue_number(label),
                    }
                )
        frequency["wt_lost"].update(wt_lost)
        frequency["gained"].update(gained)

    freq_rows = []
    for klass in ["wt_lost", "gained"]:
        for residue, count in sorted(
            frequency[klass].items(), key=lambda item: (-item[1], residue_number(item[0]), item[0])
        ):
            freq_rows.append(
                {
                    "state": args.state,
                    "transition_class": klass,
                    "residue": residue,
                    "count": count,
                    "total_variants": len(mutant_variants),
                }
            )

    write_csv(out / "overlap_with_WT.csv", overlap_rows, ["variant", "wt_top_total", "shared", "shared_fraction", "wt_lost", "gained"])
    write_csv(out / "wt_vs_variants_lost_gained.csv", transition_rows, ["state", "variant", "transition_class", "residue", "residue_number"])
    write_csv(out / "transition_frequency.csv", freq_rows, ["state", "transition_class", "residue", "count", "total_variants"])
    print(f"[OK] comparison tables: {out}")


def render_structure_path(state: str, variant: str, wt: str, pdb_arg: str | None = None) -> Path:
    if pdb_arg:
        return Path(pdb_arg).expanduser()
    variant_pdb = DATA_ROOT / "prepared" / state / variant / f"{variant}.pdb"
    if variant_pdb.exists():
        return variant_pdb
    wt_pdb = DATA_ROOT / "prepared" / state / wt / f"{wt}.pdb"
    if wt_pdb.exists():
        print(f"[WARN] missing variant structure {variant_pdb}; using WT structure {wt_pdb}")
        return wt_pdb
    raise SystemExit(f"missing render structure: {variant_pdb}")


def render_pymol(args: argparse.Namespace) -> None:
    table = DATA_ROOT / "compare" / args.state / "wt_vs_variants_lost_gained.csv"
    groups = {"shared": [], "wt_lost": [], "gained": []}
    for row in csv_rows(table):
        if row["variant"] == args.variant:
            groups[row["transition_class"]].append(row["residue_number"])

    def plus(values: list[str]) -> str:
        return "+".join(values) if values else "999999"

    pdb = render_structure_path(args.state, args.variant, args.wt, getattr(args, "pdb", None))
    out_dir = DATA_ROOT / "render" / args.state
    out_dir.mkdir(parents=True, exist_ok=True)
    pml = out_dir / f"{args.variant}_network_residues.pml"
    png = out_dir / f"{args.variant}_network_residues.png"
    write_text(
        pml,
        f"""
load {pdb}, cdkl5
hide everything
bg_color white
set ray_shadows, 0
set orthoscopic, on
select prot, cdkl5 and polymer.protein
show cartoon, prot
color wheat, prot
set cartoon_transparency, 0.15
select shared, prot and name CA and resi {plus(groups['shared'])}
select wt_lost, prot and name CA and resi {plus(groups['wt_lost'])}
select gained, prot and name CA and resi {plus(groups['gained'])}
show spheres, shared
show spheres, wt_lost
show spheres, gained
color forest, shared
color marine, wt_lost
set_color varmdyn_orange, [0.92, 0.42, 0.00]
color varmdyn_orange, gained
set sphere_scale, 0.65
zoom prot, 3
ray 1600, 1200
png {png}, dpi=300
quit
""",
    )
    run_command(["pymol", "-cq", str(pml)])
    print(f"[OK] rendered: {png}")


def run_full(args: argparse.Namespace) -> None:
    states = ["apo", "holo"] if args.state == "all" else [args.state]
    for state in states:
        root = args.apo_root if state == "apo" else args.holo_root
        if not root:
            raise SystemExit(f"set --{state}-root or VARMDYN_{state.upper()}_ROOT")
        state_args = argparse.Namespace(**vars(args))
        state_args.state = state
        state_args.root = root
        variants = resolve_variants(state_args)
        print(f"[INFO] state={state}")
        print(f"[INFO] variants={','.join(variants)}")
        for variant in variants:
            prepare_variant(state_args, variant)
        for variant in variants:
            run_dynetan_variant(state_args, variant)
        compare_top25(state_args)
        render_variant = args.render_variant or next((variant for variant in variants if variant != args.wt), "")
        if render_variant and args.render:
            render_args = argparse.Namespace(**vars(state_args))
            render_args.variant = render_variant
            render_args.pdb = None
            if shutil_which("pymol"):
                render_pymol(render_args)
            else:
                print("[INFO] pymol not found; skipping render.")


def shutil_which(name: str) -> str | None:
    from shutil import which

    return which(name)


def hpc_host() -> str:
    value = os.environ.get("VARMDYN_HPC_HOST")
    if not value:
        raise SystemExit("set VARMDYN_HPC_HOST")
    return value


def hpc_project() -> Path:
    value = os.environ.get("VARMDYN_HPC_PROJECT")
    if not value:
        raise SystemExit("set VARMDYN_HPC_PROJECT")
    return Path(value)


def hpc_dynetan_work() -> Path:
    value = os.environ.get("VARMDYN_DYNETAN_WORK")
    if not value:
        raise SystemExit("set VARMDYN_DYNETAN_WORK")
    return Path(value)


def hpc_conda_env() -> str:
    return os.environ.get("VARMDYN_CONDA_ENV", "varmdyn_dynetan")


def hpc_stage_tag() -> str:
    return os.environ.get("VARMDYN_DYNETAN_STAGE_TAG", "concat750_w1_s750_apo_validation_20260526")


def ssh_control_path() -> str:
    return os.environ.get("VARMDYN_SSH_CONTROL_PATH", "")


def ssh_command(remote_command: str) -> list[str]:
    cmd = ["ssh"]
    control_path = ssh_control_path()
    if control_path and Path(control_path).exists():
        cmd += ["-S", control_path]
    cmd += [hpc_host(), remote_command]
    return cmd


def scp_command(src: str, dst: str, *, recursive: bool = False) -> list[str]:
    cmd = ["scp"]
    if recursive:
        cmd.append("-r")
    control_path = ssh_control_path()
    if control_path and Path(control_path).exists():
        cmd += ["-o", f"ControlPath={control_path}"]
    cmd += [src, dst]
    return cmd


def hpc_remote(path: str | Path) -> str:
    return f"{hpc_host()}:{path}"


def hpc_remote_sbatch() -> Path:
    return hpc_project() / "03_md/analysis_repro/slurm/varmdyn_dynetan_replay_validation_apo.sh"


def run_capture(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("[run] " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def hpc_stage() -> None:
    if not LEGACY_REPLAY_SBATCH.exists():
        raise SystemExit(f"missing sbatch template: {LEGACY_REPLAY_SBATCH}")
    dst = hpc_remote_sbatch()
    run_command(ssh_command(f"mkdir -p {dst.parent} {hpc_project() / '03_md/analysis_repro/logs'}"))
    run_command(scp_command(str(LEGACY_REPLAY_SBATCH), hpc_remote(dst)))
    print(f"[OK] staged network sbatch: {dst}")


def hpc_submit() -> str:
    env = (
        f"VARMDYN_HPC_PROJECT={hpc_project()} "
        f"VARMDYN_DYNETAN_WORK={hpc_dynetan_work()} "
        f"VARMDYN_CONDA_ENV={hpc_conda_env()} "
        f"VARMDYN_DYNETAN_STAGE_TAG={hpc_stage_tag()}"
    )
    proc = run_capture(ssh_command(f"cd {hpc_project()} && {env} sbatch {hpc_remote_sbatch()}"))
    text = (proc.stdout or "") + (proc.stderr or "")
    print(text.strip())
    match = re.search(r"Submitted batch job\s+(\d+)", text)
    if not match:
        raise SystemExit(f"could not parse job id from sbatch output:\n{text}")
    job_id = match.group(1)
    LAST_HPC_JOB_FILE.write_text(job_id + "\n", encoding="utf-8")
    print(f"[OK] submitted network replay job {job_id}")
    return job_id


def resolve_hpc_job_id(job_id: str | None, *, required: bool = False) -> str | None:
    if job_id:
        return job_id
    if LAST_HPC_JOB_FILE.exists():
        recorded = LAST_HPC_JOB_FILE.read_text(encoding="utf-8").strip()
        if recorded:
            return recorded
    if required:
        raise SystemExit("--job-id is required because no previous network job id is recorded")
    return None


def hpc_status(job_id: str | None = None) -> None:
    if job_id:
        queue_cmd = f"squeue -j {job_id} -o '%.18i %.9P %.28j %.8u %.2t %.10M %.10l %.6D %R'"
        acct_cmd = f"sacct -j {job_id} --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P"
    else:
        hpc_user = os.environ.get("VARMDYN_HPC_USER", os.environ.get("USER", ""))
        queue_cmd = f"squeue -u {hpc_user} -o '%.18i %.9P %.28j %.8u %.2t %.10M %.10l %.6D %R'"
        acct_cmd = (
            f"sacct -u {hpc_user} --starttime now-2days "
            "--format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P | grep cdkl5_dynetan"
        )
    proc = run_capture(ssh_command(queue_cmd), check=False)
    print("[squeue]\n" + (proc.stdout.strip() or "(no queued/running jobs matched)"))
    proc = run_capture(ssh_command(acct_cmd), check=False)
    print("[sacct]\n" + (proc.stdout.strip() or "(no recent accounting rows matched)"))


def hpc_wait(job_id: str, poll_seconds: int) -> None:
    while True:
        proc = run_capture(ssh_command(f"squeue -j {job_id} -h"), check=False)
        if not proc.stdout.strip():
            break
        print(proc.stdout.strip())
        time.sleep(poll_seconds)
    proc = run_capture(ssh_command(f"sacct -j {job_id} --format=JobID,State,ExitCode -P -n | head -20"))
    print(proc.stdout.strip())


def hpc_compare() -> None:
    cmd = (
        f"cd {hpc_dynetan_work()} && "
        "module load anaconda3/2023.09-0 >/dev/null 2>&1 && "
        f"conda run -n {hpc_conda_env()} python 07_compare_networks_all_variants.py "
        "--results-root TutorialResults_CDKL5 "
        "--mode concatenated "
        f"--stage-tag {hpc_stage_tag()} "
        "--wt 01_WT "
        "--top-n 25"
    )
    run_command(ssh_command(cmd))


def hpc_fetch(outdir: Path) -> None:
    dst = outdir / hpc_stage_tag()
    dst.mkdir(parents=True, exist_ok=True)
    remote_work = hpc_dynetan_work()
    run_command(
        scp_command(
            hpc_remote(remote_work / "TutorialResults_CDKL5/_comparisons_concatenated"),
            str(dst),
            recursive=True,
        )
    )
    local_results = dst / "TutorialResults_CDKL5"
    local_results.mkdir(parents=True, exist_ok=True)
    remote_results = remote_work / "TutorialResults_CDKL5"
    find_cmd = (
        f"find {remote_results} -path '*/concatenated/*_{hpc_stage_tag()}.csv' "
        "-printf '%P\\n'"
    )
    proc = run_capture(ssh_command(find_cmd))
    relpaths = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    for relpath in relpaths:
        local_path = local_results / relpath
        local_path.parent.mkdir(parents=True, exist_ok=True)
        run_command(scp_command(hpc_remote(remote_results / relpath), str(local_path)))
    print(f"[OK] fetched network comparisons and {len(relpaths)} replay CSVs into {dst}")


def hpc_run(args: argparse.Namespace) -> None:
    hpc_stage()
    job_id = hpc_submit()
    if not args.no_wait:
        hpc_wait(job_id, args.poll_seconds)
        hpc_compare()
        hpc_fetch(Path(args.outdir))


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state", choices=["apo", "holo"], required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--variants", default=os.environ.get("VARMDYN_VARIANTS", ""))
    parser.add_argument("--wt", default=os.environ.get("VARMDYN_WT", "01_WT"))


def add_prep(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--input-mode",
        choices=["auto", "prepared", "raw"],
        default=os.environ.get("VARMDYN_INPUT_MODE", "auto"),
        help="auto prefers prepared striped_v2 inputs; raw builds protein-only inputs from chunks",
    )
    parser.add_argument(
        "--prepared-topology-suffix",
        default=os.environ.get(
            "VARMDYN_PREPARED_TOPOLOGY_SUFFIX",
            "02.leap/com/cdl.com.striped_v2.prmtop",
        ),
    )
    parser.add_argument(
        "--prepared-traj-suffix",
        default=os.environ.get(
            "VARMDYN_PREPARED_TRAJ_SUFFIX",
            "04.ptraj/com/concatenated/production-25-to-29-concatenated-750frames.striped_v2.mdcrd.nc",
        ),
    )
    parser.add_argument(
        "--prepared-ref-traj-suffix",
        default=os.environ.get(
            "VARMDYN_PREPARED_REF_TRAJ_SUFFIX",
            "04.ptraj/com/cr1/traj-proc/production-25-to-29-500ns.cr1.striped_v2.mdcrd.nc",
        ),
    )
    parser.add_argument(
        "--topology-suffix",
        default=os.environ.get("VARMDYN_TOPOLOGY_SUFFIX", "02.leap/com/cdl.com.wat.leap.prmtop"),
    )
    parser.add_argument(
        "--traj-template",
        default=os.environ.get("VARMDYN_TRAJ_TEMPLATE", "03.pmemd/com/{replica}/{chunk}md.mdcrd.nc"),
    )
    parser.add_argument("--replicas", default=os.environ.get("VARMDYN_REPLICAS", "cr1,cr2,cr3"))
    parser.add_argument("--chunks", default=os.environ.get("VARMDYN_CHUNKS", "25,26,27,28,29"))
    parser.add_argument("--stride", type=int, default=int(os.environ.get("VARMDYN_TRAJ_STRIDE", "20")))
    parser.add_argument("--apo-strip-mask", default=os.environ.get("VARMDYN_APO_STRIP_MASK", ":WAT,Na+,Cl-"))
    parser.add_argument(
        "--holo-strip-mask",
        default=os.environ.get("VARMDYN_HOLO_STRIP_MASK", ":WAT,Na+,Cl-,ATP,MG"),
    )
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--force", action="store_true")


def add_dynetan(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--stage-tag")
    parser.add_argument("--num-winds", type=int, default=1)
    parser.add_argument("--num-sampled-frames", type=int, default=750)
    parser.add_argument("--cutoff", type=float, default=4.5)
    parser.add_argument("--contact-persistence", type=float, default=0.75)
    parser.add_argument("--ncores", type=int, default=int(os.environ.get("VARMDYN_NCORES", "8")))
    parser.add_argument("--top-nodes", type=int, default=25)
    parser.add_argument("--top-edges", type=int, default=100)
    parser.add_argument("--cartesian-backend", default="serial")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("prepare")
    add_common(p)
    add_prep(p)

    p = sub.add_parser("run")
    add_common(p)
    add_dynetan(p)
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("compare")
    add_common(p)
    p.add_argument("--stage-tag")

    p = sub.add_parser("render")
    p.add_argument("--state", choices=["apo", "holo"], required=True)
    p.add_argument("--variant", default=os.environ.get("VARMDYN_RENDER_VARIANT", "02_L119R"))
    p.add_argument("--wt", default=os.environ.get("VARMDYN_WT", "01_WT"))
    p.add_argument("--pdb")

    p = sub.add_parser("full")
    p.add_argument("--state", choices=["apo", "holo", "all"], default="apo")
    p.add_argument("--apo-root", default=os.environ.get("VARMDYN_APO_ROOT", ""))
    p.add_argument("--holo-root", default=os.environ.get("VARMDYN_HOLO_ROOT", ""))
    p.add_argument("--variants", default=os.environ.get("VARMDYN_VARIANTS", ""))
    p.add_argument("--wt", default=os.environ.get("VARMDYN_WT", "01_WT"))
    p.add_argument("--render-variant", default=os.environ.get("VARMDYN_RENDER_VARIANT", ""))
    p.add_argument("--render", action="store_true")
    add_prep(p)
    add_dynetan(p)

    args = parser.parse_args()
    if args.command == "prepare":
        for variant in resolve_variants(args):
            prepare_variant(args, variant)
    elif args.command == "run":
        for variant in resolve_variants(args):
            run_dynetan_variant(args, variant)
    elif args.command == "compare":
        compare_top25(args)
    elif args.command == "render":
        render_pymol(args)
    elif args.command == "full":
        run_full(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

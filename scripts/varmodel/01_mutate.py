#!/usr/bin/env python3
"""Step 01: Automated Modeller mutation modeling for CDKL5 variant panel.

Run from any directory with no arguments:

    python scripts/varmodel/01_mutate.py

Inputs:
    input/varmodel/01_structure/target.B99990001_with_cryst.pdb

Outputs:
    data/varmodel/01_mutants/ (7 all-atom mutant 3D PDB structures)
    data/varmodel/02_tables/mutate_summary.csv
    data/varmodel/02_tables/manifest.csv
"""

from __future__ import annotations

import csv
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

from Bio.Data.IUPACData import protein_letters_3to1 as P3
from Bio.PDB import PDBParser

# Modeller imports
try:
    from modeller import Alignment, Environ, Model, Selection, log as mlog
    from modeller.automodel import autosched
    from modeller.optimizers import ConjugateGradients, MolecularDynamics

    _MODELLER_OK = True
except Exception as _exc:
    _MODELLER_OK = False
    _MODELLER_ERR = _exc

# ---------------------------------------------------------------------------
# Locations & Targets
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
INPUT_ROOT = Path(
    __import__("os").environ.get(
        "VARMDYN_MODELING_INPUT_ROOT", str(REPO_ROOT / "data" / "varmodel" / "inputs")
    )
)
DATA_ROOT = REPO_ROOT / "data" / "varmodel"

WT_PDB = INPUT_ROOT / "01_structure" / "target.B99990001_with_cryst.pdb"
PANEL_TSV = INPUT_ROOT / "03_model_panel" / "01_variant_panel.tsv"

CHAIN_ID = "A"
SEED = -49837

ONE_TO_THREE = {
    "A": "ALA",
    "C": "CYS",
    "D": "ASP",
    "E": "GLU",
    "F": "PHE",
    "G": "GLY",
    "H": "HIS",
    "I": "ILE",
    "K": "LYS",
    "L": "LEU",
    "M": "MET",
    "N": "ASN",
    "P": "PRO",
    "Q": "GLN",
    "R": "ARG",
    "S": "SER",
    "T": "THR",
    "V": "VAL",
    "W": "TRP",
    "Y": "TYR",
}


def read_variant_panel(panel_tsv: Path = PANEL_TSV) -> list[dict[str, object]]:
    """Read and validate the explicit seven-variant modeling panel."""
    required = {
        "mutation",
        "position",
        "wt",
        "mut",
        "simulation_group",
        "cluster",
        "selection_basis",
        "published_germline_classification",
        "source_workbook",
        "source_worksheet",
    }
    if not panel_tsv.exists():
        raise FileNotFoundError(f"Missing modeling-panel input: {panel_tsv}")
    with panel_tsv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"Modeling panel lacks required columns: {panel_tsv}")
        rows = list(reader)
    if len(rows) != 7 or len({row["mutation"] for row in rows}) != len(rows):
        raise ValueError("Modeling panel must contain exactly seven unique variants.")
    panel: list[dict[str, object]] = []
    for row in rows:
        mutation = row["mutation"].strip()
        wt = row["wt"].strip().upper()
        mut = row["mut"].strip().upper()
        position = int(row["position"])
        if (
            mutation != f"{wt}{position}{mut}"
            or wt not in ONE_TO_THREE
            or mut not in ONE_TO_THREE
        ):
            raise ValueError(f"Invalid mutation record in modeling panel: {row}")
        panel.append(
            {
                **row,
                "mutation": mutation,
                "position": position,
                "wt": wt,
                "mut": mut,
                "cluster": int(row["cluster"]) if row["cluster"].strip() else None,
            }
        )
    return panel


def read_cryst1(pdb_path: Path) -> str:
    """Extract CRYST1 record line if present."""
    with open(pdb_path, "r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("CRYST1"):
                return line
    return ""


def observed_wt_letter(pdb_path: Path, chain_id: str, pos: int) -> str | None:
    """Determine 1-letter residue code at position in PDB."""
    parser = PDBParser(QUIET=True)
    st = parser.get_structure("base", str(pdb_path))
    model = list(st)[0]
    chain = None
    for ch in model:
        if ch.id.strip() == chain_id:
            chain = ch
            break
    if chain is None:
        chain = list(model)[0]

    for res in chain:
        if res.id[0] != " ":
            continue
        if res.id[1] == pos:
            return P3.get(res.get_resname().strip().capitalize(), "X")
    return None


def make_restraints(mdl: Model, aln: Alignment) -> None:
    """Generate stereo, binormal, and dihedral restraints on model."""
    rsr = mdl.restraints
    rsr.clear()
    s = Selection(mdl)
    for typ in ("stereo", "phi-psi_binormal"):
        rsr.make(s, restraint_type=typ, aln=aln, spline_on_site=True)
    for typ in ("omega", "chi1", "chi2", "chi3", "chi4"):
        rsr.make(
            s,
            restraint_type=typ + "_dihedral",
            spline_range=4.0,
            spline_dx=0.3,
            spline_min_points=5,
            aln=aln,
            spline_on_site=True,
        )


def refine_md(atmsel: Selection) -> None:
    """Perform molecular dynamics simulated annealing refinement on selection."""
    md = MolecularDynamics(cap_atom_shift=0.39, md_time_step=4.0, md_return="FINAL")
    init_vel = True
    for its, equil, temps in (
        (200, 20, (150.0, 250.0, 400.0, 700.0, 1000.0)),
        (200, 600, (1000.0, 800.0, 600.0, 500.0, 400.0, 300.0)),
    ):
        for temp in temps:
            md.optimize(
                atmsel,
                init_velocities=init_vel,
                temperature=temp,
                max_iterations=its,
                equilibrate=equil,
            )
            init_vel = False


def optimize_selection(atmsel: Selection, mdl: Model) -> None:
    """Run full optimization schedule: loop autosched -> refine MD -> conjugate gradients."""
    sched = autosched.loop.make_for_model(mdl)
    for step in sched:
        step.optimize(atmsel, max_iterations=200, min_atom_shift=0.001)
    refine_md(atmsel)
    cg = ConjugateGradients()
    cg.optimize(atmsel, max_iterations=200, min_atom_shift=0.001)


def reinsert_cryst1(in_pdb: Path, out_pdb: Path, cryst1_line: str) -> None:
    """Reinsert CRYST1 header into PDB output."""
    lines = in_pdb.read_text(encoding="utf-8").splitlines()
    with out_pdb.open("w", encoding="utf-8") as out:
        if cryst1_line:
            out.write(cryst1_line.strip() + "\n")
        for line in lines:
            if not line.startswith("CRYST1"):
                out.write(line + "\n")


def mutate_variant(
    pdb_path: Path,
    chain: str,
    mut_str: str,
    wt_aa: str,
    pos: int,
    mut_aa: str,
    seed: int,
    out_dir: Path,
) -> tuple[Path, float | None, float | None, str | None, str]:
    """Execute single mutation using Modeller API and write output PDB."""
    if not _MODELLER_OK:
        raise ImportError(f"Modeller not available: {_MODELLER_ERR}")

    cryst1 = read_cryst1(pdb_path)
    obs = observed_wt_letter(pdb_path, chain, pos)
    if obs is None:
        return None, None, None, obs, f"FAIL: residue {chain}:{pos} not found in PDB"
    if obs != wt_aa:
        return (
            None,
            None,
            None,
            obs,
            f"FAIL: WT mismatch at {chain}:{pos} (expected {wt_aa}, found {obs})",
        )

    stem = pdb_path.stem
    if stem.endswith("_with_cryst"):
        stem = stem[: -len("_with_cryst")]

    final_pdb = out_dir / f"{stem}_{mut_str}_with_cryst.pdb"

    # Run inside an isolated temporary directory to avoid scratch file collisions
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        local_base = tmp_path / pdb_path.name
        shutil.copy2(pdb_path, local_base)

        cwd = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            env = Environ(rand_seed=seed)
            env.io.hetatm = True
            env.edat.dynamic_sphere = False
            env.edat.dynamic_lennard = True
            env.edat.contact_shell = 4.0
            env.edat.update_dynamic = 0.39
            env.libs.topology.read(file="$(LIB)/top_heav.lib")
            env.libs.parameters.read(file="$(LIB)/par.lib")
            mlog.minimal()

            mdl1 = Model(env, file=local_base.name)
            ali = Alignment(env)
            ali.append_model(
                mdl1, atom_files=local_base.name, align_codes=local_base.name
            )

            # Mutate target residue
            try:
                s = Selection(mdl1.chains[chain].residues[str(pos)])
            except Exception:
                s = Selection(mdl1.chains[chain].residues[pos])
            s.mutate(residue_type=ONE_TO_THREE[mut_aa])

            ali.append_model(mdl1, align_codes=local_base.name)
            mdl1.clear_topology()
            mdl1.generate_topology(ali[-1])
            mdl1.transfer_xyz(ali)
            mdl1.build(initialize_xyz=False, build_method="INTERNAL_COORDINATES")

            mdl2 = Model(env, file=local_base.name)
            mdl1.res_num_from(mdl2, ali)

            tmp_pdb = tmp_path / f"{stem}_{mut_str}.tmp"
            mdl1.write(file=str(tmp_pdb))
            mdl1.read(file=str(tmp_pdb))

            make_restraints(mdl1, ali)
            try:
                s = Selection(mdl1.chains[chain].residues[str(pos)])
            except Exception:
                s = Selection(mdl1.chains[chain].residues[pos])

            mdl1.restraints.unpick_all()
            mdl1.restraints.pick(s)

            mdl1.env.edat.nonbonded_sel_atoms = 1
            try:
                E_unopt = float(s.energy()[0])
            except Exception:
                E_unopt = None

            s.randomize_xyz(deviation=4.0)
            mdl1.env.edat.nonbonded_sel_atoms = 2
            optimize_selection(s, mdl1)
            mdl1.env.edat.nonbonded_sel_atoms = 1
            optimize_selection(s, mdl1)

            try:
                E_opt = float(s.energy()[0])
            except Exception:
                E_opt = None

            core_pdb = tmp_path / f"{stem}_{mut_str}.pdb"
            mdl1.write(file=str(core_pdb))

            reinsert_cryst1(core_pdb, final_pdb, cryst1)
            return final_pdb, E_unopt, E_opt, obs, "OK"
        finally:
            os.chdir(cwd)


def run_step_01(out_dir: Optional[Path] = None) -> dict[str, object]:
    """Execute variant modeling for all 7 target mutations and generate handoff tables."""
    if not _MODELLER_OK:
        raise RuntimeError(
            f"Modeller is not importable: {_MODELLER_ERR}. Run scripts/varmodel/00_install_modeller.sh first."
        )

    run_root = out_dir or DATA_ROOT
    target_mutants_dir = run_root / "01_mutants"
    target_tables_dir = run_root / "02_tables"
    target_mutants_dir.mkdir(parents=True, exist_ok=True)
    target_tables_dir.mkdir(parents=True, exist_ok=True)

    if not WT_PDB.exists():
        raise FileNotFoundError(f"Missing WT PDB structure: {WT_PDB}")
    panel = read_variant_panel()

    print("=" * 70)
    print("CDKL5 Variant Modeling Pipeline (Step 01: Modeller Mutate)")
    print(f"WT Structure:    {WT_PDB}")
    print(
        f"Target Variants: {len(panel)} ({', '.join(str(m['mutation']) for m in panel)})"
    )
    print(f"Output PDBs:     {target_mutants_dir}")
    print(f"Output Tables:   {target_tables_dir}")
    print("=" * 70)

    summary_rows = []
    manifest_rows = []

    for item in panel:
        mut_str = item["mutation"]
        pos = item["position"]
        wt_aa = item["wt"]
        mut_aa = item["mut"]
        simulation_group = item["simulation_group"]
        selection_basis = item["selection_basis"]
        cluster_id = item["cluster"]

        print(
            f"\n[INFO] Modeling {simulation_group}: {mut_str} (Position {pos}, {selection_basis})..."
        )
        out_pdb, e_unopt, e_opt, obs, status = mutate_variant(
            pdb_path=WT_PDB,
            chain=CHAIN_ID,
            mut_str=mut_str,
            wt_aa=wt_aa,
            pos=pos,
            mut_aa=mut_aa,
            seed=SEED,
            out_dir=target_mutants_dir,
        )

        if status == "OK":
            print(
                f"[OK] Generated {mut_str} -> {out_pdb.name} (E_unopt={e_unopt:.2f}, E_opt={e_opt:.2f})"
            )
        else:
            print(f"[ERROR] Failed {mut_str} -> {status}")

        summary_rows.append(
            {
                "pdb_in": str(WT_PDB),
                "mutation": mut_str,
                "chain": CHAIN_ID,
                "seed": SEED,
                "out_pdb": str(out_pdb) if out_pdb else "",
                "E_unopt": e_unopt,
                "E_opt": e_opt,
                "observed_WT": obs,
                "status": status,
            }
        )

        manifest_rows.append(
            {
                "mutation": mut_str,
                "position": pos,
                "cluster": cluster_id if cluster_id is not None else "N/A",
                "simulation_group": simulation_group,
                "selection_basis": selection_basis,
                "published_germline_classification": item[
                    "published_germline_classification"
                ],
                "source_workbook": item["source_workbook"],
                "source_worksheet": item["source_worksheet"],
                "status": status,
                "output_pdb": str(out_pdb.relative_to(REPO_ROOT)) if out_pdb else "",
                "observed_wt": obs,
            }
        )

    # Write mutate_summary.csv
    summary_file = target_tables_dir / "mutate_summary.csv"
    with summary_file.open("w", newline="", encoding="utf-8") as h:
        writer = csv.DictWriter(
            h,
            fieldnames=[
                "pdb_in",
                "mutation",
                "chain",
                "seed",
                "out_pdb",
                "E_unopt",
                "E_opt",
                "observed_WT",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"\n[OK] Wrote Modeller summary table: {summary_file}")

    # Write manifest.csv
    manifest_file = target_tables_dir / "manifest.csv"
    with manifest_file.open("w", newline="", encoding="utf-8") as h:
        writer = csv.DictWriter(
            h,
            fieldnames=[
                "mutation",
                "position",
                "cluster",
                "simulation_group",
                "selection_basis",
                "published_germline_classification",
                "source_workbook",
                "source_worksheet",
                "status",
                "output_pdb",
                "observed_wt",
            ],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"[OK] Wrote downstream MD handoff manifest: {manifest_file}")

    return {
        "mutants_dir": target_mutants_dir,
        "summary_csv": summary_file,
        "manifest_csv": manifest_file,
        "successful": sum(1 for r in summary_rows if r["status"] == "OK"),
        "total": len(summary_rows),
    }


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit(
            "This fixed workflow takes no arguments. Run: python scripts/varmodel/01_mutate.py"
        )
    res = run_step_01()
    return 0 if res["successful"] == res["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

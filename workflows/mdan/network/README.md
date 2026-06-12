# Network Analysis

This folder contains the generic VarMDyn DyNetAn workflow:

- `network.py` prepares sampled trajectory inputs, runs DyNetAn, compares
  configured variants against WT, and supports Slurm array planning/submission.
- `validate_outputs.py` checks user-supplied network summary tables and,
  optionally, compares them with supplied DyNetAn output directories. Reported
  residue/count differences are review items, not failures, when the input
  trajectories differ.
- `create_dynetan_env.sh`, `run_full_network.slurm`, and
  `run_network_array.slurm` support trajectory-level network runs.

Generated trajectories, DyNetAn outputs, tables, logs, and figures belong under
ignored `data/` or another runtime output root, not in this code folder.
Reusable scripts and templates belong in `workflows/`. Runtime directories may
contain logs and generated scientific outputs, but should not accumulate
workflow scripts; transient cpptraj inputs are recorded inside the corresponding
log files instead.

Runtime output map:

```text
data/mdan/network/prepared/    stripped topology and sampled trajectory products
data/mdan/network/dynetan/     per-variant DyNetAn tables and reports
data/mdan/network/compare/     WT-vs-variant lost/gained comparison tables
data/mdan/network/figures/     final figures plus clearly named render subfolders
data/mdan/network/runs/        Slurm logs, cpptraj provenance logs, and disposable cache
data/mdan/network/tables/      user-supplied and run-derived network tables
data/mdan/network/validation/  local QA reports only
```

`validation/` is for reproducibility checks, not a downstream analysis source.
`runs/cache/` is disposable runtime cache created by dependencies such as Numba;
it is safe to remove and is not a scientific output.
The generic public workflow assembles the network pathway comparison and
residue-remodel figures from VarMDyn outputs. It also produces
method-valid DyNetAn outputs, bottleneck-focused QC figures, and generic
network tables from the VarMDyn run.

## Local Checks

Run on: local workstation from the repository root. Environment: `varmdyn_env`.

```bash
python scripts/checks/check_data_inputs.py --module network --profile tables
python workflows/mdan/network/validate_outputs.py --help
```

## Network Runs

Use the repository wrapper for normal local-to-HPC work:

```bash
bash scripts/run_analysis.sh network plan --state apo --variants all
bash scripts/run_analysis.sh network submit --state apo --variants all --run
bash scripts/run_analysis.sh network plan --state holo --variants all
bash scripts/run_analysis.sh network submit --state holo --variants all --run
bash scripts/run_analysis.sh network status
bash scripts/run_analysis.sh network check-frames --state apo --variants all
bash scripts/run_analysis.sh network check-frames --state holo --variants all
bash scripts/run_analysis.sh network fetch --from scratch --run
bash scripts/run_analysis.sh network tables
bash scripts/run_analysis.sh network figures --state all
```

Run `tables` before `figures`; the residue-remodel figure reads the
run-derived residue-frequency table under `tables/from_run/`.
Both commands are local post-fetch commands through the wrapper. They read
`data/mdan/network/` by default even when the shell still has
`VARMDYN_MDAN_OUTPUT_ROOT` pointing at an HPC scratch or project path. Set
`VARMDYN_NETWORK_DATA_ROOT` only when intentionally using another local network
tree.

`check-frames` verifies that prepared DCDs have enough frames for the
750-sampled-frame DyNetAn method. A 250-frame prepared DCD is a smoke/input
readiness artifact, not a full-method network result.

Runtime note: with the default chunks `25-29`, replicas `cr1,cr2,cr3`, and
stride `20`, each variant preparation reads 15 raw trajectory chunks and should
write a 3,750-frame prepared DCD. The cpptraj preparation step is normally short
relative to DyNetAn; DyNetAn is the long-running stage. When refactoring, record
Slurm elapsed time and prepared frame counts together so runtime changes can be
distinguished from scheduler noise or method changes.

For direct execution on a machine with trajectory inputs and DyNetAn available:

```bash
python workflows/mdan/network/network.py full --state apo --apo-root /path/to/apo
python workflows/mdan/network/network.py full --state holo --holo-root /path/to/holo
```

Before moving or changing method-bearing code here, compare the behavior against
the existing committed VarMDyn workflow, then document only the generic public
command path.

Method parity means preserving the DyNetAn settings and preparation logic. Exact
network residues may differ across trajectory ensembles or independently
prepared structures.

Figure/table outputs:

- Overlap table: `tables/from_run/network_overlap_apo_vs_holo.csv`.
- Residue-frequency table: `tables/from_run/network_residue_transition_frequency.csv`.
- Network pathway comparison: `figures/network_pathway_comparison.png`.
- Structural residue-remodel composite: `figures/network_residue_remodel.png`
  and `figures/network_residue_remodel.svg`.

For exact residue-remodel surface-panel framing against a known reference
structure set, pass generic reference PDBs:

```bash
bash scripts/run_analysis.sh network figures --state all \
  --remodel-apo-reference /path/to/apo_reference.pdb \
  --remodel-holo-reference /path/to/holo_reference.pdb
```

Those references are used only to align temporary ChimeraX render inputs under
`runs/`; prepared VarMDyn outputs are not changed.

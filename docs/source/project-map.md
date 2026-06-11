# Project Map

This page shows the main folders in a local VarMDyn checkout.

```text
VarMDyn/
  README.md
  envs/
  scripts/
  workflows/
    clustering/
    varmodel/
    md/
    mdan/
  docs/
  data/
```

## 1. Source Folders

| Folder | Contents |
|---|---|
| `envs/` | Conda environment definitions. |
| `scripts/` | Setup, checks, and top-level workflow helpers. |
| `workflows/clustering/` | rSASA, exposure, C-alpha/COM clustering, reports, and plots. |
| `workflows/varmodel/` | MODELLER mutation workflow and run wrapper. |
| `workflows/md/` | Apo/holo simulation control layer, dry-run stages, checks, and HPC bridge commands. |
| `workflows/mdan/` | RMSD, RMSF, displacement, network, and rendering workflows. |
| `docs/source/` | MkDocs documentation source. |

## 2. Run Folders

| Folder | Use |
|---|---|
| `data/` | User-supplied data, fetched outputs, and generated runs. |

For HPC runs, `VARMDYN_RUN_ROOT` can point to scratch or another external run
folder.

## 3. Module Entry Points

| Module | Start here | Environment | Typical output |
|---|---|---|---|
| `clustering` | `bash scripts/run_clustering.sh` | `varmdyn_env` | `data/clustering/` |
| `varmodel` | `bash scripts/run_varmodel.sh --dry-run` | `varmdyn_modeller` | `data/varmodel/` |
| `md/apo` | `bash scripts/run_md.sh status --state apo` | local `varmdyn_env`; remote HPC control env | `data/md/apo/` |
| `md/holo` | `bash scripts/run_md.sh status --state holo` | local `varmdyn_env`; `varmdyn_pymol` for transfer | `data/md/holo/` |
| `mdan/rms` | `bash scripts/run_analysis.sh rms plan --state apo --start 25 --end 29` | local `varmdyn_env`; remote AMBER modules | `data/mdan/rms/` |
| `mdan/rms/rmsd` | `bash scripts/run_analysis.sh rmsd all` | `varmdyn_env` | `data/mdan/rms/rmsd/` |
| `mdan/rms/rmsf` | `bash scripts/run_analysis.sh rmsf all` | `varmdyn_env` | `data/mdan/rms/rmsf/` |
| `mdan/dynamics` | `bash scripts/run_dynamics_local.sh` | `varmdyn_env` | `data/mdan/dynamics/` |
| `mdan/network` | `python workflows/mdan/network/network.py --help` | `varmdyn_env`; `varmdyn_dynetan` for replay | `data/mdan/network/` |
| `mdan/function/full` | `python workflows/mdan/function/full/schematic.py` | `varmdyn_env` | `data/function/full/` |
| `mdan/function/kinase` | `python workflows/mdan/function/kinase/annotation.py` | `varmdyn_env`; `varmdyn_pymol` for PyMOL renders | `data/function/kinase/` |
| `mdan/function/msa` | `python workflows/mdan/function/msa/msa.py` | `varmdyn_env` | `data/function/msa/` |
| `mdan/function/mechanism` | `python workflows/mdan/function/mechanism/mechanism_split.py --help` | `varmdyn_env` | `data/function/mechanism/` |

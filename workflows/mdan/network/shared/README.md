# Network Shared

This folder is a standalone dynamic-network packet. A collaborator can download
only this folder, place it in a local or HPC working directory, point it to
simulation topology/trajectory files, and run the network workflow without the
rest of VarMDyn.

The packet includes:

```text
network_shared.py          main CLI: prepare, run, compare, render, full
run_network_array.slurm    Slurm array runner for one state and many variants
create_dynetan_env.sh      conda environment builder for DyNetAn
env.sh.example             editable path template
sync_code_to_hpc.sh        local-to-HPC code sync helper
submit_network_array.sh    HPC submit helper
fetch_network_results.sh   HPC-to-local lightweight result fetch helper
check_shared_packet.sh     local packet sanity check
```

## 1. What The Workflow Does

For each state and variant, the workflow:

1. reads prepared protein-only inputs when available, or raw simulation chunks
   when explicitly requested;
2. keeps the prepared-input route separate from the raw-input convenience route;
3. writes prepared topology, sampled NetCDF, PDB, PSF, and DCD files under
   `data/network/full/prepared/<state>/<variant>/`;
4. runs DyNetAn on the prepared PDB/PSF/DCD pair;
5. writes top-node, top-edge, bottleneck, and network report files under
   `data/network/full/dynetan/<state>/<variant>/`;
6. compares WT top-25 bottleneck residues with each variant;
7. fetches only lightweight CSV/TXT/PDB files back to the local machine.

The PDB used for local rendering is generated from the same simulation input:

```text
data/network/full/prepared/<state>/<variant>/<variant>.pdb
```

## 2. Download Only This Folder

Recommended folder-only download:

```bash
svn export https://github.com/paulshamrat/VarMDyn/trunk/workflows/mdan/network/shared network_shared
cd network_shared
```

If `svn` is not available, use git sparse checkout:

```bash
git clone --filter=blob:none --sparse https://github.com/paulshamrat/VarMDyn.git VarMDyn_sparse
cd VarMDyn_sparse
git sparse-checkout set workflows/mdan/network/shared
cp -R workflows/mdan/network/shared ../network_shared
cd ../network_shared
```

You can also copy this folder manually from a VarMDyn checkout and rename it
`network_shared`.

Check that the packet is complete:

```bash
bash check_shared_packet.sh
python network_shared.py --help
```

## 3. Software Requirements

The packet uses different tools for local coordination, HPC analysis, and
optional rendering.

Required locally:

```text
bash
python 3.10 or newer
ssh and rsync, if syncing to HPC from a local machine
```

Required on HPC for `prepare`, `run`, and `full`:

```text
Slurm, for array submission
conda, mamba, Miniforge, Mambaforge, or Anaconda
AmberTools/cpptraj on PATH
```

The DyNetAn conda environment is created by:

```bash
bash create_dynetan_env.sh
```

That script creates `varmdyn_dynetan` by default and installs the Python stack
needed by `network_shared.py`:

```text
python 3.10
dynetan 2.2.2
MDAnalysis 2.9
ParmEd
NumPy
SciPy
pandas
networkx
matplotlib
numba
ipywidgets/traitlets
python-louvain
```

Check the environment after installation:

```bash
conda activate varmdyn_dynetan
export PYTHONNOUSERSITE=1
export NUMBA_CACHE_DIR="${PWD}/data/numba_cache"
mkdir -p "$NUMBA_CACHE_DIR"
python -c "import dynetan, MDAnalysis, parmed, networkx; print('network environment OK')"
cpptraj -h | head
```

Optional local rendering:

```text
PyMOL on PATH for `python network_shared.py render`
ChimeraX, only if you use separate surface-rendering scripts
```

If your HPC uses environment modules, load conda and AmberTools before running
the packet. Example module names vary by institution:

```bash
module load miniforge3
module load amber
```

## 4. Local Setup

From the local `network_shared` folder:

```bash
bash check_shared_packet.sh
source env.sh.example
```

Edit the path exports for your machine/account. Optional local rendering needs
PyMOL on `PATH`; ChimeraX can be used separately for publication-style surfaces
if your lab has its own rendering scripts.

## 5. Sync Code From Local To HPC

Before you can set up the HPC environment or run the arrays, you must first copy this packet from your local computer to the HPC cluster.

From the local `network_shared` folder:

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_REPO=/path/to/hpc/network_shared
bash sync_code_to_hpc.sh
```

The sync helper copies the packet code and excludes the generated `data/` folder.

If your site needs a custom SSH command, set:

```bash
export VARMDYN_SSH_COMMAND='ssh'
export VARMDYN_RSYNC_SSH="$VARMDYN_SSH_COMMAND"
```

## 6. HPC Setup

Once the packet is synced to your HPC working directory, SSH into the cluster and create the DyNetAn environment there:

```bash
cd /path/to/hpc/network_shared
bash create_dynetan_env.sh
source env.sh.example
export VARMDYN_APO_ROOT=/path/to/apo/simulation/root
export VARMDYN_HOLO_ROOT=/path/to/holo/simulation/root
```

The environment script expects `conda` on `PATH`. On many HPC systems this means loading a Miniforge, Mambaforge, or Anaconda module first.

If the environment already exists but does not match the required stack, rebuild it once:

```bash
VARMDYN_DYNETAN_RECREATE=1 bash create_dynetan_env.sh
```

The script uses `conda env create` by default. If your site has a working `mamba` installation and you prefer it:

```bash
VARMDYN_CONDA_CREATE_TOOL=mamba bash create_dynetan_env.sh
```

## 7. Expected Simulation Layout (On HPC)

Because MD trajectories are incredibly large, the DyNetAn calculations are performed directly on the HPC cluster. 

On your **HPC environment**, you must define one or both simulation roots where your trajectories physically reside. You can set these in your terminal or inside an `env.sh` file:

```bash
# Exported on the HPC:
export VARMDYN_APO_ROOT=/path/to/apo/simulation/root
export VARMDYN_HOLO_ROOT=/path/to/holo/simulation/root
```

Each root should contain variant folders that start with a 2-digit number and an underscore (e.g., `01_WT`). The script automatically scans the root and discovers them:

```text
/path/to/apo/simulation/root/
├── 01_WT/
├── 02_L119R/
├── 03_D193H/
├── 04_G202E/
├── 05_Q219K/
└── 06_C291Y/
```

### 3.1 Preferred Input: Prepared Network Files

For reproducible network comparisons, use a pre-stripped topology and a
pre-concatenated 750-frame trajectory. This matches the analysis convention used
for the manuscript-style replay.

By default, `VARMDYN_INPUT_MODE=auto` uses this route whenever both files exist:

```text
01_WT/
├── 02.leap/com/cdl.com.striped_v2.prmtop
└── 04.ptraj/com/
    ├── concatenated/
    │   └── production-25-to-29-concatenated-750frames.striped_v2.mdcrd.nc
    └── cr1/traj-proc/
        └── production-25-to-29-500ns.cr1.striped_v2.mdcrd.nc
```

The `cr1` file is used only to write a rendering reference PDB when it is
available. DyNetAn uses the concatenated 750-frame trajectory.

If your prepared filenames differ, set:

```bash
export VARMDYN_INPUT_MODE=prepared
export VARMDYN_PREPARED_TOPOLOGY_SUFFIX='relative/path/to/stripped.prmtop'
export VARMDYN_PREPARED_TRAJ_SUFFIX='relative/path/to/concatenated_750frames.nc'
export VARMDYN_PREPARED_REF_TRAJ_SUFFIX='relative/path/to/reference_first_frame.nc'
```

### 3.2 Optional Input: Raw Trajectory Chunks

Raw mode is useful for a new project that does not already have prepared
network files. It is not the strict replay route.

Set:

```bash
export VARMDYN_INPUT_MODE=raw
```

The raw route expects these paths by default:

```text
01_WT/
├── 02.leap/com/cdl.com.wat.leap.prmtop
└── 03.pmemd/com/
    ├── cr1/
    │   ├── 25md.mdcrd.nc
    │   ├── 26md.mdcrd.nc
    │   └── ...
    ├── cr2/
    └── cr3/
```

If your filenames or folder names differ from this, override the raw paths
before submitting your jobs:

```bash
export VARMDYN_TOPOLOGY_SUFFIX='relative/path/to/system.prmtop'
export VARMDYN_TRAJ_TEMPLATE='03.pmemd/com/{replica}/{chunk}md.mdcrd.nc'
export VARMDYN_REPLICAS='cr1,cr2,cr3'
export VARMDYN_CHUNKS='25,26,27,28,29'
```

Advanced trajectory path options are shown by:

```bash
python network_shared.py prepare --help
```

Manually specify variants instead of auto-discovering:

```bash
export VARMDYN_VARIANTS=01_WT,02_L119R
```

## 8. Submit Array Jobs On HPC

From the HPC `network_shared` folder:

```bash
cd /path/to/hpc/network_shared
source env.sh.example
export VARMDYN_APO_ROOT=/path/to/apo/simulation/root
export VARMDYN_VARIANTS=01_WT,02_L119R
```

For a two-system apo test:

> [!TIP]
> **Copying Commands**: Make sure to copy only the command text (e.g., `bash submit_network_array.sh apo 0-1`) and NOT your terminal prompt (like `(base) [user@node]$`). Including the prompt will cause bash to throw a `syntax error near unexpected token` error.

```bash
bash submit_network_array.sh apo 0-1
```

For all six holo systems:

```bash
unset VARMDYN_VARIANTS
bash submit_network_array.sh holo 0-5
```

The submit wrapper launches one Slurm array for variants and one dependent
compare job. Logs go under:

```text
data/mdan/network_full/logs/
```

If you set a custom `VARMDYN_NETWORK_DATA_ROOT` on HPC, set the same location as
`VARMDYN_HPC_NETWORK_DATA_ROOT` before fetching.

## 9. Fetch Lightweight Results To Local

From the local `network_shared` folder:

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_REPO=/path/to/hpc/network_shared
export VARMDYN_HPC_NETWORK_DATA_ROOT=/path/to/hpc/network_shared/data/network/full
bash fetch_network_results.sh
```

This fetches:

```text
data/network/full/dynetan/**/*.csv
data/network/full/dynetan/**/*.txt
data/network/full/compare/**/*.csv
data/network/full/prepared/**/*.pdb
```

It does not fetch trajectories, DCD files, NetCDF files, PSF files, or topology
files.

## 10. Local Compare And Rendering

After fetching lightweight results:

```bash
python network_shared.py compare \
  --state apo \
  --root data/network/full/prepared/apo \
  --variants 01_WT,02_L119R
```

Render one variant locally with PyMOL:

```bash
python network_shared.py render \
  --state apo \
  --variant 02_L119R
```

## 11. Single-Process Run

For small tests on an interactive HPC node, run one state without Slurm:

```bash
python network_shared.py full \
  --state apo \
  --apo-root "$VARMDYN_APO_ROOT" \
  --variants 01_WT,02_L119R
```

Use Slurm arrays for full production-size analyses.

## 12. Cleanup Rule

Keep generated files under `data/`. This folder is ignored by the
main VarMDyn repository and are safe to remove after you have copied any results
you need.

## 13. Advanced Publication Rendering (CDKL5 Specific)

The default `python network_shared.py render` command is protein-agnostic and will dynamically zoom and color any protein. However, to reproduce the exact CDKL5 publication figures (which feature hand-tuned camera angles, offset labeling, 3D arrows, and surface representations), you must use the specialized scripts bundled in the `remodel/` folder.

### Software Requirements
To run these advanced renders locally on your machine, you must have the following software installed and accessible from your terminal (`PATH`):
- **PyMOL 2.5.0 or newer** (for `render_cartoon.py`)
- **UCSF ChimeraX 1.6 or newer** (for the `.cxc` surface macros)

#### Installing PyMOL
The easiest way to install PyMOL is via `conda-forge`. You can create a dedicated visualization environment:
```bash
conda create -n varmdyn_pymol -c conda-forge pymol-open-source
conda activate varmdyn_pymol
```

#### Installing ChimeraX
ChimeraX is best installed directly from the UCSF website. Download the installer for your operating system (Windows, macOS, or Linux) from:
[https://www.rbvi.ucsf.edu/chimerax/download.html](https://www.rbvi.ucsf.edu/chimerax/download.html)

### 13a. Generating the 3D Structural Bottleneck Map

After you have downloaded the analysis results into the `data/` folder, you can generate all 3D visualizations (PyMOL cartoons, ChimeraX surfaces, and final SVG/PNG composite) at once using the master layout script.

Ensure your visualization conda environment (e.g., `varmdyn_pymol`) is active:

```bash
cd remodel/

# Generate the Structural Bottleneck Remodeling Map
bash build_structural_bottleneck_map.sh
```

This script will automatically locate your downloaded PDBs, launch PyMOL and ChimeraX to render the structures with the ATP/Mg, crop the excess whitespace, and generate the final composite at: `data/network/full/render/structural_bottleneck_remodeling_map.png`

### 13c. Generating 2D Network Grids

In addition to the 3D structural rendering, the `remodel/` folder contains the scripts used to generate the large 6-variant grid showing network pathways for the publication.

Run them from the `remodel/` directory after fetching the data:

```bash
cd remodel/

# Render the individual variant pathways via PyMOL
python render_mutant_network_pathways.py

# Assemble the 6-variant comparison grid
python build_network_pathway_grid.py
```

These scripts will automatically output the final high-resolution PNG: `data/network/full/render/mutant_network_pathway_grid.png`.

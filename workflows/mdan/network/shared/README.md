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

1. reads a simulation topology and trajectory chunks from a simulation folder;
2. strips solvent, ions, and ligand as needed for protein-only DyNetAn nodes;
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
svn export https://github.com/paulshamrat/varmdyn/trunk/workflows/mdan/network/shared network_shared
cd network_shared
```

If `svn` is not available, use git sparse checkout:

```bash
git clone --filter=blob:none --sparse https://github.com/paulshamrat/varmdyn.git varmdyn_sparse
cd varmdyn_sparse
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

## 3. Expected Simulation Layout

Set one or both simulation roots:

```bash
export VARMDYN_APO_ROOT=/path/to/apo/simulation/root
export VARMDYN_HOLO_ROOT=/path/to/holo/simulation/root
```

Each root should contain system folders such as:

```text
01_WT/
02_L119R/
03_D193H/
04_G202E/
05_Q219K/
06_C291Y/
```

By default each system folder is expected to contain:

```text
02.leap/com/cdl.com.wat.leap.prmtop
03.pmemd/com/cr1/25md.mdcrd.nc
03.pmemd/com/cr1/26md.mdcrd.nc
...
03.pmemd/com/cr3/29md.mdcrd.nc
```

If your filenames differ, override these variables before submitting:

```bash
export VARMDYN_TOPOLOGY_SUFFIX='relative/path/to/system.prmtop'
export VARMDYN_VARIANTS=01_WT,02_L119R
```

Advanced trajectory path options are shown by:

```bash
python network_shared.py prepare --help
```

## 4. Software Requirements

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
export NUMBA_CACHE_DIR="${PWD}/runs/numba_cache"
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

## 5. Local Setup

From the local `network_shared` folder:

```bash
bash check_shared_packet.sh
source env.sh.example
```

Edit the path exports for your machine/account. Optional local rendering needs
PyMOL on `PATH`; ChimeraX can be used separately for publication-style surfaces
if your lab has its own rendering scripts.

## 6. HPC Setup

Copy or sync the packet to your HPC working directory, then create the DyNetAn
environment there:

```bash
cd /path/to/hpc/network_shared
bash create_dynetan_env.sh
source env.sh.example
export VARMDYN_APO_ROOT=/path/to/apo/simulation/root
export VARMDYN_HOLO_ROOT=/path/to/holo/simulation/root
```

The environment script expects `conda` on `PATH`. On many HPC systems this means
loading a Miniforge, Mambaforge, or Anaconda module first.

## 7. Sync Code From Local To HPC

From the local `network_shared` folder:

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_REPO=/path/to/hpc/network_shared
bash sync_code_to_hpc.sh
```

The sync helper copies the packet code and excludes generated `data/` and
`runs/` folders.

If your site needs a custom SSH command, set:

```bash
export VARMDYN_SSH_COMMAND='ssh'
export VARMDYN_RSYNC_SSH="$VARMDYN_SSH_COMMAND"
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
runs/mdan/network_full/logs/
```

## 9. Fetch Lightweight Results To Local

From the local `network_shared` folder:

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_REPO=/path/to/hpc/network_shared
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

Keep generated files under `data/` or `runs/`. These folders are ignored by the
main VarMDyn repository and are safe to remove after you have copied any results
you need.

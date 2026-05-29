# Shared Dynamic Network Packet

This folder is a small guide-and-wrapper packet for running the VarMDyn dynamic
network workflow on an HPC system and bringing lightweight results back for
local comparison and rendering.

It uses the main VarMDyn network implementation:

```text
workflows/mdan/network/network.py
workflows/mdan/network/run_network_array.slurm
```

The scripts here only help set paths, sync code, submit Slurm arrays, and fetch
CSV/PDB outputs. They do not duplicate the DyNetAn analysis logic.

## 1. What The Workflow Does

For each state and variant, the workflow:

1. reads a simulation topology and trajectory chunks from the simulation folder;
2. strips solvent, ions, and ligand as needed for protein-only DyNetAn nodes;
3. writes prepared topology, sampled NetCDF, PDB, PSF, and DCD files under
   `data/network/full/prepared/<state>/<variant>/`;
4. runs DyNetAn on the prepared PDB/PSF/DCD pair;
5. writes top-node, top-edge, bottleneck, and network report files under
   `data/network/full/dynetan/<state>/<variant>/`;
6. runs a WT-vs-variant comparison after all variant array tasks succeed;
7. fetches only lightweight CSV/TXT/PDB files back to the local machine.

The PDB used for local rendering comes from the prepared simulation-derived
folder:

```text
data/network/full/prepared/<state>/<variant>/<variant>.pdb
```

That means each rendered variant can use the matching state/variant structure
created from its own simulation input.

## 2. Expected Simulation Layout

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

Advanced trajectory path changes can be passed directly to
`workflows/mdan/network/network.py`; see:

```bash
python workflows/mdan/network/network.py prepare --help
```

## 3. Local Setup

Clone VarMDyn locally:

```bash
git clone https://github.com/paulshamrat/varmdyn.git
cd varmdyn
bash scripts/create_varmdyn_env.sh
conda activate varmdyn_env
python scripts/init_data_layout.py
source data/varmdyn_data.env
```

Optional rendering tools are installed separately. Use PyMOL for cartoon
rendering and ChimeraX for surface rendering if you want to rebuild the network
figure locally.

## 4. HPC Setup

On the HPC system, clone or sync the same VarMDyn repo into a working directory:

```bash
git clone https://github.com/paulshamrat/varmdyn.git
cd varmdyn
```

Create the DyNetAn environment on the HPC system:

```bash
bash workflows/mdan/network/create_dynetan_env.sh
```

Then set runtime paths:

```bash
source workflows/mdan/network/shared/env.sh.example
export VARMDYN_APO_ROOT=/path/to/apo/simulation/root
export VARMDYN_HOLO_ROOT=/path/to/holo/simulation/root
```

Edit the exported paths for your HPC account before running jobs.

## 5. Sync Code From Local To HPC

From the local VarMDyn checkout, set:

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_REPO=/path/to/hpc/varmdyn
```

Then sync code only:

```bash
bash workflows/mdan/network/shared/sync_code_to_hpc.sh
```

This excludes `data/`, `runs/`, `.local_docs/`, and other generated files.

## 6. Submit Array Jobs On HPC

From the HPC VarMDyn checkout:

```bash
cd /path/to/hpc/varmdyn
source workflows/mdan/network/shared/env.sh.example
export VARMDYN_APO_ROOT=/path/to/apo/simulation/root
export VARMDYN_VARIANTS=01_WT,02_L119R
```

For a two-system apo test:

```bash
bash workflows/mdan/network/shared/submit_network_array.sh apo 0-1
```

For all six holo systems:

```bash
unset VARMDYN_VARIANTS
bash workflows/mdan/network/shared/submit_network_array.sh holo 0-5
```

The submit wrapper launches one Slurm array for variants and one dependent
compare job. Logs go under:

```text
runs/mdan/network_full/logs/
```

## 7. Fetch Lightweight Results To Local

From the local VarMDyn checkout:

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_REPO=/path/to/hpc/varmdyn
bash workflows/mdan/network/shared/fetch_network_results.sh
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

## 8. Local Compare And Rendering

After fetching lightweight results:

```bash
conda activate varmdyn_env
python workflows/mdan/network/network.py compare \
  --state apo \
  --root data/network/full/prepared/apo \
  --variants 01_WT,02_L119R
```

Render one variant locally with PyMOL:

```bash
python workflows/mdan/network/network.py render \
  --state apo \
  --variant 02_L119R
```

For the state-paired network figure:

```bash
python scripts/check_data_inputs.py --module network --profile render
bash workflows/mdan/network/remodel.sh
```

## 9. Cleanup Rule

Keep code under `workflows/` and generated files under `data/` or `runs/`.
Those generated folders are ignored by git.

Before committing shared workflow changes, run:

```bash
git status --short
git diff --check
python scripts/check_repo_ready.py
python scripts/check_manuscript_workflows.py --run-root runs
mkdocs build --strict
```

# Analysis

`workflows/mdan/` contains RMSD, RMSF, displacement, network, and structural
rendering scripts used for the analysis parts of the study.

Unless a subsection says otherwise, run analysis commands from the local
VarMDyn repository root in `varmdyn_env`, with inputs and outputs under ignored
`data/`. Commands that submit or inspect HPC replay jobs say so explicitly and
name the remote environment.

Start this page after the MD workflow has produced, copied, or fetched the
analysis inputs needed by the specific analysis module. VarMDyn already keeps
the analysis code under `workflows/mdan/`; the MD
[post-processing step](md.md#10-md-post-processing-before-analysis) only creates
some upstream trajectory products for those modules.

For the current scratch-first workflow, analysis commands that read MD
trajectories should read from the HPC scratch MD tree unless you intentionally
pass another root. The active MD root is the folder containing `apo/` and
`holo/`, usually `/scratch/$USER/VarMDyn/data/md`. RMS and network outputs
created on HPC should stay beside that tree under `/scratch/$USER/VarMDyn/data/mdan/`
until you intentionally sync them to project storage.

Use the MD post-processing step when the downstream analysis needs
`cdl.com.striped_v2.prmtop`, per-replica stripped trajectories, the
three-replica stride-20 concatenated trajectory, or aggregate RMSF sanity
`.agr` files. Do not treat that step as a replacement for the existing `mdan`
analysis modules.

The validated RMSD/RMSF route calculates apo and holo/ATP-Mg per replica from
protein-only stripped trajectories and then averages across `cr1`, `cr2`, and
`cr3`; those tables are not calculated from the three-replica concatenated
trajectory. Existing VarMDyn RMSD/RMSF plotting scripts consume the prepared
source tables or `.agr` inputs described below.

| Analysis module | Existing VarMDyn location | Main input expectation |
|---|---|---|
| RMSD summaries and plots | `workflows/mdan/rmsd/` | RMSD by-system summary tables such as `rmsd_bb_mean_sd.csv`. |
| RMSF plots and overlays | `workflows/mdan/rmsf/` | `.agr` source files or the local RMSF source manifest. |
| N-lobe/Y171 dynamics | `workflows/mdan/dynamics/` | kept displacement TSVs and RMSF source bundles under `data/dynamics/`. |
| Network replay and figures | `workflows/mdan/network/` | prepared protein-only topology plus the stride-20 concatenated trajectory, or fetched replay tables. |
| Structure/function panels | `workflows/mdan/function/` | source structures, sequence/domain tables, and rendered assets under `data/function/` or related `data/` folders. |

## 1.1. Analysis Environments

Use the main local environment for table checks, RMSD/RMSF plotting,
displacement plots, and most structure/function figure scripts:

Run on: local workstation from the repository root. Environment: activate
`varmdyn_env`.

```bash
conda activate varmdyn_env
```

Use `varmdyn_pymol` only when a command renders through PyMOL. The Python
workflow runner can stay in `varmdyn_env`; PyMOL-specific VarMDyn commands use
the local `varmdyn_pymol` environment by default.

Trajectory-level DyNetAn network replay uses `varmdyn_dynetan` on the machine
where the replay job runs. Local table validation and network figure checks do
not require `varmdyn_dynetan`.

| Task | Where | Environment |
|---|---|---|
| RMSD/RMSF/displacement plotting and data checks | local workstation | `varmdyn_env` |
| PyMOL rendered structure panels | local workstation or render host | `varmdyn_pymol` via `VARMDYN_PYMOL_CMD` |
| DyNetAn trajectory replay | local workstation or HPC compute job | `varmdyn_dynetan` |
| HPC network staging/submission helpers | local workstation controlling HPC | `varmdyn_env`; remote replay env from `VARMDYN_CONDA_ENV` |

## 1.2. Runtime Paths

Run on: local workstation from the repository root. Environment:
`varmdyn_env`. Paths: local `data/` plus optional HPC bridge roots.

```bash
export VARMDYN_RUN_ROOT=$PWD/data
export VARMDYN_DATA_ROOT=$PWD/data
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_HPC_HOST=user@login.example.edu
```

For Google Colab analysis, use the dedicated [Google Colab](../setup/colab.md)
page first. Keep Colab paths and HPC paths in separate runs.

For scratch-based MD analysis, first confirm the source root instead of guessing:

Run on: local workstation from the repository root. Environment:
`varmdyn_env`. Remote command prints the HPC-visible MD source and output roots.

```bash
bash scripts/run_analysis.sh rms plan --state apo --start 25 --end 29
```

The printed `md_root` is the trajectory source. The printed `out_root` is where
RMSD/RMSF tables will be written. If you omit `--md-root`, VarMDyn uses the
bridge-configured scratch MD root. Use `--md-root` only when the same completed
simulation tree has been copied to project storage or another HPC-visible path.

## 1.3. Function And Structural Annotations

Function-oriented figure scripts are grouped by purpose:

Path map only. These folders live under the VarMDyn repository root.

```text
workflows/mdan/function/full/       full-length protein schematic
workflows/mdan/function/kinase/     kinase-domain annotation
workflows/mdan/function/msa/        sequence retrieval, MSA, and domain tables
workflows/mdan/function/mechanism/  mechanism composites
```

They read user-supplied source panels and sequence inputs from `data/` and write
generated outputs under `data/mdan/function/`.

### Ligand-Transfer Context

Use this optional figure when you want a source/provenance explanation of where
ligand coordinates came from. It is separate from the MD transfer QA panel: the
MD panel checks the current simulation inputs, while this analysis figure
labels project-specific source structures and ligand/cofactor positions.

This is not part of the normal scratch-based analysis path. Do not run it until
you have placed the required source files under ignored `data/` or you have
intentionally set an internal `VARMDYN_SOURCE_ROOT` for a private
reproducibility check.

Run on: local workstation. Environment: `varmdyn_env`; PyMOL rendering uses
the local `varmdyn_pymol` environment.

```bash
python workflows/mdan/function/kinase/atpmg_context.py \
  --homology data/function/atpmg_context/homology.pdb \
  --ref4bgq data/function/atpmg_context/4BGQ.pdb \
  --ref8fp5 data/function/atpmg_context/8FP5.pdb \
  --atp-on-hm data/function/atpmg_context/ATP_on_hm.mol2 \
  --r38-on-hm data/function/atpmg_context/38R_on_hm.mol2 \
  --out data/md/figures/atpmg_context_panel.png
```

For public/generic use, keep this as a project-specific optional figure and
provide your own source structures under `data/`. Private reproducibility
checks may set `VARMDYN_SOURCE_ROOT` in an ignored local shell or note file,
but that is not part of the public analysis route.

## 1.4. RMSD

### 1.4.1. Build RMSD/RMSF Tables From MD Outputs

After MD post-processing has completed, build analysis2-style RMSD and RMSF
tables from the per-replica stripped trajectories. This route uses each
replica separately and then writes mean/SD tables across `cr1`, `cr2`, and
`cr3`; it does not calculate RMSD/RMSF from the three-replica concatenated
network trajectory.

Run on: local workstation. Environment: local `varmdyn_env`; remote cpptraj
jobs use HPC AMBER modules through Slurm. Omit `--md-root` to use the
bridge-configured scratch MD root. The default output root is the sibling
analysis folder, for example `/scratch/$USER/VarMDyn/data/mdan/rms` when the MD
root is `/scratch/$USER/VarMDyn/data/md`.

```bash
# Plan only: show MD source root, output root, variants, and target files.
bash scripts/run_analysis.sh rms plan --state apo --start 25 --end 29
bash scripts/run_analysis.sh rms plan --state holo --start 25 --end 29

# Submit RMSD/RMSF table generation.
bash scripts/run_analysis.sh rms submit --state apo --start 25 --end 29 --run
bash scripts/run_analysis.sh rms submit --state holo --start 25 --end 29 --run

# If submit says all selected variants are already complete, no Slurm job was
# submitted for that state. Otherwise monitor until the arrays finish.
bash scripts/run_md.sh slurm --execute
bash scripts/run_analysis.sh rms check --state apo --start 25 --end 29
bash scripts/run_analysis.sh rms check --state holo --start 25 --end 29
```

RMS submit is guarded. It queues only variants with missing RMSD/RMSF outputs
and submits nothing when the selected state/window is already complete. Use
`--force` only when intentionally regenerating existing RMS tables.

Expected outputs:

```text
data/mdan/rms/rmsd/by_system/apo/<variant>/rmsd_bb_mean_sd.csv
data/mdan/rms/rmsd/by_system/atpmg/<variant>/rmsd_bb_mean_sd.csv
data/mdan/rms/rmsf/by_system/apo/<variant>/rmsf_mean_sd.csv
data/mdan/rms/rmsf/by_system/atpmg/<variant>/rmsf_mean_sd.csv
```

For the standard chunks `25-29` window, a completed RMSD table should contain
one header plus 25,000 frames per variant/state. A completed RMSF table should
contain one header plus one row per protein residue.

If RMS submit fails with unequal replica lengths, rerun the MD post-processing
check first. A `BADFRAMES` result in post-processing means the analysis source
exists but is not valid for RMS averaging yet.

Use `--variants WT,MUT1` for a small test before running all systems.

### 1.4.2. Plot Existing RMSD Source Tables

Inspect available options:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python workflows/mdan/rmsd/summarize.py --help
python workflows/mdan/rmsd/plot.py --help
```

The plotting scripts consume existing RMSD source tables and write outputs
under:

```text
data/mdan/rmsd/
```

## 1.5. RMSF And Dynamics

This section covers residue fluctuation (RMSF) overlay plotting and local dynamics displacement calculations.

### 1.5.1. RMSF Figures

RMSF figure scripts use `.agr` files or generated RMSF summaries:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python workflows/mdan/rmsf/overlay.py --help
python workflows/mdan/rmsf/supplementary.py --help
```

Common variables:

Run on: local workstation from the repository root. Environment:
`varmdyn_env`. Paths: ignored local RMSF source bundle under `data/`.

```bash
export VARMDYN_RMSF_SOURCE_INPUT_ROOT=$VARMDYN_DATA_ROOT/rmsf_source_inputs
export VARMDYN_RMSF_SOURCE_MANIFEST=$VARMDYN_DATA_ROOT/rmsf_source_input_manifest.tsv
```

### 1.5.2. N-Lobe/Y171 RMSF And Displacement

Local plotting from kept displacement/RMSF tables:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
export DYNAMICS_NLOBE_Y171_INPUT_ROOT=$VARMDYN_DATA_ROOT/dynamics
bash scripts/run_dynamics_local.sh
```

Expected input layout:

```text
$DYNAMICS_NLOBE_Y171_INPUT_ROOT/
  kept_tsvs/
    nlobe_apo/
    nlobe_holo/
    y171_apo/
    y171_holo/
```

## 1.6. Network Analysis

This workflow validates and replays the DyNetAn residue-communication analysis
used for the network tables and the network-remodeling figure.

### 1.6.1. Folder Logic

VarMDyn keeps code and data separate:

Path map only.

```text
workflows/   code only
data/        user-supplied inputs, fetched CSVs, and generated outputs/figures
```

The `data/` folder is ignored by git. A user can clone the
repo, create this layout, place the required data files there, and run the same
commands without knowing another user's folder structure.

Create the local layout:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
cd /path/to/VarMDyn
conda activate varmdyn_env
python scripts/data/init_data_layout.py
source data/varmdyn_data.env
```

### 1.6.2. What DyNetAn Does Here

DyNetAn builds residue communication networks from MD trajectories. Each protein
residue is a node. Edges are retained for residue pairs that remain in contact
across the sampled trajectory, and generalized correlations are used to weight
communication between nodes.

The replay protocol uses:

- concatenated three-replica trajectories;
- 750 sampled frames;
- 4.5 A residue-contact cutoff;
- 75% contact-persistence cutoff;
- same-residue and consecutive-residue contact exclusion;
- protein-only nodes for both apo and holo/ATP-Mg states;
- top-25 bottleneck residues by edge-betweenness-derived score;
- WT-referenced lost/gained residue comparisons across the configured variants.

### 1.6.3. Put Data In The VarMDyn Layout

For table validation and rendering, place or link files here. This is a folder
map, not a shell command block:

```text
data/network/tables/network_residue_transition_frequency.csv
data/network/tables/network_overlap_apo_vs_atpmg.csv
data/structures/apo/WT.apo.pdb
data/structures/holo_atpmg/WT.keepATPmg.pdb
```

Fetched DyNetAn replay outputs use this layout. This is also a folder map:

```text
data/network/replay/apo/$VARMDYN_DYNETAN_STAGE_TAG/
  TutorialResults_<SYSTEM>/
  _comparisons_concatenated/

data/network/replay/holo/$VARMDYN_DYNETAN_STAGE_TAG/
  TutorialResults_<SYSTEM>/
  _comparisons_concatenated/
```

For full trajectory-level replay from simulation roots, VarMDyn uses one
consolidated CLI:

Run on: machine with trajectory inputs. Environment: `varmdyn_dynetan` for
trajectory-level replay.

```bash
python workflows/mdan/network/network.py full --state apo
python workflows/mdan/network/network.py full --state holo
python workflows/mdan/network/network.py full --state all
```

It discovers system folders from the selected state root, keeps WT first when a
WT folder is present, writes trajectory-derived outputs under ignored
`data/mdan/network/full/`, writes run logs under `data/mdan/network/runs/`, and
skips completed DyNetAn outputs unless `--force` is used.

Residue renders from this workflow use the prepared PDB for the same state and
variant by default:

```text
data/mdan/network/full/prepared/<state>/<variant>/<variant>.pdb
```


If you have a local read-only source tree containing reference tables and replay
CSVs, copy only the lightweight inputs into `data/`:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
export VARMDYN_SOURCE_ROOT=/path/to/source/tree
python scripts/data/sync_data_from_sources.py --module network
source data/varmdyn_data.env
```

This does not modify the source tree and does not place copied data under git
tracking, because `data/` is ignored.

Check the local data layout:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python scripts/checks/check_data_inputs.py --module network --profile tables
python scripts/checks/check_data_inputs.py --module network --profile render
python scripts/checks/check_data_inputs.py --module network --profile apo-replay
```

Run the holo replay check only after you have copied or fetched a matching holo
DyNetAn replay directory:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python scripts/checks/check_data_inputs.py --module network --profile holo-replay
```

### 1.6.4. Configure The DyNetAn Replay Environment

Local table validation and figure rendering use `varmdyn_env`. The trajectory-level network replay also needs DyNetAn. Create the optional replay environment on the machine where the replay job will run:

Run on: local workstation or HPC system that will execute DyNetAn replay.
Environment: create or activate `varmdyn_dynetan`.

```bash
conda env create -f envs/varmdyn_dynetan.yml
conda activate varmdyn_dynetan
python -c "import dynetan, traitlets, ipywidgets, networkx, MDAnalysis; import importlib.metadata as md; print('DyNetAn environment OK:', md.version('dynetan'))"
```

If your HPC system already has an equivalent environment, set `VARMDYN_CONDA_ENV` to that environment name. The tested replay stack uses DyNetAn 2.2.2 with MDAnalysis 2.9.

### 1.6.5. Configure HPC Replay Paths

Set these for HPC replay work:

Run on: local workstation before bridge/HPC replay commands, or inside the HPC
checkout for manual repair. Environment: `varmdyn_env` for local orchestration;
remote replay uses `VARMDYN_CONDA_ENV`.

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_USER=user
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_DYNETAN_WORK=/path/to/dynetan_work
export VARMDYN_CONDA_ENV=varmdyn_dynetan
export VARMDYN_DYNETAN_STAGE_TAG=concat750_w1_s750_apo_validation_YYYYMMDD
```

Verify that SSH can run a real command:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
ssh "$VARMDYN_HPC_HOST" "hostname"
```

Check the remote DyNetAn work directory:

Run on: local workstation. Environment: `varmdyn_env`; remote replay jobs use
the conda environment named by `VARMDYN_CONDA_ENV`.

```bash
python scripts/checks/check_data_inputs.py --module network --profile remote --remote --timeout-seconds 60
```

### 1.6.6. Validate Existing Tables

With `source data/varmdyn_data.env` loaded, the validator uses the standard
`data/` paths automatically:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py \
  --outdir data/mdan/network_validation/manuscript_tables
```

Expected table validation:

```text
OK frequency: 25 rows, 5 columns
OK overlap: 5 rows, 9 columns
```

### 1.6.7. Run Full Network Analysis From Simulation Roots

Set the apo and/or holo roots. Each root should contain one WT folder and any
variant folders you want to analyze:

Run on: machine with trajectory inputs. Environment: `varmdyn_dynetan`. Paths:
state roots containing prepared or raw simulation folders.

```bash
export VARMDYN_APO_ROOT=/path/to/apo/root
export VARMDYN_HOLO_ROOT=/path/to/holo/root
```

Run all discovered apo systems:

Run on: machine with trajectory inputs. Environment: `varmdyn_dynetan`.

```bash
python workflows/mdan/network/network.py full --state apo
```

Run all discovered holo/ATP-Mg systems:

Run on: machine with trajectory inputs. Environment: `varmdyn_dynetan`.

```bash
python workflows/mdan/network/network.py full --state holo
```

Run both states:

Run on: machine with trajectory inputs. Environment: `varmdyn_dynetan`.

```bash
python workflows/mdan/network/network.py full --state all
```

To test only a subset:

Run on: machine with trajectory inputs. Environment: `varmdyn_dynetan`.

```bash
python workflows/mdan/network/network.py full \
  --state apo \
  --variants WT,MUT1
```

For Slurm:

Run on: HPC system. Environment: Slurm job activates the configured DyNetAn
environment, usually `varmdyn_dynetan`.

```bash
mkdir -p data/mdan/network/runs/logs
sbatch workflows/mdan/network/run_full_network.slurm apo
sbatch workflows/mdan/network/run_full_network.slurm holo
sbatch workflows/mdan/network/run_full_network.slurm all
```

For production-sized runs, prefer the array wrapper. Each variant runs in a
separate Slurm task, then one dependent compare job builds the WT-referenced
lost/gained tables:

Run on: HPC system. Environment: Slurm job activates the configured DyNetAn
environment, usually `varmdyn_dynetan`.

```bash
export VARMDYN_APO_ROOT=/path/to/apo/root
export VARMDYN_HOLO_ROOT=/path/to/holo/root
export VARMDYN_DYNETAN_STAGE_TAG=varmdyn_full_holo

mkdir -p data/mdan/network/runs/logs
jobid=$(sbatch --parsable --array=0-5 workflows/mdan/network/run_network_array.slurm holo variant)
sbatch --dependency=afterok:${jobid} workflows/mdan/network/run_network_array.slurm holo compare
```

For VarMDyn MD outputs that have already completed the 500 ns post-processing
step, point the array wrapper at the prepared topology and concatenated
trajectory files. This route supports plain variant folders such as `WT` and
`L119R`; it does not require numeric variant prefixes.

Run on: HPC system from the synced VarMDyn project checkout. Environment:
Slurm job activates `varmdyn_dynetan`; AMBER-compatible tools provide
`cpptraj` during preparation.

```bash
export VARMDYN_APO_ROOT=/path/to/md/apo
export VARMDYN_HOLO_ROOT=/path/to/md/holo
export VARMDYN_NETWORK_DATA_ROOT=/path/to/VarMDyn/data/mdan/network/full
export VARMDYN_NETWORK_RUN_ROOT=/path/to/VarMDyn/data/mdan/network/runs
export VARMDYN_TOPOLOGY_SUFFIX=02.leap/com/cdl.com.striped_v2.prmtop
export VARMDYN_TRAJ_TEMPLATE=04.ptraj/com/concatenated/production-25-to-29-concatenated-750frames.striped_v2.mdcrd.nc
export VARMDYN_REPLICAS=combined
export VARMDYN_CHUNKS=25
export VARMDYN_VARIANTS=WT,MUT1
export VARMDYN_WT=WT
export VARMDYN_DYNETAN_STAGE_TAG=varmdyn_500ns

mkdir -p data/mdan/network/runs/logs
jobid=$(sbatch --parsable --array=0-1 workflows/mdan/network/run_network_array.slurm apo variant)
sbatch --dependency=afterok:${jobid} workflows/mdan/network/run_network_array.slurm apo compare
```

For active scratch analysis, keep this alongside the MD scratch tree:

```bash
export VARMDYN_APO_ROOT=/scratch/$USER/VarMDyn/data/md/apo
export VARMDYN_HOLO_ROOT=/scratch/$USER/VarMDyn/data/md/holo
export VARMDYN_NETWORK_DATA_ROOT=/scratch/$USER/VarMDyn/data/mdan/network/full
export VARMDYN_NETWORK_RUN_ROOT=/scratch/$USER/VarMDyn/data/mdan/network/runs
```

This keeps generated simulation data in `data/md/` and generated MD-analysis
products in `data/mdan/`, matching the repository module layout.

For a two-system test, set the variant list and shrink the array:

Run on: HPC system. Environment: Slurm job activates the configured DyNetAn
environment, usually `varmdyn_dynetan`.

```bash
export VARMDYN_VARIANTS=WT,MUT1
mkdir -p data/mdan/network/runs/logs
jobid=$(sbatch --parsable --array=0-1 workflows/mdan/network/run_network_array.slurm apo variant)
sbatch --dependency=afterok:${jobid} workflows/mdan/network/run_network_array.slurm apo compare
```

A standalone shared packet for collaborators is available in:

```text
workflows/mdan/network/shared/
```

It can be downloaded by itself and contains its own network runner, DyNetAn
environment builder, Slurm array script, and helpers for syncing code to HPC,
submitting array jobs, and fetching only lightweight CSV/TXT/PDB outputs back to
the local checkout.

The shared packet has two input routes:

- `VARMDYN_INPUT_MODE=prepared`: use a pre-stripped topology and a
  pre-concatenated stride-20 trajectory. Use this for validated replay.
- `VARMDYN_INPUT_MODE=raw`: build protein-only inputs from raw trajectory
  chunks. Use this for a new project that does not already have prepared
  network files.

The default is `auto`, which prefers prepared inputs when both files are present:

Path map only.

```text
<simulation_root>/<variant>/02.leap/com/cdl.com.striped_v2.prmtop
<simulation_root>/<variant>/04.ptraj/com/concatenated/production-25-to-29-concatenated-750frames.striped_v2.mdcrd.nc
```

Raw mode still supports chunked inputs such as:

Path map only.

```text
<simulation_root>/<variant>/02.leap/com/cdl.com.wat.leap.prmtop
<simulation_root>/<variant>/03.pmemd/com/cr1/25md.mdcrd.nc
```

For a strict replay, point the state root to the folder that already contains
the prepared files, then run the array wrapper from inside the shared packet:

Run on: HPC system inside `workflows/mdan/network/shared/`. Environment:
the shared wrapper uses its own configured DyNetAn environment.

```bash
source env.sh.example
export VARMDYN_INPUT_MODE=prepared
export VARMDYN_APO_ROOT=/path/to/apo/prepared/root
export VARMDYN_VARIANTS=WT,MUT1
bash submit_network_array.sh apo 0-1
```

### 1.6.8. Replay Apo Network Analysis From An Existing DyNetAn Work Directory

Stage the sbatch script:

Run on: local workstation. Environment: `varmdyn_env`; remote job execution
uses the environment named by `VARMDYN_CONDA_ENV`.

```bash
python workflows/mdan/network/network.py hpc-stage
```

Submit a new replay job:

Run on: local workstation. Environment: `varmdyn_env`; remote job execution
uses `VARMDYN_CONDA_ENV`.

```bash
python workflows/mdan/network/network.py hpc-submit
```

Check status:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python workflows/mdan/network/network.py hpc-status
```

Wait for a known job id:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python workflows/mdan/network/network.py hpc-wait --job-id JOBID
```

After the array job completes, rebuild comparison tables on HPC:

Run on: local workstation. Environment: `varmdyn_env`; remote comparison uses
`VARMDYN_CONDA_ENV`.

```bash
python workflows/mdan/network/network.py hpc-compare
```

Fetch lightweight CSV outputs into the standard local data layout:

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python workflows/mdan/network/network.py hpc-fetch
```

### 1.6.9. Validate Fetched Apo Replay Outputs

Run on: local workstation. Environment: `varmdyn_env`.

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py \
  --stage-tag $VARMDYN_DYNETAN_STAGE_TAG \
  --outdir data/mdan/network_validation/$VARMDYN_DYNETAN_STAGE_TAG
```

Expected replay validation:

```text
OK frequency: 25 rows, 5 columns
OK overlap: 5 rows, 9 columns
OK apo frequency replay: 12 rows compared
OK apo overlap replay: 20 fields compared
```

### 1.6.10. Build The Associated Network Figure

The network-remodel figure reads apo and holo/ATP-Mg structure files from
`data/structures/` by default and writes rendered outputs to `data/`:

Run on: local workstation. Environment: `varmdyn_env`; PyMOL is delegated
through `VARMDYN_PYMOL_CMD`, while ChimeraX and Inkscape must be available on
the system PATH.

```bash
python scripts/checks/check_data_inputs.py --module network --profile render
bash workflows/mdan/network/remodel.sh
```

Expected output:

```text
data/mdan/network/network_remodel_final.svg
data/mdan/network/network_remodel_final_preview.png
```

The build uses PyMOL for residue-coloring cartoon panels, ChimeraX for surface
context panels, and Inkscape for SVG-to-PNG previews.

# Dynamic Network Analysis

This workflow validates and replays the DyNetAn residue-communication analysis
used for the network tables and the network-remodeling figure.

## 1. Folder Logic

VarMDyn keeps code and data separate:

```text
workflows/   code only
data/        user-supplied inputs and fetched lightweight CSV outputs
runs/        generated validation reports and rendered figures
```

The `data/` and `runs/` folders are ignored by git. A user can clone the
repo, create this layout, place the required data files there, and run the same
commands without knowing another user's folder structure.

Create the local layout:

```bash
cd /path/to/varmdyn
conda activate varmdyn_env
python scripts/init_data_layout.py
source data/varmdyn_data.env
```

## 2. What DyNetAn Does Here

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
- WT-referenced lost/gained residue comparisons across the five variants.

## 3. Put Data In The VarMDyn Layout

For table validation and rendering, place or link files here. This is a folder
map, not a shell command block:

```text
data/network/tables/network_residue_transition_frequency.csv
data/network/tables/network_overlap_apo_vs_atpmg.csv
data/structures/apo/01_WT.apo.pdb
data/structures/holo_atpmg/01_WT.keepATPmg.pdb
```

Fetched DyNetAn replay outputs use this layout. This is also a folder map:

```text
data/network/replay/apo/$VARMDYN_DYNETAN_STAGE_TAG/
  TutorialResults_CDKL5/
  _comparisons_concatenated/

data/network/replay/holo/$VARMDYN_DYNETAN_STAGE_TAG/
  TutorialResults_CDKL5/
  _comparisons_concatenated/
```

For full trajectory-level replay from simulation roots, VarMDyn uses one
consolidated CLI:

```bash
python workflows/mdan/network/network.py full --state apo
python workflows/mdan/network/network.py full --state holo
python workflows/mdan/network/network.py full --state all
```

It discovers system folders matching `NN_NAME`, keeps `01_WT` first, writes
under ignored `data/network/full/` and `runs/mdan/network_full/`, and skips
completed DyNetAn outputs unless `--force` is used.

Residue renders from this workflow use the prepared PDB for the same state and
variant by default:

```text
data/network/full/prepared/<state>/<variant>/<variant>.pdb
```


If you have a local read-only source tree containing reference tables and replay
CSVs, copy only the lightweight inputs into `data/`:

```bash
export VARMDYN_SOURCE_ROOT=/path/to/source/tree
python scripts/sync_data_from_sources.py --module network
source data/varmdyn_data.env
```

This does not modify the source tree and does not place copied data under git
tracking, because `data/` is ignored.

Check the local data layout:

```bash
python scripts/check_data_inputs.py --module network --profile tables
python scripts/check_data_inputs.py --module network --profile render
python scripts/check_data_inputs.py --module network --profile apo-replay
```

Run the holo replay check only after you have copied or fetched a matching holo
DyNetAn replay directory:

```bash
python scripts/check_data_inputs.py --module network --profile holo-replay
```

## 4. Configure The DyNetAn Replay Environment

Local table validation and figure rendering use `varmdyn_env`. The trajectory-level network replay also needs DyNetAn. Create the optional replay environment on the machine where the replay job will run:

```bash
conda env create -f envs/dynetan_env.yml
conda activate varmdyn_dynetan
python -c "import dynetan, traitlets, ipywidgets, networkx, MDAnalysis; import importlib.metadata as md; print('DyNetAn environment OK:', md.version('dynetan'))"
```

If your HPC system already has an equivalent environment, set `VARMDYN_CONDA_ENV` to that environment name. The tested replay stack uses DyNetAn 2.2.2 with MDAnalysis 2.9.

## 5. Configure HPC Replay Paths

Set these for HPC replay work:

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_USER=user
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_DYNETAN_WORK=/path/to/dynetan_work
export VARMDYN_CONDA_ENV=varmdyn_dynetan
export VARMDYN_DYNETAN_STAGE_TAG=concat750_w1_s750_apo_validation_YYYYMMDD
```

Verify that SSH can run a real command:

```bash
ssh "$VARMDYN_HPC_HOST" "hostname"
```

Check the remote DyNetAn work directory:

```bash
python scripts/check_data_inputs.py --module network --profile remote --remote --timeout-seconds 60
```

## 6. Validate Existing Tables

With `source data/varmdyn_data.env` loaded, the validator uses the standard
`data/` paths automatically:

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py \
  --outdir runs/mdan/network_validation/manuscript_tables
```

Expected table validation:

```text
OK frequency: 25 rows, 5 columns
OK overlap: 5 rows, 9 columns
```

## 7. Run Full Network Analysis From Simulation Roots

Set the apo and/or holo roots. Each root should contain folders such as
`01_WT`, `02_L119R`, and so on:

```bash
export VARMDYN_APO_ROOT=/path/to/legacy/apo/root
export VARMDYN_HOLO_ROOT=/path/to/legacy/holo/root
```

Run all discovered apo systems:

```bash
python workflows/mdan/network/network.py full --state apo
```

Run all discovered holo/ATP-Mg systems:

```bash
python workflows/mdan/network/network.py full --state holo
```

Run both states:

```bash
python workflows/mdan/network/network.py full --state all
```

To test only a subset:

```bash
python workflows/mdan/network/network.py full \
  --state apo \
  --variants 01_WT,02_L119R
```

For Slurm:

```bash
sbatch workflows/mdan/network/run_full_network.slurm apo
sbatch workflows/mdan/network/run_full_network.slurm holo
sbatch workflows/mdan/network/run_full_network.slurm all
```

For production-sized runs, prefer the array wrapper. Each variant runs in a
separate Slurm task, then one dependent compare job builds the WT-referenced
lost/gained tables:

```bash
export VARMDYN_APO_ROOT=/path/to/legacy/apo/root
export VARMDYN_HOLO_ROOT=/path/to/legacy/holo/root
export VARMDYN_DYNETAN_STAGE_TAG=varmdyn_full_holo

jobid=$(sbatch --parsable --array=0-5 workflows/mdan/network/run_network_array.slurm holo variant)
sbatch --dependency=afterok:${jobid} workflows/mdan/network/run_network_array.slurm holo compare
```

For a two-system test, set the variant list and shrink the array:

```bash
export VARMDYN_VARIANTS=01_WT,02_L119R
jobid=$(sbatch --parsable --array=0-1 workflows/mdan/network/run_network_array.slurm apo variant)
sbatch --dependency=afterok:${jobid} workflows/mdan/network/run_network_array.slurm apo compare
```

## 8. Replay Apo Network Analysis From An Existing DyNetAn Work Directory

Stage the sbatch script:

```bash
python workflows/mdan/network/network.py hpc-stage
```

Submit a new replay job:

```bash
python workflows/mdan/network/network.py hpc-submit
```

Check status:

```bash
python workflows/mdan/network/network.py hpc-status
```

Wait for a known job id:

```bash
python workflows/mdan/network/network.py hpc-wait --job-id JOBID
```

After the array job completes, rebuild comparison tables on HPC:

```bash
python workflows/mdan/network/network.py hpc-compare
```

Fetch lightweight CSV outputs into the standard local data layout:

```bash
python workflows/mdan/network/network.py hpc-fetch
```

## 9. Validate Fetched Apo Replay Outputs

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py \
  --stage-tag $VARMDYN_DYNETAN_STAGE_TAG \
  --outdir runs/mdan/network_validation/$VARMDYN_DYNETAN_STAGE_TAG
```

Expected replay validation:

```text
OK frequency: 25 rows, 5 columns
OK overlap: 5 rows, 9 columns
OK apo frequency replay: 12 rows compared
OK apo overlap replay: 20 fields compared
```

## 10. Build The Associated Network Figure

The network-remodel figure reads apo and holo/ATP-Mg structure files from
`data/structures/` by default and writes rendered outputs to `runs/`:

```bash
python scripts/check_data_inputs.py --module network --profile render
bash workflows/mdan/network/remodel.sh
```

Expected output:

```text
runs/mdan/network/network_remodel_final.svg
runs/mdan/network/network_remodel_final_preview.png
```

The build uses PyMOL for residue-coloring cartoon panels, ChimeraX for surface
context panels, and Inkscape for SVG-to-PNG previews.

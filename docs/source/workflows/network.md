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

The manuscript-facing replay uses:

- concatenated three-replica trajectories;
- 750 sampled frames;
- 4.5 A residue-contact cutoff;
- 75% contact-persistence cutoff;
- same-residue and consecutive-residue contact exclusion;
- top-25 bottleneck residues by edge-betweenness-derived score;
- WT-referenced lost/gained residue comparisons across the five variants.

## 3. Put Data In The VarMDyn Layout

For table validation and rendering, place or link files here:

```text
data/network/tables/network_residue_transition_frequency.csv
data/network/tables/network_overlap_apo_vs_atpmg.csv
data/structures/apo/01_WT.apo.pdb
data/structures/holo_atpmg/01_WT.keepATPmg.pdb
```

Fetched DyNetAn replay outputs use this layout:

```text
data/network/replay/apo/$VARMDYN_DYNETAN_STAGE_TAG/
  TutorialResults_CDKL5/
  _comparisons_concatenated/

data/network/replay/holo/$VARMDYN_DYNETAN_STAGE_TAG/
  TutorialResults_CDKL5/
  _comparisons_concatenated/
```

At the moment, the included HPC replay wrapper is the apo replay path. Holo
network rendering is supported through the holo/ATP-Mg structure path above; a
full holo DyNetAn replay needs the corresponding holo DyNetAn work directory.


If you have a local read-only source tree containing the manuscript-facing tables
and replay CSVs, copy only the lightweight inputs into `data/`:

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
python scripts/check_data_inputs.py --module network --profile holo-replay
```

## 4. Configure The DyNetAn Replay Environment

Local table validation and figure rendering use `varmdyn_env`. The trajectory-level network replay also needs DyNetAn. Create the optional replay environment on the machine where the replay job will run:

```bash
conda env create -f envs/dynetan_env.yml
conda activate varmdyn_dynetan
python -c "import dynetan, networkx, MDAnalysis; print('DyNetAn environment OK')"
```

If your HPC system already has an equivalent environment, set `VARMDYN_CONDA_ENV` to that environment name.

## 5. Configure HPC Replay Paths

Set these for HPC replay work:

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_USER=user
export VARMDYN_HPC_PROJECT=/path/to/hpc_project_root
export VARMDYN_DYNETAN_WORK=/path/to/dynetan_work
export VARMDYN_CONDA_ENV=varmdyn_dynetan
export VARMDYN_DYNETAN_STAGE_TAG=concat750_w1_s750_apo_validation_YYYYMMDD
export VARMDYN_SSH_CONTROL_PATH=$HOME/.ssh/hpc.sock
```

Verify that the bridge can run a real command:

```bash
python scripts/check_hpc_bridge.py --timeout-seconds 60
```

If the socket is stale, refresh it:

```bash
rm -f ~/.ssh/hpc.sock
# recreate the socket using your institution's SSH helper or an ssh ControlMaster command
python scripts/check_hpc_bridge.py --timeout-seconds 60
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

## 7. Replay Apo Network Analysis On HPC

Stage the sbatch script:

```bash
python workflows/mdan/network/run_network_replay_hpc.py stage
```

Submit a new replay job:

```bash
python workflows/mdan/network/run_network_replay_hpc.py submit
```

Check status:

```bash
python workflows/mdan/network/run_network_replay_hpc.py status
```

Wait for a known job id:

```bash
python workflows/mdan/network/run_network_replay_hpc.py wait --job-id JOBID
```

After the array job completes, rebuild comparison tables on HPC:

```bash
python workflows/mdan/network/run_network_replay_hpc.py compare
```

Fetch lightweight CSV outputs into the standard local data layout:

```bash
python workflows/mdan/network/run_network_replay_hpc.py fetch
```

## 8. Validate Fetched Apo Replay Outputs

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

## 9. Build The Associated Network Figure

The network-remodel figure reads apo and holo/ATP-Mg structure files from
`data/structures/` by default and writes rendered outputs to `runs/`:

```bash
python scripts/check_data_inputs.py --module network --profile render
bash workflows/mdan/figures/network_remodel_integrated_review/scripts/build_final_figure.sh
```

Expected output:

```text
runs/mdan/figures/network_remodel_integrated_review/network_remodel_final.svg
runs/mdan/figures/network_remodel_integrated_review/network_remodel_final_preview.png
```

The build uses PyMOL for residue-coloring cartoon panels, ChimeraX for surface
context panels, and Inkscape for SVG-to-PNG previews.

# Dynamic Network Analysis

This workflow replays and validates the DyNetAn-based residue-communication
analysis used for the network tables and network-remodeling figure.

## 1. What DyNetAn Does Here

DyNetAn builds residue communication networks from MD trajectories. In this
project, each protein residue is treated as a node. Edges are retained for
residue pairs that remain in contact across the sampled trajectory, and DyNetAn
uses generalized correlations to weight communication between nodes.

The manuscript-facing replay uses:

- concatenated three-replica trajectories;
- 750 sampled frames;
- 4.5 A residue-contact cutoff;
- 75% contact-persistence cutoff;
- same-residue and consecutive-residue contact exclusion;
- top-25 bottleneck residues by edge-betweenness-derived score;
- WT-referenced lost/gained residue comparisons across the five variants.

The VarMDyn wrapper does not store trajectories or DyNetAn outputs in git. It
stages scripts to Palmetto, fetches lightweight CSV outputs into ignored local
folders, and validates those outputs against supplied manuscript tables.

## 2. Start From The Repository Root

```bash
cd /path/to/varmdyn
conda activate varmdyn_env

export VARMDYN_RUN_ROOT=$PWD/runs
export VARMDYN_PRIVATE_DATA=$PWD/data_private
export MPLCONFIGDIR=/tmp/varmdyn-matplotlib
mkdir -p "$VARMDYN_RUN_ROOT" "$VARMDYN_PRIVATE_DATA"
```

## 3. Set Network Runtime Variables

Use your private Palmetto paths. Keep these in your shell, not in git:

```bash
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
export VARMDYN_PALMETTO_USER=user
export VARMDYN_PALMETTO_PROJECT=/path/to/private/palmetto_project
export VARMDYN_DYNETAN_WORK=/path/to/private/dynetan_work
export VARMDYN_CONDA_ENV=cdkl5-activation
export VARMDYN_DYNETAN_STAGE_TAG=concat750_w1_s750_apo_validation_YYYYMMDD
export VARMDYN_SSH_CONTROL_PATH=$HOME/.ssh/palmetto.sock
```

## 4. Verify The Palmetto Bridge

Run this before staging or checking remote paths. It checks both the socket and a
real remote command:

```bash
python scripts/check_palmetto_bridge.py --timeout-seconds 10
```

If it reports a missing or stale socket, refresh the bridge in your terminal:

```bash
rm -f ~/.ssh/palmetto.sock
palmettobridge
# approve password/Duo prompt
python scripts/check_palmetto_bridge.py --timeout-seconds 10
```

A good bridge reports a scheduler login node such as
`vm-slurm-p-loginXX.palmetto.clemson.edu` and your Palmetto username.

Then check local and remote network inputs:

```bash
python scripts/check_private_inputs.py --module network
python scripts/check_private_inputs.py --module network --remote --timeout-seconds 10
```

The remote check first verifies `hostname && whoami`; if that fails, refresh the
bridge before continuing.

## 5. Validate Existing Tables

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py \
  --frequency /path/to/private/network_residue_transition_frequency.csv \
  --overlap /path/to/private/network_overlap_apo_vs_atpmg.csv \
  --outdir runs/mdan/network_validation/manuscript_tables
```

Expected local-table validation:

```text
OK frequency: 25 rows, 5 columns
OK overlap: 5 rows, 9 columns
```

## 6. Replay Network Analysis On Palmetto

Stage the sbatch script:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py stage
```

Submit a new replay job:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py submit
```

Check status:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py status
```

Wait for a known job id:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py wait --job-id JOBID
```

After the array job completes, rebuild comparison tables on Palmetto:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py compare
```

Fetch lightweight CSV outputs locally:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py fetch --outdir data_private/network
```

## 7. Validate Fetched Replay Outputs

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py \
  --frequency /path/to/private/network_residue_transition_frequency.csv \
  --overlap /path/to/private/network_overlap_apo_vs_atpmg.csv \
  --apo-results data_private/network/$VARMDYN_DYNETAN_STAGE_TAG/TutorialResults_CDKL5 \
  --apo-comparisons data_private/network/$VARMDYN_DYNETAN_STAGE_TAG/_comparisons_concatenated \
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

## 8. Build The Associated Network Figure

The network-remodel figure uses the recurrent WT-lost/gained residue sets from
the network tables. Rendering requires private apo and ATP-Mg/holo PDB files.
Set them at run time:

```bash
export VARMDYN_NETWORK_APO_PDB=/path/to/private/apo/cdl.com.gas.leap.pdb
export VARMDYN_NETWORK_HOLO_PDB=/path/to/private/atp_mg/cdl.com.gas.leap.pdb

bash workflows/mdan/figures/network_remodel_integrated_review/scripts/build_final_figure.sh
```

The build uses PyMOL for residue-coloring cartoon panels, ChimeraX for surface
context panels, and Inkscape for SVG-to-PNG previews. Outputs are generated under
`workflows/mdan/figures/network_remodel_integrated_review/` and are ignored by
git.

Expected final output:

```text
workflows/mdan/figures/network_remodel_integrated_review/network_remodel_final.svg
workflows/mdan/figures/network_remodel_integrated_review/network_remodel_final_preview.png
```

## 9. Output Locations

```text
data_private/network/$VARMDYN_DYNETAN_STAGE_TAG/
runs/mdan/network_validation/$VARMDYN_DYNETAN_STAGE_TAG/
workflows/mdan/figures/network_remodel_integrated_review/network_remodel_final.svg
```

These outputs are local generated files and are ignored by git.

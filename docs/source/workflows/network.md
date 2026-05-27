# Dynamic Network Analysis

The network workflow validates and replays DyNetAn-based residue communication
analysis.

## 1. What This Workflow Does

1. Checks that required input paths are configured.
2. Validates network frequency and overlap tables.
3. Stages and runs a DyNetAn replay on Palmetto or another compatible HPC system.
4. Builds comparison tables.
5. Fetches compact CSV outputs locally.
6. Validates replay-derived apo values against the supplied summary tables.

The manuscript protocol uses concatenated three-replica trajectories, 750 sampled
frames, a 4.5 A contact cutoff, 75% contact persistence, same/consecutive residue
exclusion, top-25 bottleneck residues, and WT-referenced lost/gained residue
frequencies across the five variants.

## 2. Configure Runtime Variables

```bash
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
export VARMDYN_PALMETTO_USER=user
export VARMDYN_PALMETTO_PROJECT=/path/to/hpc_project_root
export VARMDYN_DYNETAN_WORK=/path/to/dynetan_work
export VARMDYN_CONDA_ENV=varmdyn_env
export VARMDYN_DYNETAN_STAGE_TAG=concat750_w1_s750_apo_validation
```

Optional SSH control socket:

```bash
export VARMDYN_SSH_CONTROL_PATH=/path/to/ssh_control_socket
```

## 3. Preflight Checks

Local check:

```bash
python scripts/check_private_inputs.py --module network
```

Remote check:

```bash
python scripts/check_private_inputs.py --module network --remote --timeout-seconds 10
```

If this stalls or reports SSH timeouts, first verify the Palmetto bridge in your
own terminal:

```bash
palmetto
ssh -S ~/.ssh/palmetto.sock shamrap@slogin.palmetto.clemson.edu "hostname && whoami"
```

If a command says to look for a Duo push, approve that push before rerunning the
remote check. For scheduler work, the hostname should be a login node such as
`vm-slurm-p-loginXX.palmetto.clemson.edu`.

## 4. Validate Supplied Tables

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py \
  --frequency data_private/network/network_residue_transition_frequency.csv \
  --overlap data_private/network/network_overlap_apo_vs_atpmg.csv \
  --outdir runs/mdan/network_validation/manuscript_tables
```

## 5. Palmetto Replay Commands

Stage scripts:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py stage
```

Submit the replay:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py submit
```

Check status:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py status
```

Compare after completion:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py compare
```

Fetch compact CSV outputs:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py fetch --outdir data_private/network
```

## 6. Validate Fetched Replay Outputs

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py \
  --frequency data_private/network/network_residue_transition_frequency.csv \
  --overlap data_private/network/network_overlap_apo_vs_atpmg.csv \
  --apo-results data_private/network/$VARMDYN_DYNETAN_STAGE_TAG/TutorialResults_CDKL5 \
  --apo-comparisons data_private/network/$VARMDYN_DYNETAN_STAGE_TAG/_comparisons_concatenated \
  --stage-tag $VARMDYN_DYNETAN_STAGE_TAG \
  --outdir runs/mdan/network_validation/$VARMDYN_DYNETAN_STAGE_TAG
```

Expected successful summary:

```text
OK frequency: ... rows, ... columns
OK overlap: ... rows, ... columns
OK apo frequency replay: ... rows compared
OK apo overlap replay: ... fields compared
```

## 7. Output Locations

```text
data_private/network/$VARMDYN_DYNETAN_STAGE_TAG/
runs/mdan/network_validation/$VARMDYN_DYNETAN_STAGE_TAG/
```

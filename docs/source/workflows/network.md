# Dynamic Network Analysis

The network workflow validates and replays DyNetAn-derived network analysis
without storing network outputs in the public repository.

## 1. Workflow Stages

1. Check private input configuration.
2. Validate existing network frequency/overlap tables.
3. Run or reuse a Palmetto DyNetAn replay.
4. Build comparison tables.
5. Fetch lightweight outputs locally.
6. Validate replay-derived apo values against supplied tables.

## 2. Configure Runtime Variables

```bash
export VARMDYN_PALMETTO_HOST=user@slogin.example.edu
export VARMDYN_PALMETTO_USER=user
export VARMDYN_PALMETTO_PROJECT=/path/to/private/palmetto_project
export VARMDYN_DYNETAN_WORK=/path/to/private/dynetan_work
export VARMDYN_CONDA_ENV=varmdyn_env
export VARMDYN_DYNETAN_STAGE_TAG=concat750_w1_s750_apo_validation
```

Optional SSH control socket:

```bash
export VARMDYN_SSH_CONTROL_PATH=/path/to/private/ssh_control_socket
```

## 3. Preflight Checks

Local check:

```bash
python scripts/check_private_inputs.py --module network
```

Remote check:

```bash
python scripts/check_private_inputs.py --module network --remote
```

## 4. Validate Supplied Tables

```bash
python workflows/mdan/network/validate_network_manuscript_outputs.py \
  --frequency data_private/network/network_residue_transition_frequency.csv \
  --overlap data_private/network/network_overlap_apo_vs_atpmg.csv \
  --outdir runs/mdan/network_validation/manuscript_tables
```

## 5. Palmetto Replay Commands

Stage:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py stage
```

Submit:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py submit
```

Status:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py status
```

Compare after completion:

```bash
python workflows/mdan/network/run_network_replay_palmetto.py compare
```

Fetch lightweight CSV outputs:

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

These folders are ignored by git.

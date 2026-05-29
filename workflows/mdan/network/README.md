# Network Analysis Module

This folder contains the code for DyNetAn network replay, table validation, and
comparison checks. It should stay code-only.

Use the repository-level data layout. This is a folder map, not a shell command
block:

```text
data/
  network/tables/
  network/replay/apo/
  network/replay/holo/
  structures/apo/
  structures/holo_atpmg/

runs/
  mdan/network_validation/
  mdan/figures/
```

Create the folders and local env file from the repository root:

```bash
python scripts/init_data_layout.py
source data/varmdyn_data.env
```

Check data for network table validation, rendering, and replay:

```bash
python scripts/check_data_inputs.py --module network --profile tables
python scripts/check_data_inputs.py --module network --profile render
python scripts/check_data_inputs.py --module network --profile apo-replay
```

Use `--profile holo-replay` only after a matching holo DyNetAn replay directory
has been copied or fetched into `data/network/replay/holo/`.

For full trajectory-level replay from user-supplied apo/holo simulation roots,
use the consolidated CLI:

```bash
python workflows/mdan/network/network.py full --state apo
python workflows/mdan/network/network.py full --state holo
python workflows/mdan/network/network.py full --state all
```

It discovers `NN_NAME` system folders automatically, keeps `01_WT` first, writes
under ignored `data/network/full/` and `runs/mdan/network_full/`, and skips
completed DyNetAn outputs unless `--force` is used.

For faster HPC runs, use the array wrapper so each variant gets its own Slurm
task and the compare step runs only after the array succeeds:

```bash
export VARMDYN_APO_ROOT=/path/to/apo/root
export VARMDYN_HOLO_ROOT=/path/to/holo/root
export VARMDYN_DYNETAN_STAGE_TAG=varmdyn_full_holo

jobid=$(sbatch --parsable --array=0-5 workflows/mdan/network/run_network_array.slurm holo variant)
sbatch --dependency=afterok:${jobid} workflows/mdan/network/run_network_array.slurm holo compare
```

Use `VARMDYN_VARIANTS=01_WT,02_L119R` with a matching `--array=0-1` when testing
a small subset.

For a standalone collaborator-facing packet with its own runner, DyNetAn
environment builder, Slurm array script, local sync, fetch, and rendering notes,
see:

```text
workflows/mdan/network/shared/
```

Network residue renders use the prepared structure for the same state and
variant by default:

```text
data/network/full/prepared/<state>/<variant>/<variant>.pdb
```

Existing manuscript-style DyNetAn work directories can also be staged,
submitted, checked, compared, and fetched through the same CLI with the
`hpc-*` subcommands.

See the MkDocs page `docs/source/workflows/network.md` for the full protocol.

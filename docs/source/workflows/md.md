# Molecular Dynamics

`workflows/md/` is the VarMDyn control layer for molecular-dynamics simulation
campaigns. It follows the same public workflow style as clustering and variant
modeling: configuration files, dry-run commands, explicit checks, and generated
data kept outside git.

Current scope: path layout, varmodel handoff, run initialization, dry-run stage
commands, HPC bridge commands, Slurm dependency submission, production-chunk
planning, and completion checks. Full AMBER prep/LEaP/equilibration templates
are owned by `workflows/md/`; legacy folders are provenance inputs, not the
public VarMDyn interface.

## 1. Storage Pattern

Use scratch for active data generation:

```bash
export VARMDYN_MD_GENERATION_ROOT=/scratch/$USER/VarMDyn/data/md
```

That scratch path is the HPC scratch partition when commands run on the HPC
system. If local status commands show `/scratch/... MISSING`, that only means
the local workstation does not have the HPC scratch filesystem mounted.

Use the HPC project partition as the durable analysis source:

```bash
export VARMDYN_MD_PROJECT_ROOT=/path/to/hpc_project/VarMDyn/data/md
```

Use local `data/` only for compact fetched outputs:

```bash
export VARMDYN_DATA_ROOT=$PWD/data
```

## 2. State Folder Architecture

VarMDyn keeps a simple state-level wrapper. Variant systems live under
`systems/`, while the method-stage folders inside each variant preserve the
legacy protocol shape:

```text
$VARMDYN_MD_GENERATION_ROOT/
  apo/
    01_variants/
    systems/
      01_WT/
        01.prep/
        02.leap/com/
        03.pmemd/com/cr1/
        03.pmemd/com/cr2/
        03.pmemd/com/cr3/
        04.ptraj/com/
        protocol/com/cr1/
        protocol/com/cr2/
        protocol/com/cr3/
      02_L119R/
      ...
  holo/
    01_variants/
    systems/
      01_WT/
        ligprep/
        01.prep/
        02.leap/com/
        03.pmemd/com/cr1/
        03.pmemd/com/cr2/
        03.pmemd/com/cr3/
        04.ptraj/com/
        protocol/com/cr1/
        protocol/com/cr2/
        protocol/com/cr3/
      02_L119R/
      ...
```

The project partition uses the same `data/md/apo/` and `data/md/holo/` state
wrappers after completed products are synced out of scratch.

## 3. HPC Bridge Configuration

Before executing remote commands, configure the local control plane variables to target your remote cluster login and project folders:

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_PROJECT=/path/to/hpc_project/VarMDyn
export VARMDYN_HPC_SCRATCH=/scratch/$USER/VarMDyn
```

Check cluster connectivity, synchronize the pipeline code, and initialize remote workspaces:

```bash
# Check SSH configuration and reachability
python workflows/md/bridge.py check

# Sync codebase to the HPC host
python workflows/md/bridge.py sync-code --execute

# Initialize directories on the remote scratch/project partitions
python workflows/md/bridge.py init --execute
```

## 4. Local Dry Runs

Local dry runs check state configurations, show variant availability, and verify execution scripts without running remote tasks:

```bash
# Check Apo layout status and configured stage scripts
python workflows/md/apo/run.py --status
python workflows/md/apo/run.py --stage handoff
python workflows/md/apo/run.py --stage all
python workflows/md/apo/run.py --check all

# Check Holo layout status
python workflows/md/holo/run.py --status
python workflows/md/holo/run.py --stage handoff
python workflows/md/holo/run.py --stage all
python workflows/md/holo/run.py --check all
```

Dry runs print planned actions to stdout. Add `--execute` to a local runner command only when running tasks directly on the workstation.

## 5. Initialize layouts and Stage Variants

To set up your simulation directories locally (or on the remote target) and hand off the variant PDB models generated in the previous step:

```bash
python workflows/md/apo/run.py --init --execute
python workflows/md/holo/run.py --init --execute
python workflows/md/apo/run.py --stage handoff --execute
python workflows/md/holo/run.py --stage handoff --execute
```

The state configurations can be reviewed/edited at:
- `workflows/md/apo/config.yaml`
- `workflows/md/holo/config.yaml`

## 6. Remote Job Stage & Slurm Submission

Since production molecular dynamics runs are computationally intensive, submission scripts queue all stages with Slurm `afterok` dependency tags. 

Run the remote bridge control to inspect and launch the full pipeline on the HPC:

```bash
# Inspect submit actions remotely (dry-run)
python workflows/md/bridge.py run --state apo --status

# Stage all files and submit Slurm job arrays
python workflows/md/bridge.py run --state apo --stage all --execute --remote-execute
python workflows/md/bridge.py run --state holo --stage all --execute --remote-execute
```

To extend a completed campaign or plan new production chunks (e.g. extending a 500 ns run to 1 us), plan the trajectory targets and submit the extension chunks:

```bash
# Plan extension chunk allocation
python workflows/md/trajectory.py --state apo --action plan --target-ns 1000

# Submit extension chunks (30 to 34) on the cluster
VARMDYN_MD_PROD_START=30 VARMDYN_MD_PROD_END=34 python workflows/md/apo/run.py --stage prod
```

Verification of prepared trajectory stages can be checked using:
```bash
python workflows/md/trajectory.py --state apo --action prepared-plan
```

## 7. Fetch Compact Outputs

Once the simulation arrays complete on the HPC and outputs are moved to the durable project partition, fetch only the compact summaries, coordinate restart files, and analysis-ready plots back to the local workstation:

```bash
python workflows/md/bridge.py fetch --state apo --execute
python workflows/md/bridge.py fetch --state holo --execute
```

All heavy trajectory binaries (NetCDF/DCD files) must remain on the HPC file system to preserve local disk space and repository hygiene.

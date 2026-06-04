# md

This workflow is the VarMDyn-facing molecular-dynamics control layer.

It keeps the public module style close to `workflows/clustering/` and
`workflows/varmodel/`: configuration-driven commands, dry-run first, explicit
checks, and generated data outside git.

Current scope: orchestration, path layout, varmodel handoff, bridge commands,
Slurm dependency submission, production-chunk planning, and completion checks.
Full AMBER prep/LEaP/equilibration templates are intentionally module-owned
under `workflows/md/`; legacy script folders are compatibility/provenance
inputs, not the VarMDyn interface.

## 1. Storage Rule

Scratch is for data generation. The HPC project partition is the durable source
for analysis.

```bash
export VARMDYN_MD_GENERATION_ROOT=/scratch/$USER/VarMDyn/data/md
export VARMDYN_MD_PROJECT_ROOT=/path/to/hpc_project/VarMDyn/data/md
```

`/scratch/$USER` is the HPC scratch filesystem. Local status output may show
that path as missing; real generation happens after the workflow is run through
the HPC bridge or from the HPC checkout.

Local fetches should write compact outputs under:

```bash
export VARMDYN_DATA_ROOT=$PWD/data
```

## 2. Folder Architecture

The VarMDyn state wrapper is simple. Each state keeps its variant systems under
`systems/`, while the method-stage folders inside each variant preserve the
legacy protocol shape:

```text
data/md/apo/systems/<variant>/{01.prep,02.leap,03.pmemd,04.ptraj,protocol}
data/md/holo/systems/<variant>/{ligprep,01.prep,02.leap,03.pmemd,04.ptraj,protocol}
```

## 3. Apo

Dry-run from the repository root:

```bash
python workflows/md/apo/run.py --status
python workflows/md/apo/run.py --stage all
python workflows/md/apo/run.py --check all
```

Create the run layout:

```bash
python workflows/md/apo/run.py --init --execute
python workflows/md/apo/run.py --stage handoff --execute
```

## 4. Holo ATP/Mg

Dry-run from the repository root:

```bash
python workflows/md/holo/run.py --status
python workflows/md/holo/run.py --stage all
python workflows/md/holo/run.py --check all
```

Create the run layout:

```bash
python workflows/md/holo/run.py --init --execute
python workflows/md/holo/run.py --stage handoff --execute
```

## 5. Production Chunks

Production is planned as chained 100 ns chunks. A completed 500 ns campaign uses
chunks 25-29; extending to 1 us adds chunks 30-34 after the existing restart
files.

```bash
python workflows/md/trajectory.py --state apo --action plan --target-ns 1000
VARMDYN_MD_PROD_START=30 VARMDYN_MD_PROD_END=34 python workflows/md/apo/run.py --stage prod
```

For a fresh run, use the full submitter after prep/LEaP templates have produced
the expected protocol scripts. It submits cr1 equilibration, queues restart
propagation from `cr1/24md.restrt` to `cr2/cr3`, then queues production chunks
with `afterok` dependencies:

```bash
python workflows/md/apo/run.py --stage full_submit
python workflows/md/holo/run.py --stage full_submit
```

## 6. HPC Bridge

The bridge is the local control plane for HPC work:

```bash
python workflows/md/bridge.py check
python workflows/md/bridge.py sync-code
python workflows/md/bridge.py init
python workflows/md/bridge.py run --state apo --status
```

Add `--execute` only after dry-run output looks correct.

## 7. One-Nanosecond Smoke Test

The smoke runner stages apo or holo ATP/Mg continuations from a user-supplied
validated source tree, writes active data in scratch, and can sync completed
smoke products to the HPC project partition. By default it uses one Slurm array
per state, with WT and all configured variants as array elements.

This is a continuation smoke, not a substitute for full prep, LEaP,
equilibration, and production validation.

On the HPC system:

```bash
export VARMDYN_MD_SMOKE_SOURCE_ROOT=/path/to/validated_md_source
export VARMDYN_MD_GENERATION_ROOT=/scratch/$USER/VarMDyn/data/md
export VARMDYN_MD_PROJECT_ROOT=/path/to/hpc_project/VarMDyn/data/md

python workflows/md/smoke.py --state apo --action prepare
python workflows/md/smoke.py --state apo --action submit --execute
python workflows/md/smoke.py --state apo --action check
python workflows/md/smoke.py --state apo --action sync-project --execute
```

Repeat with `--state holo`, or use `--state all` for apo and holo together.
For a smaller test, pass `--variants 01_WT`.

## 8. Public Boundary

Public docs describe the reusable VarMDyn workflow. Internal parity checks
against local validation roots are not public user requirements.

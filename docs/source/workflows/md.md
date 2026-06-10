# Molecular Dynamics

`workflows/md/` is the VarMDyn control layer for molecular-dynamics simulation
campaigns. It follows the same public workflow style as clustering and variant
modeling: configuration files, dry-run commands, explicit checks, and generated
data kept outside git.

Current scope: path layout, varmodel handoff, run initialization, dry-run stage
commands, HPC bridge commands, Slurm dependency submission, production-chunk
planning, and completion checks. Full AMBER prep/LEaP/equilibration templates
are owned by `workflows/md/`; source protocol folders are provenance inputs, not the
public VarMDyn interface.

## Module Layout

The MD module keeps only stable interfaces and shared helpers at the top level.
Implementation scripts are grouped by responsibility so apo and holo stay easy
to compare.

| Path | Boundary |
|---|---|
| `cli.py` | User-facing dispatcher behind `bash scripts/run_md.sh ...`. |
| `bridge.py` | Local-to-HPC bridge, code sync, remote command execution, and compact fetches. |
| `lib.py`, `runner.py`, `protocol.py` | Shared config, state-runner, and protocol inspection helpers. |
| `apo/` | Apo config plus apo-owned shell stages. |
| `holo/` | Holo config plus holo-only ATP/Mg transfer and shell stages. |
| `stages/` | Internal Python operations for handoff, Slurm submit, restart, storage, cleanup, validation, and post-processing. |
| `leap/` | LEaP neutralization, ion report, and LEaP output checks. |
| `templates/` | AMBER protocol inputs and templates preserved for reproducible simulation setup. |

Normal users should call `bash scripts/run_md.sh ...`. Direct calls into
`workflows/md/stages/` and `workflows/md/leap/` are mainly for debugging or for
bridge-launched remote execution.

After local MD code changes or after pulling a new VarMDyn version, resync the
durable HPC checkout before testing remote commands:

Run on: local workstation. Environment: local `varmdyn_env`.

```bash
bash scripts/run_md.sh sync-code --execute
bash scripts/run_md.sh status --state all
bash scripts/run_md.sh protocol --state apo --kind premd
bash scripts/run_md.sh protocol --state holo --kind premd
bash scripts/run_md.sh postprocess --state apo --action plan --start 25 --end 29
```

These commands do not launch new simulation chunks. They verify that the local
wrapper, synced HPC checkout, apo/holo state configs, protocol templates, and
post-processing planner still agree.

## 1. MD Environments

Use the main local environment for VarMDyn MD control commands:

Run on: local workstation from the repository root. Environment: activate
`varmdyn_env`.

```bash
conda activate varmdyn_env
```

Run `bash scripts/run_md.sh ...`, `python workflows/md/bridge.py ...`, and MD
status/plan/check commands from the local workstation in `varmdyn_env`.

Holo ATP/Mg transfer and PyMOL rendering use the smaller PyMOL environment. The
workflow runner still runs from `varmdyn_env`, but `VARMDYN_PYMOL_CMD` should
point to the `varmdyn_pymol` interpreter:

Run on: local workstation from the repository root. Environment: any
conda-capable shell; creates or updates `varmdyn_pymol`.

```bash
bash scripts/env/ensure_pymol_env.sh
```

On HPC, bridge-launched Python control tasks use the lightweight
remote `varmdyn_env` control environment. AMBER simulation stages use HPC
AMBER modules through Slurm. Do not run MD workflow scripts from the HPC
base/default Python because it may not include required packages such as
PyYAML.

On Google Colab, the VarMDyn Python control environment can run public smoke
checks, planning, lightweight analysis, and documentation checks. Colab does
not provide AMBER modules by default. Do not launch LEaP, PMEMD, or cpptraj MD
stages in Colab until AMBER/AmberTools is installed and the corresponding
commands are configured for that runtime.

Environment summary:

| Task | Where | Environment |
|---|---|---|
| Local MD controller, bridge, status, planning, submit dry-runs | local workstation | `varmdyn_env` |
| Holo ATP/Mg PyMOL transfer/rendering | local workstation | `varmdyn_pymol` via `VARMDYN_PYMOL_CMD` |
| Public Colab smoke, planning, lightweight analysis | Google Colab | Colab `varmdyn_env`; AMBER/AmberTools required before MD engine stages |
| Remote bridge orchestration | HPC project checkout through bridge | HPC `varmdyn_env` control env |
| LEaP, PMEMD, cpptraj simulation/trajectory stages | HPC compute jobs | AMBER modules plus Slurm |

Whenever a command depends on a specific environment, the command block below
states `Run on` and `Environment`. Treat those labels as part of the command.

## 2. Storage Pattern

Use scratch for active data generation:

Run on: local workstation before bridge commands, or inside the HPC checkout for
manual repair. Environment: `varmdyn_env`. Path: active MD generation root on
HPC scratch.

```bash
export VARMDYN_MD_GENERATION_ROOT=/scratch/$USER/VarMDyn/data/md
```

Run the workflow code from a durable checkout, typically on the HPC project
partition, and use the scratch path only as the generated-data target.

That scratch path is the HPC scratch partition when commands run on the HPC
system. If local status commands show `/scratch/... MISSING`, that only means
the local workstation does not have the HPC scratch filesystem mounted.

Use the HPC project partition as the durable analysis source:

Run on: local workstation before bridge commands, or inside the HPC checkout for
manual repair. Environment: `varmdyn_env`. Path: durable HPC project MD root.

```bash
export VARMDYN_MD_PROJECT_ROOT=/path/to/hpc_project/VarMDyn/data/md
```

Use local `data/` only for compact fetched outputs:

Run on: local workstation from the repository root. Environment:
`varmdyn_env`. Path: ignored local `data/`.

```bash
export VARMDYN_DATA_ROOT=$PWD/data
```

Scratch data should be copied to the project partition before any long pause or
after each major campaign milestone, such as a completed 500 ns run. Prefer
`rsync` copy plus verification over direct `mv`; only clean scratch after the
project copy has been verified.

## 3. State Folder Architecture

VarMDyn keeps a simple state-level wrapper that mirrors the validated state roots.
Plain variant folders live directly under `apo/` or `holo/`, while `variants/`
is only a staging area for varmodel handoff PDBs. The method-stage folders
inside each variant preserve the validated protocol shape:

```text
$VARMDYN_MD_GENERATION_ROOT/
  apo/
    variants/
    WT/
      01.prep/
      02.leap/com/
      03.pmemd/com/cr1/
      03.pmemd/com/cr2/
      03.pmemd/com/cr3/
      04.ptraj/com/
      protocol/com/cr1/
      protocol/com/cr2/
      protocol/com/cr3/
    MUT1/
    ...
  holo/
    variants/
    WT/
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
    MUT1/
    ...
```

The project partition uses the same `data/md/apo/` and `data/md/holo/` state
wrappers after completed products are synced out of scratch.

By default, MD consumes WT plus every successful variant in the varmodel
manifest (`variants: all`) and uses plain folder names such as `WT` or the
mutation name from the manifest. Small test runs can pass `--variants WT` or
use a single mutation from the varmodel manifest. Larger local panels are
auto-discovered from `data/varmodel/manifest.csv`; VarMDyn does not require a
hard-coded number of variants or numeric variant prefixes. The MD stage folders
inside each system stay the same.

## 4. HPC Bridge Configuration

If you already completed the HPC block in [Getting Started](../getting-started.md),
do not repeat this section. Continue with [Local Bridge Checks](#5-local-bridge-checks)
or the apo/holo protocol stages below. Use this section only for a fresh shell,
a fresh machine, or bridge/HPC repair.

Before executing remote commands, authenticate the local SSH bridge. Ignored
local path files such as `.local_docs/paths.env` and `data/varmdyn_data.env`
can be auto-loaded by the bridge tools, so a configured checkout does not
require retyping HPC paths.

The bridge has one job split into two parts: keep code current on the durable
HPC project checkout, then launch remote stages and Slurm submissions from that
checkout. The generated MD files still go to HPC scratch through
`VARMDYN_MD_GENERATION_ROOT`.

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment: HPC `varmdyn_env` control environment. Runs on: HPC through bridge
for remote checks, code sync, environment verification, and directory
initialization.

```bash
# Local workstation command; checks project/scratch remotely.
python workflows/md/bridge.py check --execute

# Local workstation command; syncs only code/config/docs to the HPC project checkout.
python workflows/md/bridge.py sync-code --execute

# Local workstation command; creates or updates the remote control env.
python workflows/md/bridge.py setup-env --env hpc --execute

# Local workstation command; verifies local envs and remote control env.
python scripts/checks/check_readiness.py --hpc

# Local workstation command; creates MD directories on HPC scratch/project.
python workflows/md/bridge.py init --execute
```

If your bridge status helper is not green, run your local bridge authentication
helper, approve authentication, then rerun the commands above.

For a generic public setup, or if no ignored local path file exists, configure
the local control plane variables to target your remote cluster login and
project folders:

Run on: local workstation from the repository root. Environment:
`varmdyn_env`. Paths: variables target remote HPC project/scratch locations but
are exported in the local controller shell.

```bash
export VARMDYN_HPC_HOST=user@login.example.edu
export VARMDYN_HPC_PROJECT=/path/to/hpc_project/VarMDyn
export VARMDYN_HPC_USER=user
export VARMDYN_HPC_SCRATCH=/scratch/user/VarMDyn
export VARMDYN_HPC_PYTHON=/path/to/conda/envs/varmdyn_env/bin/python
```

Use the remote HPC username in `VARMDYN_HPC_SCRATCH`. If you export the path on
your local workstation, local `$USER` may be different from the remote account.

After setting those variables, run the same local bridge sequence shown above:
`check`, `sync-code`, `setup-env --env hpc`, `check_readiness.py --hpc`, then
`init`. Run them one at a time and fix any failure before continuing.

## 5. Local Bridge Checks

The normal MD controller is the local MD wrapper. These checks run from the
local checkout and ask the remote modular apo/holo runners to report their
current state, available systems, stage scripts, and stage aliases through the
authenticated bridge.

Run on: local workstation. Environment: local `varmdyn_env`. Remote
environment: HPC `varmdyn_env` through the authenticated bridge.

```bash
# Check apo/holo layout status and configured modular stages on HPC.
bash scripts/run_md.sh status --state apo
bash scripts/run_md.sh status --state holo

# Print planned remote actions without executing them.
bash scripts/run_md.sh stage --state apo --name handoff
bash scripts/run_md.sh stage --state holo --name prepare
```

Add `--run` only when you are intentionally running a remote stage. Direct
`python workflows/md/bridge.py ...`, `workflows/md/apo/run.py`, and
`workflows/md/holo/run.py` commands are developer/debug interfaces. Normal MD
work should use `bash scripts/run_md.sh ...`.

## 6. Initialize layouts and Stage Variants

If you completed the bridge initialization in Getting Started or
[HPC Bridge Configuration](#4-hpc-bridge-configuration), the remote `apo/` and
`holo/` state folders already exist. Do not initialize them again unless you
are repairing layout or starting from a clean remote checkout.

When initialization is needed, use the bridge so the command runs on HPC:

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment: HPC `varmdyn_env` control environment. Runs on: HPC through
bridge.

```bash
python workflows/md/bridge.py init --execute
```

Do not run `python workflows/md/apo/run.py --init --execute` or
`python workflows/md/holo/run.py --init --execute` from the local workstation
when `VARMDYN_MD_GENERATION_ROOT` points to `/scratch/...`; that path exists on
HPC, not locally.

Direct state-runner initialization is an advanced fallback for developers
inside the durable HPC checkout or for intentionally local test roots. It is
not the normal user-facing path.

The handoff reads the varmodel manifest, stages WT plus successful modeled
variants into `variants/`, and creates one plain system folder per variant under
each state. For example, if the manifest contains mutation `MUT1`, MD gets
`apo/MUT1/...` and `holo/MUT1/...`; no numeric prefix is added.

The state configurations can be reviewed/edited at:
- `workflows/md/apo/config.yaml`
- `workflows/md/holo/config.yaml`

For holo ATP/Mg setup, ensure the compact PyMOL environment on the local
workstation. Transfer ATP/Mg locally, generate the QA panel locally, then sync
the prepared `ligprep/` inputs to HPC scratch for AMBER LEaP/PMEMD.

Run on: local workstation. Environment: `varmdyn_pymol`.

```bash
bash scripts/env/ensure_pymol_env.sh
```

Before running local holo transfer, keep the validated ATP/Mg template source
inside VarMDyn-owned data. The default location is
`$VARMDYN_MD_PROJECT_ROOT/templates/atpmg` for the active local run root; set
`VARMDYN_MD_ATPMG_TEMPLATE_ROOT` only when you intentionally want to override
that local template source. Routine VarMDyn runs should not depend on the
protected source simulation tree. The protected source tree remains read-only provenance for
creating or auditing the VarMDyn-owned copy. The default transfer mode uses a
PyMOL core fit over residues 30-220 before Hu2024 ATP/Mg LEaP preparation.

## 7. Apo Protocol Stages

The apo workflow follows the validated protocol shape while keeping the reusable
VarMDyn controls under `workflows/md/`.

Normal local-controlled route:

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment: HPC `varmdyn_env` control environment plus AMBER modules for
LEaP/PMEMD stages. Runs on: HPC through bridge.

```bash
bash scripts/run_md.sh status --state apo
bash scripts/run_md.sh stage --state apo --name handoff --run
bash scripts/run_md.sh stage --state apo --name prep --run
bash scripts/run_md.sh check --state apo --name prep
bash scripts/run_md.sh stage --state apo --name leap_submit --run

# Wait until the LEaP Slurm array leaves the queue before the LEaP gate.
bash scripts/run_md.sh slurm --execute
bash scripts/run_md.sh check --state apo --name leap
```

Direct apo state-runner or bridge-run commands are advanced fallbacks for
developers inside the HPC checkout or for intentionally local test roots. The
normal user-facing entry point is `bash scripts/run_md.sh`.

The prep stage cleans/stages the receptor model into `01.prep/cdl.prot.noH.pdb`.
The normal all-variant LEaP path submits a Slurm array so `tleap` does not run
as a long login-node loop. The direct `leap` stage remains available for a
single/debug run inside the HPC checkout. LEaP builds gas and solvated OPC
systems under `02.leap/com/`:
`cdl.com.gas.leap.*` and `cdl.com.wat.leap.*`. Ion addition is neutralization
based on the current variant/system charge; the template does not force a fixed
number of ions for every variant.

LEaP array wrappers and logs are state-local: apo writes under
`apo/logs/leap/`, and holo writes under `holo/logs/leap/`. They do not use the
shared `data/md/logs/` path.

Apo protocol and production controls after prep and LEaP gates pass:

Run on: local workstation. Environment: local `varmdyn_env`; submit/check
commands run on HPC through the bridge.

```bash
# Inspect apo minimization, heating, and equilibration stages 01-24.
bash scripts/run_md.sh protocol --state apo --kind premd

# Inspect apo production chunks and per-chunk length.
bash scripts/run_md.sh protocol --state apo --kind prod

# Ask scratch how far apo has already completed for this target window.
bash scripts/run_md.sh plan --state apo --action status --target-ns 500

# Fresh apo start: run preMD 01-24, copy cr1/24md restart to cr2/cr3,
# then run 100 ns production chunk 25.
bash scripts/run_md.sh submit --state apo --target-ns 100
bash scripts/run_md.sh submit --state apo --target-ns 100 --run

# Extend completed apo 100 ns to 500 ns: chunks 26-29.
bash scripts/run_md.sh plan --state apo --action check-prod --target-ns 100
bash scripts/run_md.sh submit --state apo --from-ns 100 --target-ns 500
bash scripts/run_md.sh submit --state apo --from-ns 100 --target-ns 500 --run

# Extend completed apo 500 ns to 1000 ns: chunks 30-34.
bash scripts/run_md.sh plan --state apo --action check-prod --target-ns 500
bash scripts/run_md.sh submit --state apo --from-ns 500 --target-ns 1000
bash scripts/run_md.sh submit --state apo --from-ns 500 --target-ns 1000 --run
```

Apo restart/resume rule:

- `bash scripts/run_md.sh submit --state apo --target-ns 100 --run` is the
  normal fresh apo start. It submits `cr1` preMD/equilibration steps `01mi`
  through `24md`, restart propagation from `cr1/24md.restrt` to `cr2` and
  `cr3`, and production chunk `25md` for all replicas.
- `bash scripts/run_md.sh submit --state apo --from-ns 100 --target-ns 500 --run`
  extends an already completed 100 ns apo campaign. It does not rerun chunk 25;
  it starts from each replica's existing `25md.restrt` and submits chunks 26-29
  as chained Slurm arrays: 27 waits for 26, 28 waits for 27, and 29 waits for
  28.
- `bash scripts/run_md.sh submit --state apo --from-ns 500 --target-ns 1000 --run`
  extends from existing `29md.restrt` files and submits chunks 30-34.
- `bash scripts/run_md.sh plan --state apo --action status --target-ns 500`
  reports the common completed ns across all apo variants/replicas and the
  completed chunks found for each replica in the target scratch/project root.
- The submitter checks the target chunks before queuing jobs. If any requested
  production chunks already exist, it prints the detected completed ns and
  refuses to submit. Use a later extension window instead. Use `--force` only
  when you intentionally want to resubmit existing chunks.
- Always run `bash scripts/run_md.sh plan --state apo --action check-prod
  --target-ns <completed_ns>` before an extension so missing restart outputs are
  caught before new jobs are queued.
- Do not rerun the same extension command while those chunks are queued or
  running; wait for completion/status checks first.
- Before rerunning an extension after a cancellation or interruption, confirm
  no `26-29` production chunks remain active:
  `bash scripts/run_md.sh slurm --execute`. The submitter also refuses
  overlapping production-array jobs by default.
- If you intentionally cancelled an interrupted apo 100 ns to 500 ns extension,
  preview the cleanup first, then delete only those extension chunks:
  `bash scripts/run_md.sh cleanup --state apo --from-ns 100 --target-ns 500 --cancel-jobs`
  and
  `bash scripts/run_md.sh cleanup --state apo --from-ns 100 --target-ns 500 --cancel-jobs --run`.
- Avoid fresh 500 ns or 1000 ns commands during routine work. If you omit
  `--from-ns`, the wrapper treats the campaign as fresh and uses the full
  submitter from equilibration. For safety, fresh campaigns above 100 ns require
  an explicit `--allow-fresh-long` override.

## 8. Holo ATP/Mg Protocol Stages

The holo workflow starts from the apo/varmodel receptor, then transfers ATP/Mg
from a validated template before LEaP. This stage is sensitive: ligand
coordinates should be transferred by the PyMOL core-fit route, then verified
before simulation.

Run on: local workstation. Environment: `varmdyn_env` for the VarMDyn MD
module. `VARMDYN_PYMOL_CMD` points the transfer stage to the small
`varmdyn_pymol` interpreter. The sync step runs locally and writes only
prepared holo inputs to HPC scratch through the bridge.

Use this route when you want to verify ATP/Mg placement locally before any
remote LEaP or PMEMD step. The command does five things in order:

1. Builds the local holo layout from WT plus the successful varmodel variants.
2. Seeds each holo `ligprep/` folder with the receptor from apo/varmodel output.
3. Fits the validated ATP/Mg template onto the target kinase core over residues
   `30-220`.
4. Writes ATP-only, Mg-only, merged receptor+ATP/Mg, PyMOL session, and QA PNGs.
5. Optionally syncs only the prepared holo inputs to HPC scratch.

Before running the transfer, make sure the local PyMOL environment exists:

Run on: local workstation. Environment: any conda-capable shell; creates or
updates `varmdyn_pymol`.

```bash
bash scripts/env/ensure_pymol_env.sh
```

Then run the local transfer from the main VarMDyn environment. The MD CLI uses
an absolute conda command automatically.

Run on: local workstation from the repository root. Environment:
`varmdyn_env`; transfer/rendering delegates to local `varmdyn_pymol`. Path:
local `data/md/holo/` plus synced holo inputs to HPC scratch.

```bash
# Transfer ATP/Mg locally, render QA images, check outputs, compose a panel,
# and sync prepared ligprep inputs to HPC scratch.
bash scripts/run_md.sh local-holo-transfer --sync-inputs --execute
```

> **Note**
> `VARMDYN_PYMOL_CMD` is an advanced override for unusual local PyMOL setups.
> Do not set it during normal runs. If an old bad value is still exported in
> your shell, `local-holo-transfer` warns and falls back to the default conda
> command.

The local transfer writes per-variant files under:

```text
data/md/holo/<variant>/ligprep/
  cdl.prot.noH.pdb
  template_atpmg_source.pdb
  ligand-only-from-complex-atponly.pdb
  mg-only-from-complex-mgonly.pdb
  cdl.prot.noH_atpmg_from8fp5.pdb
  transfer_core_30_220.log
  transfer_core_30_220.pml
  transfer_core_30_220_overlay.pse
  transfer_kinase_context.png
  transfer_ligand_zoom.png
  transfer_core_30_220_overlay.png
```

It also writes the compact multi-variant QA panel:

```text
data/md/holo/transfer_panel.png
```

The exact template-source filename can differ by project; the bundled ATP/Mg
template may keep its original PDB-derived filename. Inspect
`transfer_panel.png`, `transfer_kinase_context.png`,
`transfer_ligand_zoom.png`, and `transfer_core_30_220_overlay.pse` before
continuing. The kinase-context view should show the target receptor, fitted
template core, transferred ATP, and Mg in a recognizable kinase orientation.

The synced HPC scratch layout can then continue at `prepare`, `leap_submit`,
and the later AMBER stages:

Holo LEaP uses the same state-local logging rule as apo: wrappers and logs stay
under `holo/logs/leap/`.

Run on: local workstation. Environment: local `varmdyn_env`; remote command
runs in the HPC `varmdyn_env` control environment plus AMBER modules.

```bash
bash scripts/run_md.sh stage --state holo --name prepare --run
bash scripts/run_md.sh stage --state holo --name leap_submit --run
bash scripts/run_md.sh slurm --execute
bash scripts/run_md.sh check --state holo --name leap
```

VarMDyn keeps ATP/Mg coordinate transfer local-first. Do not run remote
`holo transfer` stages through the bridge; `bash scripts/run_md.sh
local-holo-transfer --sync-inputs --execute` is the supported user-facing
coordinate-transfer path. The lower-level state runner remains an internal
implementation detail for the local wrapper.

The transfer stage fits the template and target kinase cores over residues
30-220, extracts ATP and Mg from the transformed template, and writes the holo
receptor/ligand staging files under `ligprep/`. The validation stage checks
that ATP/Mg placement remains consistent with the validated source. For
inspection, the transfer stage also writes
`ligprep/transfer_kinase_context.png`,
`ligprep/transfer_ligand_zoom.png`,
`ligprep/transfer_core_30_220_overlay.png` and
`ligprep/transfer_core_30_220_overlay.pse`, showing the target receptor,
template core, transferred ATP, and Mg before LEaP.

LEaP writes `ion_report.txt` beside `leap.log` for every state and variant.
Use it as a quick sanity check for reported system charge, requested ion
species, added ion count, and the Na/Cl residues detected in the final solvated
PDB.

Ligand-transfer context figures are source-backed provenance figures.
VarMDyn's generated MD transfer QA figure is separate: it documents the ATP/Mg
placement used for the current simulation setup. Keep project-specific context
assets local/private unless a public, generic source is supplied.

Holo protocol and production controls after local transfer, preparation, and
LEaP gates pass:

Run on: local workstation. Environment: local `varmdyn_env`; submit/check
commands run on HPC through the bridge.

```bash
# Inspect holo minimization, heating, and equilibration stages 01-24.
bash scripts/run_md.sh protocol --state holo --kind premd

# Inspect holo production chunks and per-chunk length.
bash scripts/run_md.sh protocol --state holo --kind prod

# Ask scratch how far holo has already completed for this target window.
bash scripts/run_md.sh plan --state holo --action status --target-ns 500

# Fresh holo start: run preMD 01-24, copy cr1/24md restart to cr2/cr3,
# then run 100 ns production chunk 25.
bash scripts/run_md.sh submit --state holo --target-ns 100
bash scripts/run_md.sh submit --state holo --target-ns 100 --run

# Extend completed holo 100 ns to 500 ns: chunks 26-29.
bash scripts/run_md.sh plan --state holo --action check-prod --target-ns 100
bash scripts/run_md.sh submit --state holo --from-ns 100 --target-ns 500
bash scripts/run_md.sh submit --state holo --from-ns 100 --target-ns 500 --run

# Extend completed holo 500 ns to 1000 ns: chunks 30-34.
bash scripts/run_md.sh plan --state holo --action check-prod --target-ns 500
bash scripts/run_md.sh submit --state holo --from-ns 500 --target-ns 1000
bash scripts/run_md.sh submit --state holo --from-ns 500 --target-ns 1000 --run
```

Holo restart/resume rule:

- `bash scripts/run_md.sh submit --state holo --target-ns 100 --run` is the
  normal fresh holo start. It submits `cr1` preMD/equilibration steps `01mi`
  through `24md`, restart propagation from `cr1/24md.restrt` to `cr2` and
  `cr3`, and production chunk `25md` for all replicas.
- `bash scripts/run_md.sh submit --state holo --from-ns 100 --target-ns 500 --run`
  extends an already completed 100 ns holo campaign. It does not rerun chunk 25;
  it starts from each replica's existing `25md.restrt` and submits chunks 26-29
  as chained Slurm arrays: 27 waits for 26, 28 waits for 27, and 29 waits for
  28.
- `bash scripts/run_md.sh submit --state holo --from-ns 500 --target-ns 1000 --run`
  extends from existing `29md.restrt` files and submits chunks 30-34.
- `bash scripts/run_md.sh plan --state holo --action status --target-ns 500`
  reports the common completed ns across all holo variants/replicas and the
  completed chunks found for each replica in the target scratch/project root.
- The submitter checks the target chunks before queuing jobs. If any requested
  production chunks already exist, it prints the detected completed ns and
  refuses to submit. Use a later extension window instead. Use `--force` only
  when you intentionally want to resubmit existing chunks.
- Always run `bash scripts/run_md.sh plan --state holo --action check-prod
  --target-ns <completed_ns>` before an extension so missing restart outputs are
  caught before new jobs are queued.
- Do not rerun the same extension command while those chunks are queued or
  running; wait for completion/status checks first.
- Before rerunning an extension after a cancellation or interruption, confirm
  no `26-29` production chunks remain active:
  `bash scripts/run_md.sh slurm --execute`. The submitter also refuses
  overlapping production-array jobs by default.
- If you intentionally cancelled an interrupted holo 100 ns to 500 ns extension,
  preview the cleanup first, then delete only those extension chunks:
  `bash scripts/run_md.sh cleanup --state holo --from-ns 100 --target-ns 500 --cancel-jobs`
  and
  `bash scripts/run_md.sh cleanup --state holo --from-ns 100 --target-ns 500 --cancel-jobs --run`.
- Avoid fresh 500 ns or 1000 ns commands during routine work. If you omit
  `--from-ns`, the wrapper treats the campaign as fresh and uses the full
  submitter from equilibration. For safety, fresh campaigns above 100 ns require
  an explicit `--allow-fresh-long` override.

The protocol summary reports `stage`, `ensemble`, `steps`, physical `length`,
`temp0`, `ntb`, `ntp`, `restraint_wt`, and the description line from the actual
Amber input. In both apo and holo, `01mi` to `24md` cover minimization, NVT
heating, restrained NVT/NPT equilibration, and short unrestrained NPT MD before
production. Production targets must be divisible by the configured chunk size,
currently 100 ns; a request such as 150 ns is rejected so the run does not
silently drift away from the validated restart-chain protocol.

## 9. Remote Job Stage & Slurm Submission

Since production molecular dynamics runs are computationally intensive, the full
submitter queues one Slurm array per dependent stage: `cr1` equilibration,
restart propagation to `cr2`/`cr3`, and one production array per 100 ns chunk.
Each stage uses Slurm `afterok` dependencies, so later replicas and chunks do
not start until the required upstream restart exists.

Run the MD stages in this order. Use the apo or holo section above for the
state-specific fresh-run and extension commands. Do not run an extension until
the previous completion check passes.

1. Handoff WT and successful varmodel variants.
2. Run apo/holo prep and LEaP.
3. Wait for LEaP Slurm arrays to finish, then run apo/holo LEaP gates.
4. Run the short validation arrays and wait for both validation arrays to finish.
5. Submit the state-specific production chain.
6. Wait for Slurm completion and check the expected chunk outputs.
7. Confirm the completed production target with the state-specific
   `check-prod` command.
8. Run MD post-processing to create the analysis-ready `04.ptraj` products.
9. Sync completed products to the project partition when you are ready for
   durable storage or project-partition analysis.
10. Only then restore/schedule extension chunks 30-34 if targeting 1000 ns.

Run the remote bridge control to inspect and launch the full pipeline on the HPC:

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment: HPC `varmdyn_env` control environment plus AMBER modules. Runs on:
HPC through bridge.

```bash
# Inspect submit actions remotely (dry-run)
bash scripts/run_md.sh status --state apo
```

Submit and check production with the state-specific commands in the apo or holo
section above.

Dependency logic:

- `cr1` equilibration runs steps `01mi` through `24md`.
- Before queuing equilibration, the submitter refreshes the
  `job-1-24-equilibration.sh` launcher from the VarMDyn template in the HPC
  project checkout. This updates Slurm/path plumbing only; AMBER method inputs
  such as `01mi.in` through `24md.in` and `25md.in` remain the validated
  protocol files.
- The preMD/equilibration Slurm wrapper follows the validated `eq1-24` resource
  request by default: one node, 32 tasks on that node, 1 CPU per task, 64G
  memory, and 48 hours. Production chunk arrays follow the validated 100 ns chunk
  request by default: 1 GPU, 2 CPUs, 16G memory, and 48 hours. Override
  `EQ_TIME`, `EQ_MEM`, `EQ_NTASKS`, `EQ_TASKS_PER_NODE`, `TIME`, `MEM`, or
  `CPUS` only when the queue policy or benchmark timing requires it.
- Slurm wrapper scripts, manifests, and logs are written under the state root,
  such as `apo/logs/...` or `holo/logs/...`. Apo and holo submissions must never
  share one mutable manifest path.
- restart propagation waits for the `cr1` equilibration array with `afterok`.
- production chunk `25` waits for restart propagation.
- production chunk `26` waits for the entire `25` array.
- each later chunk waits for the prior chunk array.
- `cr2` and `cr3` production can be queued before their copied restart exists
  only when the queued job has an `afterok` dependency on restart propagation.
- after restart propagation, `cr1`, `cr2`, and `cr3` each continue their own
  production restart chain. `cr2/26` follows `cr2/25`; it does not depend on
  `cr1/25`.

If an equilibration array leaves the queue immediately, inspect Slurm
accounting and logs before resubmitting. The earlier failure mode
`SLURM_NTASKS: unbound variable` means an old scratch launcher was used; sync
the fixed code and rerun the normal `submit --target-ns 100 --run` command so
the launcher is refreshed from the project checkout.

If apo and holo were submitted back-to-back with an older VarMDyn version that
wrote wrappers under shared `data/md/logs/...`, cancel those arrays before
resubmitting. The corrected submitter writes state-local wrappers under
`data/md/apo/logs/...` and `data/md/holo/logs/...`.

After layout or LEaP changes, run the short PMEMD validation arrays before
launching the full campaign. This keeps the real `apo/<variant>/...` and
`holo/<variant>/...` folder names, writes validation-specific
`varmdyn_validate_*` files, runs a shortened preMD minimization array, then runs
a dependent production array over `cr1`, `cr2`, and `cr3`.

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment: HPC `varmdyn_env` control environment plus AMBER modules. Runs on:
HPC through bridge.

```bash
# Submit apo validation arrays.
bash scripts/run_md.sh validate --state apo --variants all --action all

# Submit holo validation arrays after local ATP/Mg transfer and sync-inputs.
bash scripts/run_md.sh validate --state holo --variants all --action all

# Monitor Slurm until the validation jobs leave the queue.
bash scripts/run_md.sh slurm --execute

# Then run final output gates.
bash scripts/run_md.sh validate --state apo --variants all --action check
bash scripts/run_md.sh validate --state holo --variants all --action check
```

The final gate should print `OK` for every variant and for
`cr1/varmdyn_validate_01mi.mdout`,
`cr1/varmdyn_validate_25md.mdout`,
`cr2/varmdyn_validate_25md.mdout`, and
`cr3/varmdyn_validate_25md.mdout`.

For a smaller layout test, pass `--variants WT`.

Variant folders are not numbered, but production chunks are. The validated method
uses 100 ns production chunks named by restart-chain step (`25md`, `26md`, ...).
The apo and holo sections above show the exact commands for the normal 100 ns
start followed by 500 ns and 1000 ns extensions. The shared mapping is:

| Target | From | Submitted chunks | Wrapper behavior |
|---:|---:|---|---|
| 100 ns | 0 ns | 25 | fresh start: equilibration, restart propagation, chunk 25 |
| 500 ns | 100 ns | 26-29 | extension only |
| 1000 ns | 500 ns | 30-34 | extension only |

For extension chunks beyond `29md`, missing extension input/scripts are
generated from the validated `29md` 100 ns template at submit time.

> **Note**
> A fresh 500 ns or 1000 ns run is technically possible, but it is not the
> routine operating pattern and requires the explicit `--allow-fresh-long`
> override. For normal campaigns, launch 100 ns first, check completion, sync
> durable outputs, then extend from the completed target.

Verification of prepared trajectory stages can be checked using:

Run on: local workstation from the repository root. Environment:
`varmdyn_env`; remote planner uses HPC `varmdyn_env` through the bridge.

```bash
bash scripts/run_md.sh plan --state apo --action prepared-plan
```

## 10. MD Post-Processing Before Analysis

Completed PMEMD chunks are not yet analysis-ready. After the target production
window finishes, run cpptraj post-processing once per state to create the first
canonical `04.ptraj` products used by prepared trajectory replay and aggregate
RMSF sanity checks.

Post-processing is window-based. Choose the production chunks you want to
prepare with `--start` and `--end`: `25-26` prepares the first 200 ns per
replica, `25-29` prepares the first 500 ns per replica, and `30-34` prepares a
later 500 ns extension window. This lets simulation continue toward 1000 ns
while you post-process and inspect an earlier window.

The workflow strips solvent and ions, writes a protein-only
`cdl.com.striped_v2.prmtop`, creates one stripped trajectory per replica,
concatenates the three replicas with the requested stride, and writes an
aggregate RMSF `.agr` file. The validated 25-29, stride-20 window keeps the
historical `750frames` concatenated filename; other windows use a clear
`stride<value>` label in the concatenated filename.

### 10.1. What The Current Post-Processing Step Covers

Post-processing converts raw PMEMD trajectory chunks into the smaller,
protein-only prepared products that the network-style analysis workflows
expect. It does not rerun MD and it does not change the production trajectory.
It reads completed `03.pmemd/` outputs, writes cpptraj input files under
`04.ptraj/`, and submits a state-level Slurm array with one task per variant.

This is the modular VarMDyn form of trajectory preparation that was previously
often run manually or "on the fly" before a specific analysis. VarMDyn makes
that boundary explicit: finish PMEMD first, prepare the canonical trajectories
once, then let analysis workflows reuse those prepared products.

| Step | Input | Action | Output |
|---|---|---|---|
| Topology strip | `02.leap/com/cdl.com.wat.leap.prmtop` | Remove solvent, ions, and optional ligands from the topology. | `02.leap/com/cdl.com.striped_v2.prmtop` |
| Replica trajectory strip | `03.pmemd/com/cr*/<start>-<end>md.mdcrd.nc` | Autoimage each replica and strip the same mask from every frame. | `04.ptraj/com/cr*/traj-proc/production-<start>-to-<end>-<ns>.cr*.striped_v2.mdcrd.nc` |
| Concatenation and subsampling | Three stripped replica trajectories | Read `cr1`, `cr2`, and `cr3` with the requested stride. | `04.ptraj/com/concatenated/production-<start>-to-<end>-concatenated-<label>.striped_v2.mdcrd.nc` |
| Aggregate RMSF sanity route | The concatenated trajectory for that window | Align, average, realign, and calculate backbone RMSF by residue. | `04.ptraj/com/rmsf/rmsf.byresidue.agr` |

The default analysis trajectory is protein-only:

```text
apo strip mask:  :WAT,Na+,Cl-
holo strip mask: :WAT,Na+,Cl-,ATP,MG
```

For holo, ATP/Mg are used during simulation setup and retained in the raw PMEMD
outputs, but the default network/RMSF analysis products strip ATP and Mg so apo
and holo residue-network calculations use the same protein-only node set. Keep
the raw trajectories if a later ligand-aware analysis is needed.

Source protocol notes include multiple trajectory flavors:

| Trajectory flavor | Purpose | VarMDyn handling |
|---|---|---|
| `striped` / sampled-20 trajectories | Older protein-only trajectory processing and plotting. | Superseded by the explicit `striped_v2` prepared route for new VarMDyn analysis. |
| `striped_v2` prepared trajectories | Final protein-only prepared route used by DyNetAn/network replay and related residue analyses. | Default VarMDyn post-processing output. |
| `keepATPmg` trajectories | Holo ligand-aware inspection where ATP/Mg should remain in the trajectory. | Not the default network/RMSF route; keep raw holo trajectories for this or add an explicit ligand-aware post-processing mode when needed. |

The default VarMDyn command combines the validated concat-plus-downsample idea
into one cpptraj pass by reading each stripped replica with stride `20`. For
the standard chunks `25-29` window, each replica contributes 25,000 stripped
frames; the concatenated stride-20 output contains 3,750 frames. The filename
keeps the historical `750frames` label for compatibility, but the check command
validates the actual NetCDF frame count.

This is not yet every possible analysis-prep mode. Keep the boundary clear:

| Analysis-prep need | Current VarMDyn status |
|---|---|
| Protein-only topology and per-replica stripped trajectories | Covered by this post-processing step. |
| Three-replica concatenated, stride-20 prepared trajectory | Covered by this post-processing step. |
| Aggregate RMSF `.agr` from the prepared trajectory | Covered by this post-processing step. |
| RMSD/RMSF tables from per-replica stripped trajectories | Built by the Analysis page after this step with `bash scripts/run_analysis.sh rms ...`. That validated route calculates each replica first, then averages `cr1`, `cr2`, and `cr3`; it does not use the concatenated trajectory as its source. |
| Holo ligand-retaining `keepATPmg` trajectory flavor | Not yet a default VarMDyn post-processing mode; keep raw holo outputs until a ligand-aware mode is added. |
| Per-replica clean/aligned trajectories for RMSD and displacement replay | Not yet covered here; this belongs to the dynamics analysis-prep path. |
| RMSD CSV, RMSF CSV, ROI displacement CSV, kept displacement TSVs, and figure products | Downstream analysis outputs, not outputs of this current post-processing command. |

So the safe workflow is: run this post-processing before network-style replay
and prepared-trajectory sanity checks, then run the dedicated analysis workflows
for RMSD/RMSF, displacement, Y171, and network figures. If a downstream
analysis asks for per-replica RMSD/RMSF tables, use the Analysis page RMS route
after this post-processing check passes. If a downstream analysis asks for a
clean aligned trajectory or a kept displacement table, do not assume this
post-processing command has produced it yet.

The command phases are:

| Command action | What happens |
|---|---|
| `plan` | Prints the state root, chunk window, stride, strip mask, variants, and expected outputs. |
| `submit` | Checks which selected variants are missing outputs, writes cpptraj input files only for those variants, writes the manifest/array wrapper, then prints the `sbatch` command without submitting it. |
| `submit --run` | Submits the Slurm array only for variants with missing outputs. If all selected variants are already complete, it prints a skip message and submits nothing. |
| `check` | Verifies every expected post-processing output and NetCDF frame count for every variant. |

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment: HPC `varmdyn_env` control environment; cpptraj runs in a Slurm job
with AMBER modules. Outputs are written beside the simulation folders being
post-processed.

Use `--force` only when you intentionally want to regenerate an already
completed post-processing window. Without `--force`, VarMDyn avoids duplicate
post-processing arrays for completed outputs.

For chunks `25-29`, the strict check expects 25,000 frames in each per-replica
stripped trajectory and 3,750 frames in the three-replica concatenated
stride-20 trajectory. A `BADFRAMES` result means the file exists but is not
analysis-ready.

### 10.2. Confirm The Simulation Source Root

Before post-processing, decide where the completed simulation folders live. By
default, the bridge reads from the configured HPC scratch MD root. You do not
need to type that path; the `plan` command prints the actual `md_root` it will
use.

The default root comes from the bridge environment, usually
`VARMDYN_MD_GENERATION_ROOT`. In the local/private docs preview, this value is
loaded from ignored local path files such as `.local_docs/paths.env`. For the
usual scratch-first workflow, that default is `/scratch/$USER/VarMDyn/data/md`.

Confirm the active default before submitting:

Run on: local workstation from the repository root. Environment:
`varmdyn_env`; remote command prints the HPC-visible path it will use.

```bash
bash scripts/run_md.sh postprocess --state apo --action plan --start 25 --end 29
```

In the output, check:

- `md_root`: the MD root containing `apo/` and `holo/`;
- `run_root`: the selected state folder;
- `variants`: the systems that will be processed.

The printed `md_root` is a report of the path VarMDyn will use. It does not
set or change the path by itself.

Use that default when you just finished generating data on scratch. If the
completed simulation tree has already been copied to the HPC project partition
or to an external storage path mounted on the HPC system, pass `--md-root` to
point at that durable source instead.

The MD root must be the folder that directly contains the `apo/` and `holo/`
state folders. For a project-storage copy, that root is usually
`/path/to/hpc_visible/VarMDyn/data/md`.

Use the same `--md-root` value for `plan`, `submit`, and `check`. Mixing source
roots between those phases can make the check look in a different location than
the Slurm job wrote.

To change the default path used by bridge commands, edit your ignored local
path file and rebuild the local docs preview:

```bash
# .local_docs/paths.env
export VARMDYN_MD_GENERATION_ROOT=/scratch/$USER/VarMDyn/data/md
```

Set `VARMDYN_MD_GENERATION_ROOT` to the active generation source, usually
scratch. Use `--md-root` when you want a one-command override, for example to
post-process a copied project-storage tree without changing the default bridge
path.

If the remote command says it cannot open `workflows/md/stages/postprocess.py`
or any other VarMDyn workflow file, the HPC project checkout is stale. Sync
code from the local checkout, then rerun the post-processing command. This is a
code sync only: it updates scripts, configs, and docs in the durable HPC
project checkout. It does not copy simulation data from scratch or project
storage.

Run on: local workstation from the repository root. Environment:
`varmdyn_env`; updates the durable HPC project checkout.

```bash
python workflows/md/bridge.py sync-code --execute
```

Run on: local workstation from the repository root. Environment:
`varmdyn_env`; remote cpptraj jobs use AMBER modules through Slurm. Path:
bridge-configured HPC scratch MD root.

```bash
# Submit apo cpptraj post-processing array.
bash scripts/run_md.sh postprocess --state apo --action submit --start 25 --end 29
bash scripts/run_md.sh postprocess --state apo --action submit --start 25 --end 29 --run

# If submit says no Slurm job was submitted because all outputs already exist,
# skip the queue monitor and go directly to the check command.
# Otherwise monitor until the post-processing jobs leave the queue.
bash scripts/run_md.sh slurm --execute
bash scripts/run_md.sh postprocess --state apo --action check --start 25 --end 29
```

If the completed apo simulations are already in project storage or another
mounted HPC path, pass that root explicitly. Do not pass a local workstation
path such as `/home/paul/...` here unless that exact path is also mounted on
the HPC system. The remote Palmetto command must be able to see the path.

Run on: local workstation from the repository root. Environment:
`varmdyn_env`; remote cpptraj jobs use AMBER modules through Slurm. Path:
explicit HPC-visible MD root passed with `--md-root`.

```bash
bash scripts/run_md.sh postprocess --state apo --action plan --md-root /path/to/hpc_visible/VarMDyn/data/md --start 25 --end 29
bash scripts/run_md.sh postprocess --state apo --action submit --md-root /path/to/hpc_visible/VarMDyn/data/md --start 25 --end 29 --run
bash scripts/run_md.sh postprocess --state apo --action check --md-root /path/to/hpc_visible/VarMDyn/data/md --start 25 --end 29
```

Run the same post-processing for holo after the holo production window
finishes:

Run on: local workstation from the repository root. Environment:
`varmdyn_env`; remote cpptraj jobs use AMBER modules through Slurm. Path:
bridge-configured HPC scratch MD root unless `--md-root` is supplied.

```bash
bash scripts/run_md.sh postprocess --state holo --action plan --start 25 --end 29
bash scripts/run_md.sh postprocess --state holo --action submit --start 25 --end 29
bash scripts/run_md.sh postprocess --state holo --action submit --start 25 --end 29 --run

# If submit says no Slurm job was submitted because all outputs already exist,
# skip the queue monitor and go directly to the check command.
bash scripts/run_md.sh slurm --execute
bash scripts/run_md.sh postprocess --state holo --action check --start 25 --end 29
```

Use `--md-root /path/to/hpc_visible/VarMDyn/data/md` in the holo commands too
when the holo simulation tree is not in bridge-configured scratch.

Expected analysis-ready outputs for every state and variant:

```text
02.leap/com/cdl.com.striped_v2.prmtop
04.ptraj/com/cr1/traj-proc/production-25-to-29-500ns.cr1.striped_v2.mdcrd.nc
04.ptraj/com/cr2/traj-proc/production-25-to-29-500ns.cr2.striped_v2.mdcrd.nc
04.ptraj/com/cr3/traj-proc/production-25-to-29-500ns.cr3.striped_v2.mdcrd.nc
04.ptraj/com/concatenated/production-25-to-29-concatenated-750frames.striped_v2.mdcrd.nc
04.ptraj/com/rmsf/rmsf.byresidue.agr
```

Use these prepared products before moving into the [Analysis](analysis.md)
workflow.

For the current scratch-first path, leave the completed simulation tree in
scratch and run post-processing without `--md-root`. The plan command will
print the scratch `md_root` and state `run_root`; verify those paths before
submitting. If you later copy the same simulation tree to project storage or an
external HPC-visible path before post-processing, rerun the same commands with
`--md-root` pointing to that copied tree.

## 11. Scratch To Project Storage

Use scratch for active simulation generation and, for now, post-processing.
Copy completed simulation and prepared trajectory products to the project
partition when you are ready for durable storage, long pauses, or
project-partition analysis. This copy operation is optional before
post-processing if you are still working from scratch, but it should be done
before relying on the data long term because scratch can be purged.

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment: HPC `varmdyn_env` control environment plus rsync/cpptraj/AMBER
tools as needed. Runs on: HPC through bridge.

```bash
# Dry-run: preview copy from scratch to durable project storage.
bash scripts/run_md.sh storage --state all --variants all --action sync-project --verify

# Execute: copy scratch products to durable project storage and verify sizes.
bash scripts/run_md.sh storage --state all --variants all --action sync-project --verify --run

# Later, restore project products back to scratch for extension.
bash scripts/run_md.sh storage --state all --variants all --action restore-scratch --verify
bash scripts/run_md.sh storage --state all --variants all --action restore-scratch --verify --run
```

After restoring project products to scratch, plan and submit extension chunks
with the state-specific commands in the apo or holo section above.

The storage helper copies by default. Use `--delete` only for a deliberate
mirror operation after checking the source and destination paths. Use
`--checksum` only when byte-level rsync verification is needed and the extra
time on large trajectory files is acceptable.

Local storage is different from project storage. Do not fetch full raw
trajectories to the local workstation as the default. Use local `data/` for
compact outputs, QA images, summaries, and selected analysis-ready products
that you actually need to inspect locally.

## 12. Optional Local Fetch

This is optional and separate from HPC project storage. Use it only when you
want small outputs on your local workstation for inspection, plotting, or
record keeping.

Do not use fetch as your durable backup. For durable storage, use the storage
sync commands in Section 11 to copy scratch data to the HPC project partition
or another HPC-visible storage location. Fetch is for compact local copies
after the remote data source is ready.

Run on: local workstation. Local environment: `varmdyn_env`. Remote source:
HPC project partition through bridge/rsync.

```bash
bash scripts/run_md.sh fetch --state apo --execute
bash scripts/run_md.sh fetch --state holo --execute
```

All heavy trajectory binaries such as NetCDF/DCD files should stay on the HPC
file system by default. Local `data/` should receive only compact summaries, QA
images, small tables, selected restart/coordinate files, or analysis products
you actually need to inspect locally.

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

## 1. MD Environments

Use the main local environment for VarMDyn MD control commands:

```bash
conda activate varmdyn_env
```

Run `bash scripts/run_md.sh ...`, `python workflows/md/bridge.py ...`, and MD
status/plan/check commands from the local workstation in `varmdyn_env`.

Holo ATP/Mg transfer and PyMOL rendering use the smaller PyMOL environment. The
workflow runner still runs from `varmdyn_env`, but `VARMDYN_PYMOL_CMD` should
point to the `varmdyn_pymol` interpreter:

```bash
bash scripts/ensure_pymol_env.sh
```

On Palmetto/HPC, bridge-launched Python control tasks use the lightweight
remote `varmdyn_env` control environment. AMBER simulation stages use Palmetto
AMBER modules through Slurm. Do not run MD workflow scripts from the HPC
base/default Python because it may not include required packages such as
PyYAML.

Environment summary:

| Task | Where | Environment |
|---|---|---|
| Local MD controller, bridge, status, planning, submit dry-runs | local workstation | `varmdyn_env` |
| Holo ATP/Mg PyMOL transfer/rendering | local workstation | `varmdyn_pymol` via `VARMDYN_PYMOL_CMD` |
| Remote bridge orchestration | HPC project checkout through bridge | HPC `varmdyn_env` control env |
| LEaP, PMEMD, cpptraj simulation/trajectory stages | Palmetto compute jobs | AMBER modules plus Slurm |

Whenever a command depends on a specific environment, the command block below
states `Run on` and `Environment`. Treat those labels as part of the command.

## 2. Storage Pattern

Use scratch for active data generation:

```bash
export VARMDYN_MD_GENERATION_ROOT=/scratch/$USER/VarMDyn/data/md
```

Run the workflow code from a durable checkout, typically on the HPC project
partition, and use the scratch path only as the generated-data target.

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

Scratch data should be copied to the project partition before any long pause or
after each major campaign milestone, such as a completed 500 ns run. Prefer
`rsync` copy plus verification over direct `mv`; only clean scratch after the
project copy has been verified.

## 3. State Folder Architecture

VarMDyn keeps a simple state-level wrapper that mirrors the legacy state roots.
Plain variant folders live directly under `apo/` or `holo/`, while `variants/`
is only a staging area for varmodel handoff PDBs. The method-stage folders
inside each variant preserve the legacy protocol shape:

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
    L119R/
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
    L119R/
    ...
```

The project partition uses the same `data/md/apo/` and `data/md/holo/` state
wrappers after completed products are synced out of scratch.

By default, MD consumes WT plus every successful variant in the varmodel
manifest (`variants: all`) and uses plain folder names such as `WT`, `R59X`, or
`A123T`. Legacy source comparisons map names privately when needed; VarMDyn
does not require numeric variant prefixes. The MD stage folders inside each
system stay the same.

## 4. HPC Bridge Configuration

If you already completed the HPC block in [Getting Started](../getting-started.md),
do not repeat this section. Continue with [Local Bridge Checks](#5-local-bridge-checks)
or the apo/holo protocol stages below. Use this section only for a fresh shell,
a fresh machine, or bridge/HPC repair.

Before executing remote commands, authenticate the local SSH bridge. In Paul's
local/private checkout, `.local_docs/paths.env` and `data/varmdyn_data.env` are
auto-loaded by the bridge tools, so the normal command path does not require
retyping Palmetto paths.

The bridge has one job split into two parts: keep code current on the durable
HPC project checkout, then launch remote stages and Slurm submissions from that
checkout. The generated MD files still go to HPC scratch through
`VARMDYN_MD_GENERATION_ROOT`.

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment: HPC `varmdyn_env` control environment. Runs on: HPC through bridge
for remote checks, code sync, environment verification, and directory
initialization.

```bash
# Local workstation: check the user-owned Palmetto bridge.
palmettostatus

# Local workstation command; checks project/scratch remotely.
python workflows/md/bridge.py check --execute

# Local workstation command; syncs code to the HPC project checkout.
python workflows/md/bridge.py sync-code --execute

# Local workstation command; creates or updates the remote control env.
python workflows/md/bridge.py setup-env --env hpc --execute

# Local workstation command; verifies local envs and remote control env.
python scripts/check_readiness.py --hpc

# Local workstation command; creates MD directories on HPC scratch/project.
python workflows/md/bridge.py init --execute
```

If `palmettostatus` is not green, run `palmettobridge`, approve authentication,
then rerun the commands above.

For a generic public setup, or if no ignored local path file exists, configure
the local control plane variables to target your remote cluster login and
project folders:

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

The normal MD controller is the local bridge. These checks run from the local
checkout and ask the remote modular apo/holo runners to report their current
state, available systems, stage scripts, and stage aliases.

Run on: local workstation. Environment: local `varmdyn_env`. Remote
environment: HPC `varmdyn_env` through the authenticated bridge.

```bash
# Check apo/holo layout status and configured modular stages on HPC.
python workflows/md/bridge.py run --state apo --status --execute
python workflows/md/bridge.py run --state holo --status --execute

# Print planned remote actions without executing them.
python workflows/md/bridge.py run --state apo --stage handoff --execute
python workflows/md/bridge.py run --state holo --stage transfer --execute
```

Add `--remote-execute` only when you are intentionally running the remote
stage. The direct `workflows/md/apo/run.py` and `workflows/md/holo/run.py`
commands are thin wrappers around the shared runner and are mainly for
developer/debug use inside the HPC checkout or with intentionally local test
roots. Do not use direct state runners from the local workstation against
`/scratch/...` or `/project/...` roots.

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
each state. For example, if varmodel contains `L119R`, MD gets
`apo/L119R/...` and `holo/L119R/...`; no numeric prefix is added.

The state configurations can be reviewed/edited at:
- `workflows/md/apo/config.yaml`
- `workflows/md/holo/config.yaml`

For holo ATP/Mg setup, ensure the compact PyMOL environment on the local
workstation. Transfer ATP/Mg locally, generate the QA panel locally, then sync
the prepared `ligprep/` inputs to HPC scratch for AMBER LEaP/PMEMD.

Run on: local workstation. Environment: `varmdyn_pymol`.

```bash
bash scripts/ensure_pymol_env.sh
```

Before running local holo transfer, keep the validated ATP/Mg template source
inside VarMDyn-owned data. The default location is
`$VARMDYN_MD_PROJECT_ROOT/templates/atpmg` for the active local run root; set
`VARMDYN_MD_ATPMG_TEMPLATE_ROOT` only when you intentionally want to override
that local template source. Routine VarMDyn runs should not depend on the
legacy simulation tree. The legacy tree remains read-only provenance for
creating or auditing the VarMDyn-owned copy. The default transfer mode uses a
PyMOL core fit over residues 30-220 before Hu2024 ATP/Mg LEaP preparation.

## 7. Apo Protocol Stages

The apo workflow follows the legacy protocol shape while keeping the reusable
VarMDyn controls under `workflows/md/`.

Normal local-controlled route:

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment: HPC `varmdyn_env` control environment plus AMBER modules for
LEaP/PMEMD stages. Runs on: HPC through bridge.

```bash
python workflows/md/bridge.py run --state apo --status --execute
python workflows/md/bridge.py run --state apo --stage handoff --execute --remote-execute
python workflows/md/bridge.py run --state apo --stage prep --execute --remote-execute
python workflows/md/bridge.py run --state apo --check prep --execute --remote-execute
python workflows/md/bridge.py run --state apo --stage leap_submit --execute --remote-execute

# Wait until the LEaP Slurm array leaves the queue before the LEaP gate.
python workflows/md/bridge.py slurm --execute
python workflows/md/bridge.py run --state apo --check leap --execute --remote-execute
```

Direct apo state-runner commands are an advanced fallback for developers inside
the HPC checkout or for intentionally local test roots. The normal user-facing
entry point is `bash scripts/run_md.sh`.

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
bash scripts/ensure_pymol_env.sh
```

Then run the local transfer from the main VarMDyn environment. The MD CLI uses
an absolute conda command automatically.

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
  8FP5.pdb
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

Inspect `transfer_panel.png`, `transfer_kinase_context.png`,
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

The legacy manuscript Supplementary Figure S2-style ATP/38R overlay is a
source-backed ligand-transfer context figure. VarMDyn's generated MD transfer
QA figure is separate: it documents the ATP/Mg placement used for the current
simulation setup. Keep manuscript-style ATP/38R context assets local/private
unless a public, generic source is supplied.

Holo protocol and production controls after local transfer, preparation, and
LEaP gates pass:

Run on: local workstation. Environment: local `varmdyn_env`; submit/check
commands run on HPC through the bridge.

```bash
# Inspect holo minimization, heating, and equilibration stages 01-24.
bash scripts/run_md.sh protocol --state holo --kind premd

# Inspect holo production chunks and per-chunk length.
bash scripts/run_md.sh protocol --state holo --kind prod

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
silently drift away from the legacy restart-chain protocol.

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
7. Sync completed products from scratch to the project partition.
8. Only then restore/schedule extension chunks 30-34 if targeting 1000 ns.

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
  such as `01mi.in` through `24md.in` and `25md.in` remain the legacy-matched
  protocol files.
- The preMD/equilibration Slurm wrapper follows the legacy `eq1-24` resource
  request by default: one node, 32 tasks on that node, 1 CPU per task, 64G
  memory, and 48 hours. Production chunk arrays follow the legacy 100 ns chunk
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

Variant folders are not numbered, but production chunks are. The legacy method
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
```bash
bash scripts/run_md.sh plan --state apo --action prepared-plan
```

## 10. Scratch To Project Storage

Use scratch for active simulation generation and the project partition as the
durable source for later analysis. A typical 500 ns to 1000 ns extension cycle
is:

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment: HPC `varmdyn_env` control environment plus rsync/cpptraj/AMBER
tools as needed. Runs on: HPC through bridge.

```bash
# After 500 ns completes, copy scratch products to durable project storage.
python workflows/md/bridge.py exec --execute -- python workflows/md/storage.py --state all --variants all --action sync-project --verify --execute

# Later, restore project products back to scratch for extension.
python workflows/md/bridge.py exec --execute -- python workflows/md/storage.py --state all --variants all --action restore-scratch --verify --execute
```

After restoring project products to scratch, plan and submit extension chunks
with the state-specific commands in the apo or holo section above.

The storage helper copies by default. Use `--delete` only for a deliberate
mirror operation after checking the source and destination paths. Use
`--checksum` only when byte-level rsync verification is needed and the extra
time on large trajectory files is acceptable.

## 11. One-Nanosecond Smoke Test

Before launching long production campaigns, run a short continuation smoke test
on the HPC system. The smoke runner stages WT and configured variants from a
user-supplied validated source tree, runs one Slurm array per state, and checks
for completed 1 ns PMEMD output.

This validates continuation PMEMD execution, state/variant/replica array
submission, scratch-to-project storage, and compact output checks. It is not a
replacement for the full prep, LEaP, equilibration, and production workflow.

Run on: local workstation. Local environment: `varmdyn_env`. Remote
environment: HPC `varmdyn_env` control environment plus AMBER modules. Runs on:
HPC through bridge.

```bash
export VARMDYN_MD_SMOKE_SOURCE_ROOT=/path/to/validated_md_source

python workflows/md/bridge.py exec --execute -- python workflows/md/smoke.py --state all --variants all --replicas all --action prepare
python workflows/md/bridge.py exec --execute -- python workflows/md/smoke.py --state apo --variants all --replicas all --action submit --execute
python workflows/md/bridge.py exec --execute -- python workflows/md/smoke.py --state holo --variants all --replicas all --action submit --execute
python workflows/md/bridge.py exec --execute -- python workflows/md/smoke.py --state all --variants all --replicas all --action check
python workflows/md/bridge.py exec --execute -- python workflows/md/smoke.py --state all --variants all --replicas all --action sync-project --execute
```

For a smaller smoke test, pass `--variants WT`; omit `--replicas all` to use
the default `cr1` replica only.

## 12. Fetch Compact Outputs

Once the simulation arrays complete on the HPC and outputs are moved to the durable project partition, fetch only the compact summaries, coordinate restart files, and analysis-ready plots back to the local workstation:

Run on: local workstation. Local environment: `varmdyn_env`. Remote source:
HPC project partition through bridge/rsync.

```bash
python workflows/md/bridge.py fetch --state apo --execute
python workflows/md/bridge.py fetch --state holo --execute
```

All heavy trajectory binaries (NetCDF/DCD files) must remain on the HPC file system to preserve local disk space and repository hygiene.

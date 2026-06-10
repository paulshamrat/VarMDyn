# md

This workflow is the VarMDyn-facing molecular-dynamics control layer.

It keeps the public module style close to `workflows/clustering/` and
`workflows/varmodel/`: configuration-driven commands, dry-run first, explicit
checks, and generated data outside git.

Current scope: orchestration, path layout, varmodel handoff, bridge commands,
Slurm dependency submission, production-chunk planning, and completion checks.
Full AMBER prep/LEaP/equilibration templates are intentionally module-owned
under `workflows/md/`; source protocol folders are compatibility/provenance
inputs, not the VarMDyn interface.

## Module Layout

The MD module keeps only the stable interfaces and shared helpers at the top
level. Implementation scripts are grouped by responsibility so apo and holo stay
easy to compare.

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

```bash
conda activate varmdyn_env
```

Run `bash scripts/run_md.sh ...`, `python workflows/md/bridge.py ...`, and MD
status/plan/check commands from the local workstation in `varmdyn_env`.

Holo ATP/Mg transfer and PyMOL rendering use `varmdyn_pymol`. The workflow
runner still runs from `varmdyn_env`, but `VARMDYN_PYMOL_CMD` points to the
PyMOL interpreter:

```bash
bash scripts/env/ensure_pymol_env.sh
```

On HPC, bridge-launched Python control tasks use the lightweight
remote `varmdyn_env` control environment. LEaP, PMEMD, and cpptraj stages use
AMBER modules through Slurm. Avoid the HPC base/default Python for workflow
scripts because it may miss required packages such as PyYAML.

| Task | Where | Environment |
|---|---|---|
| MD controller, bridge, status, planning, submit dry-runs | local workstation | `varmdyn_env` |
| Holo ATP/Mg transfer/rendering | local workstation | `varmdyn_pymol` via `VARMDYN_PYMOL_CMD` |
| Remote bridge orchestration | HPC project checkout through bridge | HPC `varmdyn_env` control env |
| LEaP, PMEMD, cpptraj | HPC compute jobs | AMBER modules plus Slurm |

## 2. Storage Rule

Scratch is for data generation. The HPC project partition is the durable source
for analysis.

Run the VarMDyn workflow code from a durable project-partition checkout. Point
generated MD products to scratch with `VARMDYN_MD_GENERATION_ROOT`, then sync
completed products back to project storage.

```bash
export VARMDYN_MD_GENERATION_ROOT=/scratch/$USER/VarMDyn/data/md
export VARMDYN_MD_PROJECT_ROOT=/path/to/hpc_project/VarMDyn/data/md
```

After each major production milestone, copy scratch data to the project
partition and verify it before cleaning scratch:

Run on: local workstation. Environment: local `varmdyn_env`; remote command
runs in the HPC `varmdyn_env` control environment.

```bash
bash scripts/run_md.sh stage --state apo --name sync_project --run
```

To extend a saved campaign later, restore from project to scratch, confirm the
completed target, then use the apo or holo extension command from the relevant
state section below.

Run on: local workstation. Environment: local `varmdyn_env`; remote command
runs in the HPC `varmdyn_env` control environment plus AMBER modules.

```bash
bash scripts/run_md.sh stage --state apo --name restore_scratch --run
```

`/scratch/$USER` is the HPC scratch filesystem. Local status output may show
that path as missing; real generation happens after the workflow is run through
the HPC bridge or from the HPC checkout.

Local fetches should write compact outputs under:

```bash
export VARMDYN_DATA_ROOT=$PWD/data
```

## 3. Folder Architecture

The VarMDyn state wrapper mirrors the validated state roots. Each state keeps the
variant folders directly under `apo/` or `holo/`, while `variants/` is only a
staging area for varmodel handoff inputs.

```text
data/md/apo/<variant>/{01.prep,02.leap,03.pmemd,04.ptraj,protocol}
data/md/holo/<variant>/{ligprep,01.prep,02.leap,03.pmemd,04.ptraj,protocol}
```

By default, MD consumes WT plus every successful variant in the varmodel
manifest (`variants: all`) and uses plain folder names such as `WT`, `R59X`, or
`A123T`. Private source comparisons map names privately when needed; VarMDyn
does not require numeric variant prefixes.

## 4. Apo

Check the remote apo runner from the repository root:

Run on: local workstation. Environment: local `varmdyn_env`; remote command
runs in the HPC `varmdyn_env` control environment.

```bash
bash scripts/run_md.sh status --state apo
bash scripts/run_md.sh stage --state apo --name handoff
```

The second command prints the planned remote handoff action. Add
`--run` only when you intentionally want the remote stage to run.

If you already ran `python workflows/md/bridge.py init --execute` from Getting
Started or the MD docs, do not repeat it. Create the run layout through the
local-to-HPC bridge only when starting from a clean remote checkout or repairing
layout:

Run on: local workstation. Environment: local `varmdyn_env`; remote command
runs in the HPC `varmdyn_env` control environment.

```bash
python workflows/md/bridge.py init --execute
```

Direct state-runner initialization is only for developers inside the HPC
checkout or for intentionally local test roots. The normal user-facing entry
point is `bash scripts/run_md.sh`.

After `prep`, the LEaP stage probes each variant charge, renders one explicit
neutralization command, and writes an audit trail:

```text
02.leap/charge_probe.log
02.leap/neutralization_plan.txt
02.leap/leap.log
02.leap/ion_report.txt
```

For all variants, submit LEaP as a Slurm array from the local bridge instead of
running `tleap` as a long login-node loop:
LEaP array wrappers and logs are state-local: apo writes under
`apo/logs/leap/`, and holo writes under `holo/logs/leap/`.

Run on: local workstation. Environment: local `varmdyn_env`; remote command
runs in the HPC `varmdyn_env` control environment plus AMBER modules.

```bash
bash scripts/run_md.sh stage --state apo --name leap_submit --run

# Wait until the LEaP Slurm array leaves the queue before checking outputs.
bash scripts/run_md.sh slurm --execute
```

Check all generated apo LEaP outputs with:

Run on: local workstation through bridge for HPC roots. Environment: local
`varmdyn_env`; remote command uses the HPC `varmdyn_env` control environment
plus AMBER tools.

```bash
bash scripts/run_md.sh check --state apo --name leap
```

Apo protocol and production controls:

```bash
# Inspect apo preMD stages 01-24 and production chunk lengths.
bash scripts/run_md.sh protocol --state apo --kind premd
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
  through `24md`, restart propagation to `cr2` and `cr3`, and production chunk
  `25md`.
- `bash scripts/run_md.sh submit --state apo --from-ns 100 --target-ns 500 --run`
  extends an already completed 100 ns apo campaign. It does not rerun chunk 25;
  it starts from each replica's existing `25md.restrt` and submits chunks 26-29
  as chained Slurm arrays: 27 waits for 26, 28 waits for 27, and 29 waits for
  28.
- `bash scripts/run_md.sh plan --state apo --action status --target-ns 500`
  reports the common completed ns across all apo variants/replicas and the
  completed chunks found for each replica in the target scratch/project root.
- The submitter checks requested target chunks before queuing jobs. If any
  requested production chunks already exist, it prints the detected completed ns
  and refuses to submit. Use a later extension window instead. Use `--force`
  only when you intentionally want to resubmit existing chunks.
- Check completed outputs before extending:
  `bash scripts/run_md.sh plan --state apo --action check-prod --target-ns 100`.
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
  `--from-ns`, the wrapper treats the campaign as fresh and starts from
  equilibration. For safety, fresh campaigns above 100 ns require an explicit
  `--allow-fresh-long` override.

## 5. Holo ATP/Mg

Check the remote holo runner from the repository root:

Run on: local workstation. Environment: local `varmdyn_env`; remote command
runs in the HPC `varmdyn_env` control environment.

```bash
bash scripts/run_md.sh status --state holo
```

ATP/Mg coordinate transfer is local-only in the user-facing workflow. Use
`bash scripts/run_md.sh local-holo-transfer --sync-inputs --execute`; do not run
remote `holo transfer` stages through the bridge.

Create the run layout through the local-to-HPC bridge when the MD roots point
to HPC scratch/project paths:

Run on: local workstation. Environment: local `varmdyn_env`; remote command
runs in the HPC `varmdyn_env` control environment.

```bash
python workflows/md/bridge.py init --execute
```

Direct state-runner initialization is only for developers inside the HPC
checkout or for intentionally local test roots. The normal user-facing entry
point is `bash scripts/run_md.sh`.

The holo ATP/Mg setup uses a PyMOL core-fit transfer over the conserved kinase
core before Hu2024 LEaP preparation. Prefer running this on the local
workstation, inspecting the local QA outputs, then syncing only the prepared
`ligprep/` inputs to HPC scratch:

Run on: local workstation. Environment: `varmdyn_pymol`.

```bash
bash scripts/env/ensure_pymol_env.sh
```

Keep the validated ATP/Mg template source in VarMDyn-owned local data before
running transfer. The default location is
`$VARMDYN_MD_PROJECT_ROOT/templates/atpmg` for the active local run root; set
`VARMDYN_MD_ATPMG_TEMPLATE_ROOT` only to override that local template source.
Do not point routine runs at an external source simulation tree. Keep source
trees read-only and copy the validated template into VarMDyn-owned data.

Local transfer and handoff to HPC scratch:

Run on: local workstation. Use `varmdyn_env` for the workflow runner.
`local-holo-transfer` defaults to an absolute conda command, so no manual PyMOL
path is needed after
`bash scripts/env/ensure_pymol_env.sh` succeeds.

```bash
bash scripts/run_md.sh local-holo-transfer --sync-inputs --execute
```

> **Note**
> `VARMDYN_PYMOL_CMD` is an advanced override for unusual local PyMOL setups.
> Do not set it during normal runs. If an old bad value is still exported in
> the shell, `local-holo-transfer` warns and falls back to the default conda
> command.

`local-holo-transfer` runs `handoff`, `seed`, `transfer`, `transfer_check`,
composes `data/md/holo/transfer_panel.png`, and then syncs prepared holo inputs
to HPC scratch when `--sync-inputs` is present. Inspect these local outputs
before moving on:

```text
data/md/holo/<variant>/ligprep/ligand-only-from-complex-atponly.pdb
data/md/holo/<variant>/ligprep/mg-only-from-complex-mgonly.pdb
data/md/holo/<variant>/ligprep/cdl.prot.noH_atpmg_from8fp5.pdb
data/md/holo/<variant>/ligprep/transfer_kinase_context.png
data/md/holo/<variant>/ligprep/transfer_ligand_zoom.png
data/md/holo/<variant>/ligprep/transfer_core_30_220_overlay.png
data/md/holo/<variant>/ligprep/transfer_core_30_220_overlay.pse
data/md/holo/transfer_panel.png
```

After local transfer and `--sync-inputs`, continue on HPC with preparation and
LEaP. Holo LEaP uses the same charge-probe and ion-report gate as apo.
Holo LEaP logs stay under `holo/logs/leap/`.

Run on: local workstation. Environment: local `varmdyn_env`; remote command
runs in the HPC `varmdyn_env` control environment plus AMBER modules.

```bash
bash scripts/run_md.sh stage --state holo --name prepare --run
bash scripts/run_md.sh stage --state holo --name leap_submit --run

# Wait until the LEaP Slurm array leaves the queue before checking outputs.
bash scripts/run_md.sh slurm --execute
bash scripts/run_md.sh check --state holo --name leap
```

Holo protocol and production controls:

```bash
# Inspect holo preMD stages 01-24 and production chunk lengths.
bash scripts/run_md.sh protocol --state holo --kind premd
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
  through `24md`, restart propagation to `cr2` and `cr3`, and production chunk
  `25md`.
- `bash scripts/run_md.sh submit --state holo --from-ns 100 --target-ns 500 --run`
  extends an already completed 100 ns holo campaign. It does not rerun chunk 25;
  it starts from each replica's existing `25md.restrt` and submits chunks 26-29
  as chained Slurm arrays: 27 waits for 26, 28 waits for 27, and 29 waits for
  28.
- `bash scripts/run_md.sh plan --state holo --action status --target-ns 500`
  reports the common completed ns across all holo variants/replicas and the
  completed chunks found for each replica in the target scratch/project root.
- The submitter checks requested target chunks before queuing jobs. If any
  requested production chunks already exist, it prints the detected completed ns
  and refuses to submit. Use a later extension window instead. Use `--force`
  only when you intentionally want to resubmit existing chunks.
- Check completed outputs before extending:
  `bash scripts/run_md.sh plan --state holo --action check-prod --target-ns 100`.
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
  `--from-ns`, the wrapper treats the campaign as fresh and starts from
  equilibration. For safety, fresh campaigns above 100 ns require an explicit
  `--allow-fresh-long` override.

## 6. Short Validation And Dependencies

Production is planned as chained 100 ns chunks. Variant folders stay plain
(`WT`, `L119R`, ...), but production chunks keep their validated restart-chain
numbers. Use the apo/holo sections above for state-specific fresh-run and
extension commands. The submit command rejects targets that are not divisible
by 100 ns.

For a fresh run, use the state-specific submit commands in the apo or holo
section after prep/LEaP templates have produced the expected protocol scripts.
The submitter queues `cr1` equilibration, restart propagation from
`cr1/24md.restrt` to `cr2/cr3`, then production chunks as Slurm arrays with
`afterok` dependencies. For extensions, the state-specific commands check the
existing completed target and submit only the missing production chunks.
Before queuing equilibration, the submitter refreshes
`job-1-24-equilibration.sh` from the VarMDyn template in the HPC project
checkout. This updates Slurm/path plumbing only; AMBER method inputs such as
`01mi.in` through `24md.in` and `25md.in` stay validated.
The preMD/equilibration Slurm wrapper follows the validated `eq1-24` resource
request by default: one node, 32 tasks on that node, 1 CPU per task, 64G memory,
and 48 hours. Production chunk arrays follow the validated 100 ns chunk request by
default: 1 GPU, 2 CPUs, 16G memory, and 48 hours. Override `EQ_TIME`,
`EQ_MEM`, `EQ_NTASKS`, `EQ_TASKS_PER_NODE`, `TIME`, `MEM`, or `CPUS` only when
the queue policy or benchmark timing requires it.
Slurm wrapper scripts, manifests, and logs are written under the state root,
such as `apo/logs/...` or `holo/logs/...`; apo and holo submissions must not
share one mutable manifest path.

For validation after layout or LEaP changes, run the short PMEMD array test. It
uses the real state/variant folders, writes `varmdyn_validate_*` inputs and
outputs, runs a shortened preMD minimization array, then runs a dependent
production array for `cr1`, `cr2`, and `cr3`.

```bash
# Submit apo validation arrays.
bash scripts/run_md.sh validate --state apo --variants all --action all

# Submit holo validation arrays after local ATP/Mg transfer and sync-inputs.
bash scripts/run_md.sh validate --state holo --variants all --action all

# Wait until the validation jobs leave the Slurm queue.
bash scripts/run_md.sh slurm --execute

# Then run final output gates.
bash scripts/run_md.sh validate --state apo --variants all --action check
bash scripts/run_md.sh validate --state holo --variants all --action check
```

The final gates should print `OK` for each variant at
`cr1/varmdyn_validate_01mi.mdout`,
`cr1/varmdyn_validate_25md.mdout`,
`cr2/varmdyn_validate_25md.mdout`, and
`cr3/varmdyn_validate_25md.mdout`.

For a smaller layout test, pass `--variants WT`.

## 7. MD Post-Processing Before Analysis

After production completes, run cpptraj post-processing before network-style
prepared trajectory replay and aggregate RMSF sanity checks. This creates the
first canonical `04.ptraj` files expected by those workflows.

Post-processing is window-based. Choose the production chunks with `--start`
and `--end`: `25-26` prepares 200 ns, `25-29` prepares 500 ns, and `30-34`
prepares a later 500 ns extension window. This lets simulation continue toward
1000 ns while you inspect an earlier window.

Post-processing reads completed `03.pmemd` chunks, writes cpptraj inputs under
`04.ptraj`, and submits one Slurm array task per variant. It creates a
protein-only `striped_v2` topology, strips each replica trajectory, concatenates
and subsamples `cr1`, `cr2`, and `cr3`, and writes aggregate backbone RMSF by
residue. The validated 25-29, stride-20 window keeps the historical
`750frames` concatenated filename; other windows use a `stride<value>` filename
label. Apo strips `:WAT,Na+,Cl-`; holo strips `:WAT,Na+,Cl-,ATP,MG` for the
default protein-only analysis products.
For chunks `25-29`, strict checks expect 25,000 frames in each per-replica
stripped trajectory and 3,750 frames in the concatenated stride-20 trajectory.
`BADFRAMES` means the file exists but must be regenerated before downstream
analysis.

This modularizes the validated analysis-prep behavior. The default route is
the final protein-only `striped_v2` path used by prepared network/RMSF analysis.
Ligand-retaining `keepATPmg` trajectories are a separate source flavor for
holo ligand-aware inspection and are not the default residue-network input.
The validated RMSD/RMSF route uses per-replica protein-only stripped
trajectories for apo and holo/ATP-Mg, then averages `cr1`, `cr2`, and `cr3`;
those tables are not calculated from the three-replica concatenated trajectory.
Clean aligned trajectories, RMSD CSVs, RMSF CSVs, ROI displacement CSVs, and
kept displacement TSVs are downstream dynamics-analysis products and are not
generated by this current post-processing command.

Run on: local workstation. Environment: local `varmdyn_env`; remote cpptraj
jobs use HPC AMBER modules through Slurm. By default the bridge reads completed
simulations from HPC scratch. If you have already copied the completed
simulation tree to project storage or another HPC-visible location, pass
`--md-root /path/to/hpc_visible/VarMDyn/data/md`. That root must contain the
`apo/` and `holo/` folders, and the same value should be used for `plan`,
`submit`, and `check`. Do not pass a local workstation path unless that exact
path is also mounted on the HPC system.

```bash
bash scripts/run_md.sh postprocess --state apo --action plan --start 25 --end 26
bash scripts/run_md.sh postprocess --state apo --action plan --start 25 --end 29
bash scripts/run_md.sh postprocess --state apo --action submit --start 25 --end 29 --run
bash scripts/run_md.sh slurm --execute
bash scripts/run_md.sh postprocess --state apo --action check --start 25 --end 29

bash scripts/run_md.sh postprocess --state holo --action plan --start 25 --end 29
bash scripts/run_md.sh postprocess --state holo --action submit --start 25 --end 29 --run
bash scripts/run_md.sh slurm --execute
bash scripts/run_md.sh postprocess --state holo --action check --start 25 --end 29
```

`submit --run` submits only variants with missing post-processing outputs. If
the selected window is already complete for every variant, it prints a skip
message and submits no Slurm job. Use `--force` only when you intentionally
want to regenerate existing outputs.

Explicit source-root example:

```bash
bash scripts/run_md.sh postprocess --state apo --action plan --md-root /path/to/hpc_visible/VarMDyn/data/md --start 25 --end 29
```

Expected products include `02.leap/com/cdl.com.striped_v2.prmtop`,
per-replica `production-<start>-to-<end>-<ns>.*.striped_v2.mdcrd.nc`, the
window-specific concatenated trajectory, and
`04.ptraj/com/rmsf/rmsf.byresidue.agr`.

## 8. Storage And Fetch

Keep active generation and current post-processing in scratch. Copy the full
simulation tree to project storage when you need durable storage, a long pause,
or project-partition analysis. Fetch only compact outputs locally.

Run on: local workstation. Environment: local `varmdyn_env`; remote copies run
through the bridge.

```bash
bash scripts/run_md.sh storage --state all --variants all --action sync-project --verify
bash scripts/run_md.sh storage --state all --variants all --action sync-project --verify --run

bash scripts/run_md.sh storage --state all --variants all --action restore-scratch --verify
bash scripts/run_md.sh storage --state all --variants all --action restore-scratch --verify --run

bash scripts/run_md.sh fetch --state apo --execute
bash scripts/run_md.sh fetch --state holo --execute
```

Storage sync is for durable remote copies. Fetch is optional and should bring
back only compact local outputs for inspection, not full raw trajectories.

## 9. HPC Bridge

The bridge is the local control plane for HPC work:

Run on: local workstation. Environment: local `varmdyn_env`; remote commands
use the HPC `varmdyn_env` control environment.

```bash
python workflows/md/bridge.py check --execute
python workflows/md/bridge.py sync-code --execute
python workflows/md/bridge.py setup-env --env hpc --execute
python scripts/checks/check_readiness.py --hpc
python workflows/md/bridge.py init --execute
bash scripts/run_md.sh status --state apo
```

`sync-code` updates only the durable HPC project checkout with the current
VarMDyn code, configs, and docs. It does not copy simulation data from scratch
or project storage.

Add `--execute` only after dry-run output looks correct.

## 10. Developer Smoke Tests

`workflows/md/stages/smoke.py` is a developer/HPC plumbing helper for tiny
continuation checks from an already validated source tree. It is not part of
the normal public MD runbook. Normal users should follow handoff, prep, LEaP,
equilibration, production, post-processing, and analysis instead.

## 11. Public Boundary

Public docs describe the reusable VarMDyn workflow. Internal parity checks
against local validation roots are not public user requirements.

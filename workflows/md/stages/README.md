# MD Stages

These scripts are internal implementation pieces for the unified MD command:

```bash
bash scripts/run_md.sh ...
```

Keep user-facing commands in `scripts/run_md.sh` and `workflows/md/cli.py`.
Keep state-specific shell/AMBER templates under `workflows/md/apo/` and
`workflows/md/holo/`.

| Script | Role |
|---|---|
| `handoff.py` | Stage WT and varmodel variants into apo/holo MD system folders. |
| `submit.py` | Submit preMD, restart propagation, and production chunks with Slurm dependencies. |
| `restart.py` | Copy `cr1/24md.restrt` into `cr2` and `cr3` after preMD completion. |
| `trajectory.py` | Plan/check production chunks and extension windows. |
| `postprocess.py` | Prepare stripped, concatenated, and RMSF-ready trajectory products. |
| `storage.py` | Sync scratch generation data to/from durable project storage. |
| `cleanup.py` | Cancel and clean interrupted production extension chunks. |
| `validate.py` | Run short PMEMD validation arrays for generated layouts. |
| `smoke.py` | Compatibility smoke runner for short source-layout continuation tests. |

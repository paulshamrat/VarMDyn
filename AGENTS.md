# Agent Guide

This file gives public-safe instructions for coding agents working in VarMDyn.
It is intentionally generic: private machine paths, usernames, unpublished
manuscript details, and source-repository parity checks belong in ignored local
notes, not here.

## First Reads

Start with:

1. `README.md`
2. `docs/source/getting-started.md`
3. `docs/source/project-map.md`
4. The workflow page for the task you are changing
5. `SKILLS.md` for the short workflow map

If a private local checkpoint exists, read it after this file for maintainer
context. Do not copy private checkpoint details into public docs.

## Public/Private Boundary

- Public docs and tracked files must use generic paths such as `data/`,
  `/path/to/...`, and `/scratch/$USER/...`.
- Do not expose real usernames, SSH sockets, private project paths, license
  keys, unpublished manuscript internals, or generated MD trajectories.
- Keep generated data under ignored folders such as `data/`, `.local_docs/`,
  `site/`, and workflow output directories.
- Keep private agent notes under ignored local note folders.

## Entry Points

Prefer stable user-facing wrappers:

```bash
bash scripts/run_clustering.sh
bash scripts/run_varmodel.sh
bash scripts/run_md.sh ...
bash scripts/run_analysis.sh ...
python scripts/docs/build_local_docs.py --serve
```

Use lower-level files under `workflows/` for implementation and debugging, not
as the first command shown to users unless the workflow page explicitly says so.

## Documentation Rules

- Every runnable command block should make clear where it runs, which
  environment it needs, and which paths it reads or writes.
- Keep Google Colab, local workstation, and HPC instructions separate.
- Public Colab instructions may cover smoke/light workflows. MD engine stages
  require the user to install and configure AMBER/AmberTools in that runtime.
- Public HPC instructions may mention Slurm and AMBER-compatible tools, but must
  stay site-neutral.
- Test commands before documenting them. Prefer a dry-run plus the safest real
  validation available.

## MD/HPC Rules

- VarMDyn is local-first: local commands control remote HPC work through the
  bridge when heavy compute is needed.
- Code sync updates the durable HPC checkout only; it does not copy simulation
  data.
- Scratch is for active data generation. Durable project or external storage is
  for longer-term storage and analysis sources.
- `--md-root` must point to a path visible from the machine where the remote
  command runs. Do not use a local workstation path for an HPC command unless
  that exact path is mounted on the HPC system.
- Post-processing and production submissions should be guarded against
  accidental duplicate work; use force flags only when intentionally
  regenerating outputs.

## Testing Checklist

Before handing off code or docs changes, run the relevant subset:

```bash
python scripts/checks/check_repo_ready.py
mkdocs build --strict
python scripts/docs/build_local_docs.py --strict
git diff --check
```

For changed Python entry points, also run `python -m py_compile` on those files.
For bridge/HPC changes, sync code before remote validation.

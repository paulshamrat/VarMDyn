# Output Policy

`VarMDyn` should stay small, public-safe, and scripts-first.

- Keep `workflows/` as code plus intentional small public seed inputs only.
- Put user-supplied data, fetched lightweight analysis outputs, and generated run products in `data/` (or `$VARMDYN_RUN_ROOT`).
- Do not commit manuscript figures, manuscript tables, trajectories, RMSF/RMSD
  source files, network outputs, VMD intermediates, or exploratory run products.
- Keep machine-specific paths and account settings in your shell environment or
  ignored local notes. Use template paths such as `/path/to/data` in shared
  documentation.
- The only tracked data exception is the public clustering seed Excel/PDB under
  `workflows/clustering/data/raw/`.

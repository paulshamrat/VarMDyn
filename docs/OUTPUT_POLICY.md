# Output Policy

`varmdyn` should stay small, public-safe, and scripts-first.

- Put generated outputs in `runs/` or `$VARMDYN_RUN_ROOT`.
- Keep user-supplied private inputs in `data_private/`, `private_data/`, or
  external storage.
- Do not commit manuscript figures, manuscript tables, trajectories, RMSF/RMSD
  source files, network outputs, VMD intermediates, or exploratory run products.
- Do not commit personal directory paths, HPC usernames, socket paths, or
  license keys. Use template paths such as `/path/to/private/data`.
- The only tracked data exception is the public clustering seed Excel/PDB under
  `workflows/clustering/data/raw/`.

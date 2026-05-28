RMSF overlay review workflow
============================

This folder contains scripts for rebuilding apo/ATP-Mg RMSF overlay panels from
user-supplied RMSF inputs. The public repository does not track RMSF `.agr`
files, manuscript panels, or HPC-specific HPC paths.

Inputs
------

Provide inputs at run time through environment variables or CLI
arguments:

- `VARMDYN_MD_LEGACY_ROOT=/path/to/md_input_root`
- `VARMDYN_RMSF_SOURCE_INPUT_ROOT=/path/to/rmsf_source_inputs`
- `VARMDYN_RMSF_SOURCE_MANIFEST=/path/to/rmsf_source_input_manifest.tsv`

Outputs
-------

Write generated panels to `runs/` or `$VARMDYN_RUN_ROOT`.

Public-safety rule
------------------

Do not commit RMSF source files, generated panels, personal paths, HPC
usernames, or project directory layouts.

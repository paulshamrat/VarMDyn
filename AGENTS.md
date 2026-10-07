# VarMDyn contributor rules

Read README.md, the affected stage README and config/cdkl5-activation/README.md before editing.

- Scientific source lives under scripts/, not workflows/. Keep stage numbering and source provenance.
- Keep only README.md at the scripts/ root. Launchers belong to their owning stage; use canonical checks/, env/ and data/ utility paths instead of forwarding aliases. When moving a launcher, verify its repository-root resolution from an unrelated working directory and update documentation, Makefile and readiness inventories.
- Keep public paths generic; obtain external trajectory roots through configuration. Never include credentials, private manuscript/feedback files, machine paths or generated simulation data.
- Keep data/ and logs/ contents ignored except scaffold .gitkeep files. Tests may contain compact synthetic fixtures.
- Read existing code before editing. Make the smallest change needed, preserve scientific definitions and verify callers when relocating source.
- Separate processing from plotting for new code; document inherited mixed implementations until split and numerically validated.
- Develop on dev1. Public main receives only approved sanitized release snapshots with clean history. Do not push an unvalidated migration as a reproduction release.
- Local Palmetto access must use the hpc CLI; do not execute inherited direct SSH/rsync helpers against that site.
- Before commits, run Ruff formatting/lint and py_compile for changed Python, bash -n for shell/Slurm, relevant regression tests and git diff --check. Record limitations; syntax checks are not numerical parity.
- Use `make verify` for the release source checks. A clean checkout must pass without ignored study inputs. Keep generated sites and caches out of releases; do not delete scientific runtime results merely to shrink a local checkout.
- Do not change scientific thresholds to resolve conflicting provenance implicitly. Entropy has a known 50-median-transitions versus 5%-transition-rate discrepancy.
- Completion markers must follow verified nonempty required outputs. Never overwrite archived trajectories during code migration.
- Validate in isolated ignored data/analysis/validation and logs/analysis/validation directories. Record input hashes and the exact comparison target. A method directory name alone is insufficient: older results can use different reference-selection rules. Report such differences and compare against the approved current baseline before changing scientific logic. Separate execution checks, downstream table parity and raw trajectory reproduction in validation claims.

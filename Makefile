.PHONY: check verify clustering-smoke varmodel-dry-run dynamics-local env-check checksums

check:
	python scripts/checks/check_repo_ready.py

verify:
	ruff format --check scripts tests
	ruff check scripts tests
	python -m compileall -q scripts tests
	python -c 'import pathlib, subprocess; [subprocess.run(["bash", "-n", str(p)], check=True) for p in pathlib.Path("scripts").rglob("*") if p.suffix in (".sh", ".slurm", ".sbatch")]'
	PYTHONPATH=scripts/clustering python -m pytest -q tests scripts/clustering/tests
	python scripts/checks/check_repo_ready.py
	git diff --check

clustering-smoke:
	bash scripts/clustering/run.sh

varmodel-dry-run:
	bash scripts/varmodel/run.sh --dry-run

dynamics-local:
	bash scripts/analysis/03_dynamics/run_local.sh

env-check:
	python -c "import matplotlib, numpy, pandas, scipy, sklearn, PIL; print('env ok')"

checksums:
	bash scripts/data/checksums.sh

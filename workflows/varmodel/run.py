#!/usr/bin/env python3
"""Refactored wrapper for CDKL5 variant model generation (mutate-only).

This stage intentionally reuses legacy `varmodel/modeller/modeller6.py`
without editing it.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import getpass
import shutil
import subprocess
import sys
from pathlib import Path

from qc import write_qc_report


def _load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "PyYAML is required to read config.yaml. Install with: pip install pyyaml"
        ) from exc
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping: {path}")
    return data


def _timestamp() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def _read_mutations(path: Path) -> list[str]:
    muts: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        muts.append(line)
    return muts


def _assert_exists(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")


def _run(cmd: list[str], cwd: Path, dry_run: bool) -> None:
    print("[CMD]", " ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, cwd=str(cwd), check=True)


def _find_modeller_config(python_exe: Path) -> Path | None:
    # Works for conda envs: <env>/bin/python -> <env>/lib/modeller-*/modlib/modeller/config.py
    env_root = python_exe.parent.parent
    candidates = sorted(env_root.glob("lib/modeller-*/modlib/modeller/config.py"))
    return candidates[-1] if candidates else None


def _patch_modeller_license(config_py: Path, key: str) -> None:
    lines = config_py.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("license"):
            lines[i] = f"license = '{key}'"
            config_py.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return
    raise RuntimeError(f"Could not find `license = ...` line in {config_py}")


def _ensure_modeller_ready(
    python_exe: Path, license_key: str | None, prompt_license: bool
) -> None:
    # First try import as-is
    probe = subprocess.run(
        [str(python_exe), "-c", "import modeller"],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        return

    err = (probe.stderr or "") + "\n" + (probe.stdout or "")
    if "Invalid license key" not in err and "check_lice_E" not in err:
        raise RuntimeError(
            "Modeller import failed (not a license error). "
            f"python_exe={python_exe}\n{err.strip()}"
        )

    key = license_key
    if not key and prompt_license:
        key = getpass.getpass("Enter MODELLER license key: ").strip()
    if not key:
        raise RuntimeError(
            "Modeller license is invalid and no key was provided. "
            "Pass --license-key or run interactively to enter key."
        )

    config_py = _find_modeller_config(python_exe)
    if not config_py:
        raise RuntimeError(
            "Could not locate modeller config.py near python_exe. "
            f"python_exe={python_exe}"
        )
    _patch_modeller_license(config_py, key)

    # Retry once after patch
    probe2 = subprocess.run(
        [str(python_exe), "-c", "import modeller"],
        capture_output=True,
        text=True,
    )
    if probe2.returncode != 0:
        err2 = (probe2.stderr or "") + "\n" + (probe2.stdout or "")
        raise RuntimeError(
            "Modeller license patch attempted but import still failed.\n"
            f"{err2.strip()}"
        )
    print(f"[OK] Modeller license configured in: {config_py}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Run refactored variant modeling stage using legacy modeller6 mutate-only mode."
    )
    ap.add_argument(
        "--config",
        default="varmodel/config.yaml",
        help="Path to stage config YAML",
    )
    ap.add_argument(
        "--run-name",
        default=None,
        help="Override run directory name (default: run_YYYYMMDD_HHMMSS)",
    )
    ap.add_argument(
        "--out-root",
        default=None,
        help="Override output root. Use an absolute /tmp path for reviewer smoke runs.",
    )
    ap.add_argument("--dry-run", action="store_true", help="Print actions only")
    ap.add_argument(
        "--license-key",
        default=None,
        help="MODELLER license key to patch automatically if key is invalid.",
    )
    ap.add_argument(
        "--no-license-prompt",
        action="store_true",
        help="Disable interactive key prompt when MODELLER license is invalid.",
    )
    ap.add_argument(
        "--mut",
        default=None,
        help="Single mutation to run (e.g. L119R) instead of mutations_list.",
    )
    args = ap.parse_args(argv)

    invocation_root = Path.cwd().resolve()
    cfg_path = (invocation_root / args.config).resolve()
    _assert_exists(cfg_path, "config")
    cfg_root = _load_yaml(cfg_path)
    cfg = cfg_root.get("varmodel", {})
    if not isinstance(cfg, dict):
        raise ValueError("`varmodel` section must be a mapping")

    # Config paths are authored relative to repository root. Support both:
    # 1) running from repo root with --config varmodel/config.yaml
    # 2) running from inside varmodel/ with --config config.yaml
    project_root = cfg_path.parent.parent.resolve()

    legacy_script = (project_root / cfg.get("legacy_script", "")).resolve()
    python_exe_cfg = str(cfg.get("python_exe", "")).strip()
    wt_pdb = (project_root / cfg.get("wt_pdb", "")).resolve()
    mut_list = (project_root / cfg.get("mutations_list", "")).resolve()
    if args.out_root:
        out_root = Path(args.out_root).expanduser().resolve()
    else:
        out_root = (project_root / cfg.get("out_root", "varmodel/outputs")).resolve()
    chain = str(cfg.get("chain", "A"))
    seed = str(cfg.get("seed", -49837))
    python_exe = Path(python_exe_cfg).resolve() if python_exe_cfg else Path(sys.executable)

    _assert_exists(legacy_script, "legacy_script")
    _assert_exists(wt_pdb, "wt_pdb")
    _assert_exists(mut_list, "mutations_list")
    _assert_exists(python_exe, "python_exe")

    if not args.dry_run:
        _ensure_modeller_ready(
            python_exe=python_exe,
            license_key=args.license_key,
            prompt_license=(not args.no_license_prompt),
        )

    run_name_cfg = str(cfg.get("run_name", "")).strip()
    run_name = args.run_name if args.run_name is not None else run_name_cfg
    if run_name:
        run_dir = out_root / run_name
    else:
        run_dir = out_root
    mutants_dir = run_dir / "mutants"
    staged_wt = run_dir / wt_pdb.name
    staged_list = run_dir / mut_list.name
    summary_csv = run_dir / "mutate_summary.csv"
    log_file = run_dir / "mutate.log"
    manifest_csv = run_dir / "manifest.csv"

    if args.mut:
        muts = [args.mut]
    else:
        muts = _read_mutations(mut_list)
        if not muts:
            raise ValueError(f"No mutations found in list: {mut_list}")

    print(f"[INFO] Config: {cfg_path}")
    print(f"[INFO] Project root: {project_root}")
    print(f"[INFO] Legacy script: {legacy_script}")
    print(f"[INFO] Python executable: {python_exe}")
    print(f"[INFO] WT PDB: {wt_pdb}")
    print(f"[INFO] Mutations: {len(muts)} -> {', '.join(muts)}")
    print(f"[INFO] Run directory: {run_dir}")

    if not args.dry_run:
        mutants_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wt_pdb, staged_wt)
        if args.mut:
            staged_list.write_text(args.mut + "\n", encoding="utf-8")
        else:
            shutil.copy2(mut_list, staged_list)

    cmd = [
        str(python_exe),
        str(legacy_script),
        "--pdb-in",
        str(staged_wt),
        "--chain",
        chain,
        "--list",
        str(staged_list),
        "--outdir-mut",
        str(mutants_dir),
        "--seed",
        seed,
        "--logfile",
        str(log_file),
    ]
    try:
        _run(cmd, cwd=project_root, dry_run=args.dry_run)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "Legacy modeller run failed. Ensure the selected python has `modeller` installed "
            f"(python_exe={python_exe})."
        ) from exc

    # Build compact manifest for downstream MD handoff.
    if args.dry_run:
        print("[DRY-RUN] Would write:", manifest_csv)
        return 0

    _assert_exists(summary_csv, "mutate_summary.csv")
    with summary_csv.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    by_mut: dict[str, dict] = {}
    for row in rows:
        mut = (row.get("mutation") or "").strip()
        if mut and mut not in by_mut:
            by_mut[mut] = row

    with manifest_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["mutation", "status", "output_pdb", "observed_wt"])
        for mut in muts:
            row = by_mut.get(mut, {})
            w.writerow(
                [
                    mut,
                    row.get("status", "MISSING"),
                    row.get("out_pdb", ""),
                    row.get("observed_WT", ""),
                ]
            )

    ok = sum(1 for mut in muts if by_mut.get(mut, {}).get("status") == "OK")
    qc = write_qc_report(summary_csv=summary_csv, expected_mutations=muts, run_dir=run_dir)
    print(f"[OK] Completed variant modeling run: {run_dir}")
    print(f"[OK] mutate_summary: {summary_csv}")
    print(f"[OK] manifest: {manifest_csv}")
    print(f"[OK] varmodel QC: {qc.qc_csv}")
    print(f"[INFO] Successful mutations: {ok}/{len(muts)}")
    print(f"[INFO] QC structure checks: {qc.ok_count}/{len(qc.rows)}")
    if qc.warnings:
        print(f"[WARN] QC warnings: {len(qc.warnings)}; see {qc.qc_summary}")
        for item in qc.warnings[:5]:
            print(f"[WARN] {item}")
    if qc.errors:
        print(f"[ERROR] QC errors: {len(qc.errors)}; see {qc.qc_summary}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build RMSD/RMSF analysis2-style tables from VarMDyn MD outputs."""

from __future__ import annotations

import argparse
import os
import shlex
import statistics
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUPPORT_DIRS = {"variants", "logs", "all", "*"}
REPLICAS = ["cr1", "cr2", "cr3"]


def md_root(args: argparse.Namespace) -> Path:
    raw = args.md_root or os.environ.get("VARMDYN_MD_GENERATION_ROOT", REPO_ROOT / "data" / "md")
    return Path(os.path.expandvars(str(raw))).expanduser()


def default_out_root(md_root_value: Path) -> Path:
    if md_root_value.name == "md":
        return md_root_value.parent / "mdan" / "rms"
    return Path(os.environ.get("VARMDYN_RUN_ROOT", REPO_ROOT / "data")) / "mdan" / "rms"


def out_root(args: argparse.Namespace) -> Path:
    raw = args.out_root or os.environ.get("VARMDYN_MDAN_RMS_ROOT")
    return Path(os.path.expandvars(raw)).expanduser() if raw else default_out_root(md_root(args))


def state_label(state: str) -> str:
    return "atpmg" if state == "holo" else "apo"


def variant_dirs(root: Path, variants: str) -> list[Path]:
    if variants != "all":
        return [root / item.strip() for item in variants.split(",") if item.strip()]
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and path.name not in SUPPORT_DIRS and not any(ch in path.name for ch in "*?[]")
    )


def window_label(start: int, end: int) -> tuple[str, str]:
    chunks = f"{start}-to-{end}"
    ns = f"{(end - start + 1) * 100}ns"
    return chunks, ns


def replica_traj(variant: Path, replica: str, start: int, end: int) -> Path:
    chunks, ns = window_label(start, end)
    return (
        variant
        / "04.ptraj"
        / "com"
        / replica
        / "traj-proc"
        / f"production-{chunks}-{ns}.{replica}.striped_v2.mdcrd.nc"
    )


def topology(variant: Path) -> Path:
    return variant / "02.leap" / "com" / "cdl.com.striped_v2.prmtop"


def write_text(path: Path, text: str, execute: bool) -> None:
    print(f"[WRITE] {path}")
    if execute:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def submit(cmd: list[str], execute: bool) -> None:
    print("[CMD]", " ".join(shlex.quote(part) for part in cmd))
    if execute:
        print(subprocess.check_output(cmd, text=True).strip())


def read_xy(path: Path) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text or text.startswith(("@", "#")):
                continue
            fields = text.split()
            if len(fields) < 2:
                continue
            try:
                xs.append(float(fields[0]))
                ys.append(float(fields[1]))
            except ValueError:
                continue
    if not xs:
        raise ValueError(f"no data points found in {path}")
    return xs, ys


def aggregate_series(files: list[Path], x_name: str, out: Path) -> None:
    series = [read_xy(path) for path in files]
    x0 = series[0][0]
    for path, (xs, _ys) in zip(files, series):
        if len(xs) != len(x0) or any(abs(a - b) > 1e-6 for a, b in zip(xs, x0)):
            raise SystemExit(f"replica coordinates do not match for {path}")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        handle.write(f"{x_name}," + ",".join(REPLICAS) + ",mean,sd\n")
        for idx, x in enumerate(x0):
            values = [ys[idx] for _xs, ys in series]
            mean = statistics.fmean(values)
            sd = statistics.stdev(values) if len(values) > 1 else 0.0
            handle.write(
                f"{int(x) if float(x).is_integer() else x},"
                + ",".join(f"{value:.6f}" for value in values)
                + f",{mean:.6f},{sd:.6f}\n"
            )


def aggregate_variant(args: argparse.Namespace) -> int:
    variant = Path(args.variant_dir).expanduser()
    out = out_root(args)
    state = state_label(args.state)
    rms_work = variant / "04.ptraj" / "com" / "analysis2"
    rmsd_files = [rms_work / replica / "rmsd_bb.dat" for replica in REPLICAS]
    rmsf_files = [rms_work / replica / "rmsf_byres.dat" for replica in REPLICAS]
    aggregate_series(rmsd_files, "frame", out / "rmsd" / "by_system" / state / variant.name / "rmsd_bb_mean_sd.csv")
    aggregate_series(rmsf_files, "residue", out / "rmsf" / "by_system" / state / variant.name / "rmsf_mean_sd.csv")
    print(f"[OK] aggregated RMS tables: {args.state}/{variant.name}")
    return 0


def prepare_variant(args: argparse.Namespace, state: str, variant: Path, execute: bool) -> None:
    top = topology(variant)
    if not top.exists():
        raise SystemExit(f"missing topology: {top}")
    for replica in REPLICAS:
        traj = replica_traj(variant, replica, args.start, args.end)
        if not traj.exists():
            raise SystemExit(f"missing trajectory: {traj}")
        work = variant / "04.ptraj" / "com" / "analysis2" / replica
        rel_top = os.path.relpath(top, work)
        rel_traj = os.path.relpath(traj, work)
        write_text(
            work / "rmsd.in",
            "\n".join(
                [
                    f"parm {rel_top}",
                    f"trajin {rel_traj}",
                    "rms first :1-303@CA,C,N out rmsd_bb.dat",
                    "run",
                    "",
                ]
            ),
            execute,
        )
        write_text(
            work / "rmsf.in",
            "\n".join(
                [
                    f"parm {rel_top}",
                    f"trajin {rel_traj}",
                    "rms first :1-303@CA,C,N",
                    "atomicfluct :1-303@CA byres out rmsf_byres.dat",
                    "run",
                    "",
                ]
            ),
            execute,
        )


def missing_outputs(args: argparse.Namespace, variant: Path) -> list[Path]:
    return [path for path in expected_outputs(args, variant) if not path.is_file()]


def prepare(args: argparse.Namespace, variants: list[Path], execute: bool) -> tuple[Path, Path]:
    if not variants:
        raise SystemExit("no variant folders selected for RMS analysis")
    logs = out_root(args) / "logs" / args.state
    manifest = logs / "rms_manifest.tsv"
    wrapper = logs / "rms_array.sh"
    rows = []
    for variant in variants:
        prepare_variant(args, args.state, variant, execute)
        rows.append("\t".join([args.state, variant.name, str(variant), str(out_root(args))]))
    write_text(manifest, "\n".join(rows) + "\n", execute)
    write_text(
        wrapper,
        f"""#!/usr/bin/env bash
set -euo pipefail

MANIFEST="{manifest}"
TASK_ID="${{SLURM_ARRAY_TASK_ID:-1}}"
LINE="$(sed -n "${{TASK_ID}}p" "$MANIFEST")"
IFS=$'\\t' read -r STATE VARIANT VARIANT_DIR OUT_ROOT <<< "$LINE"
REPO_ROOT="{REPO_ROOT}"

source "$REPO_ROOT/workflows/md/scripts/modules.sh"
varmdyn_load_amber_modules

echo "VARMDYN_RMS_START $(date -Is) state=${{STATE}} variant=${{VARIANT}}"
for replica in cr1 cr2 cr3; do
  cd "$VARIANT_DIR/04.ptraj/com/analysis2/$replica"
  cpptraj -i rmsd.in
  cpptraj -i rmsf.in
done

cd "$REPO_ROOT"
python workflows/mdan/rms.py aggregate \
  --state "$STATE" \
  --variant-dir "$VARIANT_DIR" \
  --md-root "{md_root(args)}" \
  --out-root "$OUT_ROOT" \
  --start {args.start} \
  --end {args.end}

echo "VARMDYN_RMS_DONE $(date -Is) state=${{STATE}} variant=${{VARIANT}}"
""",
        execute,
    )
    if execute:
        wrapper.chmod(0o755)
    return manifest, wrapper


def submit_rms(args: argparse.Namespace) -> int:
    variants = variant_dirs(md_root(args) / args.state, args.variants)
    if not variants:
        raise SystemExit(f"no variant folders found under {md_root(args) / args.state}")
    if not args.force:
        selected = []
        for variant in variants:
            missing = missing_outputs(args, variant)
            if missing:
                selected.append(variant)
            else:
                print(f"[SKIP] {args.state}/{variant.name}: RMSD/RMSF outputs already complete")
        variants = selected
    if not variants:
        print("[OK] all selected variants already have RMSD/RMSF outputs; no Slurm job submitted")
        print("[INFO] use --force only when you intentionally want to regenerate these outputs")
        return 0
    manifest, wrapper = prepare(args, variants, args.execute)
    logs = out_root(args) / "logs" / args.state
    cmd = [
        "sbatch",
        "--parsable",
        f"--job-name=varmdyn_{args.state}_rms",
        f"--partition={os.environ.get('RMS_PARTITION', os.environ.get('PARTITION', 'work1'))}",
        f"--cpus-per-task={os.environ.get('RMS_CPUS', '4')}",
        f"--mem={os.environ.get('RMS_MEM', '16G')}",
        f"--time={os.environ.get('RMS_TIME', '04:00:00')}",
        f"--array=1-{len(variants)}",
        f"--chdir={logs}",
        f"--output={logs / 'rms_%A_%a.out'}",
        f"--error={logs / 'rms_%A_%a.err'}",
        str(wrapper),
    ]
    print(f"manifest={manifest}")
    submit(cmd, args.execute)
    return 0


def expected_outputs(args: argparse.Namespace, variant: Path) -> list[Path]:
    state = state_label(args.state)
    base = out_root(args)
    return [
        base / "rmsd" / "by_system" / state / variant.name / "rmsd_bb_mean_sd.csv",
        base / "rmsf" / "by_system" / state / variant.name / "rmsf_mean_sd.csv",
    ]


def check(args: argparse.Namespace) -> int:
    failures = 0
    for variant in variant_dirs(md_root(args) / args.state, args.variants):
        for path in expected_outputs(args, variant):
            ok = path.is_file()
            print(f"{'OK' if ok else 'MISSING'} {path}")
            failures += 0 if ok else 1
    return 1 if failures else 0


def plan(args: argparse.Namespace) -> int:
    root = md_root(args)
    out = out_root(args)
    variants = variant_dirs(root / args.state, args.variants)
    print(f"state={args.state}")
    print(f"md_root={root}")
    print(f"out_root={out}")
    print(f"window={args.start}-to-{args.end}")
    print(f"variants={','.join(path.name for path in variants) if variants else 'none'}")
    print("outputs=rmsd/by_system/<state>/<variant>/rmsd_bb_mean_sd.csv,rmsf/by_system/<state>/<variant>/rmsf_mean_sd.csv")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "submit", "check"):
        p = sub.add_parser(name)
        p.add_argument("--state", choices=["apo", "holo"], required=True)
        p.add_argument("--variants", default="all")
        p.add_argument("--md-root", default=None)
        p.add_argument("--out-root", default=None)
        p.add_argument("--start", type=int, default=25)
        p.add_argument("--end", type=int, default=29)
        p.add_argument("--execute", action="store_true")
        p.add_argument("--force", action="store_true")
    p = sub.add_parser("aggregate")
    p.add_argument("--state", choices=["apo", "holo"], required=True)
    p.add_argument("--variant-dir", required=True)
    p.add_argument("--md-root", default=None)
    p.add_argument("--out-root", default=None)
    p.add_argument("--start", type=int, default=25)
    p.add_argument("--end", type=int, default=29)
    args = parser.parse_args()
    if args.command == "plan":
        return plan(args)
    if args.command == "submit":
        return submit_rms(args)
    if args.command == "check":
        return check(args)
    return aggregate_variant(args)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Prepare analysis-ready MD trajectories with cpptraj."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SUPPORT_DIRS = {"variants", "logs", "all", "*"}
REPLICAS = ["cr1", "cr2", "cr3"]


def generation_root(args: argparse.Namespace) -> Path:
    raw = args.md_root or os.environ.get("VARMDYN_MD_GENERATION_ROOT", "/scratch/$USER/VarMDyn/data/md")
    return Path(os.path.expandvars(raw)).expanduser()


def state_root(args: argparse.Namespace) -> Path:
    return generation_root(args) / args.state


def variant_dirs(root: Path, variants: str) -> list[Path]:
    if variants != "all":
        return [root / item for item in variants.split(",") if item.strip()]
    if not root.is_dir():
        return []
    return sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and path.name not in SUPPORT_DIRS and not any(ch in path.name for ch in "*?[]")
    )


def strip_mask(state: str) -> str:
    if state == "holo":
        return ":WAT,Na+,Cl-,ATP,MG"
    return ":WAT,Na+,Cl-"


def window_label(start: int, end: int) -> tuple[str, str]:
    chunks = f"{start}-to-{end}"
    ns = f"{(end - start + 1) * 100}ns"
    return chunks, ns


def concat_label(start: int, end: int, stride: int) -> str:
    if start == 25 and end == 29 and stride == 20:
        return "750frames"
    return f"stride{stride}"


def concatenated_name(start: int, end: int, stride: int) -> str:
    chunks, _ns = window_label(start, end)
    return f"production-{chunks}-concatenated-{concat_label(start, end, stride)}.striped_v2.mdcrd.nc"


def expected_replica_frames(start: int, end: int) -> int:
    return (end - start + 1) * 5000


def expected_concatenated_frames(start: int, end: int, stride: int) -> int:
    per_replica = expected_replica_frames(start, end)
    return (per_replica // stride) * len(REPLICAS)


def postprocess_outputs(variant: Path, start: int, end: int, stride: int) -> list[Path]:
    chunks, ns = window_label(start, end)
    base = variant / "04.ptraj" / "com"
    out = [variant / "02.leap" / "com" / "cdl.com.striped_v2.prmtop"]
    out.extend(base / replica / "traj-proc" / f"production-{chunks}-{ns}.{replica}.striped_v2.mdcrd.nc" for replica in REPLICAS)
    out.append(base / "concatenated" / concatenated_name(start, end, stride))
    out.append(base / "rmsf" / "rmsf.byresidue.agr")
    return out


def missing_outputs(variant: Path, start: int, end: int, stride: int) -> list[Path]:
    missing = []
    for path in postprocess_outputs(variant, start, end, stride):
        if not path.is_file():
            missing.append(path)
            continue
        expected = expected_frames_for_path(path, start, end, stride)
        if expected is not None and netcdf_frames(path) != expected:
            missing.append(path)
    return missing


def expected_frames_for_path(path: Path, start: int, end: int, stride: int) -> int | None:
    if path.suffix != ".nc":
        return None
    if "/concatenated/" in str(path):
        return expected_concatenated_frames(start, end, stride)
    if "/traj-proc/" in str(path):
        return expected_replica_frames(start, end)
    return None


def netcdf_frames(path: Path) -> int | None:
    cmd = (
        f"source {shlex.quote(str(REPO_ROOT / 'workflows/md/scripts/modules.sh'))}; "
        "varmdyn_load_amber_modules >/dev/null 2>&1; "
        f"ncdump -h {shlex.quote(str(path))}"
    )
    try:
        text = subprocess.check_output(["bash", "-lc", cmd], text=True, stderr=subprocess.DEVNULL)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    match = re.search(r"frame = UNLIMITED ; // \((\d+) currently\)", text)
    if match:
        return int(match.group(1))
    match = re.search(r"frame = (\d+) ;", text)
    if match:
        return int(match.group(1))
    return None


def write_text(path: Path, text: str, execute: bool) -> None:
    print(f"[WRITE] {path}")
    if execute:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def submit(cmd: list[str], execute: bool) -> str:
    print("[CMD]", " ".join(shlex.quote(part) for part in cmd))
    if not execute:
        return "DRYRUN"
    out = subprocess.check_output(cmd, text=True).strip()
    print(out)
    return out.splitlines()[-1].strip().split()[-1]


def prepare_inputs_for_variant(state: str, variant: Path, start: int, end: int, stride: int, execute: bool) -> None:
    chunks, ns = window_label(start, end)
    concat = concatenated_name(start, end, stride)
    mask = strip_mask(state)
    com = variant / "04.ptraj" / "com"
    write_text(
        com / "topology" / "strip_topology.in",
        "\n".join(
            [
                "parm ../../../02.leap/com/cdl.com.wat.leap.prmtop",
                f"parmstrip '{mask}'",
                "parmwrite out ../../../02.leap/com/cdl.com.striped_v2.prmtop",
                "run",
                "",
            ]
        ),
        execute,
    )
    for replica in REPLICAS:
        traj_lines = [f"trajin ../../../../03.pmemd/com/{replica}/{chunk}md.mdcrd.nc" for chunk in range(start, end + 1)]
        write_text(
            com / replica / "traj-proc" / f"strip-{chunks}.in",
            "\n".join(
                [
                    "parm ../../../../02.leap/com/cdl.com.wat.leap.prmtop",
                    "",
                    *traj_lines,
                    "autoimage",
                    "",
                    f"strip '{mask}'",
                    "",
                    f"trajout production-{chunks}-{ns}.{replica}.striped_v2.mdcrd.nc nobox",
                    "",
                ]
            ),
            execute,
        )
    write_text(
        com / "concatenated" / f"concat-{chunks}.in",
        "\n".join(
            [
                "parm ../../../02.leap/com/cdl.com.striped_v2.prmtop",
                "",
                *[
                    f"trajin ../{replica}/traj-proc/production-{chunks}-{ns}.{replica}.striped_v2.mdcrd.nc 1 last {stride}"
                    for replica in REPLICAS
                ],
                "",
                f"trajout {concat}",
                "",
            ]
        ),
        execute,
    )
    write_text(
        com / "rmsf" / f"rmsf-{chunks}.in",
        "\n".join(
            [
                "parm ../../../02.leap/com/cdl.com.striped_v2.prmtop",
                "",
                f"trajin ../concatenated/{concat}",
                "",
                "rms first",
                "average crdset MyAvg",
                "run",
                "rms ref MyAvg",
                "atomicfluct out rmsf.byresidue.agr @C,CA,N byres",
                "",
            ]
        ),
        execute,
    )


def prepare(root: Path, state: str, variants: list[Path], start: int, end: int, stride: int, execute: bool) -> tuple[Path, Path]:
    logs = root / "logs" / "postprocess"
    manifest = logs / "postprocess_manifest.tsv"
    wrapper = logs / "postprocess_array.sh"
    rows: list[str] = []
    chunks, _ns = window_label(start, end)
    for variant in variants:
        if not variant.is_dir():
            raise SystemExit(f"missing variant folder: {variant}")
        prepare_inputs_for_variant(state, variant, start, end, stride, execute)
        rows.append("\t".join([variant.name, str(variant)]))
    write_text(manifest, "\n".join(rows) + "\n", execute)
    write_text(
        wrapper,
        f"""#!/usr/bin/env bash
set -euo pipefail

MANIFEST="{manifest}"
TASK_ID="${{SLURM_ARRAY_TASK_ID:-1}}"
LINE="$(sed -n "${{TASK_ID}}p" "$MANIFEST")"
IFS=$'\\t' read -r VARIANT VARIANT_DIR <<< "$LINE"
REPO_ROOT="{REPO_ROOT}"

source "$REPO_ROOT/workflows/md/scripts/modules.sh"
varmdyn_load_amber_modules

echo "VARMDYN_POSTPROCESS_START $(date -Is) state={state} variant=${{VARIANT}} window={chunks}"
cd "$VARIANT_DIR"

cd "$VARIANT_DIR/04.ptraj/com/topology"
cpptraj -i strip_topology.in
cd "$VARIANT_DIR/04.ptraj/com/cr1/traj-proc"
cpptraj -i strip-{chunks}.in
cd "$VARIANT_DIR/04.ptraj/com/cr2/traj-proc"
cpptraj -i strip-{chunks}.in
cd "$VARIANT_DIR/04.ptraj/com/cr3/traj-proc"
cpptraj -i strip-{chunks}.in
cd "$VARIANT_DIR/04.ptraj/com/concatenated"
cpptraj -i concat-{chunks}.in
cd "$VARIANT_DIR/04.ptraj/com/rmsf"
cpptraj -i rmsf-{chunks}.in

echo "VARMDYN_POSTPROCESS_DONE $(date -Is) state={state} variant=${{VARIANT}} window={chunks}"
""",
        execute,
    )
    if execute:
        wrapper.chmod(0o755)
    return manifest, wrapper


def submit_postprocess(args: argparse.Namespace) -> int:
    root = state_root(args)
    variants = variant_dirs(root, args.variants)
    if not variants:
        raise SystemExit(f"no variant folders found under {root}")
    if args.force:
        submit_variants = variants
        print("[FORCE] resubmitting post-processing for all selected variants")
    else:
        submit_variants = []
        for variant in variants:
            missing = missing_outputs(variant, args.start, args.end, args.stride)
            if missing:
                print(f"[TODO] {args.state}/{variant.name}: {len(missing)} missing post-processing outputs")
                submit_variants.append(variant)
            else:
                print(f"[SKIP] {args.state}/{variant.name}: post-processing outputs already complete")
        if not submit_variants:
            print("[OK] all selected variants already have post-processing outputs; no Slurm job submitted")
            print("[INFO] use --force only when you intentionally want to regenerate these outputs")
            return 0
    manifest, wrapper = prepare(root, args.state, submit_variants, args.start, args.end, args.stride, args.execute)
    logs = root / "logs" / "postprocess"
    partition = os.environ.get("POST_PARTITION", os.environ.get("PARTITION", "work1"))
    cpus = os.environ.get("POST_CPUS", "8")
    mem = os.environ.get("POST_MEM", "32G")
    time = os.environ.get("POST_TIME", "24:00:00")
    name = f"varmdyn_{args.state}_postprocess_array"
    cmd = [
        "sbatch",
        "--parsable",
        f"--job-name={name}",
        f"--partition={partition}",
        f"--cpus-per-task={cpus}",
        f"--mem={mem}",
        f"--time={time}",
        f"--array=1-{len(submit_variants)}",
        f"--chdir={logs}",
        f"--output={logs / (name + '_%A_%a.out')}",
        f"--error={logs / (name + '_%A_%a.err')}",
        str(wrapper),
    ]
    print(f"manifest={manifest}")
    submit(cmd, args.execute)
    return 0


def check_postprocess(args: argparse.Namespace) -> int:
    root = state_root(args)
    variants = variant_dirs(root, args.variants)
    failures = 0
    for variant in variants:
        for path in postprocess_outputs(variant, args.start, args.end, args.stride):
            if not path.is_file():
                print(f"MISSING {path}")
                failures += 1
                continue
            expected = expected_frames_for_path(path, args.start, args.end, args.stride)
            if expected is None:
                print(f"OK {path}")
                continue
            observed = netcdf_frames(path)
            if observed is None:
                print(f"UNKNOWNFRAMES expected={expected} {path}")
                failures += 1
            elif observed != expected:
                print(f"BADFRAMES observed={observed} expected={expected} {path}")
                failures += 1
            else:
                print(f"OK frames={observed} {path}")
    return 1 if failures else 0


def plan_postprocess(args: argparse.Namespace) -> int:
    md_root = generation_root(args)
    root = state_root(args)
    variants = variant_dirs(root, args.variants)
    chunks, ns = window_label(args.start, args.end)
    print(f"state={args.state}")
    print(f"md_root={md_root}")
    print(f"run_root={root}")
    print(f"window={chunks}")
    print(f"length={ns}")
    print(f"stride={args.stride}")
    print(f"expected_replica_frames={expected_replica_frames(args.start, args.end)}")
    print(f"expected_concatenated_frames={expected_concatenated_frames(args.start, args.end, args.stride)}")
    print(f"strip_mask={strip_mask(args.state)}")
    print(f"variants={','.join(path.name for path in variants) if variants else 'none found; run handoff/prep first'}")
    print(
        "outputs=cdl.com.striped_v2.prmtop,"
        "per-replica striped_v2 trajectories,"
        f"{concatenated_name(args.start, args.end, args.stride)},"
        "rmsf.byresidue.agr"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Submit/check cpptraj post-processing for MD campaigns.")
    parser.add_argument("--state", choices=["apo", "holo"], required=True)
    parser.add_argument("--variants", default="all")
    parser.add_argument(
        "--md-root",
        default=None,
        help="MD root containing state folders such as apo/ and holo/. Defaults to VARMDYN_MD_GENERATION_ROOT.",
    )
    parser.add_argument("--start", type=int, default=int(os.environ.get("VARMDYN_MD_POST_START", "25")))
    parser.add_argument("--end", type=int, default=int(os.environ.get("VARMDYN_MD_POST_END", "29")))
    parser.add_argument("--stride", type=int, default=int(os.environ.get("VARMDYN_MD_POST_STRIDE", "20")))
    parser.add_argument("--action", choices=["plan", "submit", "check"], default="plan")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--force", action="store_true", help="Regenerate post-processing outputs even when they already exist.")
    args = parser.parse_args()
    if args.action == "plan":
        return plan_postprocess(args)
    if args.action == "submit":
        return submit_postprocess(args)
    return check_postprocess(args)


if __name__ == "__main__":
    raise SystemExit(main())

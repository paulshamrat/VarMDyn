#!/usr/bin/env python3
"""Build or serve a local-only MkDocs preview with machine paths filled in.

The committed documentation stays generic. This helper copies docs/source into
.local_docs/source, replaces common template paths with values from the current
environment, and builds or serves that ignored local copy.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import socket
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOCAL_ROOT = ROOT / ".local_docs"
LOCAL_SOURCE = LOCAL_ROOT / "source"
LOCAL_SITE = LOCAL_ROOT / "site"
LOCAL_CONFIG = LOCAL_ROOT / "mkdocs.local.yml"
DEFAULT_ENV_FILES = [
    ROOT / "data/varmdyn_data.env",
    LOCAL_ROOT / "paths.env",
]


def load_env_file(path: Path, *, override: bool = False) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or (key in os.environ and not override):
            continue
        try:
            parsed = shlex.split(value)
        except ValueError:
            parsed = [value.strip("\"'")]
        if not parsed:
            continue
        expanded = os.path.expandvars(parsed[0])
        os.environ[key] = expanded


def load_env_files(extra_files: list[str]) -> None:
    for path in DEFAULT_ENV_FILES:
        load_env_file(path, override=(path == LOCAL_ROOT / "paths.env"))
    for path in extra_files:
        load_env_file(Path(path).expanduser(), override=True)


def env_path(name: str, default: Path | str | None = None) -> str | None:
    value = os.environ.get(name)
    if value:
        return str(Path(value).expanduser())
    if default is None:
        return None
    return str(Path(default).expanduser())


def local_executable_command(command: str | None) -> str | None:
    if not command:
        return None
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    if not parts:
        return None
    executable = Path(os.path.expandvars(parts[0])).expanduser()
    if executable.exists():
        return command
    return None


def replacement_map() -> dict[str, str]:
    repo_root = str(ROOT)
    data_root = env_path("VARMDYN_DATA_ROOT", ROOT / "data")
    run_root = env_path("VARMDYN_RUN_ROOT", ROOT / "data")
    hpc_project = env_path("VARMDYN_HPC_PROJECT")
    hpc_project_data = env_path("VARMDYN_PROJECT_DATA_ROOT")
    hpc_md_project = env_path("VARMDYN_MD_PROJECT_ROOT")
    hpc_scratch = env_path("VARMDYN_HPC_SCRATCH")
    hpc_scratch_data = env_path("VARMDYN_SCRATCH_DATA_ROOT")
    hpc_md_generation = env_path("VARMDYN_MD_GENERATION_ROOT")
    hpc_python = env_path("VARMDYN_HPC_PYTHON")
    atpmg_template = env_path("VARMDYN_MD_ATPMG_TEMPLATE_ROOT")
    if not atpmg_template and hpc_md_project:
        atpmg_template = str(Path(hpc_md_project) / "templates/atpmg")
    pymol_cmd = local_executable_command(os.environ.get("VARMDYN_PYMOL_CMD"))
    hpc_host = os.environ.get("VARMDYN_HPC_HOST")
    hpc_user = os.environ.get("VARMDYN_HPC_USER")
    hpc_stage = env_path("VARMDYN_HPC_STAGE")
    dynetan_work = env_path("VARMDYN_DYNETAN_WORK")
    ssh_socket = env_path("VARMDYN_SSH_CONTROL_PATH")
    conda_env = os.environ.get("VARMDYN_CONDA_ENV")

    replacements = {
        "/path/to/VarMDyn": repo_root,
        "/path/to/varmdyn": repo_root,
        "$PWD/data": data_root,
        "$PWD/runs": run_root,
        "/path/to/data": data_root,
        "/path/to/output_workspace": str(Path(run_root) / "mdan/network"),
        "$HOME/.ssh/hpc.sock": ssh_socket,
        "/path/to/ssh_control_socket": ssh_socket,
        "/path/to/hpc_project_root": hpc_project,
        "/path/to/hpc_project/VarMDyn/data/md": hpc_md_project,
        "/path/to/hpc_visible/VarMDyn/data/md": hpc_md_project,
        "/path/to/hpc_visible/VarMDyn/data": hpc_project_data,
        "/path/to/hpc_visible/VarMDyn": hpc_project,
        "/path/to/hpc_project/VarMDyn/data": hpc_project_data,
        "/path/to/hpc_project/VarMDyn": hpc_project,
        "/path/to/varmdyn_project_data/md/templates/atpmg": atpmg_template,
        "/scratch/$USER/VarMDyn/data/md": hpc_md_generation,
        "/scratch/$USER/VarMDyn/data": hpc_scratch_data,
        "/scratch/$USER/VarMDyn": hpc_scratch,
        "/scratch/user/VarMDyn": hpc_scratch,
        "/path/to/conda/envs/varmdyn_env/bin/python": hpc_python,
        "/path/to/validated_atpmg_template_root": atpmg_template,
        "/path/to/varmdyn_pymol/bin/python -m pymol": pymol_cmd,
        "/path/to/dynetan_work": dynetan_work,
        "user@login.example.edu": hpc_host,
        "export VARMDYN_HPC_USER=user": f"export VARMDYN_HPC_USER={hpc_user}" if hpc_user else None,
        "export VARMDYN_CONDA_ENV=varmdyn_dynetan": (
            f"export VARMDYN_CONDA_ENV={conda_env}" if conda_env else None
        ),
        "conda activate varmdyn_dynetan": (
            f"conda activate {conda_env}" if conda_env else None
        ),
        "/path/to/apo.pdb": env_path("VARMDYN_NETWORK_APO_PDB", ROOT / "data/structures/apo/01_WT.apo.pdb"),
        "/path/to/holo_atpmg.pdb": env_path(
            "VARMDYN_NETWORK_HOLO_PDB",
            ROOT / "data/structures/holo_atpmg/01_WT.keepATPmg.pdb",
        ),
    }
    if hpc_stage:
        replacements["${REPO}/varmdyn-runs/dynamics"] = hpc_stage
    return {key: value for key, value in replacements.items() if value}


def localize_text(text: str, replacements: dict[str, str]) -> str:
    for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        text = text.replace(old, new)
    return text


def prepare_local_source() -> None:
    if LOCAL_SOURCE.exists():
        shutil.rmtree(LOCAL_SOURCE)
    LOCAL_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "docs/source", LOCAL_SOURCE)

    replacements = replacement_map()
    for path in LOCAL_SOURCE.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        path.write_text(localize_text(text, replacements), encoding="utf-8")

    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    config = config.replace("docs_dir: docs/source", "docs_dir: source")
    config += "\nsite_dir: site\n"
    LOCAL_CONFIG.write_text(config, encoding="utf-8")
    print(f"[OK] local docs source: {LOCAL_SOURCE}")
    print(f"[OK] local mkdocs config: {LOCAL_CONFIG}")


def port_is_available(host: str, port: int) -> bool:
    try:
        with socket.create_server((host, port), reuse_port=False):
            return True
    except OSError:
        return False


def choose_port(host: str, requested_port: int) -> int:
    for port in range(requested_port, requested_port + 100):
        if port_is_available(host, port):
            if port != requested_port:
                print(f"[WARN] {host}:{requested_port} is in use; serving on {host}:{port} instead.")
            return port
    raise SystemExit(f"no free port found from {requested_port} to {requested_port + 99} on {host}")


def run_mkdocs(args: argparse.Namespace) -> int:
    mkdocs = shutil.which("mkdocs")
    if not mkdocs:
        fallback = Path.home() / "miniforge3/bin/mkdocs"
        mkdocs = str(fallback) if fallback.exists() else None
    if not mkdocs:
        raise SystemExit("mkdocs not found. Install docs requirements or activate an environment with mkdocs.")

    if args.serve:
        port = choose_port(args.host, args.port)
        print(f"[OK] local docs preview: http://{args.host}:{port}/")
        cmd = [mkdocs, "serve", "-f", str(LOCAL_CONFIG), "-a", f"{args.host}:{port}"]
    else:
        cmd = [mkdocs, "build", "-f", str(LOCAL_CONFIG)]
        if args.strict:
            cmd.append("--strict")
    print("[RUN] " + " ".join(cmd))
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true", help="serve the local docs preview")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--strict", action="store_true", help="use mkdocs build --strict")
    parser.add_argument(
        "--env-file",
        action="append",
        default=[],
        help="extra KEY=VALUE or export KEY=VALUE file to read before substitution",
    )
    args = parser.parse_args()

    load_env_files(args.env_file)
    prepare_local_source()
    return run_mkdocs(args)


if __name__ == "__main__":
    sys.exit(main())

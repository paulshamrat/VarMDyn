"""Keep public source snapshots independent of private runtime material."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_tracked_release_has_no_runtime_or_manuscript_products():
    files = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT, text=True
    ).split("\0")
    forbidden_extensions = {
        ".nc",
        ".dcd",
        ".xtc",
        ".trr",
        ".docx",
        ".odt",
        ".xlsx",
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".pyc",
    }
    for name in filter(None, files):
        path = Path(name)
        # Files removed in the pending cleanup are absent from the work tree.
        if not (ROOT / path).exists():
            continue
        assert path.suffix.lower() not in forbidden_extensions, name
        assert path.parts[0] not in {"site", "workflows", "manuscript"}, name
        if path.parts[0] in {"data", "logs"}:
            assert path.name == ".gitkeep", name

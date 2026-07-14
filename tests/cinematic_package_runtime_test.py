"""Prove invalid staged packages are rejected before an atomic publish."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "source/blender"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from publish_sequences import validate_package


SOURCE_PACKAGE = REPO_ROOT / "assets/scrolly/v2"


def require_rejection(root: Path, label: str) -> None:
    try:
        validate_package(root)
    except (OSError, RuntimeError, ValueError):
        return
    raise AssertionError(f"invalid package was accepted: {label}")


with tempfile.TemporaryDirectory() as temporary:
    package = Path(temporary) / "v2"
    shutil.copytree(SOURCE_PACKAGE, package)
    validate_package(package)

    poster = package / "poster-desktop.webp"
    original_poster = poster.read_bytes()
    poster.write_bytes(b"not-a-webp")
    require_rejection(package, "corrupt poster")
    poster.write_bytes(original_poster)

    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sequences"]["desktop"]["totalBytes"] += 1
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    require_rejection(package, "false byte accounting")

validate_package(SOURCE_PACKAGE)
print("CINEMATIC_PACKAGE_RUNTIME_PASS corrupt_poster=1 byte_accounting=1 original_intact=1")

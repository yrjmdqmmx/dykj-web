"""Failure-path tests for sequence locks, fingerprints, and atomic swaps."""

from __future__ import annotations

import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "source/blender"
import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pipeline_io import atomic_directory_swap, exclusive_lock, recover_backup
from sequence_cache import prepare_render_cache
from sequence_contract import render_settings_contract


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    lock_path = root / "pipeline.lock"
    with exclusive_lock(lock_path, "test"):
        try:
            with exclusive_lock(lock_path, "test"):
                raise AssertionError("second lock unexpectedly succeeded")
        except RuntimeError:
            pass

    output = root / "output"
    backup = root / "backup"
    backup.mkdir()
    (backup / "old.txt").write_text("old", encoding="utf-8")
    recover_backup(output, backup)
    require((output / "old.txt").read_text(encoding="utf-8") == "old",
            "orphan backup was not recovered")

    staging = root / "staging"
    staging.mkdir()
    (staging / "new.txt").write_text("new", encoding="utf-8")
    calls = {"count": 0}

    def fail_second_replace(source, target):
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("injected publish failure")
        Path(source).replace(target)

    try:
        atomic_directory_swap(staging, output, backup, replace=fail_second_replace)
        raise AssertionError("injected directory swap failure was not raised")
    except OSError:
        pass
    require((output / "old.txt").read_text(encoding="utf-8") == "old",
            "old output was not restored after publish failure")
    require((staging / "new.txt").read_text(encoding="utf-8") == "new",
            "failed staging set should remain available")

first = render_settings_contract(
    blend_sha256="a" * 64,
    blender_version="5.1.1",
    render_script_sha256="b" * 64,
    sequence_contract_sha256="c" * 64,
    sequence_cache_sha256="e" * 64,
)
second = render_settings_contract(
    blend_sha256="a" * 64,
    blender_version="5.1.1",
    render_script_sha256="d" * 64,
    sequence_contract_sha256="c" * 64,
    sequence_cache_sha256="e" * 64,
)
require(first["renderContractSha256"] != second["renderContractSha256"],
        "render script changes must invalidate the raw-frame fingerprint")

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary) / "cache"
    settings_path = root / "render-settings.json"
    (root / "desktop").mkdir(parents=True)
    (root / "desktop/frame-0001.png").write_bytes(b"legacy")
    try:
        prepare_render_cache(root, settings_path, first, reset=False)
        raise AssertionError("metadata-free cached frame was unexpectedly trusted")
    except RuntimeError:
        pass
    prepare_render_cache(root, settings_path, first, reset=True)
    require(settings_path.is_file(), "reset cache did not write current settings")
    try:
        prepare_render_cache(root, settings_path, second, reset=False)
        raise AssertionError("mismatched render settings were unexpectedly trusted")
    except RuntimeError:
        pass

print(
    "CINEMATIC_PIPELINE_RUNTIME_PASS "
    "lock=1 rollback=1 recovery=1 fingerprint=1 strict_cache=1"
)

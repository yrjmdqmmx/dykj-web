"""Strict raw-frame cache metadata handling for the production render pipeline."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


def has_cached_frames(root: Path) -> bool:
    return any(root.glob("*/frame-*.png"))


def write_settings(settings_path: Path, settings: dict) -> None:
    temporary = settings_path.with_name(
        f".{settings_path.name}.{os.getpid()}.tmp"
    )
    temporary.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, settings_path)


def prepare_render_cache(
    root: Path,
    settings_path: Path,
    expected: dict,
    *,
    reset: bool,
) -> None:
    if reset and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    if settings_path.exists():
        actual = json.loads(settings_path.read_text(encoding="utf-8"))
        if actual != expected:
            raise RuntimeError(
                "render cache belongs to a different scene/configuration; "
                "rerun with DINGYI_RESET_RENDER_CACHE=1"
            )
        return

    if has_cached_frames(root):
        raise RuntimeError(
            "render cache contains frames without matching metadata; "
            "rerun with DINGYI_RESET_RENDER_CACHE=1"
        )
    write_settings(settings_path, expected)

"""Cross-process lock and recoverable directory swap helpers for asset pipelines."""

from __future__ import annotations

import fcntl
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator


Replace = Callable[[str | Path, str | Path], None]


@contextmanager
def exclusive_lock(path: Path, label: str) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"another {label} process already holds {path}") from exc
        handle.seek(0)
        handle.truncate()
        handle.write(f"pid={os.getpid()}\n")
        handle.flush()
        yield
    finally:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def recover_backup(output: Path, backup: Path, *, replace: Replace = os.replace) -> None:
    if backup.exists() and not output.exists():
        replace(backup, output)


def atomic_directory_swap(
    staging: Path,
    output: Path,
    backup: Path,
    *,
    replace: Replace = os.replace,
) -> None:
    if backup.exists():
        raise RuntimeError(f"unresolved backup exists: {backup}")
    moved_previous = False
    try:
        if output.exists():
            replace(output, backup)
            moved_previous = True
        replace(staging, output)
    except BaseException:
        if moved_previous and not output.exists() and backup.exists():
            replace(backup, output)
        raise

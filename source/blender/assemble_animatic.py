"""Assemble the 24 low-resolution Blender poses into an animated WebP."""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - exercised as a user-facing guard
    raise SystemExit(
        "Pillow is required. Install source/blender/requirements-preview.txt "
        "with the Python interpreter used for this command."
    ) from exc


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from preview_contract import ANIMATIC_FRAME_NAMES, ANIMATIC_SIZE

PREVIEW_DIR = REPO_ROOT / "source/blender/previews"
FRAME_DIR = PREVIEW_DIR / "animatic"
OUTPUT = PREVIEW_DIR / "five-act-animatic.webp"


def main() -> None:
    frame_paths = sorted(FRAME_DIR.glob("f*.webp"))
    actual_names = tuple(path.name for path in frame_paths)
    if actual_names != ANIMATIC_FRAME_NAMES:
        raise SystemExit(
            f"Animatic poses do not match expected names/order: {actual_names}"
        )

    frames = []
    for frame_path in frame_paths:
        with Image.open(frame_path) as image:
            image.load()
            if image.format != "WEBP" or image.size != ANIMATIC_SIZE:
                raise SystemExit(
                    f"Invalid animatic pose {frame_path.name}: {image.format} {image.size}"
                )
            if getattr(image, "n_frames", 1) != 1:
                raise SystemExit(f"Animatic source pose must be a still: {frame_path.name}")
            frames.append(image.convert("RGB").copy())

    first, *remaining = frames
    temporary = OUTPUT.with_name(f".{OUTPUT.stem}.tmp.webp")
    temporary.unlink(missing_ok=True)
    try:
        first.save(
            temporary,
            format="WEBP",
            save_all=True,
            append_images=remaining,
            duration=167,
            loop=0,
            quality=72,
            method=6,
        )
        with Image.open(temporary) as animation:
            if (
                animation.format != "WEBP"
                or animation.size != ANIMATIC_SIZE
                or not getattr(animation, "is_animated", False)
                or getattr(animation, "n_frames", 1) != len(ANIMATIC_FRAME_NAMES)
            ):
                raise RuntimeError("Assembled animatic failed format/size/frame-count validation")
            for frame_index in range(animation.n_frames):
                animation.seek(frame_index)
                animation.load()
        os.replace(temporary, OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"ANIMATIC_COMPLETE {OUTPUT} frames={len(frames)} duration_ms={len(frames) * 167}")


if __name__ == "__main__":
    main()

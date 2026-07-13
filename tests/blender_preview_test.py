"""Artifact checks for the three Blender visual quality gates."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError as exc:
    raise SystemExit(
        "Pillow is required; install source/blender/requirements-preview.txt before this test"
    ) from exc


REPO_ROOT = Path(__file__).resolve().parents[1]
BLENDER_SOURCE = REPO_ROOT / "source/blender"
if str(BLENDER_SOURCE) not in sys.path:
    sys.path.insert(0, str(BLENDER_SOURCE))

from preview_contract import ANIMATIC_FRAME_NAMES, ANIMATIC_SIZE, STILL_CONTRACT

PREVIEW_DIR = REPO_ROOT / "source/blender/previews"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


missing = sorted(name for name in STILL_CONTRACT if not (PREVIEW_DIR / name).is_file())
require(not missing, f"missing preview stills: {missing}")
for name, expected_size in STILL_CONTRACT.items():
    path = PREVIEW_DIR / name
    with Image.open(path) as image:
        image.load()
        require(image.format == "WEBP", f"preview is not decodable WebP: {name}")
        require(image.size == expected_size,
                f"preview has wrong dimensions: {name}={image.size}, expected={expected_size}")
        require(getattr(image, "n_frames", 1) == 1, f"preview still is unexpectedly animated: {name}")

animatic_frames = sorted((PREVIEW_DIR / "animatic").glob("f*.webp"))
require(tuple(path.name for path in animatic_frames) == ANIMATIC_FRAME_NAMES,
        "five-act animatic frame names/order do not match the 1..96 sampling contract")
for path in animatic_frames:
    with Image.open(path) as image:
        image.load()
        require(image.format == "WEBP" and image.size == ANIMATIC_SIZE,
                f"animatic pose is invalid: {path.name} format={image.format} size={image.size}")
        require(getattr(image, "n_frames", 1) == 1,
                f"animatic source pose must be a still: {path.name}")

animatic = PREVIEW_DIR / "five-act-animatic.webp"
require(animatic.is_file(), "missing low-resolution five-act animated WebP preview")
with Image.open(animatic) as image:
    require(image.format == "WEBP" and image.size == ANIMATIC_SIZE,
            f"five-act animation has wrong format/size: {image.format} {image.size}")
    require(bool(getattr(image, "is_animated", False)), "five-act WebP is not animated")
    require(getattr(image, "n_frames", 1) == 24,
            f"five-act WebP must contain 24 decoded frames, got {getattr(image, 'n_frames', 1)}")
    for frame_index in range(image.n_frames):
        image.seek(frame_index)
        image.load()
        require(image.size == ANIMATIC_SIZE, f"decoded animation frame {frame_index} has wrong size")

print(
    f"BLENDER_PREVIEW_PASS stills={len(STILL_CONTRACT)} "
    f"animatic_frames={len(animatic_frames)} animatic_bytes={animatic.stat().st_size}"
)

"""Cross-check website sequence acts against markers stored in the .blend file."""

from __future__ import annotations

import sys
from pathlib import Path

import bpy


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "source/blender"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from sequence_contract import ACTS, DESKTOP, MOBILE


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


markers = {marker.name: marker.frame for marker in bpy.context.scene.timeline_markers}
expected_starts = (
    markers["ACT_01_SYSTEM"],
    markers["ACT_02_INTEGRATION"],
    markers["ACT_03_PRECISION"],
    markers["ACT_04_SERVICE"],
    markers["ACT_05_DELIVERY"],
)
require(expected_starts == (1, 19, 38, 56, 79), f"unexpected source markers: {expected_starts}")
require(tuple(act["desktopFrames"][0] for act in ACTS) == expected_starts,
        "desktop act ranges do not begin on source timeline markers")
require(tuple(act["desktopFrames"][1] for act in ACTS) == (18, 37, 55, 78, 96),
        "desktop act ranges do not end immediately before the next marker")
require(DESKTOP.source_frames == tuple(range(1, 97)), "desktop must retain all source frames")
for act_index, start in enumerate(expected_starts):
    sampled = MOBILE.source_frames[act_index * 8:(act_index + 1) * 8]
    require(len(sampled) == 8, f"mobile act {act_index + 1} does not contain eight frames")
    require(sampled[0] == start, f"mobile act {act_index + 1} omits its exact source marker")
    require(sampled[-1] == ACTS[act_index]["desktopFrames"][1],
            f"mobile act {act_index + 1} omits its exact source endpoint")

print("BLENDER_SEQUENCE_CONTRACT_PASS acts=5 desktop=96 mobile=40")

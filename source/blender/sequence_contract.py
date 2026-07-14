"""Shared contract for production scrollytelling sequence generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


VERSION = "2.0.0"
DISCLAIMER = "结构与动画为工程示意，不对应具体品牌或型号。"
GENERATED_FROM = "source/blender/dingyi-vacuum-system.blend"
SAMPLES = 64
WEBP_QUALITIES = tuple(range(82, 77, -1))
PRIORITY_MAX_BYTES = 2_000_000


@dataclass(frozen=True)
class SequenceSpec:
    name: str
    width: int
    height: int
    source_frames: tuple[int, ...]
    total_max_bytes: int
    poster_name: str
    poster_max_bytes: int
    poster_index: int
    priority_frames: tuple[int, ...]
    cache_size: int

    @property
    def frame_count(self) -> int:
        return len(self.source_frames)

    @property
    def frame_names(self) -> tuple[str, ...]:
        return tuple(
            f"frame-{index:04d}" for index in range(1, self.frame_count + 1)
        )


DESKTOP = SequenceSpec(
    name="desktop",
    width=1920,
    height=1080,
    source_frames=tuple(range(1, 97)),
    total_max_bytes=8_000_000,
    poster_name="poster-desktop.webp",
    poster_max_bytes=180_000,
    poster_index=8,
    priority_frames=(1, 18, 19, 37, 38, 55, 56, 78, 79, 96),
    cache_size=16,
)

MOBILE = SequenceSpec(
    name="mobile",
    width=720,
    height=960,
    source_frames=(
        1, 3, 6, 8, 11, 13, 16, 18,
        19, 22, 24, 27, 30, 32, 35, 37,
        38, 40, 43, 45, 48, 50, 53, 55,
        56, 59, 62, 65, 69, 72, 75, 78,
        79, 81, 84, 86, 89, 91, 94, 96,
    ),
    total_max_bytes=2_000_000,
    poster_name="poster-mobile.webp",
    poster_max_bytes=120_000,
    poster_index=4,
    priority_frames=(1, 8, 9, 16, 17, 24, 25, 32, 33, 40),
    cache_size=9,
)

SEQUENCES = (DESKTOP, MOBILE)

ACTS = (
    {
        "id": "startup",
        "title": "完整系统启动",
        "progress": [0.0, 0.2],
        "desktopFrames": [1, 18],
        "mobileFrames": [1, 8],
    },
    {
        "id": "integration",
        "title": "系统集成",
        "progress": [0.2, 0.4],
        "desktopFrames": [19, 37],
        "mobileFrames": [9, 16],
    },
    {
        "id": "precision",
        "title": "精密工程",
        "progress": [0.4, 0.6],
        "desktopFrames": [38, 55],
        "mobileFrames": [17, 24],
    },
    {
        "id": "service",
        "title": "运维能力",
        "progress": [0.6, 0.8],
        "desktopFrames": [56, 78],
        "mobileFrames": [25, 32],
    },
    {
        "id": "delivery",
        "title": "可靠交付",
        "progress": [0.8, 1.0],
        "desktopFrames": [79, 96],
        "mobileFrames": [33, 40],
    },
)


def render_settings_contract(
    *,
    blend_sha256: str,
    blender_version: str,
    render_script_sha256: str,
    sequence_contract_sha256: str,
    sequence_cache_sha256: str,
) -> dict:
    """Return the complete pixel-generation contract stored beside raw frames."""
    payload = {
        "pipelineVersion": 3,
        "blend": GENERATED_FROM,
        "blendSha256": blend_sha256,
        "blender": blender_version,
        "render": {
            "engine": "CYCLES",
            "device": "METAL",
            "samples": SAMPLES,
            "denoising": True,
            "adaptiveSampling": True,
            "viewTransform": "AgX",
            "filmTransparent": False,
            "persistentData": True,
            "output": {
                "fileFormat": "PNG",
                "colorMode": "RGB",
                "colorDepth": "8",
                "compression": 60,
            },
        },
        "scripts": {
            "renderSequencesSha256": render_script_sha256,
            "sequenceContractSha256": sequence_contract_sha256,
            "sequenceCacheSha256": sequence_cache_sha256,
        },
        "sequences": {
            spec.name: {
                "camera": "Camera_Desktop" if spec.name == "desktop" else "Camera_Mobile",
                "width": spec.width,
                "height": spec.height,
                "sourceFrames": list(spec.source_frames),
            }
            for spec in SEQUENCES
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["renderContractSha256"] = hashlib.sha256(encoded).hexdigest()
    return payload

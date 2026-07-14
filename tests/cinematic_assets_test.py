"""Verify the published five-act scrollytelling asset contract."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = REPO_ROOT / "assets/scrolly/v2"
MANIFEST_PATH = ASSET_ROOT / "manifest.json"

EXPECTED = {
    "desktop": {
        "frame_count": 96,
        "size": (1920, 1080),
        "template": "desktop/frame-{frame}.webp",
        "total_limit": 8_000_000,
        "poster": "poster-desktop.webp",
        "poster_limit": 180_000,
        "priority": (1, 18, 19, 37, 38, 55, 56, 78, 79, 96),
        "source_frames": tuple(range(1, 97)),
    },
    "mobile": {
        "frame_count": 40,
        "size": (720, 960),
        "template": "mobile/frame-{frame}.webp",
        "total_limit": 2_000_000,
        "poster": "poster-mobile.webp",
        "poster_limit": 120_000,
        "priority": (1, 8, 9, 16, 17, 24, 25, 32, 33, 40),
        "source_frames": (
            1, 3, 6, 8, 11, 13, 16, 18,
            19, 22, 24, 27, 30, 32, 35, 37,
            38, 40, 43, 45, 48, 50, 53, 55,
            56, 59, 62, 65, 69, 72, 75, 78,
            79, 81, 84, 86, 89, 91, 94, 96,
        ),
    },
}

EXPECTED_ACTS = (
    ("startup", "完整系统启动", (0.0, 0.2), (1, 18), (1, 8)),
    ("integration", "系统集成", (0.2, 0.4), (19, 37), (9, 16)),
    ("precision", "精密工程", (0.4, 0.6), (38, 55), (17, 24)),
    ("service", "运维能力", (0.6, 0.8), (56, 78), (25, 32)),
    ("delivery", "可靠交付", (0.8, 1.0), (79, 96), (33, 40)),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_still(path: Path, expected_size: tuple[int, int]) -> None:
    require(path.is_file(), f"missing image: {path.relative_to(REPO_ROOT)}")
    require(path.stat().st_size > 0, f"empty image: {path.relative_to(REPO_ROOT)}")
    with Image.open(path) as image:
        image.load()
        require(image.format == "WEBP", f"not a decodable WebP: {path.name}")
        require(image.size == expected_size,
                f"wrong dimensions: {path.name}={image.size}, expected={expected_size}")
        require(getattr(image, "n_frames", 1) == 1,
                f"sequence image must be a still: {path.name}")


require(MANIFEST_PATH.is_file(), "missing assets/scrolly/v2/manifest.json")
manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
require(manifest.get("version") == "2.0.0", "manifest version must be 2.0.0")
require(manifest.get("disclaimer") == "结构与动画为工程示意，不对应具体品牌或型号。",
        "manifest must carry the approved engineering illustration disclaimer")
require(manifest.get("generatedFrom") == "source/blender/dingyi-vacuum-system.blend",
        "manifest must identify the reproducible Blender source")
require(manifest.get("buildProof") == "build-proof.json",
        "manifest must reference the committed build proof")
proof_path = ASSET_ROOT / "build-proof.json"
require(proof_path.is_file(), "published assets must include build-proof.json")
build_proof = json.loads(proof_path.read_text(encoding="utf-8"))
blend_sha256 = manifest.get("blendSha256", "")
render_contract_sha256 = manifest.get("renderContractSha256", "")
require(len(blend_sha256) == 64 and all(char in "0123456789abcdef" for char in blend_sha256),
        "manifest blendSha256 must be a lowercase SHA-256")
require(len(render_contract_sha256) == 64
        and all(char in "0123456789abcdef" for char in render_contract_sha256),
        "manifest renderContractSha256 must be a lowercase SHA-256")
blend_bytes = (REPO_ROOT / "source/blender/dingyi-vacuum-system.blend").read_bytes()
require(not blend_bytes.startswith(b"version https://git-lfs.github.com/spec/v1"),
        "Blender source is only an LFS pointer; checkout must enable Git LFS")
source_digest = hashlib.sha256(blend_bytes).hexdigest()
require(blend_sha256 == source_digest,
        "manifest blendSha256 does not match the tracked Blender source")
require(build_proof.get("blendSha256") == blend_sha256,
        "build proof Blender fingerprint does not match manifest")
require(build_proof.get("renderContractSha256") == render_contract_sha256,
        "build proof render fingerprint does not match manifest")
render = manifest.get("render", {})
require(render.get("engine") == "CYCLES", "production frames must use Cycles")
require(render.get("device") == "METAL", "production frames must use Cycles Metal")
require(isinstance(render.get("samples"), int) and 64 <= render["samples"] <= 96,
        "production samples must stay within 64..96")
require(render.get("denoising") is True, "production denoising must be enabled")
require(render.get("adaptiveSampling") is True,
        "production manifest must record adaptive sampling")
require(render.get("viewTransform") == "AgX", "production frames must use AgX")
encoder = manifest.get("encoder", {})
require(encoder.get("pillow") == "12.2.0", "assets must use the locked Pillow encoder")
require(isinstance(encoder.get("libwebp"), str) and encoder["libwebp"],
        "manifest must record the libwebp version")
require(encoder.get("method") == 6, "WebP method must be 6")

sequences = manifest.get("sequences")
require(isinstance(sequences, dict), "manifest.sequences must be an object")

for variant, expected in EXPECTED.items():
    sequence = sequences.get(variant)
    require(isinstance(sequence, dict), f"missing manifest sequence: {variant}")
    require(sequence.get("frameCount") == expected["frame_count"],
            f"{variant} frameCount mismatch")
    require((sequence.get("width"), sequence.get("height")) == expected["size"],
            f"{variant} manifest dimensions mismatch")
    require(sequence.get("frameTemplate") == expected["template"],
            f"{variant} frameTemplate mismatch")
    require(sequence.get("indexPad") == 4, f"{variant} indexPad must be 4")
    require(sequence.get("poster") == expected["poster"], f"{variant} poster mismatch")
    require(tuple(sequence.get("priorityFrames", ())) == expected["priority"],
            f"{variant} priorityFrames must contain all five-act boundaries")
    require(tuple(sequence.get("sourceFrames", ())) == expected["source_frames"],
            f"{variant} source frame mapping mismatch")
    expected_cache = 16 if variant == "desktop" else 9
    require(sequence.get("cacheSize") == expected_cache,
            f"{variant} cacheSize must be {expected_cache}")
    require(isinstance(sequence.get("webpQuality"), int)
            and 78 <= sequence["webpQuality"] <= 82,
            f"{variant} WebP quality must stay within 78..82")

    directory = ASSET_ROOT / variant
    expected_names = tuple(
        f"frame-{index:04d}.webp" for index in range(1, expected["frame_count"] + 1)
    )
    actual_names = tuple(sorted(path.name for path in directory.glob("*.webp")))
    require(actual_names == expected_names,
            f"{variant} sequence has missing, extra, or misnumbered frames")

    total_bytes = 0
    byte_by_index: dict[int, int] = {}
    for index, name in enumerate(expected_names, start=1):
        path = directory / name
        read_still(path, expected["size"])
        byte_by_index[index] = path.stat().st_size
        total_bytes += path.stat().st_size

    require(total_bytes <= expected["total_limit"],
            f"{variant} sequence is {total_bytes} bytes; limit={expected['total_limit']}")
    require(sequence.get("totalBytes") == total_bytes,
            f"{variant} totalBytes does not match files")
    require(sequence.get("maxBytes") == expected["total_limit"],
            f"{variant} maxBytes mismatch")

    priority_bytes = sum(byte_by_index[index] for index in expected["priority"])
    require(priority_bytes <= 2_000_000,
            f"{variant} priority frames are {priority_bytes} bytes; limit=2000000")
    require(sequence.get("priorityBytes") == priority_bytes,
            f"{variant} priorityBytes does not match files")

    poster = ASSET_ROOT / expected["poster"]
    read_still(poster, expected["size"])
    require(poster.stat().st_size <= expected["poster_limit"],
            f"{variant} poster is {poster.stat().st_size} bytes; limit={expected['poster_limit']}")
    require(sequence.get("posterBytes") == poster.stat().st_size,
            f"{variant} posterBytes does not match file")
    require(sequence.get("posterMaxBytes") == expected["poster_limit"],
            f"{variant} posterMaxBytes mismatch")
    require(isinstance(sequence.get("posterQuality"), int)
            and 60 <= sequence["posterQuality"] <= 82,
            f"{variant} posterQuality must stay within 60..82")

acts = manifest.get("acts")
require(isinstance(acts, list) and len(acts) == 5, "manifest must declare exactly five acts")
for actual, (act_id, title, progress, desktop_frames, mobile_frames) in zip(acts, EXPECTED_ACTS):
    require(actual.get("id") == act_id, f"act order/id mismatch: expected {act_id}")
    require(actual.get("title") == title, f"{act_id} title mismatch")
    require(tuple(actual.get("progress", ())) == progress,
            f"{act_id} progress range mismatch")
    require(tuple(actual.get("desktopFrames", ())) == desktop_frames,
            f"{act_id} desktop frame range mismatch")
    require(tuple(actual.get("mobileFrames", ())) == mobile_frames,
            f"{act_id} mobile frame range mismatch")

print(
    "CINEMATIC_ASSETS_PASS "
    f"desktop={sequences['desktop']['totalBytes']} "
    f"mobile={sequences['mobile']['totalBytes']} "
    f"posters={sequences['desktop']['posterBytes']}+{sequences['mobile']['posterBytes']}"
)

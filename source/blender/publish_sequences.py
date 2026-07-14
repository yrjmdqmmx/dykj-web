"""Encode lossless Cycles frames as budgeted WebP assets and publish atomically."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, __version__ as PILLOW_VERSION, features


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pipeline_io import atomic_directory_swap, exclusive_lock, recover_backup
from sequence_contract import (
    ACTS,
    DISCLAIMER,
    GENERATED_FROM,
    PRIORITY_MAX_BYTES,
    SEQUENCES,
    VERSION,
    WEBP_QUALITIES,
    render_settings_contract,
)


REPO_ROOT = SCRIPT_DIR.parents[1]
EXPECTED_BLEND = REPO_ROOT / GENERATED_FROM
RAW_ROOT = SCRIPT_DIR / "render-cache/v2"
SETTINGS_PATH = RAW_ROOT / "render-settings.json"
CACHE_ROOT = SCRIPT_DIR / "render-cache"
PUBLISH_PARENT = REPO_ROOT / "assets/scrolly"
OUTPUT_ROOT = PUBLISH_PARENT / "v2"
STAGING_ROOT = CACHE_ROOT / "publish-v2-staging"
BACKUP_ROOT = CACHE_ROOT / "publish-v2-previous"
LOCK_PATH = CACHE_ROOT / ".publish-v2.lock"
WORKERS = max(1, min(4, (os.cpu_count() or 2) // 2))
BUILD_PROOF_NAME = "build-proof.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def recover_orphan_backup() -> None:
    PUBLISH_PARENT.mkdir(parents=True, exist_ok=True)
    CACHE_ROOT.mkdir(parents=True, exist_ok=True)
    recover_backup(OUTPUT_ROOT, BACKUP_ROOT)
    if BACKUP_ROOT.exists() and OUTPUT_ROOT.exists():
        shutil.rmtree(BACKUP_ROOT)


def validate_render_settings(
    actual: dict,
    blend_path: Path = EXPECTED_BLEND,
) -> dict:
    blender_version = actual.get("blender", "")
    if not blender_version.startswith("5.1."):
        raise RuntimeError(f"unsupported raw-frame Blender version: {blender_version}")
    expected = render_settings_contract(
        blend_sha256=sha256(blend_path),
        blender_version=blender_version,
        render_script_sha256=sha256(SCRIPT_DIR / "render_sequences.py"),
        sequence_contract_sha256=sha256(SCRIPT_DIR / "sequence_contract.py"),
        sequence_cache_sha256=sha256(SCRIPT_DIR / "sequence_cache.py"),
    )
    if actual != expected:
        raise RuntimeError(
            "raw-frame settings no longer match the current Blender source or render contract"
        )
    return actual


def load_render_settings(
    settings_path: Path = SETTINGS_PATH,
    blend_path: Path = EXPECTED_BLEND,
) -> dict:
    if not settings_path.is_file():
        raise RuntimeError("render_sequences.py must complete before publishing")
    actual = json.loads(settings_path.read_text(encoding="utf-8"))
    return validate_render_settings(actual, blend_path)


def load_build_proof(root: Path) -> dict:
    proof_path = root / BUILD_PROOF_NAME
    if not proof_path.is_file():
        raise RuntimeError(f"published package is missing {BUILD_PROOF_NAME}")
    actual = json.loads(proof_path.read_text(encoding="utf-8"))
    return validate_render_settings(actual)


def validate_source(spec, render_settings: dict) -> tuple[Path, ...]:
    expected_settings = render_settings["sequences"][spec.name]
    if expected_settings != {
        "camera": "Camera_Desktop" if spec.name == "desktop" else "Camera_Mobile",
        "width": spec.width,
        "height": spec.height,
        "sourceFrames": list(spec.source_frames),
    }:
        raise RuntimeError(f"{spec.name} raw settings do not match the sequence contract")

    directory = RAW_ROOT / spec.name
    expected = tuple(directory / f"{stem}.png" for stem in spec.frame_names)
    actual = tuple(sorted(directory.glob("*.png")))
    if actual != expected:
        raise RuntimeError(f"{spec.name} raw sequence is missing or misnumbered")
    for path in expected:
        with Image.open(path) as image:
            image.load()
            if image.format != "PNG" or image.size != (spec.width, spec.height):
                raise RuntimeError(f"invalid raw frame: {path}")
    return expected


def encode_one(source: Path, target: Path, quality: int) -> None:
    temporary = target.with_name(f".{target.stem}.{os.getpid()}.tmp.webp")
    temporary.unlink(missing_ok=True)
    try:
        with Image.open(source) as image:
            source_size = image.size
            converted = image.convert("RGB")
            try:
                converted.save(
                    temporary,
                    format="WEBP",
                    quality=quality,
                    method=6,
                    exact=True,
                )
            finally:
                converted.close()
        with Image.open(temporary) as encoded:
            encoded.load()
            if encoded.format != "WEBP" or encoded.size != source_size:
                raise RuntimeError(f"encoded WebP validation failed: {target}")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def encode_variant(spec, sources: tuple[Path, ...]) -> tuple[Path, int, int]:
    for quality in WEBP_QUALITIES:
        candidate = STAGING_ROOT / f".{spec.name}-q{quality}"
        shutil.rmtree(candidate, ignore_errors=True)
        candidate.mkdir(parents=True, exist_ok=False)
        targets = tuple(
            candidate / f"frame-{index:04d}.webp"
            for index in range(1, spec.frame_count + 1)
        )

        def encode_pair(pair: tuple[Path, Path]) -> None:
            encode_one(pair[0], pair[1], quality)

        with ThreadPoolExecutor(max_workers=WORKERS) as executor:
            tuple(executor.map(encode_pair, zip(sources, targets)))
        total_bytes = sum(path.stat().st_size for path in targets)
        print(
            f"ENCODE_ATTEMPT variant={spec.name} quality={quality} bytes={total_bytes} "
            f"limit={spec.total_max_bytes}",
            flush=True,
        )
        if total_bytes <= spec.total_max_bytes:
            final_dir = STAGING_ROOT / spec.name
            os.replace(candidate, final_dir)
            return final_dir, quality, total_bytes
        shutil.rmtree(candidate)
    raise RuntimeError(
        f"{spec.name} cannot meet {spec.total_max_bytes} bytes within WebP quality 78..82"
    )


def encode_poster(spec, source: Path) -> tuple[Path, int, int]:
    target = STAGING_ROOT / spec.poster_name
    for quality in range(82, 59, -2):
        encode_one(source, target, quality)
        size = target.stat().st_size
        if size <= spec.poster_max_bytes:
            return target, quality, size
    raise RuntimeError(
        f"{spec.poster_name} cannot meet {spec.poster_max_bytes} bytes at acceptable quality"
    )


def sequence_manifest(
    spec,
    directory: Path,
    quality: int,
    total_bytes: int,
    poster_quality: int,
    poster_bytes: int,
) -> dict:
    priority_bytes = sum(
        (directory / f"frame-{index:04d}.webp").stat().st_size
        for index in spec.priority_frames
    )
    if priority_bytes > PRIORITY_MAX_BYTES:
        raise RuntimeError(
            f"{spec.name} priority set is {priority_bytes}; limit={PRIORITY_MAX_BYTES}"
        )
    return {
        "frameCount": spec.frame_count,
        "width": spec.width,
        "height": spec.height,
        "frameTemplate": f"{spec.name}/frame-{{frame}}.webp",
        "indexPad": 4,
        "poster": spec.poster_name,
        "priorityFrames": list(spec.priority_frames),
        "sourceFrames": list(spec.source_frames),
        "cacheSize": spec.cache_size,
        "webpQuality": quality,
        "totalBytes": total_bytes,
        "maxBytes": spec.total_max_bytes,
        "priorityBytes": priority_bytes,
        "posterQuality": poster_quality,
        "posterBytes": poster_bytes,
        "posterMaxBytes": spec.poster_max_bytes,
    }


def read_webp(path: Path, size: tuple[int, int]) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"missing staged WebP: {path}")
    with Image.open(path) as image:
        image.load()
        if (
            image.format != "WEBP"
            or image.size != size
            or getattr(image, "n_frames", 1) != 1
        ):
            raise RuntimeError(f"invalid staged WebP: {path}")


def validate_package(root: Path, render_settings: dict | None = None) -> None:
    if render_settings is None:
        render_settings = load_build_proof(root)
    manifest_path = root / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("version") != VERSION:
        raise RuntimeError("staged manifest version mismatch")
    if data.get("generatedFrom") != GENERATED_FROM or data.get("disclaimer") != DISCLAIMER:
        raise RuntimeError("staged manifest provenance/disclaimer mismatch")
    if data.get("blendSha256") != render_settings["blendSha256"]:
        raise RuntimeError("staged manifest blend fingerprint mismatch")
    if data.get("renderContractSha256") != render_settings["renderContractSha256"]:
        raise RuntimeError("staged manifest render fingerprint mismatch")
    if data.get("buildProof") != BUILD_PROOF_NAME:
        raise RuntimeError("staged manifest build proof path mismatch")
    if data.get("acts") != list(ACTS):
        raise RuntimeError("staged manifest five-act ranges/titles mismatch")
    encoder = data.get("encoder", {})
    if encoder != {
        "pillow": PILLOW_VERSION,
        "libwebp": features.version("webp"),
        "method": 6,
    }:
        raise RuntimeError("staged manifest encoder provenance mismatch")
    render = data.get("render", {})
    for key in (
        "engine",
        "device",
        "samples",
        "denoising",
        "adaptiveSampling",
        "viewTransform",
    ):
        if render.get(key) != render_settings["render"].get(key):
            raise RuntimeError(f"staged manifest render.{key} mismatch")

    sequences = data.get("sequences", {})
    for spec in SEQUENCES:
        sequence = sequences.get(spec.name, {})
        required = {
            "frameCount": spec.frame_count,
            "width": spec.width,
            "height": spec.height,
            "frameTemplate": f"{spec.name}/frame-{{frame}}.webp",
            "indexPad": 4,
            "poster": spec.poster_name,
            "priorityFrames": list(spec.priority_frames),
            "sourceFrames": list(spec.source_frames),
            "cacheSize": spec.cache_size,
            "maxBytes": spec.total_max_bytes,
            "posterMaxBytes": spec.poster_max_bytes,
        }
        if any(sequence.get(key) != value for key, value in required.items()):
            raise RuntimeError(f"staged {spec.name} manifest contract mismatch")
        quality = sequence.get("webpQuality")
        if not isinstance(quality, int) or quality not in WEBP_QUALITIES:
            raise RuntimeError(f"staged {spec.name} WebP quality is outside 78..82")
        poster_quality = sequence.get("posterQuality")
        if not isinstance(poster_quality, int) or not 60 <= poster_quality <= 82:
            raise RuntimeError(f"staged {spec.name} poster quality is outside 60..82")

        directory = root / spec.name
        expected_names = tuple(f"{stem}.webp" for stem in spec.frame_names)
        actual_names = tuple(sorted(path.name for path in directory.glob("*.webp")))
        if actual_names != expected_names:
            raise RuntimeError(f"staged {spec.name} filenames mismatch")
        frame_sizes = {}
        for index, name in enumerate(expected_names, start=1):
            path = directory / name
            read_webp(path, (spec.width, spec.height))
            frame_sizes[index] = path.stat().st_size
        total_bytes = sum(frame_sizes.values())
        priority_bytes = sum(frame_sizes[index] for index in spec.priority_frames)
        if total_bytes > spec.total_max_bytes or sequence.get("totalBytes") != total_bytes:
            raise RuntimeError(f"staged {spec.name} total byte accounting/budget failed")
        if (
            priority_bytes > PRIORITY_MAX_BYTES
            or sequence.get("priorityBytes") != priority_bytes
        ):
            raise RuntimeError(f"staged {spec.name} priority byte accounting/budget failed")

        poster = root / spec.poster_name
        read_webp(poster, (spec.width, spec.height))
        poster_bytes = poster.stat().st_size
        if poster_bytes > spec.poster_max_bytes or sequence.get("posterBytes") != poster_bytes:
            raise RuntimeError(f"staged {spec.name} poster byte accounting/budget failed")


def build_manifest(render_settings: dict, sequences: dict) -> dict:
    source_render = render_settings["render"]
    return {
        "version": VERSION,
        "generatedFrom": GENERATED_FROM,
        "blendSha256": render_settings["blendSha256"],
        "renderContractSha256": render_settings["renderContractSha256"],
        "buildProof": BUILD_PROOF_NAME,
        "disclaimer": DISCLAIMER,
        "render": {
            key: source_render[key]
            for key in (
                "engine",
                "device",
                "samples",
                "denoising",
                "adaptiveSampling",
                "viewTransform",
            )
        },
        "encoder": {
            "pillow": PILLOW_VERSION,
            "libwebp": features.version("webp"),
            "method": 6,
        },
        "sequences": sequences,
        "acts": list(ACTS),
    }


def run() -> None:
    recover_orphan_backup()
    render_settings = load_render_settings()
    shutil.rmtree(STAGING_ROOT, ignore_errors=True)
    STAGING_ROOT.mkdir(parents=True, exist_ok=False)
    try:
        sequences = {}
        for spec in SEQUENCES:
            sources = validate_source(spec, render_settings)
            directory, quality, total_bytes = encode_variant(spec, sources)
            poster, poster_quality, poster_bytes = encode_poster(
                spec, sources[spec.poster_index - 1]
            )
            sequences[spec.name] = sequence_manifest(
                spec,
                directory,
                quality,
                total_bytes,
                poster_quality,
                poster_bytes,
            )
            print(
                f"ENCODE_COMPLETE variant={spec.name} quality={quality} "
                f"bytes={total_bytes} poster={poster.stat().st_size}",
                flush=True,
            )

        (STAGING_ROOT / "manifest.json").write_text(
            json.dumps(
                build_manifest(render_settings, sequences),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (STAGING_ROOT / BUILD_PROOF_NAME).write_text(
            json.dumps(render_settings, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        validate_package(STAGING_ROOT, render_settings)
        atomic_directory_swap(STAGING_ROOT, OUTPUT_ROOT, BACKUP_ROOT)
        shutil.rmtree(BACKUP_ROOT, ignore_errors=True)
    finally:
        shutil.rmtree(STAGING_ROOT, ignore_errors=True)
    print(f"SEQUENCE_PUBLISH_COMPLETE root={OUTPUT_ROOT}", flush=True)


def main() -> None:
    with exclusive_lock(LOCK_PATH, "Dingyi sequence publish"):
        run()


if __name__ == "__main__":
    main()

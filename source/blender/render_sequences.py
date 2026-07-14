"""Render resumable, lossless production frames from the Dingyi Blender scene.

The browser assets are encoded separately by ``publish_sequences.py`` so WebP
quality can be tuned to the locked byte budgets without rerendering Cycles.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import bpy


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pipeline_io import exclusive_lock
from sequence_cache import prepare_render_cache
from sequence_contract import (
    GENERATED_FROM,
    SAMPLES,
    SEQUENCES,
    render_settings_contract,
)


REPO_ROOT = SCRIPT_DIR.parents[1]
EXPECTED_BLEND = (REPO_ROOT / GENERATED_FROM).resolve()
RAW_ROOT = SCRIPT_DIR / "render-cache/v2"
SETTINGS_PATH = RAW_ROOT / "render-settings.json"
LOCK_PATH = SCRIPT_DIR / "render-cache/.render-v2.lock"
VARIANT = os.environ.get("DINGYI_VARIANT", "all")
RESET_CACHE = os.environ.get("DINGYI_RESET_RENDER_CACHE") == "1"
RENDER_LIMIT = int(os.environ.get("DINGYI_RENDER_LIMIT", "0"))


def capture_state(scene: bpy.types.Scene) -> dict:
    image_settings = scene.render.image_settings
    return {
        "frame": scene.frame_current,
        "camera": scene.camera,
        "engine": scene.render.engine,
        "device": scene.cycles.device,
        "samples": scene.cycles.samples,
        "denoising": scene.cycles.use_denoising,
        "adaptive": scene.cycles.use_adaptive_sampling,
        "resolution_x": scene.render.resolution_x,
        "resolution_y": scene.render.resolution_y,
        "resolution_percentage": scene.render.resolution_percentage,
        "filepath": scene.render.filepath,
        "file_format": image_settings.file_format,
        "color_mode": image_settings.color_mode,
        "color_depth": image_settings.color_depth,
        "compression": image_settings.compression,
        "use_file_extension": scene.render.use_file_extension,
        "film_transparent": scene.render.film_transparent,
        "persistent_data": scene.render.use_persistent_data,
    }


def restore_state(scene: bpy.types.Scene, state: dict) -> None:
    image_settings = scene.render.image_settings
    scene.camera = state["camera"]
    scene.render.engine = state["engine"]
    scene.cycles.device = state["device"]
    scene.cycles.samples = state["samples"]
    scene.cycles.use_denoising = state["denoising"]
    scene.cycles.use_adaptive_sampling = state["adaptive"]
    scene.render.resolution_x = state["resolution_x"]
    scene.render.resolution_y = state["resolution_y"]
    scene.render.resolution_percentage = state["resolution_percentage"]
    scene.render.filepath = state["filepath"]
    image_settings.file_format = state["file_format"]
    image_settings.color_mode = state["color_mode"]
    image_settings.color_depth = state["color_depth"]
    image_settings.compression = state["compression"]
    scene.render.use_file_extension = state["use_file_extension"]
    scene.render.film_transparent = state["film_transparent"]
    scene.render.use_persistent_data = state["persistent_data"]
    scene.frame_set(state["frame"])


def enable_metal() -> str:
    preferences = bpy.context.preferences.addons["cycles"].preferences
    try:
        preferences.compute_device_type = "METAL"
        preferences.refresh_devices()
    except Exception as exc:
        raise RuntimeError(f"Metal device discovery failed: {exc}") from exc

    enabled = []
    for device in preferences.devices:
        device.use = device.type == "METAL"
        if device.use:
            enabled.append(device.name)
    if not enabled:
        raise RuntimeError("no Metal Cycles device is available")
    print(f"RENDER_DEVICE METAL devices={','.join(enabled)}", flush=True)
    return "GPU"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_settings() -> dict:
    return render_settings_contract(
        blend_sha256=sha256(EXPECTED_BLEND),
        blender_version=".".join(str(value) for value in bpy.app.version),
        render_script_sha256=sha256(Path(__file__).resolve()),
        sequence_contract_sha256=sha256(SCRIPT_DIR / "sequence_contract.py"),
        sequence_cache_sha256=sha256(SCRIPT_DIR / "sequence_cache.py"),
    )


def prepare_cache(settings: dict) -> None:
    prepare_render_cache(
        RAW_ROOT,
        SETTINGS_PATH,
        settings,
        reset=RESET_CACHE,
    )


def valid_png(path: Path, width: int, height: int) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    image = None
    try:
        image = bpy.data.images.load(str(path), check_existing=False)
        return tuple(image.size) == (width, height)
    except Exception:
        return False
    finally:
        if image is not None:
            bpy.data.images.remove(image)


def configure_scene(scene: bpy.types.Scene, device: str) -> None:
    scene.render.engine = "CYCLES"
    scene.cycles.device = device
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = True
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.render.use_persistent_data = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 60


def render_variant(scene: bpy.types.Scene, spec) -> bool:
    output_dir = RAW_ROOT / spec.name
    output_dir.mkdir(parents=True, exist_ok=True)
    scene.camera = bpy.data.objects[
        "Camera_Desktop" if spec.name == "desktop" else "Camera_Mobile"
    ]
    scene.render.resolution_x = spec.width
    scene.render.resolution_y = spec.height

    newly_rendered = 0
    for output_index, source_frame in enumerate(spec.source_frames, start=1):
        target = output_dir / f"frame-{output_index:04d}.png"
        if valid_png(target, spec.width, spec.height):
            print(
                f"RENDER_SKIP variant={spec.name} output={output_index:04d} "
                f"source={source_frame}",
                flush=True,
            )
            continue
        if RENDER_LIMIT and newly_rendered >= RENDER_LIMIT:
            print(
                f"RENDER_PAUSED variant={spec.name} newly_rendered={newly_rendered} "
                f"next={output_index:04d}",
                flush=True,
            )
            return False

        temporary = target.with_name(f".{target.stem}.tmp.png")
        temporary.unlink(missing_ok=True)
        scene.frame_set(source_frame)
        scene.render.filepath = str(temporary)
        try:
            bpy.ops.render.render(write_still=True)
            if not valid_png(temporary, spec.width, spec.height):
                raise RuntimeError(f"invalid rendered frame: {temporary}")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        print(
            f"RENDER_FRAME variant={spec.name} output={output_index:04d}/"
            f"{spec.frame_count:04d} source={source_frame} bytes={target.stat().st_size}",
            flush=True,
        )
        newly_rendered += 1
    return True


def run() -> None:
    blend_path = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    if blend_path != EXPECTED_BLEND:
        raise RuntimeError(f"open {EXPECTED_BLEND} before rendering; got {blend_path}")
    if VARIANT not in {"all", "desktop", "mobile"}:
        raise RuntimeError("DINGYI_VARIANT must be all, desktop, or mobile")
    if RENDER_LIMIT < 0:
        raise RuntimeError("DINGYI_RENDER_LIMIT must be zero or a positive integer")
    if bpy.context.scene.view_settings.view_transform != "AgX":
        raise RuntimeError("the source scene must use AgX")

    settings = expected_settings()
    prepare_cache(settings)
    scene = bpy.context.scene
    state = capture_state(scene)
    try:
        configure_scene(scene, enable_metal())
        completed = True
        for spec in SEQUENCES:
            if VARIANT in {"all", spec.name}:
                completed = render_variant(scene, spec) and completed
    finally:
        restore_state(scene, state)
    status = "COMPLETE" if completed else "PARTIAL"
    print(f"RENDER_SEQUENCE_{status} root={RAW_ROOT} variant={VARIANT}", flush=True)


def main() -> None:
    with exclusive_lock(LOCK_PATH, "Dingyi sequence render"):
        run()


if __name__ == "__main__":
    main()

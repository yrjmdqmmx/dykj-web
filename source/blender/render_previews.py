"""Render the three visual quality gates for the Dingyi Blender scene.

Run after rebuilding the source file:

    /Applications/Blender.app/Contents/MacOS/Blender \
      -b source/blender/dingyi-vacuum-system.blend \
      --python source/blender/render_previews.py

The previews are deliberately low resolution. Production sequences keep the
scene's 64-sample Cycles configuration and are rendered by render_sequences.py.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from preview_contract import ANIMATIC_FRAME_NAMES, ANIMATIC_SIZE, SAMPLED_FRAMES


REPO_ROOT = Path(__file__).resolve().parents[2]
PREVIEW_DIR = REPO_ROOT / "source/blender/previews"
EXPECTED_BLEND = (REPO_ROOT / "source/blender/dingyi-vacuum-system.blend").resolve()
PREVIEW_SAMPLES = int(os.environ.get("DINGYI_PREVIEW_SAMPLES", "24"))


def create_graybox_material() -> bpy.types.Material:
    material = bpy.data.materials.get("QA_Graybox") or bpy.data.materials.new("QA_Graybox")
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = next(
            node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"
        )
    bsdf.inputs["Base Color"].default_value = (0.22, 0.26, 0.29, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.18
    bsdf.inputs["Roughness"].default_value = 0.48
    return material


def configure_preview_render() -> bpy.types.Scene:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = PREVIEW_SAMPLES
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.quality = 84
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    return scene


def capture_render_state(scene: bpy.types.Scene) -> dict:
    """Capture every render/view-layer field this script mutates."""
    return {
        "frame": scene.frame_current,
        "camera": scene.camera,
        "engine": scene.render.engine,
        "samples": scene.cycles.samples,
        "denoising": scene.cycles.use_denoising,
        "resolution_x": scene.render.resolution_x,
        "resolution_y": scene.render.resolution_y,
        "resolution_percentage": scene.render.resolution_percentage,
        "file_format": scene.render.image_settings.file_format,
        "color_mode": scene.render.image_settings.color_mode,
        "quality": scene.render.image_settings.quality,
        "filepath": scene.render.filepath,
        "use_file_extension": scene.render.use_file_extension,
        "film_transparent": scene.render.film_transparent,
        "material_override": bpy.context.view_layer.material_override,
    }


def restore_render_state(scene: bpy.types.Scene, state: dict) -> None:
    scene.camera = state["camera"]
    scene.render.engine = state["engine"]
    scene.cycles.samples = state["samples"]
    scene.cycles.use_denoising = state["denoising"]
    scene.render.resolution_x = state["resolution_x"]
    scene.render.resolution_y = state["resolution_y"]
    scene.render.resolution_percentage = state["resolution_percentage"]
    scene.render.image_settings.file_format = state["file_format"]
    scene.render.image_settings.color_mode = state["color_mode"]
    scene.render.image_settings.quality = state["quality"]
    scene.render.filepath = state["filepath"]
    scene.render.use_file_extension = state["use_file_extension"]
    scene.render.film_transparent = state["film_transparent"]
    bpy.context.view_layer.material_override = state["material_override"]
    scene.frame_set(state["frame"])


def render_still(
    scene: bpy.types.Scene,
    filename: str,
    frame: int,
    camera_name: str,
    width: int,
    height: int,
    *,
    material_override: bpy.types.Material | None = None,
) -> None:
    camera = bpy.data.objects[camera_name]
    scene.camera = camera
    scene.frame_set(frame)
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    target = PREVIEW_DIR / filename
    temporary = target.with_name(f".{target.stem}.tmp.webp")
    temporary.unlink(missing_ok=True)
    scene.render.filepath = str(temporary)
    previous_override = bpy.context.view_layer.material_override
    bpy.context.view_layer.material_override = material_override
    try:
        bpy.ops.render.render(write_still=True)
        if not temporary.is_file() or temporary.stat().st_size == 0:
            raise RuntimeError(f"Blender did not create preview: {temporary}")
        os.replace(temporary, target)
    finally:
        bpy.context.view_layer.material_override = previous_override
        temporary.unlink(missing_ok=True)
    print(f"PREVIEW {filename} frame={frame} camera={camera_name}")


def render_animatic_frames(scene: bpy.types.Scene) -> None:
    """Render 24 poses including exact first/final states for WebP assembly."""
    output_dir = PREVIEW_DIR / "animatic"
    staging_dir = PREVIEW_DIR / ".animatic-staging"
    backup_dir = PREVIEW_DIR / ".animatic-previous"
    if backup_dir.exists() and not output_dir.exists():
        os.replace(backup_dir, output_dir)
    elif backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.rmtree(staging_dir, ignore_errors=True)
    staging_dir.mkdir(parents=True, exist_ok=False)
    scene.camera = bpy.data.objects["Camera_Desktop"]
    scene.cycles.samples = 8
    scene.render.resolution_x, scene.render.resolution_y = ANIMATIC_SIZE
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.quality = 70
    scene.render.use_file_extension = True

    try:
        for source_frame, filename in zip(SAMPLED_FRAMES, ANIMATIC_FRAME_NAMES):
            scene.frame_set(source_frame)
            scene.render.filepath = str(staging_dir / filename)
            bpy.ops.render.render(write_still=True)
            rendered = staging_dir / filename
            if not rendered.is_file() or rendered.stat().st_size == 0:
                raise RuntimeError(f"Blender did not create animatic pose: {rendered}")
            print(f"ANIMATIC_FRAME source={source_frame}")

        actual_names = tuple(sorted(path.name for path in staging_dir.glob("f*.webp")))
        if actual_names != ANIMATIC_FRAME_NAMES:
            raise RuntimeError(f"Animatic staging contract mismatch: {actual_names}")

        moved_previous = False
        try:
            if output_dir.exists():
                os.replace(output_dir, backup_dir)
                moved_previous = True
            os.replace(staging_dir, output_dir)
        except BaseException:
            if moved_previous and not output_dir.exists() and backup_dir.exists():
                os.replace(backup_dir, output_dir)
            raise
        shutil.rmtree(backup_dir, ignore_errors=True)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    print(f"ANIMATIC_FRAMES {output_dir} poses={len(SAMPLED_FRAMES)}")


def main() -> None:
    blend_path = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    if blend_path != EXPECTED_BLEND:
        raise RuntimeError(f"Open {EXPECTED_BLEND} before rendering previews; got {blend_path}")

    scene = bpy.context.scene
    state = capture_render_state(scene)
    try:
        configure_preview_render()
        graybox = create_graybox_material()

        # Gate 1: composition and silhouette before judging surface treatment.
        render_still(
            scene,
            "graybox-desktop.webp",
            1,
            "Camera_Desktop",
            960,
            540,
            material_override=graybox,
        )

        # Gate 2: final material families and four-point industrial lighting.
        render_still(scene, "lookdev-desktop.webp", 8, "Camera_Desktop", 960, 540)
        render_still(scene, "mobile-lookdev.webp", 8, "Camera_Mobile", 540, 720)

        # Gate 3: one key pose per act plus the complete low-resolution animatic.
        for filename, frame in (
            ("act01-system.webp", 10),
            ("act02-flow.webp", 29),
            ("act03-cutaway.webp", 48),
            ("act04-exploded.webp", 68),
            ("act05-delivery.webp", 96),
        ):
            render_still(scene, filename, frame, "Camera_Desktop", 960, 540)

        render_animatic_frames(scene)
    finally:
        restore_render_state(scene, state)

    print(f"PREVIEW_SET_COMPLETE {PREVIEW_DIR}")


if __name__ == "__main__":
    main()

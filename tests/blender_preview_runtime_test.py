"""Blender-side failure-safety tests for the preview renderer."""

from __future__ import annotations

import importlib.util
import tempfile
import traceback
from types import SimpleNamespace
from pathlib import Path

import bpy


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "source/blender/render_previews.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_preview_module():
    spec = importlib.util.spec_from_file_location("dingyi_render_previews", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def render_state(scene):
    return (
        scene.frame_current,
        scene.camera,
        scene.render.engine,
        scene.cycles.samples,
        scene.render.resolution_x,
        scene.render.resolution_y,
        scene.render.resolution_percentage,
        scene.render.image_settings.file_format,
        scene.render.image_settings.color_mode,
        scene.render.image_settings.quality,
        scene.render.filepath,
        scene.render.use_file_extension,
        scene.render.film_transparent,
        bpy.context.view_layer.material_override,
    )


def restore_state(scene, state) -> None:
    (
        frame,
        camera,
        engine,
        samples,
        width,
        height,
        percentage,
        file_format,
        color_mode,
        quality,
        filepath,
        use_extension,
        film_transparent,
        material_override,
    ) = state
    scene.camera = camera
    scene.render.engine = engine
    scene.cycles.samples = samples
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = percentage
    scene.render.image_settings.file_format = file_format
    scene.render.image_settings.color_mode = color_mode
    scene.render.image_settings.quality = quality
    scene.render.filepath = filepath
    scene.render.use_file_extension = use_extension
    scene.render.film_transparent = film_transparent
    bpy.context.view_layer.material_override = material_override
    scene.frame_set(frame)


def test_main_restores_state(module) -> None:
    scene = bpy.context.scene
    original = render_state(scene)
    original_render_still = module.render_still
    original_render_animatic = module.render_animatic_frames
    module.render_still = lambda *args, **kwargs: None
    module.render_animatic_frames = lambda *args, **kwargs: None
    try:
        module.main()
        require(render_state(scene) == original,
                "preview main() must restore production state after a successful run")
    finally:
        module.render_still = original_render_still
        module.render_animatic_frames = original_render_animatic
        restore_state(scene, original)


def test_failed_animatic_preserves_previous_set(module) -> None:
    scene = bpy.context.scene
    with tempfile.TemporaryDirectory(prefix="dingyi-preview-test-") as temp_dir:
        module.PREVIEW_DIR = Path(temp_dir)
        published = module.PREVIEW_DIR / "animatic"
        published.mkdir(parents=True)
        known_good = published / "f0001.webp"
        known_good.write_bytes(b"known-good-preview")
        original_bpy = module.bpy

        def fail_render(**_kwargs):
            raise RuntimeError("forced render failure")

        module.bpy = SimpleNamespace(
            data=bpy.data,
            context=bpy.context,
            ops=SimpleNamespace(render=SimpleNamespace(render=fail_render)),
        )
        try:
            try:
                module.render_animatic_frames(scene)
            except RuntimeError:
                pass
            else:
                raise AssertionError("forced missing-camera render should fail")
            require(known_good.read_bytes() == b"known-good-preview",
                    "failed animatic render destroyed or replaced the prior valid frame set")
            require(sorted(path.name for path in published.iterdir()) == ["f0001.webp"],
                    "failed animatic render left a partial published frame set")
        finally:
            module.bpy = original_bpy


def test_orphaned_backup_is_recovered(module) -> None:
    scene = bpy.context.scene
    with tempfile.TemporaryDirectory(prefix="dingyi-preview-recovery-") as temp_dir:
        module.PREVIEW_DIR = Path(temp_dir)
        backup = module.PREVIEW_DIR / ".animatic-previous"
        backup.mkdir(parents=True)
        known_good = backup / "f0001.webp"
        known_good.write_bytes(b"recoverable-preview")
        original_bpy = module.bpy

        def fail_render(**_kwargs):
            raise RuntimeError("forced render failure after backup recovery")

        module.bpy = SimpleNamespace(
            data=bpy.data,
            context=bpy.context,
            ops=SimpleNamespace(render=SimpleNamespace(render=fail_render)),
        )
        try:
            try:
                module.render_animatic_frames(scene)
            except RuntimeError:
                pass
            published = module.PREVIEW_DIR / "animatic" / "f0001.webp"
            require(published.read_bytes() == b"recoverable-preview",
                    "orphaned animation backup was not restored before a new render")
            require(not backup.exists(), "recovered backup directory should no longer be orphaned")
        finally:
            module.bpy = original_bpy


def main() -> None:
    module = load_preview_module()
    failures = []
    for test in (
        test_main_restores_state,
        test_failed_animatic_preserves_previous_set,
        test_orphaned_backup_is_recovered,
    ):
        try:
            test(module)
        except Exception as exc:  # collect both failures in the red phase
            failures.append(f"{test.__name__}: {exc}")
    if failures:
        raise AssertionError("; ".join(failures))
    print(
        "BLENDER_PREVIEW_RUNTIME_PASS state_restore=1 "
        "atomic_failure_preservation=1 orphan_backup_recovery=1"
    )


try:
    main()
except Exception:
    traceback.print_exc()
    raise SystemExit(1)

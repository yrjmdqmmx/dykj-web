"""Blender-side contract tests for the Dingyi cinematic vacuum system scene.

Run with:
    Blender -b source/blender/dingyi-vacuum-system.blend \
        --python tests/blender_scene_test.py
"""

from __future__ import annotations

import math
import sys
import traceback
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BLEND = (REPO_ROOT / "source/blender/dingyi-vacuum-system.blend").resolve()
EXPECTED_MARKERS = {
    "ACT_01_SYSTEM": 1,
    "ACT_02_INTEGRATION": 19,
    "ACT_03_PRECISION": 38,
    "ACT_04_SERVICE": 56,
    "ACT_05_DELIVERY": 79,
    "END": 96,
}
EXPECTED_CATEGORIES = {
    "SKID",
    "PIPELINE",
    "CHAMBER",
    "PUMP_ASSEMBLY",
    "INTERNALS",
    "FASTENERS",
    "FX",
    "LIGHTS_CAMERA",
}
EXPECTED_SEMANTIC_OBJECTS = {
    "Pump_Housing",
    "EndCap",
    "Shaft",
    "Rotor",
    "Seal",
    "Bearing",
    "DriveMotor",
    "ControlCabinet",
    "VacuumChamber",
}
EXPECTED_MATERIAL_FAMILIES = {
    "PowderCoat",
    "Stainless",
    "Rubber",
    "Copper",
    "Glass",
    "EmissiveTeal",
    "EmissiveAmber",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def close_vector(a, b, tolerance: float = 1.0e-5) -> bool:
    return all(math.isclose(x, y, abs_tol=tolerance) for x, y in zip(a, b))


def action_fcurve_count(action) -> int:
    """Count curves in both legacy and Blender 5 layered Actions."""
    if hasattr(action, "fcurves"):
        return len(action.fcurves)
    return sum(
        len(channelbag.fcurves)
        for layer in action.layers
        for strip in layer.strips
        for channelbag in getattr(strip, "channelbags", ())
    )


def assert_scene_contract() -> None:
    scene = bpy.context.scene
    blend_path = Path(bpy.data.filepath).resolve() if bpy.data.filepath else None
    require(blend_path == EXPECTED_BLEND, f"wrong or unsaved blend: {blend_path}")

    require(scene.frame_start == 1, f"frame_start must be 1, got {scene.frame_start}")
    require(scene.frame_end == 96, f"frame_end must be 96, got {scene.frame_end}")
    require(scene.render.engine == "CYCLES", f"render engine must be Cycles, got {scene.render.engine}")
    require(scene.get("production_render_engine") == "CYCLES",
            "scene must record Cycles as the production render engine")
    require(scene.render.resolution_x == 1920 and scene.render.resolution_y == 1080,
            f"production resolution must be 1920x1080, got {scene.render.resolution_x}x{scene.render.resolution_y}")
    require(scene.cycles.samples >= 64, f"Cycles samples must be >=64, got {scene.cycles.samples}")
    require(scene.view_settings.view_transform == "AgX",
            f"view transform must use AgX, got {scene.view_settings.view_transform}")
    require(bool(scene.cycles.use_denoising), "Cycles denoising must be enabled")

    for camera_name in ("Camera_Desktop", "Camera_Mobile"):
        camera = bpy.data.objects.get(camera_name)
        require(camera is not None and camera.type == "CAMERA", f"missing camera: {camera_name}")
    require(bpy.data.objects["Camera_Desktop"].get("text_safe_left") >= 0.35,
            "desktop camera must declare a >=35% left text-safe area")
    require(bpy.data.objects["Camera_Mobile"].get("composition") == "3:4",
            "mobile camera must declare its independent 3:4 composition")

    marker_map = {marker.name: marker.frame for marker in scene.timeline_markers}
    require(marker_map == EXPECTED_MARKERS,
            f"timeline markers differ: expected {EXPECTED_MARKERS}, got {marker_map}")

    root = bpy.data.objects.get("SYSTEM_ROOT")
    require(root is not None and root.type == "EMPTY", "missing SYSTEM_ROOT empty")
    root_children = {child.name for child in root.children}
    require(EXPECTED_CATEGORIES <= root_children,
            f"SYSTEM_ROOT missing category children: {sorted(EXPECTED_CATEGORIES - root_children)}")
    for category in EXPECTED_CATEGORIES:
        require(bpy.data.objects[category].type == "EMPTY", f"{category} must be an empty")

    expected_collections = {f"COL_{category}" for category in EXPECTED_CATEGORIES}
    actual_collections = set(bpy.data.collections.keys())
    require(actual_collections == expected_collections,
            f"scene contains startup/stray collections: {sorted(actual_collections - expected_collections)}")
    require(set(bpy.data.worlds.keys()) == {"Dingyi_World"},
            f"scene must rebuild one deterministic world, got {list(bpy.data.worlds.keys())}")
    require(scene.world and scene.world.name == "Dingyi_World", "scene uses the wrong world")
    require(scene.compositing_node_group is None,
            "startup compositor node group must not survive a reproducible rebuild")

    missing_semantics = EXPECTED_SEMANTIC_OBJECTS - set(bpy.data.objects.keys())
    require(not missing_semantics, f"missing semantic objects: {sorted(missing_semantics)}")

    material_names = set(bpy.data.materials.keys())
    for family in EXPECTED_MATERIAL_FAMILIES:
        require(any(name.startswith(family) for name in material_names),
                f"missing material family: {family}")

    mesh_objects = [obj for obj in scene.objects if obj.type == "MESH"]
    vertex_count = sum(len(obj.data.vertices) for obj in mesh_objects)
    require(len(mesh_objects) >= 100, f"need >=100 mesh objects, got {len(mesh_objects)}")
    require(vertex_count >= 30_000, f"need >=30000 mesh vertices, got {vertex_count}")

    hard_surface = [obj for obj in mesh_objects if obj.get("hard_surface")]
    require(len(hard_surface) >= 50, f"need >=50 tagged hard-surface objects, got {len(hard_surface)}")
    missing_bevel = [
        obj.name for obj in hard_surface
        if not any(modifier.type == "BEVEL" for modifier in obj.modifiers)
    ]
    require(not missing_bevel, f"hard-surface objects missing Bevel: {missing_bevel[:8]}")

    fasteners = [obj for obj in scene.objects if obj.get("pump_fastener")]
    require(len(fasteners) >= 24, f"need >=24 pump fasteners, got {len(fasteners)}")
    for fastener in fasteners:
        suffix = fastener.name.removeprefix("Pump_Fastener_")
        head = bpy.data.objects.get(f"Pump_FastenerHead_{suffix}")
        require(head is not None, f"missing fastener head for {fastener.name}")
        require(head.parent == fastener,
                f"{head.name} must be rigidly parented to {fastener.name}")

    animated_objects = [obj for obj in scene.objects if obj.animation_data and obj.animation_data.action]
    require(len(animated_objects) >= 16, f"need multiple animated objects, got {len(animated_objects)}")
    require(sum(action_fcurve_count(obj.animation_data.action) for obj in animated_objects) >= 24,
            "scene animation is too sparse")

    startup_parts = [obj for obj in scene.objects if obj.get("startup_motion")]
    require(startup_parts, "act 1 needs tagged subtle equipment operating motion")
    scene.frame_set(1)
    startup_at_1 = {obj.name: obj.location.copy() for obj in startup_parts}
    scene.frame_set(5)
    require(any(
        (obj.location - startup_at_1[obj.name]).length >= 0.005
        for obj in startup_parts
    ), "act 1 operating motion is not visible between frames 1 and 5")

    valve_wheels = sorted(
        (obj for obj in scene.objects if obj.name.startswith("Valve_Handwheel_")),
        key=lambda obj: obj.name,
    )
    require(len(valve_wheels) >= 4, "act 2 needs at least four responding valves")
    response_starts = [wheel.get("response_start") for wheel in valve_wheels]
    response_ends = [wheel.get("response_end") for wheel in valve_wheels]
    require(all(isinstance(frame, int) for frame in response_starts + response_ends),
            "valves must declare response_start/response_end frames")
    require(response_starts == sorted(set(response_starts)),
            f"valves must respond sequentially, got starts {response_starts}")
    require(all(start < end <= 37 for start, end in zip(response_starts, response_ends)),
            f"valve responses must complete inside act 2, got {list(zip(response_starts, response_ends))}")

    flow_path = bpy.data.objects.get("Flow_Path_Main")
    require(flow_path is not None and flow_path.type == "CURVE", "missing semantic flow path")
    flow_beads = sorted(
        (obj for obj in scene.objects if obj.name.startswith("Flow_Bead_")),
        key=lambda obj: obj.name,
    )
    require(len(flow_beads) >= 8, f"need at least 8 flow beads, got {len(flow_beads)}")
    for bead in flow_beads:
        follow_constraints = [constraint for constraint in bead.constraints if constraint.type == "FOLLOW_PATH"]
        require(len(follow_constraints) == 1 and follow_constraints[0].target == flow_path,
                f"{bead.name} must follow Flow_Path_Main instead of linearly crossing equipment")

    spline = flow_path.data.splines[0]
    bezier_points = spline.bezier_points
    centerline_samples = []
    for segment_index in range(len(bezier_points) - 1):
        start_point = bezier_points[segment_index]
        end_point = bezier_points[segment_index + 1]
        p0 = start_point.co
        p1 = start_point.handle_right
        p2 = end_point.handle_left
        p3 = end_point.co
        for sample_index in range(201):
            t = sample_index / 200
            inverse = 1.0 - t
            point = (
                inverse ** 3 * p0
                + 3 * inverse ** 2 * t * p1
                + 3 * inverse * t ** 2 * p2
                + t ** 3 * p3
            )
            centerline_samples.append(flow_path.matrix_world @ point)
    path_tree = KDTree(len(centerline_samples))
    for index, point in enumerate(centerline_samples):
        path_tree.insert(point, index)
    path_tree.balance()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for frame in (20, 24, 28, 32, 36):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        depsgraph.update()
        for bead in flow_beads:
            position = bead.evaluated_get(depsgraph).matrix_world.translation
            _, _, distance = path_tree.find(position)
            require(distance <= 0.04,
                    f"{bead.name} leaves the pipe centerline at frame {frame}: distance={distance:.4f}")

    exploded_parts = [obj for obj in scene.objects if obj.get("exploded_part")]
    require(len(exploded_parts) >= 16, f"need >=16 exploded parts, got {len(exploded_parts)}")
    transforms = {}
    for frame in (1, 68, 96):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        transforms[frame] = {
            obj.name: (obj.location.copy(), obj.rotation_euler.copy()) for obj in exploded_parts
        }
    for obj in exploded_parts:
        loc_1, rot_1 = transforms[1][obj.name]
        loc_68, _ = transforms[68][obj.name]
        loc_96, rot_96 = transforms[96][obj.name]
        require(close_vector(loc_1, loc_96) and close_vector(rot_1, rot_96),
                f"{obj.name} does not reassemble exactly at frame 96")
        require((loc_68 - loc_1).length >= 0.25,
                f"{obj.name} is not visibly exploded along the mechanical axis at frame 68")

    # All service parts are authored with local Z aligned to the pump's world-X
    # mechanical axis. A valid screw-out may spin around that axis, but it must
    # never tumble away from it at an interpolated frame.
    mechanical_axis = Vector((1.0, 0.0, 0.0))
    for frame in (55, 60, 64, 68, 72, 78):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for obj in exploded_parts:
            local_axis = (obj.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
            require(abs(local_axis.dot(mechanical_axis)) >= 0.999,
                    f"{obj.name} tumbles off the mechanical axis at frame {frame}: {tuple(local_axis)}")

    lights = [obj for obj in scene.objects if obj.type == "LIGHT"]
    require(len(lights) >= 3, f"need >=3 professional lights, got {len(lights)}")
    require(any(light.data.color.r > light.data.color.b for light in lights), "missing warm rim light")
    require(any(light.data.color.b > light.data.color.r for light in lights), "missing cool key/fill light")

    forbidden = [
        obj.name for obj in scene.objects
        if obj.name.startswith("Cube.")
        or obj.name.startswith("Cylinder.")
        or obj.name.startswith("\u67f1\u4f53.")
    ]
    require(not forbidden, f"default/generated names remain: {forbidden[:8]}")

    scene.frame_set(1)
    print(
        "SCENE_CONTRACT_PASS "
        f"meshes={len(mesh_objects)} vertices={vertex_count} "
        f"fasteners={len(fasteners)} animated={len(animated_objects)} "
        f"exploded={len(exploded_parts)} lights={len(lights)}"
    )


try:
    assert_scene_contract()
except Exception:
    traceback.print_exc()
    sys.exit(1)
else:
    sys.exit(0)

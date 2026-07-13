"""Build the Dingyi cinematic vacuum-system scene in Blender 5.1.x.

The scene is intentionally procedural: the public .blend can be regenerated
without private CAD files. Internal pump geometry is an engineering illustration,
not a claim about a specific manufacturer's construction.
"""

from __future__ import annotations

import math
from pathlib import Path

import bpy
from mathutils import Vector


REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_BLEND = REPO_ROOT / "source/blender/dingyi-vacuum-system.blend"
TAU = math.tau


def reset_scene() -> None:
    scene = bpy.context.scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for other_scene in list(bpy.data.scenes):
        if other_scene != scene:
            bpy.data.scenes.remove(other_scene)
    scene.animation_data_clear()
    if scene.sequence_editor:
        scene.sequence_editor_clear()
    scene.compositing_node_group = None
    for key in list(scene.keys()):
        del scene[key]
    for existing_collection in list(bpy.data.collections):
        bpy.data.collections.remove(existing_collection)
    for datablocks in (
        bpy.data.actions,
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.materials,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.images,
        bpy.data.textures,
        bpy.data.node_groups,
    ):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)
    scene.world = None
    for existing_world in list(bpy.data.worlds):
        bpy.data.worlds.remove(existing_world)
    scene.world = bpy.data.worlds.new("Dingyi_World")


def collection(name: str) -> bpy.types.Collection:
    coll = bpy.data.collections.new(f"COL_{name}")
    bpy.context.scene.collection.children.link(coll)
    return coll


def relink(obj: bpy.types.Object, coll: bpy.types.Collection) -> None:
    if coll not in obj.users_collection:
        coll.objects.link(obj)
    for linked in tuple(obj.users_collection):
        if linked != coll:
            linked.objects.unlink(obj)


def add_empty(name: str, parent=None, coll=None) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    (coll or bpy.context.scene.collection).objects.link(obj)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.45
    obj.parent = parent
    return obj


def socket(node, *names):
    for name in names:
        value = node.inputs.get(name)
        if value is not None:
            return value
    return None


def principled_material(
    name: str,
    color,
    *,
    metallic: float = 0.0,
    roughness: float = 0.45,
    transmission: float = 0.0,
    alpha: float = 1.0,
    emission=None,
    emission_strength: float = 0.0,
    noise_scale: float | None = None,
    noise_strength: float = 0.08,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    socket(bsdf, "Base Color").default_value = (*color, 1.0)
    socket(bsdf, "Metallic").default_value = metallic
    socket(bsdf, "Roughness").default_value = roughness
    if socket(bsdf, "Transmission Weight", "Transmission"):
        socket(bsdf, "Transmission Weight", "Transmission").default_value = transmission
    if socket(bsdf, "Alpha"):
        socket(bsdf, "Alpha").default_value = alpha
    if emission is not None:
        socket(bsdf, "Emission Color", "Emission").default_value = (*emission, 1.0)
        socket(bsdf, "Emission Strength").default_value = emission_strength
    if noise_scale:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = noise_scale
        noise.inputs["Detail"].default_value = 5.0
        noise.inputs["Roughness"].default_value = 0.65
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = noise_strength
        bump.inputs["Distance"].default_value = 0.12
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.diffuse_color = (*color, alpha)
    if alpha < 1.0:
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "DITHERED"
        mat.use_transparency_overlap = False
    return mat


def assign_material(obj, mat) -> None:
    if hasattr(obj.data, "materials"):
        obj.data.materials.append(mat)


def tag_hard_surface(obj, width=0.04, segments=3) -> None:
    obj["hard_surface"] = True
    bevel = obj.modifiers.new("EdgeSoftening", "BEVEL")
    bevel.width = width
    bevel.segments = segments
    bevel.limit_method = "ANGLE"


def add_cube(name, location, dimensions, mat, parent, coll, bevel=0.06):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign_material(obj, mat)
    tag_hard_surface(obj, bevel)
    obj.parent = parent
    relink(obj, coll)
    return obj


def add_cylinder(
    name,
    location,
    radius,
    depth,
    mat,
    parent,
    coll,
    *,
    rotation=(0.0, 0.0, 0.0),
    vertices=64,
    bevel=0.035,
):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    assign_material(obj, mat)
    tag_hard_surface(obj, bevel)
    obj.parent = parent
    relink(obj, coll)
    return obj


def add_torus(
    name,
    location,
    major_radius,
    minor_radius,
    mat,
    parent,
    coll,
    *,
    rotation=(0.0, 0.0, 0.0),
    major_segments=80,
    minor_segments=20,
):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius,
        minor_radius=minor_radius,
        major_segments=major_segments,
        minor_segments=minor_segments,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    assign_material(obj, mat)
    tag_hard_surface(obj, min(minor_radius * 0.22, 0.025), 2)
    obj.parent = parent
    relink(obj, coll)
    return obj


def add_sphere(name, location, radius, mat, parent, coll, segments=48, rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=segments,
        ring_count=rings,
        radius=radius,
        location=location,
    )
    obj = bpy.context.object
    obj.name = name
    assign_material(obj, mat)
    obj.parent = parent
    relink(obj, coll)
    return obj


def add_pipe(name, points, radius, mat, parent, coll, resolution=4):
    curve = bpy.data.curves.new(name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 12
    curve.bevel_depth = radius
    curve.bevel_resolution = resolution
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    coll.objects.link(obj)
    assign_material(obj, mat)
    obj.parent = parent
    return obj


def add_text(name, body, location, size, mat, parent, coll, rotation=(math.pi / 2, 0, 0)):
    bpy.ops.object.text_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.body = body
    obj.data.align_x = "CENTER"
    obj.data.align_y = "CENTER"
    obj.data.size = size
    obj.data.extrude = 0.012
    obj.data.bevel_depth = 0.005
    assign_material(obj, mat)
    obj.parent = parent
    relink(obj, coll)
    return obj


def key_transform(obj, frame, *, location=None, rotation=None, scale=None) -> None:
    if location is not None:
        obj.location = location
        obj.keyframe_insert(data_path="location", frame=frame)
    if rotation is not None:
        obj.rotation_euler = rotation
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    if scale is not None:
        obj.scale = scale
        obj.keyframe_insert(data_path="scale", frame=frame)


def linearize_actions() -> None:
    for action in bpy.data.actions:
        if hasattr(action, "fcurves"):
            curves = action.fcurves
        else:
            curves = [
                curve
                for layer in action.layers
                for strip in layer.strips
                for channelbag in getattr(strip, "channelbags", ())
                for curve in channelbag.fcurves
            ]
        for curve in curves:
            for key in curve.keyframe_points:
                key.interpolation = "BEZIER" if "Camera" in action.name else "SINE"


def look_at(obj, target) -> None:
    obj.rotation_euler = ((Vector(target) - obj.location).to_track_quat("-Z", "Y")).to_euler()


def key_camera(camera, frame, location, target) -> None:
    camera.location = location
    look_at(camera, target)
    camera.keyframe_insert(data_path="location", frame=frame)
    camera.keyframe_insert(data_path="rotation_euler", frame=frame)


def add_area_light(name, location, color, energy, size, target, parent, coll):
    data = bpy.data.lights.new(name + "_Data", "AREA")
    data.color = color
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    obj = bpy.data.objects.new(name, data)
    coll.objects.link(obj)
    obj.location = location
    obj.parent = parent
    look_at(obj, target)
    return obj


def configure_scene() -> None:
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = 96
    scene.render.engine = "CYCLES"
    scene["production_render_engine"] = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.cycles.device = "GPU"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.use_border = False
    scene.render.use_crop_to_border = False
    scene.render.filepath = ""
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.quality = 80
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.25
    scene.view_settings.gamma = 1.0
    scene.world.use_nodes = True
    world_background = scene.world.node_tree.nodes.get("Background")
    world_background.inputs["Color"].default_value = (0.0015, 0.003, 0.006, 1.0)
    world_background.inputs["Strength"].default_value = 0.075
    scene.world.color = (0.0015, 0.003, 0.006)
    scene.render.use_file_extension = True
    scene.render.fps = 24
    scene.timeline_markers.clear()
    for name, frame in (
        ("ACT_01_SYSTEM", 1),
        ("ACT_02_INTEGRATION", 19),
        ("ACT_03_PRECISION", 38),
        ("ACT_04_SERVICE", 56),
        ("ACT_05_DELIVERY", 79),
        ("END", 96),
    ):
        scene.timeline_markers.new(name, frame=frame)


def build_scene() -> None:
    reset_scene()
    configure_scene()

    # Organizational hierarchy: visible components are parented to these empties.
    master = bpy.context.scene.collection
    root = add_empty("SYSTEM_ROOT", coll=master)
    category_names = (
        "SKID",
        "PIPELINE",
        "CHAMBER",
        "PUMP_ASSEMBLY",
        "INTERNALS",
        "FASTENERS",
        "FX",
        "LIGHTS_CAMERA",
    )
    collections = {name: collection(name) for name in category_names}
    groups = {
        name: add_empty(name, parent=root, coll=collections[name]) for name in category_names
    }

    # PBR families. Names intentionally match the scene contract.
    mats = {
        "powder": principled_material(
            "PowderCoat_DeepGraphite", (0.008, 0.018, 0.026), metallic=0.48,
            roughness=0.34, noise_scale=34.0, noise_strength=0.065,
        ),
        "blue": principled_material(
            "PowderCoat_DingyiBlue", (0.008, 0.040, 0.092), metallic=0.56,
            roughness=0.30, noise_scale=42.0, noise_strength=0.050,
        ),
        "steel": principled_material(
            "Stainless_Brushed", (0.34, 0.42, 0.46), metallic=0.94,
            roughness=0.22, noise_scale=7.0, noise_strength=0.10,
        ),
        "darksteel": principled_material(
            "Stainless_Dark", (0.06, 0.075, 0.085), metallic=0.88,
            roughness=0.34, noise_scale=12.0, noise_strength=0.065,
        ),
        "rubber": principled_material(
            "Rubber_Seal", (0.008, 0.011, 0.012), metallic=0.0,
            roughness=0.72, noise_scale=25.0, noise_strength=0.13,
        ),
        "copper": principled_material(
            "Copper_Engineering", (0.39, 0.105, 0.035), metallic=0.90,
            roughness=0.23, noise_scale=10.0, noise_strength=0.055,
        ),
        "glass": principled_material(
            "Glass_Viewport", (0.025, 0.20, 0.24), metallic=0.0,
            roughness=0.08, transmission=0.72, alpha=0.32,
        ),
        "cutaway": principled_material(
            "Glass_CutawayShell", (0.012, 0.055, 0.072), metallic=0.18,
            roughness=0.16, transmission=0.58, alpha=0.20,
        ),
        "teal": principled_material(
            "EmissiveTeal_Flow", (0.01, 0.24, 0.22), roughness=0.18,
            emission=(0.01, 0.95, 0.72), emission_strength=8.0,
        ),
        "amber": principled_material(
            "EmissiveAmber_Status", (0.40, 0.11, 0.018), roughness=0.2,
            emission=(1.0, 0.25, 0.025), emission_strength=10.0,
        ),
        "white": principled_material(
            "PowderCoat_Lettering", (0.62, 0.76, 0.79), metallic=0.15,
            roughness=0.28, emission=(0.10, 0.18, 0.20), emission_strength=0.8,
        ),
    }

    # Ground and anti-vibration skid.
    add_cube("Ground", (4.5, 1.0, -0.28), (28.0, 20.0, 0.35), mats["darksteel"], groups["SKID"], collections["SKID"], 0.12)
    for idx, y in enumerate((-3.0, 3.0)):
        add_cube(f"Skid_LongBeam_{idx:02d}", (5.0, y, 0.25), (14.0, 0.42, 0.50), mats["powder"], groups["SKID"], collections["SKID"], 0.08)
    for idx, x in enumerate((-1.0, 1.0, 3.0, 5.0, 7.0, 9.0, 11.0)):
        add_cube(f"Skid_CrossBeam_{idx:02d}", (x, 0.0, 0.28), (0.38, 6.2, 0.48), mats["powder"], groups["SKID"], collections["SKID"], 0.07)
    add_cube("Skid_Deck", (5.0, 0.0, 0.58), (13.2, 5.5, 0.20), mats["darksteel"], groups["SKID"], collections["SKID"], 0.04)

    # Vacuum chamber with split shields and internal copper field rings.
    chamber = add_cylinder("VacuumChamber", (3.7, 1.25, 3.65), 2.25, 5.5, mats["cutaway"], groups["CHAMBER"], collections["CHAMBER"], vertices=128, bevel=0.07)
    chamber["engineering_role"] = "vacuum chamber"
    left_shell = add_cube("Chamber_Shell_Left", (2.72, 1.22, 3.70), (1.80, 3.95, 5.15), mats["blue"], groups["CHAMBER"], collections["CHAMBER"], 0.42)
    right_shell = add_cube("Chamber_Shell_Right", (4.68, 1.22, 3.70), (1.80, 3.95, 5.15), mats["blue"], groups["CHAMBER"], collections["CHAMBER"], 0.42)
    # The stainless core peeks between the stylized split safety shields.
    for idx, z in enumerate((1.0, 1.45, 1.9, 2.35, 2.8, 3.25, 3.7, 4.15, 4.6, 5.05, 5.5, 5.95, 6.35)):
        add_torus(f"Chamber_Rib_{idx:02d}", (3.7, 1.25, z), 2.28, 0.055, mats["steel"], groups["CHAMBER"], collections["CHAMBER"], major_segments=96, minor_segments=16)
    chamber_door = add_cylinder("Chamber_Door", (3.7, -1.08, 3.65), 1.78, 0.34, mats["darksteel"], groups["CHAMBER"], collections["CHAMBER"], rotation=(math.pi / 2, 0, 0), vertices=128, bevel=0.06)
    chamber_door_flange = add_torus("Chamber_DoorFlange", (3.7, -1.29, 3.65), 1.74, 0.15, mats["steel"], groups["CHAMBER"], collections["CHAMBER"], rotation=(math.pi / 2, 0, 0), major_segments=96, minor_segments=24)
    chamber_viewport = add_cylinder("Chamber_ViewportGlass", (3.7, -1.50, 3.65), 0.63, 0.10, mats["glass"], groups["CHAMBER"], collections["CHAMBER"], rotation=(math.pi / 2, 0, 0), vertices=96, bevel=0.025)
    chamber_viewport_ring = add_torus("Chamber_ViewportRing", (3.7, -1.58, 3.65), 0.67, 0.09, mats["copper"], groups["CHAMBER"], collections["CHAMBER"], rotation=(math.pi / 2, 0, 0), major_segments=96, minor_segments=20)
    for idx, z in enumerate((1.55, 2.15, 2.75, 3.35, 3.95, 4.55, 5.15)):
        add_torus(f"Internal_FieldRing_{idx:02d}", (3.7, 1.25, z), 1.18, 0.08, mats["copper"], groups["INTERNALS"], collections["INTERNALS"], major_segments=80, minor_segments=18)
    for idx, angle in enumerate((0.0, math.pi / 2, math.pi, 3 * math.pi / 2)):
        x = 3.7 + math.cos(angle) * 1.18
        y = 1.25 + math.sin(angle) * 1.18
        add_cylinder(f"Internal_Support_{idx:02d}", (x, y, 3.35), 0.065, 4.2, mats["steel"], groups["INTERNALS"], collections["INTERNALS"], vertices=32, bevel=0.02)

    # Control cabinet and instrumentation.
    add_cube("ControlCabinet", (-0.55, 2.05, 2.45), (2.25, 1.25, 4.45), mats["powder"], groups["SKID"], collections["SKID"], 0.16)
    add_cube("ControlCabinet_Door", (-0.55, 1.38, 2.50), (2.02, 0.12, 4.12), mats["blue"], groups["SKID"], collections["SKID"], 0.09)
    add_cube("Control_Display", (-0.55, 1.27, 3.23), (1.30, 0.08, 0.78), mats["glass"], groups["SKID"], collections["SKID"], 0.05)
    add_text("Control_Brand", "DINGYI", (-0.55, 1.17, 4.06), 0.30, mats["white"], groups["SKID"], collections["SKID"])
    add_text("Control_Subtitle", "VACUUM  SYSTEM", (-0.55, 1.17, 3.72), 0.10, mats["white"], groups["SKID"], collections["SKID"])
    for idx, x in enumerate((-0.98, -0.70, -0.42, -0.14)):
        indicator = add_sphere(f"Control_Indicator_{idx:02d}", (x, 1.17, 2.48), 0.085, mats["amber"] if idx == 0 else mats["teal"], groups["FX"], collections["FX"], 32, 16)
        key_transform(indicator, 1, scale=(0.35, 0.35, 0.35))
        key_transform(indicator, 18 + idx * 3, scale=(1.0, 1.0, 1.0))
        key_transform(indicator, 96, scale=(1.0, 1.0, 1.0))
    for idx, z in enumerate((1.15, 1.38, 1.61)):
        add_cube(f"Control_Vent_{idx:02d}", (-0.55, 1.28, z), (1.35, 0.07, 0.095), mats["darksteel"], groups["SKID"], collections["SKID"], 0.02)

    # Pump head, drive motor and engineered internals.
    pump_axis_y = -1.35
    pump_axis_z = 2.30
    add_cube("Pump_Base", (8.55, pump_axis_y, 0.92), (6.70, 2.65, 0.38), mats["powder"], groups["PUMP_ASSEMBLY"], collections["PUMP_ASSEMBLY"], 0.10)
    for idx, x in enumerate((6.25, 7.25, 9.55, 10.55)):
        add_cube(f"Pump_Foot_{idx:02d}", (x, pump_axis_y, 1.25), (0.65, 1.75, 0.55), mats["darksteel"], groups["PUMP_ASSEMBLY"], collections["PUMP_ASSEMBLY"], 0.09)
    housing = add_cylinder("Pump_Housing", (7.05, pump_axis_y, pump_axis_z), 1.55, 2.15, mats["blue"], groups["PUMP_ASSEMBLY"], collections["PUMP_ASSEMBLY"], rotation=(0, math.pi / 2, 0), vertices=128, bevel=0.075)
    housing["engineering_role"] = "schematic pump casing"
    add_torus("Pump_HousingFlange", (5.96, pump_axis_y, pump_axis_z), 1.48, 0.13, mats["steel"], groups["PUMP_ASSEMBLY"], collections["PUMP_ASSEMBLY"], rotation=(0, math.pi / 2, 0), major_segments=96, minor_segments=24)
    endcap = add_cylinder("EndCap", (5.78, pump_axis_y, pump_axis_z), 1.40, 0.34, mats["blue"], groups["PUMP_ASSEMBLY"], collections["PUMP_ASSEMBLY"], rotation=(0, math.pi / 2, 0), vertices=128, bevel=0.065)
    motor = add_cylinder("DriveMotor", (10.05, pump_axis_y, pump_axis_z), 1.23, 3.85, mats["powder"], groups["PUMP_ASSEMBLY"], collections["PUMP_ASSEMBLY"], rotation=(0, math.pi / 2, 0), vertices=128, bevel=0.08)
    fan_shroud = add_cylinder("Motor_FanShroud", (12.03, pump_axis_y, pump_axis_z), 1.31, 0.28, mats["darksteel"], groups["PUMP_ASSEMBLY"], collections["PUMP_ASSEMBLY"], rotation=(0, math.pi / 2, 0), vertices=128, bevel=0.07)
    motor_parts = [motor, fan_shroud]
    # A real industrial motor reads as axial ribs, not a stack of bellows rings.
    for idx in range(14):
        angle = idx / 14 * TAU
        y = pump_axis_y + math.cos(angle) * 1.23
        z = pump_axis_z + math.sin(angle) * 1.23
        fin = add_cube(
            f"Motor_CoolingFin_{idx:02d}",
            (10.05, y, z),
            (3.40, 0.11, 0.22),
            mats["darksteel"],
            groups["PUMP_ASSEMBLY"],
            collections["PUMP_ASSEMBLY"],
            0.025,
        )
        fin.rotation_euler.x = angle
        motor_parts.append(fin)
    motor_junction = add_cube("Motor_JunctionBox", (10.0, pump_axis_y, 3.83), (1.35, 1.28, 0.72), mats["blue"], groups["PUMP_ASSEMBLY"], collections["PUMP_ASSEMBLY"], 0.10)
    motor_nameplate = add_cube("Motor_Nameplate", (9.86, pump_axis_y - 0.67, 3.82), (0.88, 0.05, 0.32), mats["copper"], groups["PUMP_ASSEMBLY"], collections["PUMP_ASSEMBLY"], 0.025)
    motor_parts.extend((motor_junction, motor_nameplate))

    # Pump inlet and side outlet with serviceable flanges.
    add_cylinder("Pump_InletNeck", (6.75, pump_axis_y, 4.15), 0.52, 1.65, mats["blue"], groups["PUMP_ASSEMBLY"], collections["PUMP_ASSEMBLY"], vertices=80, bevel=0.045)
    add_torus("Pump_InletFlange", (6.75, pump_axis_y, 5.0), 0.62, 0.10, mats["steel"], groups["PUMP_ASSEMBLY"], collections["PUMP_ASSEMBLY"], major_segments=80, minor_segments=20)
    add_cylinder("Pump_OutletNeck", (7.05, -2.45, pump_axis_z), 0.43, 1.45, mats["blue"], groups["PUMP_ASSEMBLY"], collections["PUMP_ASSEMBLY"], rotation=(math.pi / 2, 0, 0), vertices=80, bevel=0.04)
    add_torus("Pump_OutletFlange", (7.05, -3.18, pump_axis_z), 0.53, 0.10, mats["steel"], groups["PUMP_ASSEMBLY"], collections["PUMP_ASSEMBLY"], rotation=(math.pi / 2, 0, 0), major_segments=80, minor_segments=20)

    shaft = add_cylinder("Shaft", (8.15, pump_axis_y, pump_axis_z), 0.17, 5.75, mats["steel"], groups["INTERNALS"], collections["INTERNALS"], rotation=(0, math.pi / 2, 0), vertices=64, bevel=0.025)
    rotor = add_cylinder("Rotor", (7.05, pump_axis_y, pump_axis_z), 0.75, 1.30, mats["copper"], groups["INTERNALS"], collections["INTERNALS"], rotation=(0, math.pi / 2, 0), vertices=96, bevel=0.05)
    bearing = add_torus("Bearing", (8.03, pump_axis_y, pump_axis_z), 0.64, 0.18, mats["steel"], groups["INTERNALS"], collections["INTERNALS"], rotation=(0, math.pi / 2, 0), major_segments=96, minor_segments=24)
    seal = add_torus("Seal", (5.99, pump_axis_y, pump_axis_z), 1.02, 0.12, mats["rubber"], groups["INTERNALS"], collections["INTERNALS"], rotation=(0, math.pi / 2, 0), major_segments=96, minor_segments=24)
    add_torus("Bearing_Rear", (8.48, pump_axis_y, pump_axis_z), 0.62, 0.16, mats["steel"], groups["INTERNALS"], collections["INTERNALS"], rotation=(0, math.pi / 2, 0), major_segments=80, minor_segments=20)
    for idx in range(10):
        angle = idx / 10 * TAU
        y = pump_axis_y + math.cos(angle) * 0.82
        z = pump_axis_z + math.sin(angle) * 0.82
        blade = add_cube(f"Rotor_Blade_{idx:02d}", (7.05, y, z), (1.42, 0.22, 0.44), mats["copper"], groups["INTERNALS"], collections["INTERNALS"], 0.09)
        blade.rotation_euler.x = angle

    # End-cap bolts: bodies are tagged as pump fasteners and animated.
    exploded = []
    for idx in range(24):
        angle = idx / 24 * TAU
        y = pump_axis_y + math.cos(angle) * 1.18
        z = pump_axis_z + math.sin(angle) * 1.18
        bolt = add_cylinder(
            f"Pump_Fastener_{idx:02d}", (5.48, y, z), 0.095, 0.52,
            mats["steel"], groups["FASTENERS"], collections["FASTENERS"],
            rotation=(0, math.pi / 2, 0), vertices=64, bevel=0.018,
        )
        bolt["pump_fastener"] = True
        bolt["exploded_part"] = True
        exploded.append((bolt, Vector((-1.55 - (idx % 3) * 0.09, 0, 0)), TAU * (2.0 + (idx % 2))))
        head = add_cylinder(
            f"Pump_FastenerHead_{idx:02d}", (5.20, y, z), 0.16, 0.15,
            mats["darksteel"], groups["FASTENERS"], collections["FASTENERS"],
            rotation=(0, math.pi / 2, 0), vertices=6, bevel=0.018,
        )
        # The visible hex head and threaded shank are one rigid fastener. The
        # shank owns the service animation so the head cannot be left behind.
        head_world = head.matrix_world.copy()
        head.parent = bolt
        head.matrix_world = head_world
        head["pump_fastener_head"] = True

    # Main serviceable pieces participate in the same axial disassembly.
    for obj, offset, spin in (
        (endcap, Vector((-3.25, 0, 0)), TAU * 0.25),
        (seal, Vector((-1.65, 0, 0)), TAU * 0.15),
        (bearing, Vector((0.40, 0, 0)), TAU * 0.15),
        (shaft, Vector((2.20, 0, 0)), TAU * 0.50),
        (rotor, Vector((1.50, 0, 0)), TAU * 0.35),
    ):
        obj["exploded_part"] = True
        exploded.append((obj, offset, spin))

    for obj, offset, spin in exploded:
        # ZYX evaluates the keyed Z spin after the fixed Y=90° alignment,
        # equivalent to R_base @ R_localZ for these coaxial parts.
        obj.rotation_mode = "ZYX"
        base_loc = obj.location.copy()
        base_rot = obj.rotation_euler.copy()
        key_transform(obj, 1, location=base_loc, rotation=base_rot)
        key_transform(obj, 55, location=base_loc, rotation=base_rot)
        exploded_rot = base_rot.copy()
        # Cylinders and toruses are authored with local Z aligned to the
        # pump's world-X mechanical axis. Rotating local Z keeps every part
        # coaxial throughout Euler interpolation; rotating Euler X would make
        # the already Y-oriented parts tumble between keyframes.
        exploded_rot.z += spin
        key_transform(obj, 68, location=base_loc + offset, rotation=exploded_rot)
        key_transform(obj, 78, location=base_loc + offset, rotation=exploded_rot)
        key_transform(obj, 96, location=base_loc, rotation=base_rot)

    # The drive assembly clears the shaft before the internal service parts
    # separate. Every rib and cover moves as one rigid functional assembly.
    for obj in motor_parts:
        obj["service_assembly"] = True
        base_loc = obj.location.copy()
        base_rot = obj.rotation_euler.copy()
        key_transform(obj, 1, location=base_loc, rotation=base_rot)
        key_transform(obj, 55, location=base_loc, rotation=base_rot)
        key_transform(obj, 68, location=base_loc + Vector((3.40, 0, 0)), rotation=base_rot)
        key_transform(obj, 78, location=base_loc + Vector((3.40, 0, 0)), rotation=base_rot)
        key_transform(obj, 96, location=base_loc, rotation=base_rot)

    # Sub-pixel-to-few-pixel isolation vibration communicates that the unit is
    # running without breaking the apparent rigidity of the skid and piping.
    for obj in [housing, *motor_parts]:
        obj["startup_motion"] = True
        base_loc = obj.location.copy()
        for frame, y_offset in (
            (1, 0.0),
            (5, 0.024),
            (9, -0.020),
            (13, 0.016),
            (17, -0.010),
            (18, 0.0),
        ):
            key_transform(obj, frame, location=base_loc + Vector((0.0, y_offset, 0.0)))

    # Precision act opens the two stylized chamber shields.
    for shell, direction in ((left_shell, -1.0), (right_shell, 1.0)):
        base = shell.location.copy()
        key_transform(shell, 1, location=base)
        key_transform(shell, 37, location=base)
        key_transform(shell, 48, location=base + Vector((direction * 1.55, 0.0, 0.18)))
        key_transform(shell, 78, location=base + Vector((direction * 1.55, 0.0, 0.18)))
        key_transform(shell, 96, location=base)

    # Slide the service door clear while the camera passes into the chamber.
    # Keeping the four pieces synchronized makes the motion read as one rigid
    # flange assembly without claiming a model-specific hinge arrangement.
    for door_part in (
        chamber_door,
        chamber_door_flange,
        chamber_viewport,
        chamber_viewport_ring,
    ):
        base = door_part.location.copy()
        key_transform(door_part, 1, location=base)
        key_transform(door_part, 37, location=base)
        key_transform(door_part, 48, location=base + Vector((3.45, -0.35, 0.28)))
        key_transform(door_part, 55, location=base)
        key_transform(door_part, 96, location=base)

    # Stainless pipelines, valves and animated flow beads.
    pipe_points = [(-0.2, 0.9, 5.25), (1.2, 0.9, 5.25), (1.2, -0.2, 6.35), (4.1, -0.2, 6.35), (4.1, 1.25, 6.55)]
    add_pipe("Pipeline_UpperManifold", pipe_points, 0.19, mats["steel"], groups["PIPELINE"], collections["PIPELINE"], 5)
    pump_pipe_points = [(4.35, 1.25, 5.75), (6.0, 1.0, 5.75), (6.75, 0.1, 5.0), (6.75, pump_axis_y, 5.0)]
    add_pipe("Pipeline_ToPump", pump_pipe_points, 0.23, mats["steel"], groups["PIPELINE"], collections["PIPELINE"], 5)
    flow_path_object = add_pipe("Flow_Path_Main", pipe_points + pump_pipe_points[1:], 0.055, mats["teal"], groups["FX"], collections["FX"], 3)
    flow_path_object.data.path_duration = 96
    add_pipe("Pipeline_ServiceReturn", [(7.05, -3.15, 2.3), (7.05, -3.8, 2.3), (1.0, -3.8, 2.3), (1.0, -1.0, 1.1)], 0.16, mats["steel"], groups["PIPELINE"], collections["PIPELINE"], 4)
    for idx, x in enumerate((0.85, 2.35, 5.45, 7.05)):
        valve_z = 5.25 if idx < 2 else (5.75 if idx == 2 else 2.3)
        valve_y = 0.9 if idx < 2 else (0.78 if idx == 2 else -3.15)
        add_cylinder(f"Valve_Body_{idx:02d}", (x, valve_y, valve_z), 0.30, 0.52, mats["steel"], groups["PIPELINE"], collections["PIPELINE"], rotation=(0, math.pi / 2, 0), vertices=64, bevel=0.04)
        wheel = add_torus(f"Valve_Handwheel_{idx:02d}", (x, valve_y, valve_z + 0.58), 0.34, 0.055, mats["copper"], groups["PIPELINE"], collections["PIPELINE"], major_segments=64, minor_segments=16)
        base_rot = wheel.rotation_euler.copy()
        response_start = 18 + idx * 3
        response_end = response_start + 8
        wheel["response_start"] = response_start
        wheel["response_end"] = response_end
        key_transform(wheel, 1, rotation=base_rot)
        key_transform(wheel, response_start, rotation=base_rot)
        turned = base_rot.copy()
        turned.z += TAU * 0.75
        key_transform(wheel, response_end, rotation=turned)
        key_transform(wheel, 96, rotation=turned)

    for idx in range(8):
        bead = add_sphere(f"Flow_Bead_{idx:02d}", (0.0, 0.0, 0.0), 0.105, mats["teal"], groups["FX"], collections["FX"], 32, 16)
        follow_path = bead.constraints.new("FOLLOW_PATH")
        follow_path.name = "Follow_Flow_Path"
        follow_path.target = flow_path_object
        follow_path.use_fixed_location = True
        follow_path.forward_axis = "FORWARD_X"
        follow_path.up_axis = "UP_Z"
        start = 18 + idx
        follow_path.offset_factor = 0.0
        follow_path.keyframe_insert(data_path="offset_factor", frame=1)
        follow_path.keyframe_insert(data_path="offset_factor", frame=start)
        follow_path.offset_factor = 1.0
        follow_path.keyframe_insert(data_path="offset_factor", frame=37)
        follow_path.keyframe_insert(data_path="offset_factor", frame=96)
        key_transform(bead, 1, scale=(0.01, 0.01, 0.01))
        key_transform(bead, start, scale=(0.01, 0.01, 0.01))
        key_transform(bead, min(start + 2, 34), scale=(1.0, 1.0, 1.0))
        key_transform(bead, 35, scale=(1.0, 1.0, 1.0))
        key_transform(bead, 37, scale=(0.01, 0.01, 0.01))
        key_transform(bead, 96, scale=(0.01, 0.01, 0.01))

    # Cinematic cameras.
    desktop_data = bpy.data.cameras.new("Camera_Desktop_Data")
    desktop_data.lens = 52
    desktop_data.sensor_width = 36
    desktop_data.shift_x = -0.17
    desktop = bpy.data.objects.new("Camera_Desktop", desktop_data)
    collections["LIGHTS_CAMERA"].objects.link(desktop)
    desktop.parent = groups["LIGHTS_CAMERA"]
    desktop["text_safe_left"] = 0.38
    desktop["composition"] = "16:9"
    key_camera(desktop, 1, (17.5, -23.5, 11.4), (5.1, 0.0, 3.0))
    key_camera(desktop, 18, (15.4, -20.5, 9.8), (5.4, 0.0, 3.1))
    key_camera(desktop, 37, (13.2, -17.5, 8.0), (5.8, 0.0, 3.2))
    key_camera(desktop, 48, (6.4, -8.8, 5.6), (3.7, 1.15, 3.55))
    key_camera(desktop, 55, (12.3, -13.8, 6.5), (6.0, -1.0, 2.8))
    key_camera(desktop, 68, (17.0, -23.0, 9.5), (8.1, -1.1, 2.65))
    key_camera(desktop, 78, (13.8, -15.6, 7.2), (7.4, -1.2, 2.65))
    key_camera(desktop, 96, (17.8, -23.8, 11.6), (5.2, 0.0, 3.0))

    mobile_data = bpy.data.cameras.new("Camera_Mobile_Data")
    mobile_data.lens = 48
    mobile_data.sensor_width = 28
    mobile_data.shift_y = -0.12
    mobile = bpy.data.objects.new("Camera_Mobile", mobile_data)
    collections["LIGHTS_CAMERA"].objects.link(mobile)
    mobile.parent = groups["LIGHTS_CAMERA"]
    mobile["composition"] = "3:4"
    mobile["subject_fill"] = 0.62
    key_camera(mobile, 1, (11.4, -25.5, 11.6), (5.0, 0.0, 3.0))
    key_camera(mobile, 18, (10.6, -22.5, 10.2), (4.8, 0.0, 3.1))
    key_camera(mobile, 37, (9.2, -15.5, 7.8), (3.8, 0.6, 3.5))
    key_camera(mobile, 55, (12.2, -14.5, 6.7), (7.2, -1.0, 2.7))
    key_camera(mobile, 78, (13.0, -16.2, 7.4), (7.0, -1.0, 2.7))
    key_camera(mobile, 96, (11.4, -25.5, 11.6), (5.0, 0.0, 3.0))

    bpy.context.scene.camera = desktop

    # Four-point industrial lighting: cool key, warm rim, overhead fill, pump accent.
    add_area_light("Light_CoolKey", (0.0, -7.5, 12.5), (0.30, 0.62, 1.0), 1500, 7.5, (4.0, 0.0, 3.0), groups["LIGHTS_CAMERA"], collections["LIGHTS_CAMERA"])
    add_area_light("Light_WarmRim", (11.5, 5.0, 9.2), (1.0, 0.28, 0.075), 2100, 6.0, (6.0, 0.0, 3.0), groups["LIGHTS_CAMERA"], collections["LIGHTS_CAMERA"])
    add_area_light("Light_OverheadFill", (4.0, 1.0, 14.5), (0.55, 0.74, 0.86), 1250, 8.0, (4.0, 0.0, 2.5), groups["LIGHTS_CAMERA"], collections["LIGHTS_CAMERA"])
    add_area_light("Light_PumpAccent", (12.0, -6.0, 5.0), (1.0, 0.50, 0.19), 950, 4.0, (8.2, -1.3, 2.4), groups["LIGHTS_CAMERA"], collections["LIGHTS_CAMERA"])

    linearize_actions()
    bpy.context.scene.frame_set(1)
    OUTPUT_BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND), compress=True)
    print(f"BUILT {OUTPUT_BLEND}")


if __name__ == "__main__":
    build_scene()

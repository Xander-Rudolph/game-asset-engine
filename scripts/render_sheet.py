#!/usr/bin/env python3
"""Render a model to a sprite sheet: N angles across, one row per pose.

Runs Blender (the `bpy` module) inside the ComfyUI container, because that is the
only thing in this stack that can pose a rigged FBX.  ComfyUI-3D-Pack's renderer
only takes its own MESH type and its loader reads .obj/.ply/.glb, not the FBX
that rigging produces, and no node in the install outputs the RIGGED_MESH that
UniRigExportPosedFBX wants, so in-graph posing is unreachable headlessly.

    # static mesh, four facings
    scripts/render_sheet.py output/mesh/golem.glb

    # rigged FBX with an animation baked in: 4 poses sampled across the action
    scripts/render_sheet.py output/golem_rigged.fbx --poses even:4

    # explicit frames
    scripts/render_sheet.py output/golem_anim.fbx --poses frames:1,7,13,19

    # hand-authored poses: a role pose file from poses/roles/, compiled into
    # bone transforms for this rig by scripts/bone_roles.py, then rendered
    scripts/bone_roles.py compile poses/roles/attack.json output/rigged/unit_rogue.fbx \\
        --out output/poses/unit_rogue_attack.json
    scripts/render_sheet.py output/rigged/unit_rogue.fbx \\
        --poses transforms:output/poses/unit_rogue_attack.json --check

    # a .blend with a shape key set per pose; scripts/face_rig.py --help shows
    # how to make this file, and sphere_keys.json holds
    # [{}, {"@shape_keys": {"jawOpen": 1.0}}]
    scripts/render_sheet.py output/face_rig/spheres/target_keys.blend \\
        --poses transforms:output/face_rig/sphere_keys.json --zoom 1.6

Sheet layout is poses down, angles across: the order most engines want when
slicing a sheet into a flipbook.

Bone transform JSON is a list of poses, each a map of bone name to a transform:

    [
      {},                                                  # frame 1: rest
      {"RightArm": {"rotate": [0, -35, 0]}},               # frame 2: wind up
      {"RightArm": {"rotate": [0, 55, 0]},
       "Spine":    {"rotate": [8, 0, 0], "translate": [0, 0.02, 0]}}
    ]

Rotations are XYZ Euler degrees, applied to the pose bone; translations are in
Blender units along the bone's own axes.  Unknown bone names are reported rather
than silently ignored: a typo would otherwise cost you a whole sheet.  A role
pose file (poses/roles/*.json, whose "_note" keys are notes) names roles, not
bones, and is refused with the bone_roles.py compile command to run instead.

Two reserved keys in a pose set shape keys and rig properties:

    [
      {},                                                  # rest
      {"@shape_keys": {"jawOpen": 1.0}},
      {"@shape_keys": {"jawOpen": 0.4, "mouthFunnel": 0.8},
       "@props": {"mouth_open": 0.5},
       "jaw": {"rotate": [12, 0, 0]}}
    ]

"@shape_keys" sets each named key on every rendered mesh that has a key by that
name.  Every shape key starts each pose at 0, so no row inherits the one above
it.  A value outside a key's slider range widens the range instead of being
clamped to it; Blender's limits are -10 and 10.  A key with a driver follows
its driver and ignores both.  The reference key, usually Basis, is the shape
the others are measured from, so its value does nothing and naming it is
reported.  The framing is measured once, before the first pose, so a key that
pushes the mesh past it is cut off at the cell's edge: raise --zoom.  A row
that changes only a face leaves the silhouette as it was, so --check compares
such a row with the first one pixel by pixel as well: it prints how many pixels
changed at each angle, and calls the row the rest pose repeated only when none
did.

"@props" sets a custom property on the armature object, or on its armature data
when that is where the property lives, and tags it so the depsgraph runs the
drivers that read it.  A property named in any pose starts each later pose at
the value the file gave it.  Properties on pose bones are not reached.  A
property an add-on saved can refuse a value of another type, such as a list
for a single number; the pose then renders with the property as it was.

Unknown shape keys and properties, and refused property values, are reported
like unknown bones, on the terminal and in the result.

A .blend is opened as saved instead of imported into an empty scene, because
an import keeps shape keys but not the drivers that connect rig properties to
them.  After loading, the parts of the file an import would not bring are set
aside: its lights, cameras and light probes are left out of the render; its
render, EEVEE and colour management settings go back to the factory ones an
import starts from; its compositor and sequencer are switched off; only the
active view layer renders; and holdouts are cleared.  An object is neither
framed nor rendered when it is hidden from render or from the camera, or sits
only in collections that are excluded from the view layer or switched off for
render, directly or through a parent collection.  What is left is framed and
lit like any other model.  Opening a .blend runs its Python-expression
drivers, so treat a .blend from someone else as code.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shlex
import shutil
import subprocess
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import container as _container, exec_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# Whichever profile is up: the packaged image names its container
# comfyui-packaged, the from-source one comfyui.
SVC = _container()

# Blender's hard limits on a shape key's slider range, and so on its value.
SHAPE_KEY_LIMIT = 10.0

# The Blender half. Runs inside the container; all input arrives as one JSON blob
# on argv so there is no quoting to get wrong.
BLENDER_SCRIPT = r'''
import bpy, json, math, sys, os
from mathutils import Vector, Euler

cfg = json.loads(sys.argv[-1])

# --- clean slate ------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)

path = cfg["model"]
ext = os.path.splitext(path)[1].lower()
is_blend = ext == ".blend"
if is_blend:
    # Opened, not imported: an import keeps shape keys but drops drivers and the
    # rig properties they read. The factory settings are copied first and put
    # back afterwards, so the file renders as an import would, not with the
    # resolution scale, look or ray tracing it happened to be saved with.
    def plain_settings(struct):
        values = {}
        for p in struct.bl_rna.properties:
            if p.is_readonly or p.type in ("POINTER", "COLLECTION"):
                continue
            v = getattr(struct, p.identifier)
            values[p.identifier] = v[:] if getattr(p, "is_array", False) else v
        return values
    factory = {k: plain_settings(getattr(bpy.context.scene, k))
               for k in ("render", "eevee", "view_settings", "display_settings")}
    bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    for k, values in factory.items():
        struct = getattr(bpy.context.scene, k)
        for name, v in values.items():
            try:
                setattr(struct, name, v)
            except Exception:
                pass
    # The factory settings leave the compositor and the sequencer on. An import
    # has no node tree and no strips, so they do nothing there; a file's own
    # would invert or replace every cell. Only the view layer framed below
    # renders.
    bpy.context.scene.render.use_compositing = False
    bpy.context.scene.render.use_sequencer = False
    bpy.context.scene.render.use_single_layer = True
    for ob in bpy.context.scene.objects:
        if ob.type in ("LIGHT", "CAMERA", "LIGHT_PROBE"):
            ob.hide_render = True
        # A holdout renders as a hole in the alpha, which an import never has.
        if ob.is_holdout:
            ob.is_holdout = False
    def clear_holdout(lc):
        if lc.holdout:
            lc.holdout = False
        if lc.indirect_only:
            lc.indirect_only = False
        for child in lc.children:
            clear_holdout(child)
    clear_holdout(bpy.context.view_layer.layer_collection)
elif ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=path)
elif ext in (".glb", ".gltf"):
    bpy.ops.import_scene.gltf(filepath=path)
elif ext == ".obj":
    bpy.ops.wm.obj_import(filepath=path)
else:
    raise SystemExit(f"unsupported model format: {ext}")

scene = bpy.context.scene
# The scene's own collection, not the active one: a .blend can be saved with an
# excluded collection active, and a camera linked there would not render.
coll = scene.collection

# A .blend can hold things nobody meant to see, such as a template head kept for
# reference. Only what renders is framed. An import has none of these. The view
# layer's object list still holds what sits in a collection switched off for
# render, so walk the collections: an excluded one, or one hidden from render,
# hides everything under it.
def rendered_objects(lc):
    if lc.exclude or lc.collection.hide_render:
        return set()
    found = set(lc.collection.objects)
    for child in lc.children:
        found |= rendered_objects(child)
    return found

layer_objects = rendered_objects(bpy.context.view_layer.layer_collection)
def renders(ob):
    return not is_blend or (ob in layer_objects and not ob.hide_render
                            and ob.visible_camera)

if is_blend:
    # What is not framed does not render either: a reference head kept out of
    # the camera's sight would still shadow the model.
    for ob in bpy.context.scene.objects:
        if ob.hide_render is False and not renders(ob):
            ob.hide_render = True

meshes = [o for o in bpy.data.objects if o.type == "MESH" and renders(o)]

# A shape-only mesh (Hunyuan3D ShapeGen, TripoSG) arrives with no material, and
# Blender's default is white, which against a white world light renders as a
# featureless blob.  Give anything untextured a mid-grey clay so form reads.
def has_texture(ob):
    for slot in ob.material_slots:
        m = slot.material
        if m and m.use_nodes and any(n.type == "TEX_IMAGE" for n in m.node_tree.nodes):
            return True
    return False

if cfg["clay"] or not any(has_texture(o) for o in meshes):
    clay = bpy.data.materials.new("clay")
    clay.use_nodes = True
    bsdf = clay.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = tuple(cfg["clay_color"]) + (1.0,)
    bsdf.inputs["Roughness"].default_value = 0.65
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.3
    for ob in meshes:
        ob.data.materials.clear()
        ob.data.materials.append(clay)
# The armature that deforms what renders comes first. A Rigify file also holds
# its metarig, which sorts before "rig" by name and deforms nothing.
armatures = []
for ob in meshes:
    for md in ob.modifiers:
        if md.type == "ARMATURE" and md.object and md.object not in armatures:
            armatures.append(md.object)
armatures = armatures or [o for o in bpy.data.objects if o.type == "ARMATURE"]
if not meshes:
    raise SystemExit("no mesh in that file renders: each is hidden from render or "
                     "from the camera, or in a collection that is excluded or "
                     "switched off for render" if is_blend and any(
                         o.type == "MESH" for o in bpy.data.objects)
                     else "no mesh in that file")

# --- frame the subject: normalise into a unit box centred on the origin ------
lo = Vector(( 1e9,  1e9,  1e9))
hi = Vector((-1e9, -1e9, -1e9))
for ob in meshes:
    for c in ob.bound_box:
        w = ob.matrix_world @ Vector(c)
        lo = Vector((min(lo[i], w[i]) for i in range(3)))
        hi = Vector((max(hi[i], w[i]) for i in range(3)))
# Fitted to THIS mesh unless a span is given, and that distinction is the
# one people get wrong. Per-model fit is right for looking at a prop on its
# own, or for baking an inventory icon -- a coin framed against a figure's
# height is a speck. It is wrong for a SET: fit every model to its own
# bounding box and a dagger and a golem fill their cells identically, which
# reaches the engine as every creature the same size on the map and is then
# hunted for in the wrong place.
size = max((hi - lo)[i] for i in range(3)) or 1.0
if cfg.get("span"):
    size = float(cfg["span"])
centre = (lo + hi) / 2.0
# Feet on the floor, not centre on the floor: sprites read better anchored low.
floor = lo.z

root = bpy.data.objects.new("rig_root", None)
coll.objects.link(root)
for ob in list(bpy.data.objects):
    if ob is not root and ob.parent is None:
        ob.parent = root
root.location = (-centre.x, -centre.y, -floor)

pivot = bpy.data.objects.new("pivot", None)
coll.objects.link(pivot)
root.parent = pivot

# --- camera: orthographic, so sprites of the same asset stay the same size ---
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO" if cfg["ortho"] else "PERSP"
cam_data.ortho_scale = size * cfg["zoom"]
cam = bpy.data.objects.new("cam", cam_data)
coll.objects.link(cam)
scene.camera = cam

elev = math.radians(cfg["elevation"])
dist = size * 3.0
cam.location = (0.0, -dist * math.cos(elev), size * 0.5 + dist * math.sin(elev))
cam.rotation_euler = Euler((math.radians(90.0) - elev, 0.0, 0.0), "XYZ")

# --- light: flat and even, so the sheet has no directional bias -------------
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = cfg["ambient"]
scene.world = world

key = bpy.data.lights.new("key", "SUN")
key.energy = cfg["key"]
key_ob = bpy.data.objects.new("key", key)
coll.objects.link(key_ob)
key_ob.rotation_euler = Euler((math.radians(55), 0, math.radians(30)), "XYZ")
key_ob.parent = cam            # light rides the camera: every facing lit alike

scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = scene.render.resolution_y = cfg["size"]
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"   # no filmic wash on flat art

# --- poses ------------------------------------------------------------------
arm = armatures[0] if armatures else None
missing = set()
missing_keys = set()
reference_keys = set()
missing_props = set()
refused_props = {}

# Every shape key on a rendered mesh, by name. One name can live on several
# meshes (face, brows, beard), and a pose sets it on all of them. The reference
# key (Basis) is the shape the others are measured from; its value does
# nothing, so a pose that names it is told so.
shape_keys = {}
reference_names = set()
for ob in meshes:
    if ob.data.shape_keys:
        reference = ob.data.shape_keys.reference_key
        for kb in ob.data.shape_keys.key_blocks:
            if kb == reference:
                reference_names.add(kb.name)
            else:
                shape_keys.setdefault(kb.name, []).append(kb)

prop_rest = {}   # (owner, name) -> the value the file gave it

def prop_owner(name):
    if arm is None:
        return None
    for owner in (arm, arm.data):
        if name in owner.keys():
            return owner
    return None

def apply_transforms(spec):
    # Shape keys and properties start every pose from rest, as bones do below,
    # so no row inherits anything from the row above it.
    for kbs in shape_keys.values():
        for kb in kbs:
            kb.value = 0.0
    for (owner, name), v in prop_rest.items():
        owner[name] = v
        owner.update_tag()
    for name, value in spec.get("@shape_keys", {}).items():
        if name not in shape_keys:
            (reference_keys if name in reference_names else missing_keys).add(name)
            continue
        for kb in shape_keys[name]:
            kb.slider_min = min(kb.slider_min, value)
            kb.slider_max = max(kb.slider_max, value)
            kb.value = value
    for name, value in spec.get("@props", {}).items():
        owner = prop_owner(name)
        if owner is None:
            missing_props.add(name)
            continue
        old = owner[name]
        if (owner, name) not in prop_rest:
            prop_rest[(owner, name)] = old.to_list() if hasattr(old, "to_list") else old
        if isinstance(old, float) and isinstance(value, int):
            value = float(value)      # 1 in JSON must not turn a float property into an int
        try:
            owner[name] = value
        except (TypeError, ValueError, OverflowError) as e:
            # A property an add-on saved keeps its type, and refuses another one.
            # One such value must not cost the whole sheet: report it, and
            # render the pose with the property as it was.
            refused_props.setdefault(name, str(e))
            continue
        # Assigning an ID property from Python tags nothing, and without a tag
        # the depsgraph leaves every driver that reads it where it was.
        owner.update_tag()
    if arm is None:
        return
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = Euler((0, 0, 0), "XYZ")
        pb.location = (0, 0, 0)
    for bone, t in spec.items():
        if bone in ("@shape_keys", "@props"):
            continue
        pb = arm.pose.bones.get(bone)
        if pb is None:
            missing.add(bone)
            continue
        if "rotate" in t:
            pb.rotation_euler = Euler([math.radians(a) for a in t["rotate"]], "XYZ")
        if "translate" in t:
            pb.location = t["translate"]

poses = []
for pose in cfg["poses"]:
    if pose["kind"] == "even":
        a, b = scene.frame_start, scene.frame_end
        n = max(1, pose["value"])
        step = max(1, (b - a) // n) if b > a else 1
        poses += [{"kind": "frame", "value": min(b, a + i * step)} for i in range(n)]
    else:
        poses.append(pose)

out = []
for pi, pose in enumerate(poses):
    if pose["kind"] == "frame":
        scene.frame_set(pose["value"])
    elif pose["kind"] == "transforms":
        apply_transforms(pose["value"])
    bpy.context.view_layer.update()

    for ai, az in enumerate(cfg["azimuths"]):
        pivot.rotation_euler = Euler((0, 0, math.radians(az)), "XYZ")
        bpy.context.view_layer.update()
        f = os.path.join(cfg["frames_dir"], f"pose{pi:02d}_ang{ai:02d}.png")
        scene.render.filepath = f
        bpy.ops.render.render(write_still=True)
        out.append(f)

print("RENDERED " + json.dumps({
    "frames": out,
    "rows": len(poses),
    "cols": len(cfg["azimuths"]),
    "armature": arm.name if arm else None,
    "bones": len(arm.pose.bones) if arm else 0,
    "missing_bones": sorted(missing),
    "shape_keys": len(shape_keys),
    "missing_shape_keys": sorted(missing_keys),
    "reference_shape_keys": sorted(reference_keys),
    "missing_props": sorted(missing_props),
    "refused_props": refused_props,
    "frame_range": [scene.frame_start, scene.frame_end],
}))
# A Python-expression driver anywhere in the session leaves the bpy module
# hanging at interpreter exit, after every frame is written. Leave directly.
sys.stdout.flush()
os._exit(0)
'''


def is_number(v) -> bool:
    """A finite JSON number. json.loads reads NaN and Infinity, and bool is an int."""
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def check_pose(path: Path, n: int, pose) -> None:
    """Refuse a malformed pose here, rather than as a traceback from Blender."""
    if not isinstance(pose, dict):
        raise SystemExit(f"{path}: pose {n} is not a JSON object")
    for bone, t in pose.items():
        if bone in ("@shape_keys", "@props"):
            continue
        if not isinstance(t, dict):
            kind = ("true or false" if isinstance(t, bool) else "a number"
                    if isinstance(t, (int, float)) else "a string" if isinstance(t, str)
                    else "a list" if isinstance(t, list) else "null")
            raise SystemExit(f"{path}: pose {n}: bone {bone!r} holds {kind}. Expected "
                             'an object such as {"rotate": [x, y, z]}')
        for field in ("rotate", "translate"):
            if field in t and not (isinstance(t[field], list) and len(t[field]) == 3
                                   and all(is_number(x) for x in t[field])):
                raise SystemExit(f"{path}: pose {n}: bone {bone!r} {field} is "
                                 f"{t[field]!r}. Expected a list of three numbers")
    keys = pose.get("@shape_keys", {})
    if not isinstance(keys, dict):
        raise SystemExit(f'{path}: pose {n}: "@shape_keys" must map shape key '
                         "names to values")
    for name, v in keys.items():
        if not is_number(v) or not -SHAPE_KEY_LIMIT <= v <= SHAPE_KEY_LIMIT:
            raise SystemExit(f"{path}: pose {n}: shape key {name!r} is {v!r}. "
                             f"Expected a number from {-SHAPE_KEY_LIMIT:g} to "
                             f"{SHAPE_KEY_LIMIT:g}, Blender's slider limits")
    props = pose.get("@props", {})
    if not isinstance(props, dict):
        raise SystemExit(f'{path}: pose {n}: "@props" must map property names '
                         "to values")
    for name, v in props.items():
        numbers = isinstance(v, list) and len(v) > 0 and all(is_number(x) for x in v)
        if not (isinstance(v, (bool, str)) or is_number(v) or numbers):
            raise SystemExit(f"{path}: pose {n}: property {name!r} is {v!r}. "
                             "Expected a number, true or false, a string or a "
                             "list of numbers")


def refuse_role_file(path: Path, model: Path, why: str) -> None:
    """A role pose file names roles, which only bone_roles.py compile turns into
    this rig's bone names. Rendering it would draw every row at rest."""
    def show(q: Path) -> str:
        q = q.resolve()
        return str(q.relative_to(ROOT)) if q.is_relative_to(ROOT) else str(q)
    compiled = f"output/poses/{model.stem}_{path.stem}.json"
    raise SystemExit(
        f"{show(path)}: {why}, so this is a role pose file, which names roles "
        "rather than this rig's bones. Compile it for the rig, then render the "
        "result:\n"
        f"  scripts/bone_roles.py compile {show(path)} {show(model)} --out {compiled}\n"
        f"  scripts/render_sheet.py {show(model)} --poses transforms:{compiled}")


def parse_poses(spec: str, model: Path) -> list[dict]:
    kind, _, arg = spec.partition(":")
    if kind == "static":
        return [{"kind": "frame", "value": 1}]
    if kind == "frames":
        return [{"kind": "frame", "value": int(f)} for f in arg.split(",")]
    if kind == "even":
        n = int(arg)
        # Resolved container-side once the action's real range is known; a
        # placeholder here would guess wrong for every clip.
        return [{"kind": "even", "value": n}]
    if kind == "transforms":
        p = Path(arg)
        if not p.is_absolute():
            p = ROOT / p
        data = json.loads(p.read_text())
        if not isinstance(data, list):
            raise SystemExit(f"{p}: expected a JSON list of poses")
        if p.resolve().is_relative_to((ROOT / "poses" / "roles").resolve()):
            refuse_role_file(p, model, "it is in poses/roles/")
        for n, pose in enumerate(data, 1):
            note = next((k for k, v in pose.items() if k.startswith("_")
                         and not isinstance(v, dict)), None) \
                if isinstance(pose, dict) else None
            if note:
                refuse_role_file(p, model, f"pose {n} holds {note!r}, and keys "
                                 "starting with _ are notes in a role pose file")
            check_pose(p, n, pose)
        return [{"kind": "transforms", "value": d} for d in data]
    raise SystemExit(f"--poses: unknown kind {kind!r} "
                     "(static | frames:1,5,9 | even:4 | transforms:FILE)")


def to_container(p: Path) -> str:
    """Host path under the project -> the path the container sees."""
    p = p.resolve()
    for host, cont in ((ROOT / "output", "/app/output"),
                       (ROOT / "input", "/app/input"),
                       (ROOT / "workflows", "/app/user")):
        try:
            return f"{cont}/{p.relative_to(host)}"
        except ValueError:
            continue
    return str(p)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", type=Path,
                    help=".fbx (rigged/animated), .glb, .obj, or a .blend, which "
                         "is opened as saved so its drivers and rig properties work")
    ap.add_argument("--poses", default="static",
                    help="static | frames:1,5,9 | even:N | transforms:FILE. A "
                         'transforms pose may also hold "@shape_keys" and "@props"')
    ap.add_argument("--angles", type=int, default=4,
                    help="azimuths around the subject (default 4: front/right/back/left)")
    ap.add_argument("--azimuth-start", type=float, default=45.0,
                    help="degrees of the first facing. Default 45, which is what a "
                         "2:1 isometric grid needs")
    ap.add_argument("--elevation", type=float, default=30.0,
                    help="camera elevation. Default 30 matches a 2:1 dimetric grid")
    ap.add_argument("--flat", action="store_true",
                    help="render square-on (elevation 30, azimuth from 0) instead of "
                         "on the isometric diagonal. For look-dev, not for sprites")
    ap.add_argument("--size", type=int, default=256, help="pixels per cell")
    ap.add_argument("--zoom", type=float, default=1.15,
                    help="ortho scale as a multiple of the subject's largest extent")
    ap.add_argument("--persp", action="store_true",
                    help="perspective camera. The default is orthographic, "
                         "which keeps one asset the same size across angles "
                         "and frames -- NOT across assets, see --span")
    ap.add_argument("--span", type=float, default=0.0, metavar="UNITS",
                    help="frame against this fixed world height instead of "
                         "the subject's own extent, so a set of assets shares "
                         "a scale and a golem looms over a goblin")
    ap.add_argument("--key", type=float, default=1.6, help="sun strength")
    ap.add_argument("--ambient", type=float, default=0.22, help="world light strength")
    ap.add_argument("--clay", action="store_true",
                    help="force the clay material even on a textured mesh")
    ap.add_argument("--clay-color", default="0.55,0.54,0.52",
                    help="clay RGB, 0-1, comma separated")
    ap.add_argument("--out", type=Path, help="sheet png (default: alongside the model)")
    ap.add_argument("--check", action="store_true",
                    help="run scripts/sheet_check.py on the composed sheet. It "
                         "knows the cell size and azimuths from this run, so it "
                         "can also name the down-and-right facing. A row that "
                         "keeps the first row's silhouette is compared pixel by "
                         "pixel, so a face-only row is reported, not failed")
    ap.add_argument("--keep-frames", action="store_true",
                    help="keep the per-cell PNGs under output/_sheet_frames/ "
                         "instead of deleting them once the sheet is composed")
    ap.add_argument("--timeout", type=int, default=1800,
                    help="seconds before Blender is stopped inside the container "
                         "(default 1800). A hung render otherwise hangs forever")
    args = ap.parse_args()

    model = args.model if args.model.is_absolute() else ROOT / args.model
    if not model.exists():
        return int(bool(sys.stderr.write(f"no such model: {model}\n")))

    poses = parse_poses(args.poses, model)
    # A 2:1 dimetric grid (tile 64 wide by 32 high, so screen =
    # ((u-v)*32, (u+v)*16)).  A ground vector's vertical
    # screen component is sin(elevation), and tile height / tile width = 0.5, so
    # the camera sits at exactly 30 degrees.  It looks down the diagonal BETWEEN
    # the world axes, so a figure facing along a world axis (north/east/south/
    # west) must be rendered at 45/135/225/315, not 0/90/180/270. Otherwise the
    # sprite faces square-on while the ground runs diagonally under it.
    start = 0.0 if args.flat else args.azimuth_start
    azimuths = [start + i * (360.0 / args.angles) for i in range(args.angles)]
    # Unique per run: a fixed shared directory means two renders running at the
    # same time interleave their frames and each composes a sheet containing the
    # other's model. Seen for real when a batch render overlapped a manual one.
    run_id = f"{os.getpid()}_{int(time.time())}"
    frames_dir = f"/app/output/_sheet_frames/{run_id}"

    cfg = {
        "model": to_container(model),
        "poses": poses,
        "azimuths": azimuths,
        "elevation": args.elevation,
        "size": args.size,
        "zoom": args.zoom,
        "span": args.span,
        "ortho": not args.persp,
        "key": args.key,
        "ambient": args.ambient,
        "frames_dir": frames_dir,
        "clay": args.clay,
        "clay_color": [float(x) for x in args.clay_color.split(",")],
    }

    print(f"  model   {cfg['model']}")
    print(f"  poses   {args.poses}  ({len(poses)} row(s))")
    print(f"  angles  {', '.join(f'{a:g}' for a in azimuths)}")

    script = (f"import os; os.makedirs({frames_dir!r}, exist_ok=True)\n"
              + BLENDER_SCRIPT)
    info = exec_json(script, cfg, "RENDERED ", timeout=args.timeout)
    if info is None:
        if not args.keep_frames:
            # A failed or stopped render still made its frames folder.
            shutil.rmtree(ROOT / "output" / "_sheet_frames" / run_id, ignore_errors=True)
        return 1
    info["run_id"] = run_id
    if info["missing_bones"]:
        print(f"  ! bones not in the rig: {', '.join(info['missing_bones'])}")
    if info["missing_shape_keys"]:
        print(f"  ! shape keys on no rendered mesh: "
              f"{', '.join(info['missing_shape_keys'])}")
    if info["reference_shape_keys"]:
        print(f"  ! reference shape keys, whose value does nothing: "
              f"{', '.join(info['reference_shape_keys'])}")
    if info["missing_props"]:
        print(f"  ! properties on neither the armature nor its data: "
              f"{', '.join(info['missing_props'])}")
    for name, error in info["refused_props"].items():
        print(f"  ! property {name} kept its value, because Blender refused the "
              f"new one: {error}")
    if info["armature"]:
        print(f"  rig     {info['armature']} ({info['bones']} bones), "
              f"frames {info['frame_range'][0]}-{info['frame_range'][1]}")
    else:
        print("  rig     none (static mesh)")
    if info["shape_keys"]:
        print(f"  shapes  {info['shape_keys']} shape key name(s)")

    out = args.out or model.with_suffix("").with_name(model.stem + "_sheet.png")
    if not out.is_absolute():
        out = ROOT / out
    compose(info, args.size, out)

    rc = 0
    if args.check:
        # Runs here rather than being left to the caller because this is where
        # the cell size and the azimuth list already exist. Asking a human to
        # supply them is how the arithmetic checks got done by eye instead.
        from sheet_check import slice_sheet, check as sheet_checks
        cells, rows, cols = slice_sheet(out, args.size)
        findings, facts = sheet_checks(cells, rows, cols, azimuths)
        print()
        for f in facts:
            print(f"  {f}")
        for f in findings:
            print(f"  ! {f}")
        if findings:
            print("  ! the sheet has faults above. Look at it before using it.")
            rc = 1

    if not args.keep_frames:
        # The per-run directory exists so two concurrent renders cannot
        # interleave their frames. Once composed it is scratch, and nothing
        # used to delete it -- they accumulated one per run, indefinitely.
        shutil.rmtree(ROOT / "output" / "_sheet_frames" / info["run_id"],
                      ignore_errors=True)
    return rc


def compose(info: dict, cell: int, out: Path) -> None:
    from PIL import Image
    rows, cols = info["rows"], info["cols"]
    sheet = Image.new("RGBA", (cols * cell, rows * cell), (0, 0, 0, 0))
    host_frames = ROOT / "output" / "_sheet_frames" / info["run_id"]
    for i, f in enumerate(info["frames"]):
        p = host_frames / Path(f).name
        if not p.exists():
            continue
        sheet.paste(Image.open(p).convert("RGBA"), ((i % cols) * cell, (i // cols) * cell))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"  sheet   {out}  ({cols}x{rows} cells of {cell}px)")


if __name__ == "__main__":
    sys.exit(main())

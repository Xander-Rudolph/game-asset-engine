#!/usr/bin/env python3
"""Give a generated rig a face: a jaw bone, and shape keys from a template head.

UniRig's articulationxl rigs have no jaw, eye or mouth bones and no shape keys
(docs/reference/lip-sync.md, "Faces on generated meshes").  This adds the two
face parts Blender can make without a person: a jaw bone placed and weighted by
rule, and shape keys carried over from a template head with the Surface Deform
modifier.  Both run Blender (the `bpy` module) inside the ComfyUI container.

    # a jaw on a rigged character, on the bone the script takes for the head
    scripts/face_rig.py add-jaw output/rigged/unit_alchemist.fbx \\
        --out output/face_rig/alchemist_jaw.blend

    # name the head bone yourself, and write an FBX
    scripts/face_rig.py add-jaw output/rigged/unit_alchemist.fbx --head bone_4 \\
        --out output/face_rig/alchemist_jaw.fbx

    # then open the jaw in the second row of a sheet
    scripts/render_sheet.py output/face_rig/alchemist_jaw.blend \\
        --poses transforms:output/face_rig/jaw20.json

    # write a test template and targets: the spheres the method was proved on
    scripts/face_rig.py spheres --out-dir output/face_rig/spheres

    # borrow the template's shape keys
    scripts/face_rig.py transfer-shapes output/face_rig/spheres/template.blend \\
        output/face_rig/spheres/target.blend --out output/face_rig/spheres/target_keys.blend

    # a jaw on the rigged sphere, then its jawOpen on head vertices only
    scripts/face_rig.py add-jaw output/face_rig/spheres/rigged_sphere.blend \\
        --out output/face_rig/spheres/rigged_sphere_jaw.blend
    scripts/face_rig.py transfer-shapes output/face_rig/spheres/template.blend \\
        output/face_rig/spheres/rigged_sphere_jaw.blend --region --keys jawOpen \\
        --out output/face_rig/spheres/rigged_sphere_face.blend

    # a template that cannot bind, to see the failure
    scripts/face_rig.py transfer-shapes output/face_rig/spheres/bad_template.blend \\
        output/face_rig/spheres/target.blend --out output/face_rig/spheres/never.blend

where output/face_rig/jaw20.json holds [{}, {"jaw": {"rotate": [20, 0, 0]}}].
output/rigged/unit_alchemist.fbx is a UniRig articulationxl rig; any rigged
.fbx, .glb or .blend will do.

add-jaw
    The search starts at the topmost bone, by tail height, on the chain that
    climbs from the root, following at each bone the child whose tail is
    highest.  Generated weights do not always agree with the bones: on three of
    the five articulationxl rigs tried, that bone is the heaviest weight on 5
    vertices or fewer, and its parent on every vertex of the upper head.  So
    the head is the bone, from the topmost one down, that is the heaviest
    weight on the most of the highest 2% of vertices the chain moves.  The
    chain and that count are printed: check them, and pass --head when the
    pick is wrong.  Here and below, "heaviest weight" is among the groups named
    after the armature's deform bones; other groups a mesh carries, such as
    MakeHuman's Left and Right halves, are not weights.

    The rule was first measured on a unit sphere.  The vertices whose heaviest
    weight is the head bone give a box with a height H, a depth D from back to
    front and a centre C.  The jaw pivots 0.15 D behind and 0.15 H below C, and
    its tail sits 0.45 D in front of and 0.3 H below C, towards the chin.
    Vertices the head bone weights at all, inside the box, below the pivot and
    no more than 0.05 D behind C take jaw weight, fading in linearly over 0.15 H
    below the pivot, which on a sphere of radius 1 is the 0.3 unit fade the
    probe used.  The jaw takes that share of each vertex's head weight and the
    head keeps the rest, so no vertex's total weight changes.

    Rotate the jaw about its own X axis; a positive angle opens it.  The front
    is -Y, which is where Blender's front view looks from; pass --front for a
    model facing another way.  Before writing, the jaw is turned 20 degrees:
    when no vertex moves more than 0.5% of H, or the ones that do rise on
    average, it says so and writes nothing.  A generated mesh has no parted lips, so the jaw stretches
    the lower face down rather than opening a mouth.

transfer-shapes
    The template mesh with the most shape keys (or --template-mesh) is bound to
    each mesh of the model with Surface Deform, as both stand: nothing moves or
    scales the template, so it must already sit on the model's surface.  Each
    template key is set to 1 on its own and applied to the model with "apply as
    shape key".  The new key takes the modifier's name, so it is renamed to the
    template key's; a key of that name already on the model is replaced.

    --region limits the deformation to head vertices: the weights of the head
    bone and every bone below it, such as a jaw added first.

    Each key's largest displacement, and how many vertices it moves, are
    printed in world units, parent scale included.

    The bind's restrictions fall on the template: no edges shared by more than
    two faces, no concave faces, no doubled vertices and no faces with collinear
    edges.  A failed bind prints them, and Blender's own reason.

spheres
    Writes four files into --out-dir.  template.blend is a UV sphere of radius
    1 with a jawOpen key that lowers every vertex below z -0.2 by 0.3.
    target.blend is an ico sphere of radius 1.05, a different topology, with no
    keys.  rigged_sphere.blend is that ico sphere weighted wholly to one bone,
    head, which runs up the Z axis.  bad_template.blend is the template with one
    more face on an edge, so that edge has three faces and the bind fails.

Output is a .blend, which keeps everything, or an .fbx, which keeps the bones,
weights and shape keys.  Opening a .blend runs its Python-expression drivers,
so treat a .blend from someone else as code.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import exec_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SENTINEL = "FACE_RIG "
MOUNTS = ((ROOT / "output", "/app/output"), (ROOT / "input", "/app/input"))

# Quoted from docs/reference/lip-sync.md, "What Blender does headlessly", which
# takes them from the Blender manual's Surface Deform page.
BIND_RESTRICTIONS = (
    "The bind's restrictions fall on the template: no edges shared by more than "
    "two faces, no concave faces, no doubled vertices and no faces with collinear "
    "edges.")

# Shared by both subcommands. Runs inside the container, with the whole
# configuration as one JSON blob on argv.
COMMON = r'''
import bpy, json, math, os, sys
from mathutils import Vector

cfg = json.loads(sys.argv[-1])
UP = Vector((0.0, 0.0, 1.0))
FRONTS = {"-y": (0, -1, 0), "+y": (0, 1, 0), "-x": (-1, 0, 0), "+x": (1, 0, 0)}

def finish(result):
    # A Python-expression driver anywhere in the session leaves the bpy module
    # hanging at interpreter exit, after the work is done. Leave directly.
    print("FACE_RIG " + json.dumps(result))
    sys.stdout.flush()
    os._exit(0)

def fail(message, **extra):
    finish(dict(extra, error=message))

def import_file(path):
    """Bring a file's objects into the current scene."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".blend":
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.objects = list(src.objects)
        for ob in dst.objects:
            if ob is not None:
                bpy.context.scene.collection.objects.link(ob)
    else:
        fail(f"unsupported model format: {ext}")

def load_model(path):
    if path.lower().endswith(".blend"):
        bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
    else:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        import_file(path)
    return list(bpy.context.scene.objects)

def deforming_armature(meshes):
    for ob in meshes:
        for md in ob.modifiers:
            if md.type == "ARMATURE" and md.object is not None:
                return md.object
    return None

def skinned(arm, objects):
    return [o for o in objects if o.type == "MESH" and any(
        md.type == "ARMATURE" and md.object == arm for md in o.modifiers)]

def deform_bones(arm):
    return {b.name for b in arm.data.bones if b.use_deform}

def heaviest(meshes, bones):
    """(object, vertex index, world position, name of its heaviest bone) per weighted vertex.

    Only groups named after the given bones count. A mesh can carry other groups,
    such as MakeHuman's Left and Right halves, which would outweigh the head on
    most of it.
    """
    out = []
    for ob in meshes:
        index = {g.index: g.name for g in ob.vertex_groups if g.name in bones}
        mw = ob.matrix_world
        for v in ob.data.vertices:
            best = max((e for e in v.groups if e.group in index), key=lambda e: e.weight,
                       default=None)
            if best is not None and best.weight > 0.0:
                out.append((ob, v.index, mw @ v.co, index[best.group]))
    return out

def find_head(arm, meshes, name):
    """The head bone, and a report of how it was chosen."""
    bones = arm.data.bones
    if name:
        if name not in bones:
            fail(f"no bone named {name!r} in {arm.name}",
                 bones=[b.name for b in bones])
        return bones[name], {"chain": []}
    tail_z = lambda b: (arm.matrix_world @ b.tail_local).z
    roots = [b for b in bones if b.parent is None]
    if not roots:
        fail(f"{arm.name} has no bones")
    chain = [max(roots, key=lambda b: len(b.children_recursive))]
    while chain[-1].children:
        chain.append(max(chain[-1].children, key=tail_z))
    topmost = max(chain, key=tail_z)
    below = chain[:chain.index(topmost) + 1]
    names = [b.name for b in below]
    # The topmost bone is not always the one that carries the head. On three of
    # the five articulationxl rigs tried, it weights no vertex at 0.6 or more and
    # its parent is the heaviest influence on the whole head. So look at the
    # highest vertices the chain moves, and take the bone heaviest on most.
    on_chain = [h for h in heaviest(meshes, deform_bones(arm)) if h[3] in names]
    if not on_chain:
        fail("no bone on the chain from the root weights any vertex; pass --head",
             chain=[b.name for b in chain])
    on_chain.sort(key=lambda h: h[2].z, reverse=True)
    top = on_chain[:max(1, len(on_chain) // 50)]
    counts = {n: sum(1 for h in top if h[3] == n) for n in names}
    head = max(reversed(below), key=lambda b: counts[b.name])
    return head, {"chain": [b.name for b in chain], "topmost": topmost.name,
                  "top_vertices": len(top), "top_counts": {n: c for n, c in counts.items() if c}}

def region_weights(ob, bone_names):
    """Vertex index -> summed weight of the named bones' groups, capped at 1."""
    groups = {g.index for g in ob.vertex_groups if g.name in bone_names}
    out = {}
    for v in ob.data.vertices:
        w = sum(e.weight for e in v.groups if e.group in groups)
        if w > 0.0:
            out[v.index] = min(1.0, w)
    return out

def blender_output(fn):
    """Run fn and return what Blender's C code printed meanwhile."""
    import ctypes, tempfile
    libc = ctypes.CDLL(None)
    sys.stdout.flush()
    libc.fflush(None)
    saved = os.dup(1)
    with tempfile.TemporaryFile() as tmp:
        os.dup2(tmp.fileno(), 1)
        try:
            fn()
        finally:
            libc.fflush(None)
            os.dup2(saved, 1)
            os.close(saved)
        tmp.seek(0)
        return tmp.read().decode("utf-8", "replace")

def save(path):
    ext = os.path.splitext(path)[1].lower()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if ext == ".blend":
        try:
            bpy.ops.file.pack_all()
        except RuntimeError:
            pass
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=path)
    elif ext == ".fbx":
        bpy.ops.export_scene.fbx(filepath=path, use_selection=False,
                                 object_types={"ARMATURE", "MESH"},
                                 add_leaf_bones=False, bake_anim=False,
                                 path_mode="COPY", embed_textures=True)
    else:
        fail(f"--out must end in .blend or .fbx, not {ext}")
'''

ADD_JAW = COMMON + r'''
objects = load_model(cfg["model"])
arm = deforming_armature([o for o in objects if o.type == "MESH"])
if arm is None:
    fail("no armature deforms a mesh in that file, so there is no head to hang a jaw on")
meshes = skinned(arm, objects)
if cfg["name"] in arm.data.bones:
    fail(f"{arm.name} already has a bone named {cfg['name']!r}; pass --name")
bones_before = len(arm.data.bones)
head, how = find_head(arm, meshes, cfg["head"])
chain = how["chain"]
# Edit mode rebuilds the bones, and a Bone held across it points at freed memory.
head_name = head.name

F = Vector(FRONTS[cfg["front"]])
S = F.cross(UP)
region = []                       # (object, vertex index, world position, head weight)
for ob in meshes:
    g = ob.vertex_groups.get(head_name)
    if g is None:
        continue
    mw = ob.matrix_world
    for v in ob.data.vertices:
        for e in v.groups:
            if e.group == g.index and e.weight > 0.0:
                region.append((ob, v.index, mw @ v.co, e.weight))
if not region:
    fail(f"bone {head_name} weights no vertex", chain=chain)

# The head's box comes from the vertices whose heaviest influence is the head.
# Generated weights are soft: a head bone can reach the chest at a few percent.
box = ([h[2] for h in heaviest(meshes, deform_bones(arm)) if h[3] == head_name]
       or [r[2] for r in region])
def extent(axis):
    values = [co.dot(axis) for co in box]
    return min(values), max(values)
(s0, s1), (f0, f1), (u0, u1) = extent(S), extent(F), extent(UP)
H, D = u1 - u0, f1 - f0
C = S * ((s0 + s1) / 2) + F * ((f0 + f1) / 2) + UP * ((u0 + u1) / 2)
pivot = C - F * (0.15 * D) - UP * (0.15 * H)
tail = C + F * (0.45 * D) - UP * (0.30 * H)
fade = 0.15 * H

# --- the bone ------------------------------------------------------------------
for ob in bpy.context.view_layer.objects:
    ob.select_set(False)
arm.hide_set(False)
arm.hide_viewport = False
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
inv = arm.matrix_world.inverted()
eb = arm.data.edit_bones.new(cfg["name"])
eb.head = inv @ pivot
eb.tail = inv @ tail
eb.parent = arm.data.edit_bones[head_name]
eb.use_connect = False
eb.use_deform = True
# Roll the bone so its Z axis points down and back, square to the bone. A
# positive X rotation then swings the tail towards Z: the chin drops.
along = (tail - pivot).normalized()
down = -UP
square = (down - along * down.dot(along)).normalized()
eb.align_roll(arm.matrix_world.to_3x3().inverted() @ square)
bpy.ops.object.mode_set(mode="OBJECT")

# --- the weights ---------------------------------------------------------------
weighted = {}
for ob, index, co, hw in region:
    below = (pivot - co).dot(UP)
    if below <= 0.0 or (co - C).dot(F) < -0.05 * D:
        continue
    if co.dot(UP) < u0 or not s0 <= co.dot(S) <= s1:
        continue                  # outside the head's box: a shoulder, the chest
    share = min(1.0, below / fade)
    jaw_group = ob.vertex_groups.get(cfg["name"]) or ob.vertex_groups.new(name=cfg["name"])
    ob.vertex_groups[head_name].add([index], hw * (1.0 - share), "REPLACE")
    jaw_group.add([index], hw * share, "REPLACE")
    weighted[ob.name] = weighted.get(ob.name, 0) + 1
if not weighted:
    fail("no head vertex lies below and in front of the pivot; check --front and --head",
         head=head_name, chain=chain)

# --- check that it opens, then put it back -------------------------------------
pb = arm.pose.bones[cfg["name"]]
pb.rotation_mode = "XYZ"
dg = bpy.context.evaluated_depsgraph_get()
def evaluated():
    bpy.context.view_layer.update()
    return {ob.name: [ob.matrix_world @ v.co for v in ob.evaluated_get(dg).data.vertices]
            for ob in meshes if ob.name in weighted}
rest = evaluated()
pb.rotation_euler = (math.radians(20.0), 0.0, 0.0)
opened = evaluated()
pb.rotation_euler = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()
eps = 0.005 * H
moved, drop, lowest = 0, 0.0, 0.0
for name, before in rest.items():
    for a, b in zip(before, opened[name]):
        if (b - a).length > eps:
            moved += 1
            drop += (b - a).dot(UP)
            lowest = min(lowest, (b - a).dot(UP))

report = {
    "armature": arm.name, "bones": bones_before, "head": head_name, "chain": chain,
    "topmost": how.get("topmost"), "top_vertices": how.get("top_vertices"),
    "top_counts": how.get("top_counts"),
    "jaw": cfg["name"], "front": cfg["front"],
    "head_vertices": len(region), "box_vertices": len(box),
    "head_height": H, "head_depth": D,
    "pivot": list(pivot), "tail": list(tail), "fade": fade,
    "jaw_weighted": weighted,
    "moved_at_20": moved, "moved_threshold": eps,
    "mean_rise_of_moved": drop / moved if moved else 0.0, "largest_drop": lowest,
    "out": cfg["out"],
}
# Checked before anything is written, so a jaw that does not open leaves no file.
if moved == 0:
    fail("nothing moved when the jaw turned: the weights did not take", **report)
if drop >= 0:
    fail("the chin rose instead of dropping at +20 degrees; check --front", **report)
save(cfg["out"])
finish(report)
'''

TRANSFER = COMMON + r'''
import numpy as np

objects = load_model(cfg["model"])
before = set(bpy.data.objects)
import_file(cfg["template"])
added = [o for o in bpy.data.objects if o not in before]
keyed = [o for o in added if o.type == "MESH" and o.data.shape_keys
         and len(o.data.shape_keys.key_blocks) > 1]
if cfg["template_mesh"]:
    keyed = [o for o in keyed if o.name == cfg["template_mesh"]]
if not keyed:
    fail("no mesh with shape keys in the template" + (
         f" named {cfg['template_mesh']!r}" if cfg["template_mesh"] else ""),
         template_meshes=[o.name for o in added if o.type == "MESH"])
tmpl = max(keyed, key=lambda o: len(o.data.shape_keys.key_blocks))
reference = tmpl.data.shape_keys.reference_key
keys = [kb for kb in tmpl.data.shape_keys.key_blocks if kb != reference]
if cfg["keys"]:
    unknown = [k for k in cfg["keys"] if k not in tmpl.data.shape_keys.key_blocks]
    if unknown:
        fail(f"the template has no key named {', '.join(unknown)}",
             template_keys=[kb.name for kb in keys])
    keys = [kb for kb in keys if kb.name in cfg["keys"]]

targets = [o for o in objects if o.type == "MESH"]
if cfg["target"]:
    targets = [o for o in targets if o.name in cfg["target"]]
if not targets:
    fail("no target mesh in the model", meshes=[o.name for o in objects if o.type == "MESH"])

region_bones, head_name = None, None
if cfg["region"]:
    arm = deforming_armature(targets)
    if arm is None:
        fail("--region needs an armature that deforms the model, to find the head")
    targets = skinned(arm, targets)
    head, _ = find_head(arm, targets, cfg["head"])
    head_name = head.name
    region_bones = {head.name} | {b.name for b in head.children_recursive}
    heads = [h[2].z for h in heaviest(targets, deform_bones(arm)) if h[3] in region_bones]
    head_height = (max(heads) - min(heads)) if heads else 0.0

for kb in keys:
    kb.value = 0.0
results, BIND = [], "face_rig_bind"
for tgt in targets:
    if not tgt.data.polygons:
        continue
    n = len(tgt.data.vertices)
    saved = {}
    if tgt.data.shape_keys:
        for kb in tgt.data.shape_keys.key_blocks:
            saved[kb.name] = kb.value
            kb.value = 0.0
    group, inside = None, None
    if region_bones:
        weights = region_weights(tgt, region_bones)
        if not weights:
            continue
        group = tgt.vertex_groups.new(name="face_rig_region")
        for index, w in weights.items():
            group.add([index], w, "REPLACE")
        inside = np.zeros(n, dtype=bool)
        inside[list(weights)] = True

    mod = tgt.modifiers.new(BIND, "SURFACE_DEFORM")
    mod.target = tmpl
    if group is not None:
        mod.vertex_group = group.name
        mod.use_sparse_bind = True
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    tgt.select_set(True)
    bpy.context.view_layer.objects.active = tgt
    bpy.ops.object.modifier_move_to_index(modifier=BIND, index=0)
    def bind():
        bpy.ops.object.surfacedeform_bind(modifier=BIND)
        bpy.context.view_layer.update()
    said = blender_output(bind)
    if not tgt.modifiers[BIND].is_bound:
        # The operator reports FINISHED either way. The reason only reaches the
        # log, as "BKE_modifier_set_error: Object: ..., Modifier: ..., <reason>".
        reasons = sorted({line.split(f'Modifier: "{BIND}", ', 1)[1].strip()
                          for line in said.splitlines()
                          if "BKE_modifier_set_error" in line and f'Modifier: "{BIND}", ' in line})
        fail(f"Surface Deform could not bind {tgt.name} to the template mesh {tmpl.name}",
             bind_failed=True, reasons=reasons, target=tgt.name, template=tmpl.name)

    # "Moved" means more than 0.5% of the head's height with --region, else of
    # the mesh's largest extent: 0.01 on the probe's sphere, as it counted. Both,
    # and the displacements, are in world units, so a mesh under a scaled parent
    # (an FBX armature at 0.01) is measured as it stands.
    to_world = np.array(tgt.matrix_world.to_3x3())
    corners = np.array([list(tgt.matrix_world @ Vector(c)) for c in tgt.bound_box])
    extent = float((corners.max(axis=0) - corners.min(axis=0)).max())
    size = (head_height if region_bones and head_height else extent) or 1.0
    eps = 0.005 * size
    done = []
    for kb in keys:
        kb.value = 1.0
        bpy.context.view_layer.update()
        if tgt.data.shape_keys and kb.name in tgt.data.shape_keys.key_blocks:
            tgt.shape_key_remove(tgt.data.shape_keys.key_blocks[kb.name])
        bpy.ops.object.modifier_apply_as_shapekey(modifier=BIND, keep_modifier=True)
        new = tgt.data.shape_keys.key_blocks[-1]
        new.name = kb.name           # it arrives named after the modifier
        new.value = 0.0
        kb.value = 0.0
        base = np.empty(n * 3)
        moved_co = np.empty(n * 3)
        tgt.data.shape_keys.reference_key.data.foreach_get("co", base)
        new.data.foreach_get("co", moved_co)
        dist = np.linalg.norm((moved_co - base).reshape(-1, 3) @ to_world.T, axis=1)
        entry = {"key": kb.name, "max_displacement": float(dist.max()),
                 "moved": int((dist > eps).sum())}
        if inside is not None:
            entry["max_outside_region"] = float(dist[~inside].max()) if (~inside).any() else 0.0
        done.append(entry)
    bpy.ops.object.modifier_remove(modifier=BIND)
    if group is not None:
        tgt.vertex_groups.remove(group)
    for name, v in saved.items():
        if name in tgt.data.shape_keys.key_blocks:
            tgt.data.shape_keys.key_blocks[name].value = v
    results.append({"target": tgt.name, "vertices": n, "moved_threshold": eps, "keys": done})

if not results:
    fail("no target mesh had head vertices to bind" if region_bones else "no target mesh to bind")
summary = {"template": tmpl.name, "template_vertices": len(tmpl.data.vertices),
           "head": head_name, "targets": results, "out": cfg["out"]}
for ob in added:
    bpy.data.objects.remove(ob, do_unlink=True)
save(cfg["out"])
finish(summary)
'''


SPHERES = COMMON + r'''
import bmesh

def empty_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def add_jaw_open(ob):
    ob.shape_key_add(name="Basis")
    key = ob.shape_key_add(name="jawOpen")
    for v in ob.data.vertices:
        if v.co.z < -0.2:
            key.data[v.index].co = v.co + Vector((0.0, 0.0, -0.3))

made = {}
def write(name, ob):
    path = os.path.join(cfg["out_dir"], name + ".blend")
    save(path)
    made[name] = {"vertices": len(ob.data.vertices), "faces": len(ob.data.polygons),
                  "keys": [kb.name for kb in ob.data.shape_keys.key_blocks]
                          if ob.data.shape_keys else []}

empty_scene()
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1.0)
ob = bpy.context.active_object
ob.name = "template"
add_jaw_open(ob)
write("template", ob)

empty_scene()
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1.05)
ob = bpy.context.active_object
ob.name = "target"
write("target", ob)

empty_scene()
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1.05)
ob = bpy.context.active_object
ob.name = "sphere"
arm = bpy.data.objects.new("arm", bpy.data.armatures.new("arm"))
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
bone = arm.data.edit_bones.new("head")
bone.head, bone.tail = (0.0, 0.0, -1.2), (0.0, 0.0, 1.0)
bpy.ops.object.mode_set(mode="OBJECT")
ob.vertex_groups.new(name="head").add([v.index for v in ob.data.vertices], 1.0, "REPLACE")
ob.modifiers.new("arm", "ARMATURE").object = arm
ob.parent = arm
write("rigged_sphere", ob)

empty_scene()
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1.0)
ob = bpy.context.active_object
ob.name = "bad_template"
bm = bmesh.new()
bm.from_mesh(ob.data)
edge = next(e for e in bm.edges if len(e.link_faces) == 2 and abs(e.verts[0].co.z) < 0.1)
a, b = edge.verts
bm.faces.new((a, b, bm.verts.new((a.co + b.co) / 2 * 1.3)))
three = len(edge.link_faces)
bm.to_mesh(ob.data)
bm.free()
add_jaw_open(ob)
write("bad_template", ob)
finish({"out_dir": cfg["out_dir"], "files": made, "faces_on_bad_edge": three})
'''


def to_container(p: Path) -> str | None:
    """Host path -> container path, or None when the container cannot see it."""
    p = p if p.is_absolute() else ROOT / p
    p = p.resolve()
    for host, cont in MOUNTS:
        try:
            return f"{cont}/{p.relative_to(host)}"
        except ValueError:
            continue
    return None


def container_paths(args, *names: str) -> dict | None:
    out = {}
    for name in names:
        p = getattr(args, name)
        c = to_container(p)
        if c is None:
            sys.stderr.write(f"{p}: the container only sees output/ and input/, "
                             "so the file must be under one of them\n")
            return None
        if name != "out" and not (ROOT / p if not p.is_absolute() else p).exists():
            sys.stderr.write(f"no such file: {p}\n")
            return None
        out[name] = c
    if Path(out["out"]).suffix.lower() not in (".blend", ".fbx"):
        sys.stderr.write(f"--out must end in .blend or .fbx: {args.out}\n")
        return None
    return out


def add_jaw(args) -> int:
    paths = container_paths(args, "model", "out")
    if paths is None:
        return 1
    cfg = {"model": paths["model"], "out": paths["out"], "head": args.head,
           "name": args.name, "front": args.front}
    print(f"  model   {cfg['model']}")
    info = exec_json(ADD_JAW, cfg, SENTINEL, timeout=args.timeout)
    if info is None:
        return 1
    if "error" in info and "moved_at_20" not in info:
        print(f"  ! {info['error']}")
        if info.get("chain"):
            print(f"  chain   {' > '.join(info['chain'])}")
        if info.get("bones"):
            print(f"  bones   {', '.join(info['bones'])}")
        return 1
    print(f"  rig     {info['armature']} ({info['bones']} bones before the jaw)")
    if info["chain"]:
        print(f"  chain   {' > '.join(info['chain'])}")
        votes = ", ".join(f"{b} {n}" for b, n in info["top_counts"].items())
        print(f"  head    {info['head']}: topmost by tail is {info['topmost']}; of the "
              f"highest {info['top_vertices']} chain-weighted vertices, heaviest on {votes}")
    else:
        print(f"  head    {info['head']}  (from --head)")
    print(f"  region  {info['head_vertices']} vertices, box from {info['box_vertices']}: "
          f"height {info['head_height']:.4f}, depth {info['head_depth']:.4f}, "
          f"front {info['front']}")
    print(f"  jaw     {info['jaw']}: pivot {fmt(info['pivot'])}, tail {fmt(info['tail'])}, "
          f"fade {info['fade']:.4f}")
    for mesh, n in info["jaw_weighted"].items():
        print(f"  weights {mesh}: {n} vertices take jaw weight")
    print(f"  check   at 20 degrees {info['moved_at_20']} vertices move more than "
          f"{info['moved_threshold']:.4f}; mean vertical move {info['mean_rise_of_moved']:+.4f}, "
          f"largest drop {info['largest_drop']:.4f}")
    if "error" in info:
        # The check runs in Blender before saving, so a failed one wrote nothing.
        print(f"  ! {info['error']}")
        print(f"  ! nothing was written to {args.out}")
        return 1
    print(f"  wrote   {args.out}")
    return 0


def transfer_shapes(args) -> int:
    paths = container_paths(args, "template", "model", "out")
    if paths is None:
        return 1
    cfg = {"template": paths["template"], "model": paths["model"], "out": paths["out"],
           "region": args.region, "head": args.head,
           "template_mesh": args.template_mesh,
           "target": [t for t in (args.target or "").split(",") if t],
           "keys": [k for k in (args.keys or "").split(",") if k]}
    print(f"  template {cfg['template']}")
    print(f"  model    {cfg['model']}")
    info = exec_json(TRANSFER, cfg, SENTINEL, timeout=args.timeout)
    if info is None:
        return 1
    if "error" in info:
        print(f"  ! {info['error']}")
        for k in ("template_keys", "template_meshes", "meshes", "bones"):
            if info.get(k):
                print(f"    {k.replace('_', ' ')}: {', '.join(info[k])}")
        if info.get("bind_failed"):
            for reason in info.get("reasons", []):
                print(f"  ! Blender: {reason}")
            print(f"  ! {BIND_RESTRICTIONS}")
        return 1
    print(f"  bound to {info['template']} ({info['template_vertices']} vertices)"
          + (f", region under {info['head']}" if info["head"] else ""))
    for t in info["targets"]:
        print(f"  {t['target']} ({t['vertices']} vertices), moved means more than "
              f"{t['moved_threshold']:.4f}" + (" (0.5% of the head's height):" if info["head"]
                                               else " (0.5% of the mesh's largest extent):"))
        for k in t["keys"]:
            extra = (f", outside the region {k['max_outside_region']:.4f}"
                     if "max_outside_region" in k else "")
            print(f"    {k['key']:<16} max {k['max_displacement']:.4f}, "
                  f"moved {k['moved']}{extra}")
    print(f"  wrote    {args.out}")
    return 0


def spheres(args) -> int:
    out_dir = to_container(args.out_dir)
    if out_dir is None:
        sys.stderr.write(f"{args.out_dir}: the container only sees output/ and input/, "
                         "so the directory must be under one of them\n")
        return 1
    print(f"  out     {out_dir}")
    info = exec_json(SPHERES, {"out_dir": out_dir}, SENTINEL, timeout=args.timeout)
    if info is None:
        return 1
    if "error" in info:
        print(f"  ! {info['error']}")
        return 1
    for name, f in info["files"].items():
        keys = f", keys {', '.join(f['keys'])}" if f["keys"] else ""
        print(f"  wrote   {args.out_dir / (name + '.blend')}  ({f['vertices']} vertices, "
              f"{f['faces']} faces{keys})")
    print(f"  bad_template's extra face leaves one edge with {info['faces_on_bad_edge']} faces")
    return 0


def fmt(v) -> str:
    return "(" + ", ".join(f"{x:.4f}" for x in v) + ")"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    j = sub.add_parser("add-jaw", help="add a weighted jaw bone under the head")
    j.add_argument("model", type=Path, help="rigged .fbx, .glb or .blend")
    j.add_argument("--out", type=Path, required=True, help=".blend or .fbx to write")
    j.add_argument("--head", help="the head bone, when the automatic pick is wrong")
    j.add_argument("--name", default="jaw", help="name of the new bone (default jaw)")
    j.add_argument("--front", default="-y", choices=("-y", "+y", "-x", "+x"),
                   help="the way the model faces (default -y, Blender's front)")
    j.add_argument("--timeout", type=int, default=900,
                   help="seconds before giving up on Blender (default 900)")
    j.set_defaults(func=add_jaw)

    t = sub.add_parser("transfer-shapes",
                       help="copy a template head's shape keys onto a model")
    t.add_argument("template", type=Path,
                   help=".blend, .fbx, .glb or .obj holding a mesh with shape keys")
    t.add_argument("model", type=Path, help=".blend, .fbx, .glb or .obj to receive them")
    t.add_argument("--out", type=Path, required=True, help=".blend or .fbx to write")
    t.add_argument("--region", action="store_true",
                   help="deform only vertices weighted to the head bone or bones under it")
    t.add_argument("--head", help="the head bone for --region, when the automatic pick is wrong")
    t.add_argument("--template-mesh", help="the template mesh, when it holds several")
    t.add_argument("--target", help="comma separated model meshes (default: all)")
    t.add_argument("--keys", help="comma separated template keys (default: all)")
    t.add_argument("--timeout", type=int, default=900,
                   help="seconds before giving up on Blender (default 900)")
    t.set_defaults(func=transfer_shapes)

    s = sub.add_parser("spheres", help="write the test template and target spheres")
    s.add_argument("--out-dir", type=Path, default=Path("output/face_rig/spheres"),
                   help="directory under output/ or input/ (default output/face_rig/spheres)")
    s.add_argument("--timeout", type=int, default=300,
                   help="seconds before giving up on Blender (default 300)")
    s.set_defaults(func=spheres)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

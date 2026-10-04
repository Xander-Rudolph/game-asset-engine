#!/usr/bin/env python3
"""Project a generated mesh onto a game's own character mesh, keeping that
mesh's topology, UVs and skin weights, and bake the generated colour onto it.

    scripts/bg3_project.py BASE.glb SOURCE.glb --out output/bg3/halfling_m \
        [--colour output/textures/<name>/hunyuan_output.jpg] [--size 2048]
        [--lock Finger,Wrist] [--blend PATH] [--extra HEAD.glb]

Why this exists: a generated mesh is triangle soup with no edge loops, its own
UV atlas and, at best, a `bone_N` skeleton.  A game that animates characters on
its own skeleton (Baldur's Gate 3 is the case this was written for) needs the
game's topology, the game's UVs and weights to the game's bones.  So the
generated mesh is never imported into the game.  It is a shape and a colour
source: the game's own base mesh is deformed onto it with a Shrinkwrap, the
generated colour is baked onto the base mesh's UVs, and the base mesh's own
weights ride along because its vertices never changed.

What comes out, under --out as a prefix:
    <out>.glb         the deformed base mesh with its armature, Y-up, as glTF
    <out>.fbx         the same as FBX (forward -Z, up Y, Blender's defaults)
    <out>_BM.tga      base colour baked from the source (needs --colour or a
                      textured source), or left out
    <out>_NM.tga      tangent-space normals of the source baked onto the base
    <out>_PM.tga      R metalness (--metal, default 0), G roughness
                      (--rough, default 0.8), B ambient occlusion, baked
    <out>_preview.glb the fullest mesh alone, for looking at (the LODs overlap
                      in a render); not for import
    <out>.json        what was done, with every setting and count

The three TGA names follow BG3's material convention (BM, NM, PM packed
R metal, G rough, B AO, per docs.baldursgate3.game "Creating Armour");
--dds writes them as DXT5 DDS through ImageMagick as well.  The glTF carries
LSLib's EXT_lslib_profile metadata (bone order, LOD and export order, copied
from the base's glTF), which Divine's glTF importer requires, so Divine
`convert-model -i glb -o gr2 --conform-path <original GR2>` turns it into
the GR2 the Toolkit imports; on this host Divine runs under Wine.

The base mesh is the game's, so it lives OUTSIDE the repo, like the other
content libraries under MODELS_DIR (CLAUDE.md), and nothing it produces is
committed.  Pass it by an
absolute path or a path under input/ or output/; the output goes under
output/bg3/, which `cleanup.py keep` should refuse.

Alignment: when both figures hold the arms out, the source is scaled so its
floor-to-shoulder height matches the base's (the base's shoulder is a bone,
the source's is read off its arms), because a game body is headless, so
height would shrink the figure by a head, and the fingertip span changes with
how far the arms hang.  --align span or height force the other rulers.  Feet
go on the base's floor, the figure is centred in X and Y, and the head above
the base's neck line is cut away before the wrap.  The arms and legs are then
turned onto the base's rest pose (see --no-pose-match); a bent limb or a
different stance is not matched, and the wrap folds it onto the wrong
surface.  The neck ring, where the head mesh carries on from the body, is
held in place by --seam (the open loop highest on the mesh, easing in over
that fraction of the height).  --lock names vertex groups of the base mesh
(comma-separated, substring match on group names) that the wrap leaves where
they are; fingers, toes and ankles are the usual ones, since a generated
figure's hands and feet are blobs and the game's gloves and boots fit its own.

Everything runs in the container's Blender (bpy 4.5.9) on the CPU, so it never
contends with ComfyUI for the card.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import container as _container, exec_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTAINER = _container()

BLENDER = r'''
import bpy, sys, json, os, math
from mathutils import Vector, Matrix

cfg = json.loads(sys.argv[-1])
log = []


def say(msg):
    log.append(msg)
    print("  " + msg)


def load(path):
    before = set(bpy.data.objects)
    p = path.lower()
    if p.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=path)
    elif p.endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=path)
    else:
        # TEMPERANCE: the default bone heuristic adds an Icosphere as every
        # bone's display shape, which the exporter then writes out as a mesh.
        bpy.ops.import_scene.gltf(filepath=path, bone_heuristic="TEMPERANCE")
    return [o for o in bpy.data.objects if o not in before]


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def select_only(objs, active=None):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


# A clean scene: the factory cube would end up in the bake.
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ---- load ------------------------------------------------------------------
# A game's body file holds the mesh and its LODs, each skinned to the same
# armature.  Every mesh skinned to the armature is wrapped, so the LODs
# follow the shape; the fullest one is the bake target.  Anything unskinned
# is dropped.
base_objs = load(cfg["base"])
armatures = [o for o in base_objs if o.type == "ARMATURE"]
arm = armatures[0] if armatures else None
base_meshes = [o for o in base_objs if o.type == "MESH"
               and (arm is None or o.parent == arm or any(m.type == "ARMATURE" for m in o.modifiers))]
for o in base_objs:
    if o.type == "MESH" and o not in base_meshes:
        say(f"dropped {o.name}: {len(o.data.vertices)} verts, not skinned to the armature")
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if me.users == 0:
            bpy.data.meshes.remove(me)
if not base_meshes:
    raise SystemExit("the base file holds no mesh skinned to its armature")
base_meshes.sort(key=lambda o: -len(o.data.vertices))
base = base_meshes[0]
lods = base_meshes[1:]
base.name = "base"
if lods:
    say(f"base LODs following the wrap: {', '.join(f'{o.name} ({len(o.data.vertices):,} verts)' for o in lods)}")
say(f"base: {len(base.data.vertices):,} verts, {len(base.data.polygons):,} faces, "
    f"{len(base.vertex_groups)} vertex groups, {len(base.data.uv_layers)} uv layers, "
    f"armature: {arm.name + ' (' + str(len(arm.data.bones)) + ' bones)' if arm else 'none'}")
if not base.data.uv_layers:
    raise SystemExit("the base mesh has no UV layer, so nothing can be baked onto it")

src_objs = load(cfg["source"])
src_meshes = [o for o in src_objs if o.type == "MESH"]
if not src_meshes:
    raise SystemExit("the source file holds no mesh")
if len(src_meshes) > 1:
    select_only(src_meshes, src_meshes[0])
    bpy.ops.object.join()
source = bpy.context.view_layer.objects.active if len(src_meshes) > 1 else src_meshes[0]
source.name = "source"
for o in src_objs:
    if o.type != "MESH" and o not in (source,):
        bpy.data.objects.remove(o, do_unlink=True)
say(f"source: {len(source.data.vertices):,} verts, {len(source.data.polygons):,} faces, "
    f"{len(source.data.uv_layers)} uv layers, {len(source.data.materials)} materials")

# ---- extras: the game's other parts, for a clipping check --------------------
# Heads and private parts sit in the body's own frame already, so they come
# in as they are: LOD0 only, the mesh kept where its armature put it, the
# armature dropped, hidden from the bakes, in an "extras" collection.  The
# --extra ones are shown; the --extra-hidden ones are loaded hidden, to
# switch on in the outliner.  The shown ones go into the check GLB too.
extras, extras_shown = [], []
extra_coll = None
for path, shown in [(e, True) for e in cfg.get("extras") or []] + \
                   [(e, False) for e in cfg.get("extras_hidden") or []]:
    objs = load(path)
    stem = os.path.splitext(os.path.basename(path))[0]
    meshes = [o for o in objs if o.type == "MESH" and "_lod" not in o.name.lower()]
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
        for m in list(o.modifiers):
            o.modifiers.remove(m)
    for o in objs:
        if o not in meshes:
            bpy.data.objects.remove(o, do_unlink=True)
    if extra_coll is None:
        extra_coll = bpy.data.collections.new("extras")
        scene.collection.children.link(extra_coll)
    for k, o in enumerate(meshes):
        o.name = stem if k == 0 else f"{stem}.{k}"
        o.hide_render = True
        for c in list(o.users_collection):
            c.objects.unlink(o)
        extra_coll.objects.link(o)
        extras.append(o)
        if shown:
            extras_shown.append(o)
        else:
            o.hide_set(True)
    say(f"extra{'' if shown else ' (hidden)'}: {stem}, "
        f"{sum(len(o.data.vertices) for o in meshes):,} verts in {len(meshes)} mesh(es)")

# ---- align the source to the base ------------------------------------------
# A game body is headless and the generated figure is not, so height is the
# wrong ruler, and the fingertip span changes with how far the arms hang.  The
# shoulder is the joint both figures share: the base's is a bone, and the
# source's is read off its arms (the arm's centre line, fitted across the
# upper arm and forearm and carried back to the torso's edge).  Floor to
# shoulder is the ruler, the feet go on the base's floor, and the figure is
# centred on the base in X and Y.  --align span and height remain for figures
# that do not hold their arms out.
blo, bhi = bounds([base])
slo, shi = bounds([source])
wide = lambda lo, hi: (hi.x - lo.x) > 0.75 * (hi.z - lo.z)   # arms out: a T-pose with a head spans about 0.85 of its height


def bone(*names):
    if arm is None:
        return None
    low = {b.name.lower(): b for b in arm.data.bones}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    return None


def shoulder_height(obj, lo, hi):
    """The height of the shoulder joint read from the arms: the median height
    of the arm in bins along its length, a line through them, and that line
    carried back to the torso's edge (0.22 of the half span, where a game
    body's shoulder bone sits).  Only the upper half of the figure counts,
    since the feet of a wide stance reach out as well.  None unless the arms
    are held out."""
    if not wide(lo, hi):
        return None
    hw = (hi.x - lo.x) / 2
    cx = (lo.x + hi.x) / 2
    waist = (lo.z + hi.z) / 2          # the feet of a wide stance reach out too
    bins = {}
    for v in obj.data.vertices:
        p = obj.matrix_world @ v.co
        r = abs(p.x - cx) / hw
        if 0.4 <= r <= 0.9 and p.z > waist:
            bins.setdefault(int(r * 20), []).append(p.z)
    if len(bins) < 3:
        return None
    xs, zs = [], []
    for k, v in sorted(bins.items()):
        v.sort()
        xs.append((k + 0.5) / 20)
        zs.append(v[len(v) // 2])
    n = len(xs)
    mx, mz = sum(xs) / n, sum(zs) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (z - mz) for x, z in zip(xs, zs)) / sxx if sxx else 0.0
    return mz + slope * (0.22 - mx)


shoulders = [b for b in (bone("Shoulder_L"), bone("Shoulder_R")) if b]
if shoulders:
    z_sh_base = sum((arm.matrix_world @ b.head_local).z for b in shoulders) / len(shoulders)
    base_how = "shoulder bone"
else:
    z_sh_base = shoulder_height(base, blo, bhi)
    base_how = "arm line"
z_sh_src = shoulder_height(source, slo, shi)
mode = cfg.get("align", "auto")
if mode == "auto":
    if z_sh_base is not None and z_sh_src is not None:
        mode = "shoulder"
    else:
        mode = "span" if wide(blo, bhi) and wide(slo, shi) else "height"
if mode == "shoulder":
    if z_sh_base is None or z_sh_src is None:
        raise SystemExit("--align shoulder needs the arms held out on both figures")
    scale = (z_sh_base - blo.z) / max(1e-9, z_sh_src - slo.z)
    how = (f"floor to shoulder {(z_sh_src - slo.z) * scale:.3f} onto {z_sh_base - blo.z:.3f} "
           f"(base {base_how})")
elif mode == "span":
    scale = (bhi.x - blo.x) / max(1e-9, (shi.x - slo.x))
    how = "fingertip span"
else:
    scale = (bhi.z - blo.z) / max(1e-9, (shi.z - slo.z))
    how = "height"
select_only([source])
source.scale = source.scale * scale
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
slo, shi = bounds([source])
span = bhi.z - blo.z
shift = Vector(((blo.x + bhi.x) / 2 - (slo.x + shi.x) / 2, 0.0, blo.z - slo.z))
source.location += shift
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)


# ---- face the same way ------------------------------------------------------
# A generated figure stands facing +Y or -Y as its maker left it, and a wrap
# across a figure facing the wrong way puts the seat on the front and bends
# the knees backwards.  The feet say which way a standing figure faces: the
# toes reach further forward of the shin than the heel reaches behind it.
# The base's toe bone says the same for the base.
def facing(obj):
    # From the vertices themselves: an object's bound_box lags behind an
    # applied transform until the next depsgraph update.
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    z0 = min(p.z for p in pts)
    h = max(p.z for p in pts) - z0
    feet = [p.y for p in pts if p.z < z0 + 0.06 * h]
    shins = [p.y for p in pts if z0 + 0.15 * h < p.z < z0 + 0.35 * h]
    if not feet or not shins:
        return 0.0
    return sum(feet) / len(feet) - sum(shins) / len(shins)


base_face = facing(base)
ankle_b, toes_b = bone("Ankle_L", "Ankle_R"), bone("Toes_L", "Toes_R")
if ankle_b and toes_b:
    bone_face = (arm.matrix_world @ toes_b.head_local).y - (arm.matrix_world @ ankle_b.head_local).y
    if base_face * bone_face < 0:
        say(f"facing: the base's feet ({base_face:+.3f}) and its toe bone ({bone_face:+.3f}) disagree; "
            "trusting the bone")
    base_face = bone_face
src_face = facing(source)
way = lambda f: "+Y" if f > 0 else "-Y"
if base_face * src_face < 0:
    select_only([source])
    # By matrix: the glTF importer leaves objects in quaternion rotation
    # mode, where rotation_euler is ignored.
    source.matrix_world = Matrix.Rotation(math.pi, 4, "Z") @ source.matrix_world
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
    pts = [source.matrix_world @ v.co for v in source.data.vertices]
    source.location.x += (blo.x + bhi.x) / 2 - (min(p.x for p in pts) + max(p.x for p in pts)) / 2
    bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    slo, shi = bounds([source])
    say(f"facing: turned the source round; its feet pointed {way(src_face)} ({src_face:+.3f}) "
        f"and the base's point {way(base_face)} ({base_face:+.3f}); now {facing(source):+.3f}")
elif src_face == 0.0:
    say("facing: could not read the source's feet; it is taken as facing the base's way")
else:
    say(f"facing: both point {way(base_face)} (base {base_face:+.3f}, source {src_face:+.3f})")

# Cut the head off the source: a game body stops at the neck, and a head or
# hair left above it is the nearest surface for the whole upper chest, which
# it then climbs.  Only the head's footprint is cut, so arms above the neck
# line, which a drawn figure can have, are kept.
cut = bhi.z + float(cfg.get("cut_margin", 0.0)) * span
import bmesh
bm = bmesh.new()
bm.from_mesh(source.data)
above = [v for v in bm.verts
         if (source.matrix_world @ v.co).z > cut and abs((source.matrix_world @ v.co).x) < 0.25 * span]
n_cut = len(above)
if above:
    bmesh.ops.delete(bm, geom=above, context="VERTS")
bm.to_mesh(source.data)
bm.free()
source.data.update()
slo, shi = bounds([source])
# Centre in depth on what is left, so a mane of hair behind the head does
# not drag the figure backwards.
source.location.y += (blo.y + bhi.y) / 2 - (slo.y + shi.y) / 2
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
slo, shi = bounds([source])
say(f"aligned source by {mode}, x{scale:.4f}, {how}; cut {n_cut:,} head verts above z={cut:.3f}; "
    f"now height {shi.z - slo.z:.3f} on base {bhi.z - blo.z:.3f}, width {shi.x - slo.x:.3f} on "
    f"{bhi.x - blo.x:.3f}, depth {shi.y - slo.y:.3f} on {bhi.y - blo.y:.3f}")

# An unposed copy of the aligned source, for lining things up by hand.
select_only([source])
bpy.ops.object.duplicate()
source_rest = bpy.context.view_layer.objects.active
source_rest.name = "source_rest"
source_rest.hide_render = True

# ---- pose the source into the base's rest pose -----------------------------
# A concept is never drawn at exactly the rig's rest pose, and a wrap cannot
# cross a pose difference: an arm twenty degrees too high becomes a web.  So
# the source borrows the base's skin weights by nearest face, the arm and leg
# directions of both figures are measured, and the base's armature is posed
# by the difference with the source bound to it, which swings the source's
# limbs onto the base's.  The pose is then cleared, so the base is untouched.
import math
from mathutils import Matrix
pose_log = {}


def centroid(vs):
    c = Vector((0.0, 0.0, 0.0))
    for v in vs:
        c += v
    return c / len(vs) if vs else None


def pose_match():
    if arm is None or not cfg.get("pose_match", True):
        return
    span = bhi.z - blo.z
    # Each limb is a chain of segments, parent first: the bone that turns,
    # the bone at the segment's far end, the axis the slabs are cut across,
    # and the band that keeps the slabs to this limb.  Every segment is
    # aligned in 3D, so a forearm that the rig bends forward as well as down
    # is met in both.
    segments = []
    for side in ("L", "R"):
        sh, el, wr = bone(f"Shoulder_{side}"), bone(f"Elbow_{side}"), bone(f"Wrist_{side}")
        hip, kn, ank, toes = bone(f"Hip_{side}"), bone(f"Knee_{side}"), bone(f"Ankle_{side}"), bone(f"Toes_{side}")
        if sh and el and wr:
            arm_band = lambda p, h: abs(p.z - h.z) < 0.3 * span
            segments += [(sh, el, "x", arm_band, 0.3, 0.9), (el, wr, "x", arm_band, 0.3, 0.9)]
        if hip and kn and ank:
            leg_band = lambda p, h: abs(p.x - h.x) < 0.2 * span
            segments += [(hip, kn, "z", leg_band, 0.3, 0.9), (kn, ank, "z", leg_band, 0.3, 0.9)]
            if toes:
                foot_band = lambda p, h: abs(p.x - h.x) < 0.2 * span and p.z < h.z + 0.08 * span
                segments.append((ank, toes, "y", foot_band, 0.25, 0.75))
    if not segments:
        say("pose match: no Shoulder/Elbow/Wrist or Hip/Knee/Ankle bones found; skipped")
        return
    # The base's weights onto the source, by nearest face, so the armature
    # can move the source's limbs.
    for g in base.vertex_groups:
        if g.name not in source.vertex_groups:
            source.vertex_groups.new(name=g.name)
    select_only([base, source], source)
    dt = source.modifiers.new("borrow_weights", "DATA_TRANSFER")
    dt.object = base
    dt.use_vert_data = True
    dt.data_types_verts = {"VGROUP_WEIGHTS"}
    dt.vert_mapping = "POLYINTERP_NEAREST"
    dt.layers_vgroup_select_src = "ALL"
    dt.layers_vgroup_select_dst = "NAME"
    bpy.ops.object.datalayout_transfer(modifier=dt.name)
    bpy.ops.object.modifier_apply(modifier=dt.name)
    am = source.modifiers.new("pose", "ARMATURE")
    am.object = arm
    rest = [source.matrix_world @ v.co for v in source.data.vertices]

    def posed():
        dg = bpy.context.evaluated_depsgraph_get()
        ev = source.evaluated_get(dg)
        return [source.matrix_world @ v.co for v in ev.data.vertices]

    def angle(u, v):
        return math.degrees(math.acos(max(-1.0, min(1.0, u.normalized().dot(v.normalized())))))

    for turn, end, axis, band, f0, f1 in segments:
        h0 = arm.matrix_world @ turn.head_local
        h1 = arm.matrix_world @ end.head_local
        base_dir = h1 - h0
        side = 1.0 if h0.x >= 0 else -1.0
        a0, a1 = getattr(h0, axis), getattr(h1, axis)
        at0, at1 = a0 + f0 * (a1 - a0), a0 + f1 * (a1 - a0)
        half = 0.03 * span
        # The source's vertices at two stations along this segment, picked
        # in the source's rest pose and measured where the pose has put them.
        i0 = [i for i, p in enumerate(rest) if abs(getattr(p, axis) - at0) <= half and p.x * side >= 0 and band(p, h0)]
        i1 = [i for i, p in enumerate(rest) if abs(getattr(p, axis) - at1) <= half and p.x * side >= 0 and band(p, h0)]
        if not i0 or not i1:
            say(f"pose match: no source vertices for {turn.name} to {end.name}; skipped")
            continue
        now = posed()
        src_dir = centroid([now[i] for i in i1]) - centroid([now[i] for i in i0])
        rot_axis = src_dir.cross(base_dir)
        want = angle(src_dir, base_dir)
        if rot_axis.length < 1e-9 or want < 0.05:
            pose_log[turn.name] = (0.0, round(want, 1))
            continue
        # Turn the segment, and everything below it, about the bone's head
        # as it is now posed, by the one rotation that lays the measured
        # direction onto the bone's.
        pb = arm.pose.bones[turn.name]
        bpy.context.view_layer.update()
        hh = arm.matrix_world @ pb.head
        R = Matrix.Translation(hh) @ Matrix.Rotation(math.radians(want), 4, rot_axis.normalized()) @ Matrix.Translation(-hh)
        pb.matrix = arm.matrix_world.inverted() @ R @ arm.matrix_world @ pb.matrix
        bpy.context.view_layer.update()
        now = posed()
        left = angle(centroid([now[i] for i in i1]) - centroid([now[i] for i in i0]), base_dir)
        pose_log[turn.name] = (round(want, 1), round(left, 1))
    bpy.context.view_layer.update()
    select_only([source])
    bpy.ops.object.modifier_apply(modifier=am.name)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    for g in list(source.vertex_groups):
        source.vertex_groups.remove(g)
    say(f"pose match: turned (degrees, remaining error) {pose_log}, segment by segment in 3D, and applied to the source")


pose_match()

if cfg.get("check"):
    # The posed source beside the untouched base, for looking at the pose
    # match itself; nothing downstream reads it.
    os.makedirs(os.path.dirname(cfg["out"]) or ".", exist_ok=True)
    select_only([source, source_rest, base] + extras_shown + ([arm] if arm else []), base)
    bpy.ops.export_scene.gltf(filepath=f"{cfg['out']}_check.glb", export_format="GLB",
                              use_selection=True, export_skins=bool(arm), export_animations=False,
                              export_yup=True, export_materials="NONE")
    say(f"wrote {cfg['out']}_check.glb: the posed and the unposed source with the untouched base "
        "and its armature")

# ---- a wrap target without the source's layers ----------------------------
# A drawn figure wears clothes, and a generated mesh keeps them as layers: a
# hem, a cuff, a collar.  A vertex of the base near a hem snaps to whichever
# layer is nearer and its neighbour to the other, which tears the loop.  So
# the wrap aims at a voxel remesh of the source, one closed skin at --remesh
# of the base's height, while the bake still reads the source itself.
remesh = float(cfg.get("remesh", 0.005))
target = source
if remesh > 0:
    select_only([source])
    bpy.ops.object.duplicate()
    target = bpy.context.view_layer.objects.active
    target.name = "wrap_target"
    # close the neck the head cut opened, or the volume has no inside
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.fill_holes(sides=0)
    bpy.ops.object.mode_set(mode="OBJECT")
    voxel = remesh * (bhi.z - blo.z)
    rm = target.modifiers.new("bg3_project_remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    rm.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=rm.name)
    target.hide_render = True
    say(f"wrap target: voxel remesh of the source at {voxel * 1000:.1f} mm, "
        f"{len(target.data.vertices):,} verts, {len(target.data.polygons):,} faces")

# ---- a Blender file of this moment, for lining up by hand -------------------
# Everything is in place and nothing has moved yet: the armature, the base and
# its LODs with their weights, the source as posed (source), as aligned but
# unposed (source_rest) and as the wrap sees it (wrap_target).
if cfg.get("blend"):
    os.makedirs(os.path.dirname(cfg["blend"]) or ".", exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=cfg["blend"], copy=True)
    say(f"wrote {cfg['blend']}: armature, base and LODs with weights, source posed, "
        f"source_rest unposed, wrap_target remeshed, {len(extras)} extras")

# ---- an untouched copy, for the normals bake and as a record ---------------
select_only([base])
bpy.ops.object.duplicate()
pristine = bpy.context.view_layer.objects.active
pristine.name = "base_pristine"
pristine.hide_render = True

# ---- lock groups: vertices the wrap must not move ---------------------------
# Substrings of vertex-group names; a vertex in any matching group with a
# weight above --lock-weight stays where it is.  On a body the neck ring,
# fingers and toes are the usual ones: the generated hands are blobs.
patterns = [p.strip().lower() for p in cfg.get("lock", []) if p.strip()]
if patterns:
    hits = [g.name for g in base.vertex_groups if any(p in g.name.lower() for p in patterns)]
    say(f"lock groups: {len(hits)} match {patterns}: {', '.join(hits)[:300]}")

# ---- the neck seam: the open loop highest on the mesh -----------------------
# A game body ends at the neck in an open ring that the head mesh continues,
# vertex for vertex, so that ring must not move at all.  It is not found by
# weight (on this body it is weighted to the chest and shoulders, not the
# neck), but as the open edge loop with the highest mean height.  Boundary
# edges are followed into loops first, because a UV split shows as a boundary
# too.  --seam is the fraction of the height over which the hold eases off.
def top_loop(obj):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    adj = {}
    for e in bm.edges:
        if len(e.link_faces) == 1:
            a, b = e.verts
            adj.setdefault(a.index, set()).add(b.index)
            adj.setdefault(b.index, set()).add(a.index)
    bm.free()
    seen, best = set(), None
    for s in adj:
        if s in seen:
            continue
        stack, comp = [s], []
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            comp.append(u)
            stack.extend(adj[u] - seen)
        z = sum(obj.data.vertices[i].co.z for i in comp) / len(comp)
        if best is None or z > best[0]:
            best = (z, comp)
    return [obj.data.vertices[i].co.copy() for i in best[1]] if best else []


seam = float(cfg.get("seam", 0.06)) * (bhi.z - blo.z)
if seam > 0:
    ring = top_loop(base)
    if ring:
        say(f"neck seam: {len(ring)} verts on the open loop at z {min(r.z for r in ring):.3f} to "
            f"{max(r.z for r in ring):.3f} held, easing off over {seam * 100:.1f} cm")
    else:
        say("neck seam: the base has no open edge loop, so nothing is held by position")


# ---- shrinkwrap the base (and its LODs) onto the source ---------------------
def mask_for(obj):
    """How far each vertex of obj may follow the wrap: 1 everywhere, 0 on a
    vertex whose weight in the locked groups reaches --lock-weight and between
    the two below it, and 0 on the neck seam rising to 1 over --seam, so a
    held ring eases into the wrapped surface instead of stepping off it."""
    hits = {g.index for g in obj.vertex_groups
            if any(p in g.name.lower() for p in patterns)} if patterns else set()
    lw = float(cfg.get("lock_weight", 0.0))
    ring = top_loop(obj) if seam > 0 else []
    free = []
    for v in obj.data.vertices:
        w = sum(ge.weight for ge in v.groups if ge.group in hits)
        f = max(0.0, 1.0 - w / lw) if lw > 0 else (0.0 if w > 0 else 1.0)
        if ring:
            d = min((v.co - r).length for r in ring)
            f = min(f, min(1.0, d / seam))
        free.append(f)
    return free, sum(1 for f in free if f == 0.0)


def wrap(obj):
    """Move obj onto the target and smooth the move, not the mesh.

    The shrinkwrap puts every vertex on the nearest point of the target, which
    carries the base's own detail along but adds the target's facets.  The
    displacement field is then averaged over a radius (tent weights, by the
    original positions), so facet-scale noise goes and the shape change stays,
    and the base's knuckles and wrinkles are never smoothed themselves.  A game
    body is split into shells (this one into forty) whose seam vertices sit
    on top of each other; coincident vertices get the same displacement and the
    same average, so the seams stay closed, which a mesh smoother that walks
    each shell's own edges cannot promise.  The mask scales the move last."""
    select_only([obj])
    mask, n_locked = mask_for(obj)
    before = [v.co.copy() for v in obj.data.vertices]

    mod = obj.modifiers.new("bg3_project", "SHRINKWRAP")
    mod.target = target
    mod.wrap_method = cfg.get("wrap_method", "NEAREST_SURFACEPOINT")
    mod.wrap_mode = "ON_SURFACE"
    mod.offset = float(cfg.get("offset", 0.0))
    # The Armature modifier the import added must stay last, so the wrap is
    # moved ahead of it before it is applied.
    while obj.modifiers.find(mod.name) > 0:
        bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=mod.name)
    disp = [v.co - before[i] for i, v in enumerate(obj.data.vertices)]

    # Keep each vertex at its station along its bone.  A shape's limbs are
    # never quite the base's length, and a nearest-point wrap slides the skin
    # along the arm towards a shorter wrist, which bunches it at the joints
    # and bends it in the wrong place once the game animates the base's
    # bones.  So the part of the move that runs along the vertex's bones is
    # removed: girth changes, station does not.  --free-slide keeps it.
    along = across = 0.0
    if arm is not None and not cfg.get("free_slide"):
        axes = {}
        for b in arm.data.bones:
            gi = obj.vertex_groups.find(b.name)
            if gi >= 0:
                ax = (arm.matrix_world @ b.tail_local) - (arm.matrix_world @ b.head_local)
                axes[gi] = ax.normalized() if ax.length > 1e-9 else None
        for i, v in enumerate(obj.data.vertices):
            a = Vector((0.0, 0.0, 0.0))
            for g in v.groups:
                ax = axes.get(g.group)
                if ax is not None:
                    a += ax * g.weight
            if a.length > 1e-9:
                a.normalize()
                slide = disp[i].dot(a)
                along += abs(slide)
                disp[i] = disp[i] - a * slide
            across += disp[i].length
    radius = float(cfg.get("smooth_radius", 0.02)) * (bhi.z - blo.z)
    passes = int(cfg.get("smooth_passes", 2))
    if radius > 0 and passes > 0:
        from mathutils import kdtree
        kd = kdtree.KDTree(len(before))
        for i, p in enumerate(before):
            kd.insert(p, i)
        kd.balance()
        near = [[(j, 1.0 - dist / radius) for (_, j, dist) in kd.find_range(p, radius)]
                for p in before]
        for _ in range(passes):
            new = []
            for i in range(len(before)):
                acc, wsum = Vector((0.0, 0.0, 0.0)), 0.0
                for j, w in near[i]:
                    acc += disp[j] * w
                    wsum += w
                new.append(acc / wsum if wsum > 0 else disp[i])
            disp = new
    for i, v in enumerate(obj.data.vertices):
        v.co = before[i] + disp[i] * mask[i]
    obj.data.update()
    # The game mesh carries its own normals, and the exporter writes them out
    # as they are; after the move they describe the old surface, and the
    # shading breaks wherever the shape changed.  New ones come from the moved
    # faces, area weighted, and are averaged across coincident vertices so the
    # shells shade as one surface.  Authored hard edges are lost; a body has
    # none.
    from mathutils import kdtree
    acc = [Vector((0.0, 0.0, 0.0)) for _ in obj.data.vertices]
    for p in obj.data.polygons:
        for vi in p.vertices:
            acc[vi] += p.normal * p.area
    kd = kdtree.KDTree(len(obj.data.vertices))
    for i, v in enumerate(obj.data.vertices):
        kd.insert(v.co, i)
    kd.balance()
    merged = []
    for v in obj.data.vertices:
        n = Vector((0.0, 0.0, 0.0))
        for (_, j, _) in kd.find_range(v.co, 1e-5):
            n += acc[j]
        merged.append(tuple(n.normalized()) if n.length > 1e-12 else (0.0, 0.0, 1.0))
    obj.data.normals_split_custom_set_from_vertices(merged)
    obj.data.update()
    moved = [(disp[i] * mask[i]).length for i in range(len(before))]
    # Where the move went, by each vertex's heaviest group.
    by_group = {}
    for i, v in enumerate(obj.data.vertices):
        if not v.groups:
            continue
        g = max(v.groups, key=lambda ge: ge.weight).group
        by_group.setdefault(obj.vertex_groups[g].name, []).append(moved[i])
    top = sorted(by_group.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))[:8]
    n = max(1, len(before))
    say(f"{obj.name}: move along the bones removed {along / n:.4f} per vertex on average, "
        f"{across / n:.4f} kept across them; most moved groups (mean, max): "
        + ", ".join(f"{k} ({sum(v) / len(v):.3f}, {max(v):.3f})" for k, v in top))
    return moved, n_locked


moved, locked = wrap(base)
say(f"wrapped {base.name}: mean move {sum(moved) / len(moved):.4f}, max {max(moved):.4f}, "
    f"{locked:,} verts held, {sum(1 for d in moved if d < 1e-6):,} did not move")
for o in lods:
    m2, l2 = wrap(o)
    say(f"wrapped {o.name}: mean move {sum(m2) / len(m2):.4f}, max {max(m2):.4f}, {l2:,} verts held")
if target is not source:
    bpy.data.objects.remove(target, do_unlink=True)

# ---- materials for the bake ------------------------------------------------
size = int(cfg.get("size", 2048))
out = cfg["out"]
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = int(cfg.get("samples", 4))
scene.render.bake.use_selected_to_active = True
scene.render.bake.use_cage = False
scene.render.bake.cage_extrusion = float(cfg.get("extrusion", 0.02)) * (bhi.z - blo.z)
scene.render.bake.max_ray_distance = float(cfg.get("ray", 0.2)) * (bhi.z - blo.z)
scene.render.bake.margin = 16
scene.render.image_settings.file_format = "TARGA"
scene.render.image_settings.color_mode = "RGBA"

written = {}


MISS = (1.0, 0.0, 1.0, 1.0)     # a texel no ray reached keeps this colour
misses = {}


def new_image(name, colour_space):
    img = bpy.data.images.new(name, size, size, alpha=True)
    img.colorspace_settings.name = colour_space
    img.generated_color = MISS
    return img


def count_misses(img):
    """Texels still at the sentinel after a bake: rays from the base that hit
    nothing within max_ray_distance.  A high share means the shapes do not
    line up, or the distance is too short."""
    import numpy as np
    px = np.empty(size * size * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(-1, 4)
    hit = np.abs(px[:, :3] - np.array(MISS[:3], dtype=np.float32)).max(axis=1) > 0.02
    return int((~hit).sum()), int(hit.sum())


def target_material(img):
    """The base mesh bakes into whichever image node is active on its material."""
    mat = bpy.data.materials.new("bg3_project_target")
    mat.use_nodes = True
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = img
    mat.node_tree.nodes.active = node
    base.data.materials.clear()
    base.data.materials.append(mat)


def source_emits(img_path):
    """Paint the source with its colour map as pure emission, so a DIFFUSE
    COLOR bake reads the texels and nothing else."""
    mat = bpy.data.materials.new("bg3_project_source")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(img_path)
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], outn.inputs["Surface"])
    source.data.materials.clear()
    source.data.materials.append(mat)


def bake(kind, img, **kw):
    select_only([source, base], base)
    bpy.ops.object.bake(type=kind, use_selected_to_active=True,
                        cage_extrusion=scene.render.bake.cage_extrusion,
                        max_ray_distance=scene.render.bake.max_ray_distance,
                        margin=16, **kw)
    missed, hit = count_misses(img)
    misses[img.name] = missed / max(1, missed + hit)
    path = f"{out}_{img.name}.tga"
    img.filepath_raw = path
    img.file_format = "TARGA"
    img.save()
    written[img.name] = path
    say(f"baked {kind} to {os.path.basename(path)} at {size}px, "
        f"{misses[img.name] * 100:.1f}% of texels unreached")


# Colour: from --colour, or from the source's own first image texture.
colour = cfg.get("colour")
if not colour:
    for m in source.data.materials:
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    n.image.filepath_raw = f"{out}_source_colour.png"
                    n.image.file_format = "PNG"
                    n.image.save()
                    colour = n.image.filepath_raw
                    break
        if colour:
            break
if colour and source.data.uv_layers:
    source_emits(colour)
    img = new_image("BM", "sRGB")
    target_material(img)
    bake("EMIT", img)
elif colour:
    say("source has no UV layer, so its colour cannot be read; no BM written")
else:
    say("no colour map given and none on the source; no BM written")

# Normals of the source relative to the deformed base, tangent space.
img = new_image("NM", "Non-Color")
target_material(img)
bake("NORMAL", img, normal_space="TANGENT")

# AO of the base itself into the blue channel, with flat metal and roughness.
ao = new_image("AO_tmp", "Non-Color")
target_material(ao)
scene.render.bake.use_selected_to_active = False
source.hide_render = True            # or the source shadows the base's AO
scene.cycles.samples = max(16, int(cfg.get("samples", 4)))
select_only([base])
bpy.ops.object.bake(type="AO", use_selected_to_active=False, margin=16)
pm = new_image("PM", "Non-Color")
metal = float(cfg.get("metal", 0.0))
rough = float(cfg.get("rough", 0.8))
px = list(ao.pixels)
outpx = [0.0] * len(px)
for i in range(0, len(px), 4):
    outpx[i] = metal
    outpx[i + 1] = rough
    outpx[i + 2] = px[i]
    outpx[i + 3] = 1.0
pm.pixels = outpx
pm.filepath_raw = f"{out}_PM.tga"
pm.file_format = "TARGA"
pm.save()
written["PM"] = pm.filepath_raw
say(f"packed PM: R metal {metal}, G rough {rough}, B baked AO")

# ---- export the deformed base with its armature ----------------------------
bpy.data.objects.remove(pristine, do_unlink=True)
bpy.data.objects.remove(source, do_unlink=True)
for o in [base] + lods:
    o.data.materials.clear()
export = [base] + lods + ([arm] if arm else [])
select_only(export, base)
gltf_kw = dict(filepath=f"{out}.glb", export_format="GLB", use_selection=True,
               export_skins=bool(arm), export_animations=False, export_yup=True,
               export_materials="NONE")
try:
    # The game's masks ride in the vertex colours, so they must travel.
    bpy.ops.export_scene.gltf(export_vertex_color="ACTIVE", **gltf_kw)
except TypeError:
    bpy.ops.export_scene.gltf(**gltf_kw)
bpy.ops.export_scene.fbx(filepath=f"{out}.fbx", use_selection=True,
                         object_types={"ARMATURE", "MESH"}, add_leaf_bones=False,
                         bake_anim=False, use_armature_deform_only=True,
                         path_mode="STRIP", colors_type="SRGB")
written["glb"] = f"{out}.glb"
written["fbx"] = f"{out}.fbx"
# A viewing copy with the fullest mesh only: the LODs sit on top of each
# other in a render and read as a broken surface.
select_only([base] + ([arm] if arm else []), base)
bpy.ops.export_scene.gltf(filepath=f"{out}_preview.glb", export_format="GLB", use_selection=True,
                          export_skins=bool(arm), export_animations=False, export_yup=True,
                          export_materials="NONE")
written["preview"] = f"{out}_preview.glb"

info = {
    "base": cfg["base"], "source": cfg["source"], "colour": colour,
    "base_verts": len(base.data.vertices), "base_faces": len(base.data.polygons),
    "vertex_groups": len(base.vertex_groups), "bones": len(arm.data.bones) if arm else 0,
    "lods": [o.name for o in lods], "align": mode, "cut_verts": n_cut, "pose_match": pose_log,
    "scale": scale, "remesh": remesh, "locked": locked, "mean_move": sum(moved) / len(moved),
    "max_move": max(moved), "size": size, "written": written,
    "unreached": misses, "log": log,
}
with open(f"{out}.json", "w") as f:
    json.dump(info, f, indent=1)
print("BG3PROJECT " + json.dumps(info))
'''


def models_dir() -> Path | None:
    """MODELS_DIR as the compose file mounts it at /app/models: from the
    environment, else .env, resolved against the repo root."""
    import os
    raw = os.environ.get("MODELS_DIR")
    if not raw and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text().splitlines():
            if line.strip().startswith("MODELS_DIR="):
                raw = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not raw:
        return None
    return (ROOT / raw).resolve() if not Path(raw).is_absolute() else Path(raw)


def write_lslib_profile(out_glb: str, base_glb: str) -> str:
    """Put LSLib's own glTF metadata back into the export.

    Divine's glTF carries an EXT_lslib_profile extension on the scene (the
    GR2 skeleton's bone order and the LSLib version that wrote it) and on
    each mesh (LOD, export order, flags).  Blender's importer drops what it
    does not know, and Divine's glTF importer reads the scene extension
    without checking for it, so an export without it fails with "Object
    reference not set to an instance of an object" in ImportBone.  The scene
    entry is copied from the base, or built from the skin's joint order when
    the base has none, and each mesh entry is copied by mesh name.
    """
    import struct

    def read(path):
        raw = Path(path).read_bytes()
        if raw[:4] != b"glTF":
            return raw, None, b""
        n = struct.unpack_from("<I", raw, 12)[0]
        return raw, json.loads(raw[20:20 + n]), raw[20 + n:]

    ext_name = "EXT_lslib_profile"
    raw, j, rest = read(out_glb)
    if j is None:
        return "not written: the export is not a GLB"
    _, bj, _ = read(base_glb) if Path(base_glb).suffix.lower() == ".glb" else (None, None, None)
    bj = bj or {}
    base_scene = ((bj.get("scenes") or [{}])[0].get("extensions") or {}).get(ext_name)
    if base_scene:
        profile = dict(base_scene)
        origin = "copied from the base"
    else:
        joints = j["skins"][0]["joints"] if j.get("skins") else []
        profile = {"MetadataVersion": 3, "LSLibMajor": 1, "LSLibMinor": 20, "LSLibPatch": 4,
                   "BoneOrder": {j["nodes"][k].get("name", str(k)): i + 1 for i, k in enumerate(joints)},
                   "ModelName": j["nodes"][joints[0]].get("name", "") if joints else ""}
        origin = "built from the skin's joint order"
    # Divine omits empty values, and SharpGLTF refuses a file with an empty
    # dictionary in it ("ModelRoot Empty dictionary found").
    profile = {k: v for k, v in profile.items() if v not in ({}, None)}
    scene = j["scenes"][j.get("scene", 0)]
    scene.setdefault("extensions", {})[ext_name] = profile
    base_meshes = {m.get("name"): (m.get("extensions") or {}).get(ext_name) for m in bj.get("meshes", [])}
    copied = 0
    for i, m in enumerate(j.get("meshes", [])):
        ext = base_meshes.get(m.get("name"))
        if ext is None:
            ext = {k: False for k in ("Rigid", "Cloth", "MeshProxy", "ProxyGeometry", "Spring", "Occluder",
                                      "ClothPhysics", "Cloth01", "Cloth02", "Cloth04", "Impostor")}
            ext.update({"ExportOrder": i, "LOD": i, "LODDistance": 0, "ParentBone": ""})
        else:
            copied += 1
        m.setdefault("extensions", {})[ext_name] = ext
    used = j.setdefault("extensionsUsed", [])
    if ext_name not in used:
        used.append(ext_name)
    data = json.dumps(j, separators=(",", ":")).encode()
    data += b" " * (-len(data) % 4)
    out = bytearray(raw[:12]) + struct.pack("<II", len(data), 0x4E4F534A) + data + rest
    struct.pack_into("<I", out, 8, len(out))
    Path(out_glb).write_bytes(out)
    return (f"BoneOrder for {len(profile.get('BoneOrder', {}))} bones {origin}, "
            f"{copied} of {len(j.get('meshes', []))} mesh entries from the base")


def write_dds(written: dict) -> dict:
    """Each baked TGA as a DDS beside it, DXT5 with mipmaps, through
    ImageMagick's convert.  DXT5 is what ImageMagick writes; which block
    formats the game's own textures use was not checked here, so the maps are
    a starting point for the Toolkit's import, not a match for Larian's.
    Returns {map name + "_dds": path} for the maps it wrote."""
    import shutil
    import subprocess
    tool = shutil.which("magick") or shutil.which("convert")
    if tool is None:
        print("  dds        skipped: ImageMagick's convert is not on the PATH")
        return {}
    out = {}
    for name, path in list(written.items()):
        if not str(path).lower().endswith(".tga"):
            continue
        host = ROOT / path[len("/app/"):] if str(path).startswith("/app/") else Path(path)
        dds = host.with_suffix(".dds")
        r = subprocess.run([tool, str(host), "-define", "dds:compression=dxt5", str(dds)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  dds        {host.name}: convert failed: {r.stderr.strip()[:200]}")
            continue
        out[f"{name}_dds"] = str(dds.relative_to(ROOT)) if dds.is_relative_to(ROOT) else str(dds)
    return out


def to_container(p: str) -> str:
    """A host path as the container sees it: output/ and input/ are bind
    mounts, and MODELS_DIR is /app/models, which is where a game's base mesh
    kept in MODELS_DIR/bg3_library lands."""
    if p.startswith("/app/"):
        return p
    path = Path(p)
    if not path.is_absolute():
        path = ROOT / path
    mounts = [(ROOT / "output", "/app/output"), (ROOT / "input", "/app/input")]
    models = models_dir()
    if models is not None:
        mounts.append((models, "/app/models"))
    for host, cont in mounts:
        try:
            return f"{cont}/{path.resolve().relative_to(host.resolve())}"
        except ValueError:
            continue
    return str(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", help="the game's base mesh with its armature (.glb, .gltf or .fbx), "
                                 "kept outside the repo")
    ap.add_argument("source", help="the generated mesh to take the shape and colour from")
    ap.add_argument("--out", required=True,
                    help="output prefix, e.g. output/bg3/halfling_m (writes .glb, .fbx, "
                         "_BM.tga, _NM.tga, _PM.tga and .json)")
    ap.add_argument("--colour", help="the source's colour map, if it is not inside the file")
    ap.add_argument("--size", type=int, default=2048, help="bake size in pixels (default 2048)")
    ap.add_argument("--samples", type=int, default=4, help="Cycles samples per bake (default 4)")
    ap.add_argument("--lock", default="",
                    help="comma-separated substrings of base vertex-group names whose "
                         "vertices the wrap leaves in place, e.g. eye,mouth,neck")
    ap.add_argument("--align", default="auto", choices=["auto", "shoulder", "span", "height"],
                    help="scale the source by floor-to-shoulder height, fingertip span or "
                         "height; auto picks shoulder when both hold the arms out (default auto)")
    ap.add_argument("--seam", type=float, default=0.06,
                    help="hold the neck ring (the open edge loop highest on the base) and ease "
                         "the hold off over this fraction of the base's height; 0 to not hold "
                         "it (default 0.06)")
    ap.add_argument("--remesh", type=float, default=0.005,
                    help="wrap onto a voxel remesh of the source at this fraction of the base's "
                         "height, so clothing layers read as one skin; 0 wraps onto the source "
                         "itself (default 0.005)")
    ap.add_argument("--cut-margin", type=float, default=0.0,
                    help="remove source geometry above the base's top plus this fraction of "
                         "the base's height, so a head above a headless body is not wrapped "
                         "onto (default 0)")
    ap.add_argument("--dds", action="store_true",
                    help="also write each baked map as DDS (DXT5, with mipmaps) through "
                         "ImageMagick's convert, when it is on the PATH")
    ap.add_argument("--blend", metavar="PATH",
                    help="also save a .blend (Blender 4.5) of the lined-up scene before the wrap: "
                         "armature, base and LODs with weights, the source posed and unposed, "
                         "and the remeshed wrap target")
    ap.add_argument("--extra", action="append", default=[], metavar="GLB",
                    help="a game mesh in the body's frame (a head, private parts) to carry into the "
                         "check GLB and the .blend for a clipping check; repeatable")
    ap.add_argument("--extra-hidden", action="append", default=[], metavar="GLB",
                    help="as --extra, but loaded hidden in the .blend and left out of the check GLB; "
                         "for the other variants (heads B to F, the other genital sets)")
    ap.add_argument("--check", action="store_true",
                    help="also write <out>_check.glb: the posed source beside the untouched base")
    ap.add_argument("--free-slide", action="store_true",
                    help="let the wrap move vertices along their bones too (the default removes "
                         "that part of the move, so limbs keep the base's proportions)")
    ap.add_argument("--no-pose-match", action="store_true",
                    help="do not swing the source's arms and legs onto the base's before "
                         "wrapping (the default does, by borrowing the base's weights)")
    ap.add_argument("--lock-weight", type=float, default=0.0,
                    help="a vertex is held when its weight in a locked group exceeds this "
                         "(default 0, any membership)")
    ap.add_argument("--wrap-method", default="NEAREST_SURFACEPOINT",
                    choices=["NEAREST_SURFACEPOINT", "PROJECT", "NEAREST_VERTEX",
                             "TARGET_PROJECT"])
    ap.add_argument("--smooth-radius", type=float, default=0.02,
                    help="average each vertex's move over this radius, as a fraction of the "
                         "base's height, so the target's facets do not print through; 0 for "
                         "none (default 0.02)")
    ap.add_argument("--smooth-passes", type=int, default=2,
                    help="how many times the move is averaged (default 2)")
    ap.add_argument("--ray", type=float, default=0.2,
                    help="bake ray reach as a fraction of the base's height (default 0.2)")
    ap.add_argument("--metal", type=float, default=0.0, help="PM red channel (default 0)")
    ap.add_argument("--rough", type=float, default=0.8, help="PM green channel (default 0.8)")
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    cfg = {
        "base": to_container(args.base), "source": to_container(args.source),
        "out": to_container(args.out), "colour": to_container(args.colour) if args.colour else None,
        "size": args.size, "samples": args.samples,
        "lock": [s for s in args.lock.split(",") if s], "lock_weight": args.lock_weight,
        "align": args.align, "cut_margin": args.cut_margin, "pose_match": not args.no_pose_match,
        "free_slide": args.free_slide,
        "remesh": args.remesh, "seam": args.seam,
        "check": args.check, "blend": to_container(args.blend) if args.blend else None,
        "extras": [to_container(e) for e in args.extra],
        "extras_hidden": [to_container(e) for e in args.extra_hidden],
        "wrap_method": args.wrap_method, "smooth_radius": args.smooth_radius,
        "smooth_passes": args.smooth_passes,
        "metal": args.metal, "rough": args.rough, "ray": args.ray,
    }
    info = exec_json(BLENDER, cfg, "BG3PROJECT ", timeout=args.timeout)
    if info is None:
        return 1
    print(f"  base       {info['base_faces']:,} faces, {info['vertex_groups']} weight groups, "
          f"{info['bones']} bones, kept")
    print(f"  wrap       mean move {info['mean_move']:.4f}, max {info['max_move']:.4f}, "
          f"{info['locked']:,} verts locked")
    for name, share in info.get("unreached", {}).items():
        flag = "" if share < 0.02 else "   <- the shapes do not line up, or raise --ray"
        print(f"  {name:<10} {share * 100:.1f}% of texels unreached{flag}")
    for k, v in info["written"].items():
        print(f"  wrote      {v}")
    profile = write_lslib_profile(f"{args.out}.glb", args.base)
    print(f"  profile    EXT_lslib_profile: {profile}")
    record = Path(f"{args.out}.json")
    info = json.loads(record.read_text())
    info["lslib_profile"] = profile
    if args.dds:
        for name, dds in write_dds(info["written"]).items():
            info["written"][name] = dds
            print(f"  wrote      {dds}")
    record.write_text(json.dumps(info, indent=1))
    if args.blend:
        print(f"  wrote      {args.blend}")
    print(f"  record     {args.out}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

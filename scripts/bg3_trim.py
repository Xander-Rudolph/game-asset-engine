#!/usr/bin/env python3
"""Slim a game body in place: pull its skin towards its bones, region by region.

    scripts/bg3_trim.py BASE.glb --out output/bg3/<name> [--slim thigh=0.78 ...]
        [--also PART.glb ...] [--extra HEAD.glb ...] [--posed-check] [--blend PATH]

No generated shape and no AI stage are involved: the game's own mesh is moved,
and its topology, UVs, weights, vertex order and LODs stay as they were, so it
animates on the game's skeleton the way the original does.  It was written for
Baldur's Gate 3 bodies converted to glTF by LSLib's Divine.

How the move is made.  Each limb bone stands for a segment, head to the head of
the next joint (upper arm Shoulder to Elbow, forearm Elbow to Wrist, thigh Hip
to Knee, shin Knee to Ankle, the spine Root, Spine1, Spine2, Chest, Neck), and
twist bones stand for their limb's segment.  A vertex's offset from the
nearest point of each segment it is weighted to is scaled by that region's
factor, and the results are blended by the vertex's own skin weights, so the
factors meet without a step.  Bones with no segment (hands, feet, neck, head)
keep factor 1, which leaves hands and feet as they were and tapers the forearm
and shin into them.  The neck ring, the open edge loop highest on the mesh,
where the head carries on vertex for vertex, is held still and the hold eases
off over --seam of the height.  Coincident vertices on shell seams move
together, and the normals are rebuilt from the moved faces.

--also trims another skinned part with the same field (private parts, which
sit on the pelvis and would float off a slimmer one), writing <out>_<stem>.glb
for each; a part replaced in the game has to be replaced as well.  --extra
loads an untouched part (a head) beside the result in the check files for a
clipping look.  --posed-check writes <out>_posed.glb, the trimmed body and the
original posed alike (arms down, elbows bent, one leg forward), because a rest
pose hides what animation shows.

Outputs: <out>.glb (armature, body and LODs, with LSLib's EXT_lslib_profile
metadata copied from BASE so Divine converts it), <out>_preview.glb (LOD0
only), <out>.json; with --gr2 RAW.GR2 also <out>.gr2 by Divine
`convert-model --conform-path RAW.GR2` under Wine (see scripts/bg3_pack.py).

The base mesh is the game's, so it and everything made from it stay outside
the repository (MODELS_DIR/bg3_library, output/bg3/), as the note says:
docs/reference/bg3-toolkit.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import exec_json  # noqa: E402
from bg3_project import to_container, write_lslib_profile  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# Factor per region: the share of a vertex's distance from its bone that it
# keeps.  1.0 leaves a region alone.  The defaults aim at a slight, wiry
# figure: thinner arms and legs, no belly, narrower hips, chest nearly kept.
DEFAULT_SLIM = {
    "upper_arm": 0.80, "forearm": 0.85, "scapula": 0.92,
    "thigh": 0.80, "shin": 0.85,
    "pelvis": 0.88, "belly": 0.80, "waist": 0.85, "chest": 0.92,
}

BLENDER = r'''
import bpy, sys, json, os, math
from mathutils import Vector, Matrix, kdtree

cfg = json.loads(sys.argv[-1])
log = []
def say(m):
    log.append(m)


def load(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path, bone_heuristic="TEMPERANCE")
    return [o for o in bpy.data.objects if o not in before]


def select_only(objs, active=None):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
objs = load(cfg["base"])
arm = next((o for o in objs if o.type == "ARMATURE"), None)
if arm is None:
    raise SystemExit("the base file holds no armature")
meshes = [o for o in objs if o.type == "MESH" and (o.parent == arm or any(m.type == "ARMATURE" for m in o.modifiers))]
for o in objs:
    if o.type == "MESH" and o not in meshes:
        bpy.data.objects.remove(o, do_unlink=True)
meshes.sort(key=lambda o: -len(o.data.vertices))
base = meshes[0]
bpy.context.view_layer.update()


def head(name):
    b = arm.data.bones.get(name)
    return (arm.matrix_world @ b.head_local) if b else None


def segment_of(name):
    """(region, start, end) of the limb segment this bone stands for, or None."""
    parts = name.split("_")
    side = "L" if "L" in parts else "R" if "R" in parts else None   # Hip_L_Twist_01, Elbow_Twist_L
    for pre, nxt, region in (("Shoulder", "Elbow", "upper_arm"), ("Elbow", "Wrist", "forearm"),
                             ("Hip", "Knee", "thigh"), ("Knee", "Ankle", "shin"),
                             ("Scapula", "Shoulder", "scapula")):
        if name.startswith(pre) and side:
            a, b = head(f"{pre}_{side}"), head(f"{nxt}_{side}")
            if a is not None and b is not None:
                return region, a, b
    spine = {"Root_M": ("Spine1_M", "pelvis"), "Spine1_M": ("Spine2_M", "belly"),
             "Spine2_M": ("Chest_M", "waist"), "Chest_M": ("Neck_M", "chest")}
    if name in spine:
        nxt, region = spine[name]
        a, b = head(name), head(nxt)
        if a is not None and b is not None:
            return region, a, b
    return None


def closest_on(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(1e-12, ab.dot(ab))))
    return a + ab * t


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
        z = sum((obj.matrix_world @ obj.data.vertices[i].co).z for i in comp) / len(comp)
        if best is None or z > best[0]:
            best = (z, comp)
    return [obj.matrix_world @ obj.data.vertices[i].co for i in best[1]] if best else []


lo = min((base.matrix_world @ v.co).z for v in base.data.vertices)
hi = max((base.matrix_world @ v.co).z for v in base.data.vertices)
height = hi - lo
slim = cfg["slim"]
seam = float(cfg.get("seam", 0.08)) * height
ring = top_loop(base) if seam > 0 else []
say(f"base: {len(base.data.vertices):,} verts, height {height:.3f}; neck ring {len(ring)} verts held, "
    f"easing over {seam * 100:.1f} cm; factors {slim}")


def trim(obj, hold_ring):
    mw, mwi = obj.matrix_world, obj.matrix_world.inverted()
    segs = {}
    for g in obj.vertex_groups:
        s = segment_of(g.name)
        if s and slim.get(s[0], 1.0) != 1.0:
            segs[g.index] = s
    old = [mw @ v.co for v in obj.data.vertices]
    new = []
    for i, v in enumerate(obj.data.vertices):
        p = old[i]
        acc, wsum = Vector((0.0, 0.0, 0.0)), 0.0
        for ge in v.groups:
            if ge.weight <= 0:
                continue
            s = segs.get(ge.group)
            if s is None:
                acc += p * ge.weight
            else:
                region, a, b = s
                c = closest_on(p, a, b)
                acc += (c + (p - c) * slim[region]) * ge.weight
            wsum += ge.weight
        q = acc / wsum if wsum > 0 else p
        if hold_ring and ring:
            d = min((p - r).length for r in ring)
            q = p + (q - p) * min(1.0, d / seam)
        new.append(q)
    # coincident vertices (shell seams) move as one
    kd = kdtree.KDTree(len(old))
    for i, p in enumerate(old):
        kd.insert(p, i)
    kd.balance()
    for i, p in enumerate(old):
        group = [j for (_, j, _) in kd.find_range(p, 1e-5)]
        if len(group) > 1:
            m = sum((new[j] for j in group), Vector((0.0, 0.0, 0.0))) / len(group)
            for j in group:
                new[j] = m
    moved = [(new[i] - old[i]).length for i in range(len(old))]
    for i, v in enumerate(obj.data.vertices):
        v.co = mwi @ new[i]
    obj.data.update()
    # normals from the moved faces, merged across coincident vertices
    acc = [Vector((0.0, 0.0, 0.0)) for _ in obj.data.vertices]
    for f in obj.data.polygons:
        for vi in f.vertices:
            acc[vi] += f.normal * f.area
    kd2 = kdtree.KDTree(len(obj.data.vertices))
    for i, v in enumerate(obj.data.vertices):
        kd2.insert(v.co, i)
    kd2.balance()
    merged = []
    for v in obj.data.vertices:
        n = Vector((0.0, 0.0, 0.0))
        for (_, j, _) in kd2.find_range(v.co, 1e-5):
            n += acc[j]
        merged.append(tuple(n.normalized()) if n.length > 1e-12 else (0.0, 0.0, 1.0))
    obj.data.normals_split_custom_set_from_vertices(merged)
    obj.data.update()
    # where the move went, by heaviest group
    by = {}
    for i, v in enumerate(obj.data.vertices):
        if v.groups:
            g = max(v.groups, key=lambda ge: ge.weight).group
            by.setdefault(obj.vertex_groups[g].name, []).append(moved[i])
    top = sorted(by.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))[:6]
    say(f"{obj.name}: mean move {sum(moved) / len(moved):.4f}, max {max(moved):.4f}; most moved: "
        + ", ".join(f"{k} {sum(m) / len(m):.3f}" for k, m in top))
    return moved


def width(obj, z0, z1):
    xs = [(obj.matrix_world @ v.co) for v in obj.data.vertices]
    band = [p for p in xs if z0 <= p.z <= z1 and abs(p.x) < 0.25 * height]
    return (max(p.x for p in band) - min(p.x for p in band)) if band else 0.0, \
           (max(p.y for p in band) - min(p.y for p in band)) if band else 0.0


bands = {"waist": (0.55, 0.62), "hips": (0.47, 0.53), "thigh": (0.33, 0.40)}
before = {k: width(base, lo + a * height, lo + b * height) for k, (a, b) in bands.items()}

# untouched copies for the posed comparison
originals = {}
if cfg.get("posed_check"):
    select_only([base])
    bpy.ops.object.duplicate()
    originals["base"] = bpy.context.view_layer.objects.active
    originals["base"].name = "original"

for o in meshes:
    trim(o, hold_ring=True)
after = {k: width(base, lo + a * height, lo + b * height) for k, (a, b) in bands.items()}
say("widths x, depth y (m), before -> after: " + "; ".join(
    f"{k} {before[k][0]:.3f}x{before[k][1]:.3f} -> {after[k][0]:.3f}x{after[k][1]:.3f}" for k in bands))

out = cfg["out"]
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
written = {}


def export(objs, path, skins=True):
    select_only(objs, objs[0])
    kw = dict(filepath=path, export_format="GLB", use_selection=True, export_skins=skins,
              export_animations=False, export_yup=True, export_materials="NONE")
    try:
        bpy.ops.export_scene.gltf(export_vertex_color="ACTIVE", **kw)
    except TypeError:
        bpy.ops.export_scene.gltf(**kw)


hidden = [o for o in originals.values()]
for o in hidden:
    o.hide_set(True)
export(meshes + [arm], f"{out}.glb")
written["glb"] = f"{out}.glb"
export([base, arm], f"{out}_preview.glb")
written["preview"] = f"{out}_preview.glb"

# parts trimmed with the same field
for path in cfg.get("also") or []:
    stem = os.path.splitext(os.path.basename(path))[0]
    pobjs = load(path)
    parm = next((o for o in pobjs if o.type == "ARMATURE"), None)
    pmeshes = [o for o in pobjs if o.type == "MESH"]
    for o in pmeshes:
        trim(o, hold_ring=False)
    export(pmeshes + ([parm] if parm else []), f"{out}_{stem}.glb")
    written[stem] = f"{out}_{stem}.glb"
    for o in pobjs:
        o.hide_set(True)

# untouched parts for a clipping look
extras = []
for path in cfg.get("extras") or []:
    pobjs = load(path)
    stem = os.path.splitext(os.path.basename(path))[0]
    for o in pobjs:
        if o.type == "MESH" and "_lod" not in o.name.lower():
            m = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = m
            for md in list(o.modifiers):
                o.modifiers.remove(md)
            o.name = stem
            extras.append(o)
    for o in pobjs:
        if o not in extras:
            bpy.data.objects.remove(o, do_unlink=True)

if cfg.get("posed_check"):
    def pose(armature):
        def turn(name, axis, deg):
            pb = armature.pose.bones[name]
            bpy.context.view_layer.update()
            h = armature.matrix_world @ pb.head
            R = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-h)
            pb.matrix = armature.matrix_world.inverted() @ R @ armature.matrix_world @ pb.matrix
            bpy.context.view_layer.update()
        turn("Shoulder_L", "Y", 55); turn("Shoulder_R", "Y", -55)
        turn("Elbow_L", "Z", -40); turn("Elbow_R", "Z", 40)
        turn("Hip_L", "X", 45); turn("Knee_L", "X", -70); turn("Hip_R", "X", -20)
    pose(arm)
    pair = []
    for o, dx in ((base, 0.0), (originals["base"], 0.9)):
        o.hide_set(False)
        select_only([o])
        bpy.ops.object.duplicate()
        d = bpy.context.view_layer.objects.active
        for md in list(d.modifiers):
            if md.type == "ARMATURE":
                bpy.ops.object.modifier_apply(modifier=md.name)
        mw = d.matrix_world.copy()
        d.parent = None
        d.matrix_world = Matrix.Translation((dx, 0.0, 0.0)) @ mw
        pair.append(d)
    export(pair, f"{out}_posed.glb", skins=False)
    written["posed"] = f"{out}_posed.glb"
    for d in pair:
        bpy.data.objects.remove(d, do_unlink=True)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()

if extras:
    export([base] + extras + [arm], f"{out}_check.glb")
    written["check"] = f"{out}_check.glb"

if cfg.get("blend"):
    bpy.ops.wm.save_as_mainfile(filepath=cfg["blend"], copy=True)
    written["blend"] = cfg["blend"]

info = {"base": cfg["base"], "slim": slim, "verts": len(base.data.vertices),
        "lods": [o.name for o in meshes[1:]], "widths_before": before, "widths_after": after,
        "written": written, "log": log}
with open(f"{out}.json", "w") as f:
    json.dump(info, f, indent=1)
print("BG3TRIM " + json.dumps(info))
'''


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", help="the game body as glTF (Divine's convert-model output)")
    ap.add_argument("--out", required=True, help="output prefix, e.g. output/bg3/halfling_f_trim")
    ap.add_argument("--slim", action="append", default=[], metavar="REGION=FACTOR",
                    help="override a region's factor; regions: " + ", ".join(
                        f"{k} ({v})" for k, v in DEFAULT_SLIM.items()))
    ap.add_argument("--seam", type=float, default=0.08,
                    help="hold the neck ring and ease off over this fraction of the height (default 0.08)")
    ap.add_argument("--also", action="append", default=[], metavar="GLB",
                    help="another skinned part to trim with the same field; repeatable")
    ap.add_argument("--extra", action="append", default=[], metavar="GLB",
                    help="an untouched part to show beside the result in <out>_check.glb; repeatable")
    ap.add_argument("--posed-check", action="store_true",
                    help="write <out>_posed.glb: the trimmed and the original body posed alike")
    ap.add_argument("--blend", metavar="PATH", help="also save the scene as a .blend")
    ap.add_argument("--gr2", metavar="RAW_GR2",
                    help="also convert to <out>.gr2 with Divine, conformed to this original GR2")
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    slim = dict(DEFAULT_SLIM)
    for spec in args.slim:
        k, _, v = spec.partition("=")
        if k not in slim:
            ap.error(f"unknown region {k!r}; regions are {', '.join(slim)}")
        slim[k] = float(v)
    cfg = {"base": to_container(args.base), "out": to_container(args.out), "slim": slim,
           "seam": args.seam, "also": [to_container(p) for p in args.also],
           "extras": [to_container(p) for p in args.extra], "posed_check": args.posed_check,
           "blend": to_container(args.blend) if args.blend else None}
    info = exec_json(BLENDER, cfg, "BG3TRIM ", timeout=args.timeout)
    if info is None:
        return 1
    for line in info["log"]:
        print(f"  {line}")
    profile = write_lslib_profile(f"{args.out}.glb", args.base)
    print(f"  profile    EXT_lslib_profile: {profile}")
    for k, v in info["written"].items():
        print(f"  wrote      {v}")
    if args.gr2:
        from bg3_pack import divine, fail_on, winpath
        r = divine(["-a", "convert-model", "-i", "glb", "-o", "gr2",
                    "-s", winpath(Path(f"{args.out}.glb")), "-d", winpath(Path(f"{args.out}.gr2")),
                    "--conform-path", winpath(Path(args.gr2))])
        fail_on(r, "convert-model")
        print(f"  wrote      {args.out}.gr2  ({Path(f'{args.out}.gr2').stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

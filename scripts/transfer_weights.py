#!/usr/bin/env python3
"""Put a rig solved on a low-poly proxy back onto the high-resolution mesh.

    scripts/transfer_weights.py output/rigged/hero.fbx input/3d/hero_full.glb \
        --out output/rigged/hero_full.fbx

Why this exists: the rigger decimates before it solves, and the FBX it hands
back contains the DECIMATED mesh, not the one you gave it.  Feed it a 600k face
model with the budget at 48,000 and you get a 48,000 face model with a skeleton
in it.  The skeleton is good.  Your mesh is gone.

That trade is usually the right one for a game asset, and for a sprite it is
always the right one.  When it is not -- a hero seen close up, a model that has
to go back to a DCC tool, anything where the detail was the point -- this takes
the skeleton and the skin weights from the rigged proxy and interpolates them
onto the original surface, so you keep both.

The transfer is nearest-face with interpolated corner data, which is the right
mode here: proxy and original describe the same surface, so a point on one is
almost always inside a face on the other.  Nearest-vertex would quantise the
weights to the proxy's much sparser vertices and produce visible banding at the
joints.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import container as _container, exec_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTAINER = _container()

BLENDER = r'''
import bpy, sys, json, os

cfg = json.loads(sys.argv[-1])


def load(path):
    p = path.lower()
    if p.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=path)
    elif p.endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=path)
    else:
        bpy.ops.import_scene.gltf(filepath=path)


def join_meshes(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


bpy.ops.wm.read_factory_settings(use_empty=True)

# --- the rigged proxy: skeleton and weights come from here ------------------
load(cfg["rigged"])
arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
if arm is None:
    raise SystemExit("no armature in " + cfg["rigged"])
proxy = join_meshes([o for o in bpy.data.objects if o.type == "MESH"])
proxy.name = "proxy"
proxy_faces = len(proxy.data.polygons)
groups = [g.name for g in proxy.vertex_groups]
if not groups:
    raise SystemExit("the rigged file has no vertex groups, so there are no "
                     "weights to transfer")

# --- the original mesh ------------------------------------------------------
before = set(bpy.data.objects)
load(cfg["dense"])
dense_objs = [o for o in bpy.data.objects if o.type == "MESH" and o not in before]
if not dense_objs:
    raise SystemExit("no mesh in " + cfg["dense"])
dense = join_meshes(dense_objs)
dense.name = "dense"
dense_faces = len(dense.data.polygons)

# The proxy is normalised by the rigger (centred, scaled into a unit box), so
# the original almost never sits on top of it.  Match the bounding boxes before
# transferring, or every weight is read from the wrong part of the body.
def box(ob):
    import mathutils
    lo = mathutils.Vector((1e9, 1e9, 1e9))
    hi = mathutils.Vector((-1e9, -1e9, -1e9))
    for c in ob.bound_box:
        w = ob.matrix_world @ mathutils.Vector(c)
        lo = mathutils.Vector((min(lo[i], w[i]) for i in range(3)))
        hi = mathutils.Vector((max(hi[i], w[i]) for i in range(3)))
    return lo, hi

if cfg["align"]:
    plo, phi = box(proxy)
    dlo, dhi = box(dense)
    pspan = max((phi - plo)[i] for i in range(3)) or 1.0
    dspan = max((dhi - dlo)[i] for i in range(3)) or 1.0
    k = pspan / dspan
    dense.scale = (k, k, k)
    bpy.context.view_layer.update()
    dlo, dhi = box(dense)
    shift = ((plo + phi) / 2.0) - ((dlo + dhi) / 2.0)
    dense.location = dense.location + shift
    bpy.ops.object.select_all(action="DESELECT")
    dense.select_set(True)
    bpy.context.view_layer.objects.active = dense
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# --- transfer ---------------------------------------------------------------
for name in groups:
    if name not in dense.vertex_groups:
        dense.vertex_groups.new(name=name)

bpy.ops.object.select_all(action="DESELECT")
dense.select_set(True)
bpy.context.view_layer.objects.active = dense

mod = dense.modifiers.new("weights", "DATA_TRANSFER")
mod.object = proxy
mod.use_vert_data = True
mod.data_types_verts = {"VGROUP_WEIGHTS"}
# Interpolated across the nearest face, not snapped to the nearest vertex.
mod.vert_mapping = "POLYINTERP_NEAREST"
bpy.ops.object.datalayout_transfer(modifier=mod.name)
bpy.ops.object.modifier_apply(modifier=mod.name)

# --- bind -------------------------------------------------------------------
dense.parent = arm
dense.matrix_parent_inverse = arm.matrix_world.inverted()
armmod = dense.modifiers.new("armature", "ARMATURE")
armmod.object = arm

bpy.data.objects.remove(proxy, do_unlink=True)

# How many vertices actually got weight. A vertex with none is a vertex that
# will not move, which reads as a piece of the model left behind mid-stride.
unweighted = 0
for v in dense.data.vertices:
    if not any(g.weight > 0.0 for g in v.groups):
        unweighted += 1

out = cfg["out"]
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
dense.select_set(True)
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
if out.lower().endswith(".fbx"):
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True,
                             add_leaf_bones=False, bake_anim=False)
else:
    bpy.ops.export_scene.gltf(filepath=out, use_selection=True,
                              export_format="GLB")

print("TRANSFER " + json.dumps({
    "out": out,
    "proxy_faces": proxy_faces,
    "dense_faces": dense_faces,
    "bones": len(arm.data.bones),
    "groups": len(groups),
    "verts": len(dense.data.vertices),
    "unweighted": unweighted,
}))
'''


def to_container(p: str) -> str:
    if p.startswith("/app/"):
        return p
    path = Path(p)
    if not path.is_absolute():
        path = ROOT / path
    for host, cont in ((ROOT / "output", "/app/output"), (ROOT / "input", "/app/input")):
        try:
            return f"{cont}/{path.resolve().relative_to(host)}"
        except ValueError:
            continue
    return str(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rigged", help="the FBX the rigger produced (proxy mesh plus skeleton)")
    ap.add_argument("dense", help="the original high-resolution mesh")
    ap.add_argument("--out", help="where to write the rigged dense mesh "
                                  "(.fbx or .glb; default alongside the dense mesh)")
    ap.add_argument("--timeout", type=int, default=1800,
                    help="seconds before giving up on Blender (default 1800)")
    ap.add_argument("--no-align", action="store_true",
                    help="skip bounding-box alignment. Only correct when the two "
                         "meshes already share a coordinate frame")
    args = ap.parse_args()

    out = args.out
    if not out:
        p = Path(args.dense)
        out = str(p.with_name(p.stem + "_rigged.fbx"))

    cfg = {
        "rigged": to_container(args.rigged),
        "dense": to_container(args.dense),
        "out": to_container(out),
        "align": not args.no_align,
    }
    info = exec_json(BLENDER, cfg, "TRANSFER ", timeout=args.timeout)
    if info is None:
        return 1
    print(f"  proxy      {info['proxy_faces']:,} faces, {info['bones']} bones, "
          f"{info['groups']} weight groups")
    print(f"  original   {info['dense_faces']:,} faces, {info['verts']:,} verts")
    pct = info["unweighted"] / max(1, info["verts"]) * 100
    flag = "" if pct < 1.0 else "   <- check the alignment"
    print(f"  unweighted {info['unweighted']:,} verts ({pct:.2f}%){flag}")
    print(f"  wrote      {out}")
    if pct >= 1.0:
        print()
        print("  More than 1% of vertices got no weight. Usually the two meshes did")
        print("  not line up: the rigger normalises its output, so pass the mesh you")
        print("  actually gave it, or re-run without --no-align.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Measure what decimation costs a mesh, so a face budget is chosen and not guessed.

    scripts/decimation_report.py output/mesh/beast_chimera_textured.glb
    scripts/decimation_report.py input/3d/hero.glb --faces 200000,50000,18000,8000,4000,2000
    scripts/decimation_report.py hero.glb --sprite 128 --json out.json

Runs Blender inside whichever ComfyUI container is running, via docker exec,
which is the only place in this stack with a glTF/FBX importer and a GPU
renderer.  For every face budget it reports three different kinds of damage,
because they do not arrive together:

  surface   how far the decimated surface moved, as a percentage of the
            model's own height.  p95 is the number to read; max is one
            spike on one spur and says little.

  silhouette  IoU of the rendered alpha against the full-resolution render,
            at the size the asset is actually seen at.  This is the one that
            matters for a 2D game: a sprite is its outline.

  texture   mean RGB difference inside the shared silhouette, 0-255.  UVs
            survive a collapse decimation, but the triangles under them do
            not, so a texture starts to swim long before the outline breaks.

The camera is the isometric one (elevation 30, azimuth 45, orthographic) —
see docs/guide/facings.md — so the silhouette figure is measured from the
angle the game will use rather than from a flattering three-quarter view.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import container as _container, exec_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTAINER = _container()

BLENDER = r'''
import bpy, sys, json, math, os, time
import numpy as np
from mathutils import Vector, Euler
from mathutils.bvhtree import BVHTree

cfg = json.loads(sys.argv[-1])
SIZE = cfg["sprite"]
os.makedirs(cfg["shots"], exist_ok=True)


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    p = path.lower()
    if p.endswith(".fbx"):
        bpy.ops.import_scene.fbx(filepath=path)
    elif p.endswith(".obj"):
        bpy.ops.wm.obj_import(filepath=path)
    else:
        bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if not meshes:
        raise SystemExit("no mesh in " + path)
    # One object: a glTF scene can arrive split, and every measurement below
    # wants a single surface to compare against.
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return ob


def tris(ob):
    """Vertices and triangle indices in world space, as arrays."""
    me = ob.data
    me.calc_loop_triangles()
    v = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", v)
    v = v.reshape(-1, 3)
    t = np.empty(len(me.loop_triangles) * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("vertices", t)
    return v, t.reshape(-1, 3)


def bounds(v):
    return v.min(axis=0), v.max(axis=0)


def deviation(ref_bvh, v, t, height):
    """Distance from a sample of this surface to the reference surface.

    Sampled at vertices AND face centroids: a collapse decimation moves
    vertices onto the old surface where it can, so vertices alone flatter
    the result — the error lives in the middle of the new, larger faces.
    """
    pts = np.vstack([v, v[t].mean(axis=1)])
    d = []
    for p in pts:
        hit = ref_bvh.find_nearest(Vector(p))
        if hit[0] is not None:
            d.append((Vector(p) - hit[0]).length)
    d = np.asarray(d) / height * 100.0
    return {
        "mean": float(d.mean()),
        "p95": float(np.percentile(d, 95)),
        "max": float(d.max()),
    }


# --- camera: the isometric one, orthographic ------------------------
def setup_scene(ob, textured):
    for o in list(bpy.data.objects):
        if o.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(o, do_unlink=True)

    v, _ = tris(ob)
    lo, hi = bounds(v)
    size = float(max(hi - lo)) or 1.0
    centre = (lo + hi) / 2.0
    ob.location = (-centre[0], -centre[1], -centre[2])
    bpy.context.view_layer.update()

    cam_data = bpy.data.cameras.new("cam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = size * 1.15
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    elev = math.radians(cfg["elevation"])
    az = math.radians(cfg["azimuth"])
    dist = size * 3.0
    cam.location = (dist * math.cos(elev) * math.sin(az),
                    -dist * math.cos(elev) * math.cos(az),
                    dist * math.sin(elev))
    cam.rotation_euler = Euler((math.radians(90) - elev, 0.0, az), "XYZ")

    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.22
    bpy.context.scene.world = world
    key = bpy.data.lights.new("key", "SUN")
    key.energy = 1.6
    key_ob = bpy.data.objects.new("key", key)
    bpy.context.collection.objects.link(key_ob)
    key_ob.rotation_euler = Euler((math.radians(55), 0, math.radians(30)), "XYZ")
    key_ob.parent = cam

    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x = sc.render.resolution_y = SIZE
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    if not textured:
        clay = bpy.data.materials.new("clay")
        clay.use_nodes = True
        b = clay.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.55, 0.54, 0.52, 1.0)
        b.inputs["Roughness"].default_value = 0.65
        ob.data.materials.clear()
        ob.data.materials.append(clay)


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    px = np.empty(len(im.pixels), dtype=np.float32)
    im.pixels.foreach_get(px)
    bpy.data.images.remove(im)
    return px.reshape(SIZE, SIZE, 4)


def compare(a, b):
    """Silhouette IoU and, inside the shared silhouette, colour difference."""
    ma, mb = a[..., 3] > 0.5, b[..., 3] > 0.5
    inter = np.logical_and(ma, mb)
    union = np.logical_or(ma, mb)
    iou = float(inter.sum() / union.sum()) if union.sum() else 1.0
    if inter.sum():
        d = np.abs(a[..., :3][inter] - b[..., :3][inter]).mean() * 255.0
    else:
        d = 0.0
    lost = float(np.logical_and(ma, ~mb).sum())
    return iou, float(d), lost / max(1.0, float(ma.sum())) * 100.0


# --- reference -------------------------------------------------------------
src = cfg["src"]
ob = load(src)
v0, t0 = tris(ob)
lo, hi = bounds(v0)
height = float(hi[2] - lo[2]) or 1.0
ref_faces = len(t0)
ref_bvh = BVHTree.FromPolygons([tuple(p) for p in v0.tolist()],
                               [tuple(f) for f in t0.tolist()])
textured = any(
    m and m.use_nodes and any(n.type == "TEX_IMAGE" for n in m.node_tree.nodes)
    for m in (s.material for s in ob.material_slots))
setup_scene(ob, textured)
ref_img = render(cfg["shots"] + "/reference.png")

rows = []
for target in cfg["faces"]:
    if target >= ref_faces:
        continue
    ob = load(src)
    t_start = time.time()
    me = ob.data
    me.calc_loop_triangles()
    cur = len(me.loop_triangles)
    mod = ob.modifiers.new("dec", "DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = target / cur
    mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    secs = time.time() - t_start

    v, t = tris(ob)
    dev = deviation(ref_bvh, v, t, height)
    setup_scene(ob, textured)
    img = render(cfg["shots"] + f"/faces_{target}.png")
    iou, rgb, lost = compare(ref_img, img)
    rows.append({
        "target": target, "faces": len(t), "verts": len(v),
        "seconds": round(secs, 1), "surface": dev,
        "iou": iou, "rgb": rgb, "silhouette_lost_pct": lost,
    })

print("REPORT " + json.dumps({
    "src": src, "ref_faces": ref_faces, "ref_verts": len(v0),
    "height": height, "textured": textured, "sprite": SIZE, "rows": rows,
}))
'''


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", help=".glb/.gltf/.fbx/.obj, host path or container path")
    ap.add_argument("--faces", default="200000,100000,50000,25000,18000,12000,8000,6000,4000,2000,1000",
                    help="comma-separated face budgets to test")
    ap.add_argument("--sprite", type=int, default=128,
                    help="render size for the silhouette test (default 128, the "
                         "size a map token is actually drawn at)")
    ap.add_argument("--elevation", type=float, default=30.0)
    ap.add_argument("--azimuth", type=float, default=45.0)
    ap.add_argument("--json", type=Path, help="also write the raw numbers here")
    ap.add_argument("--timeout", type=int, default=3600,
                    help="seconds before giving up on Blender (default 3600). A "
                         "sweep over many budgets is the slowest thing here")
    args = ap.parse_args()

    src = args.model
    if not src.startswith("/app/"):
        p = Path(src)
        if not p.is_absolute():
            p = ROOT / p
        for host, cont in ((ROOT / "output", "/app/output"),
                           (ROOT / "input", "/app/input")):
            try:
                src = f"{cont}/{p.resolve().relative_to(host)}"
                break
            except ValueError:
                continue
        else:
            src = str(p)

    run_id = f"{os.getpid()}_{int(time.time())}"
    cfg = {
        "src": src,
        "faces": [int(f) for f in args.faces.split(",")],
        "sprite": args.sprite,
        "elevation": args.elevation,
        "azimuth": args.azimuth,
        # Under /app/output, which IS bind mounted, so the renders the numbers
        # describe can be looked at. They used to go to container /tmp, which
        # meant every measurement was unfalsifiable by eye.
        "shots": f"/app/output/_dec/{run_id}",
    }
    print(f"  renders {ROOT / 'output' / '_dec' / run_id}")
    info = exec_json(BLENDER, cfg, "REPORT ", timeout=args.timeout)
    if info is None:
        return 1

    print(f"{info['src']}")
    print(f"  {info['ref_faces']:,} faces, {info['ref_verts']:,} verts, "
          f"{'textured' if info['textured'] else 'untextured (clay)'}, "
          f"silhouette measured at {info['sprite']}px")
    print()
    print(f"  {'faces':>8}  {'ratio':>6}  {'surface p95':>11}  {'max':>6}  "
          f"{'silhouette':>10}  {'lost':>5}  {'texture':>7}  {'secs':>5}")
    for row in info["rows"]:
        print(f"  {row['faces']:>8,}  {row['faces']/info['ref_faces']:>5.1%}  "
              f"{row['surface']['p95']:>10.3f}%  {row['surface']['max']:>5.2f}%  "
              f"{row['iou']:>9.4f}  {row['silhouette_lost_pct']:>4.1f}%  "
              f"{row['rgb']:>6.1f}  {row['seconds']:>5.1f}")
    print()
    print("  surface = % of model height the surface moved (p95 of sampled points)")
    print("  silhouette = IoU of the rendered alpha vs the full-resolution render")
    print("  texture = mean RGB difference inside the shared silhouette, 0-255")

    if args.json:
        args.json.write_text(json.dumps(info, indent=2))
        print(f"\n  raw -> {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

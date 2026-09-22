#!/usr/bin/env python3
"""Bake the hair the numpy side grew: lens shells, cards, a rendered atlas.

    scripts/bake_hair.py test_bob
    scripts/bake_hair.py test_bob --dir output/hair --dome-mix 1.0 --card-mix 0.6 --samples 64

WHY: scripts/make_hair.py grows guide curves in layers over a scalp cap, and
numpy can turn them into flat cards but not into the two things the research
asks for (docs/reference/hair-cards.md): closed lens shells for the base layer,
the opaque shaped geometry the stylised look is made of (HAIR-150, HAIR-022),
and an atlas rendered from real strands with density falling across the sheet
(HAIR-018, HAIR-052).  Both need Blender, so this runs one Blender job in the
ComfyUI container, the way daz_import_probe.py does, and writes one OBJ that
`daz_import_probe.py scene --wear-obj` places on a head.

WHAT IT READS, all beside each other under --dir: `<name>_guides.npz` (the
guide polylines, their layer, width, atlas slot and U flip), `<name>_atlas.json`
(the slot layout and colours) and `<name>_cap.obj` with its two maps.  It
accepts the files flat in --dir or in a `<name>/` folder inside it.

WHAT IT WRITES, beside them: `<name>.obj` and `.mtl` (one object `hair`, faces
inside to outside under three materials: `<name>_cap`, `<name>_shell`,
`<name>_card`), `<name>_diffuse.png` (RGBA), `<name>_opacity.png` (RGBA, the
mask in every channel), `<name>_pack.png` (R root gradient, G random id, B 0)
and `<name>_bake.json`, the report.

HOW: layer 0 is swept into closed lens shells with end caps by Curve to Mesh,
layers 1 to 3 into flat cards; each card's UVs are mapped to its slot's
rectangle in the atlas; shells take custom normals from a smooth dome by Data
Transfer (HAIR-020, HAIR-066), cards a blend of the radial direction and their
own ribbon normal; the atlas is three Cycles renders of thin hair curves, one
draw per pass, with the colour dilated under alpha 0 in numpy (HAIR-054); the
OBJ is exported on the axes wear_objs imports, re-imported, and the normals and
positions that came back are measured.  Every face is checked to be wound away
from the head, the bug the research found in the old generator.

The container waits for an empty ComfyUI queue and for no other Blender job,
and never runs two of its own at once.  Standard library plus numpy on the
host; Blender 4.5.9 LTS, its numpy 1.26 and Pillow in the container (read
from output/hair_probe_hybrid/report.json and the ComfyUI requirements).
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import json
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import container, exec_json, exec_python  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "hair"
COMFY = "http://127.0.0.1:8188"
SENTINEL = "HAIR_BAKE "
STOP_SENTINEL = "HAIR_STOP "
MATERIALS = ("cap", "shell", "card")
# Game hair sits in 4k to 20k triangles (HAIR-016); reported, not enforced.
BUDGET = (4000, 20000)


# ------------------------------------------------------------ container side

BLENDER = r'''
import json, math, os, sys, time, traceback
import numpy as np
import bpy, bmesh

cfg = json.loads(sys.argv[-1])
NAME = cfg["name"]
D = cfg["dir"]
report = {"blender": bpy.app.version_string, "numpy": np.__version__, "stages_s": {},
          "counts": {}, "normals": {}, "warnings": []}
T0 = time.time()


def path(suffix):
    return os.path.join(D, NAME + suffix)


def stage(name, fn):
    t = time.time()
    out = fn()
    report["stages_s"][name] = round(time.time() - t, 3)
    return out


def unit_rows(a):
    return a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-9)


def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.node_groups,
                 bpy.data.hair_curves, bpy.data.cameras, bpy.data.lights):
        for d in list(coll):
            if d.users == 0:
                coll.remove(d)


def gpu():
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "CUDA"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "CUDA"
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU" if any(d.type == "CUDA" for d in prefs.devices) else "CPU"
    sc.cycles.use_denoising = False
    return sc.cycles.device


def face_dot_radial(V, F):
    """Signed dot of each triangle's geometric normal with the direction from
    the origin (the scalp centre) to its centroid: positive is wound outward."""
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = unit_rows(np.cross(b - a, c - a))
    r = unit_rows((a + b + c) / 3.0)
    return (n * r).sum(axis=1)


def dot_report(d):
    return {"mean": round(float(d.mean()), 4), "min": round(float(d.min()), 4),
            "fraction_positive": round(float((d > 0).mean()), 4), "faces": int(len(d))}


def corner_dot_radial(me):
    n = len(me.loops)
    nrm = np.empty(n * 3); me.corner_normals.foreach_get("vector", nrm); nrm = nrm.reshape(-1, 3)
    vi = np.empty(n, dtype=np.int32); me.loops.foreach_get("vertex_index", vi)
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    d = (nrm * unit_rows(co[vi])).sum(axis=1)
    return {"mean_dot": round(float(d.mean()), 4), "mean_abs_dot": round(float(np.abs(d).mean()), 4),
            "min_dot": round(float(d.min()), 4), "corners": n}


def smooth_vertex_normals(V, F):
    """Area-weighted vertex normals of a triangle mesh: the ribbon frame a card
    shades with when its faces are smooth."""
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    fn = np.cross(b - a, c - a)
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, F[:, k], fn)
    return unit_rows(vn)


def read_mesh(me, matrix=None):
    """Vertices, polygons as loop-index lists, loop vertex indices, and the
    named attributes Curve to Mesh carried across, each on its own domain.

    `matrix` is the owning object's matrix_world: the OBJ importer keeps the
    file's own coordinates in the mesh and puts the axis conversion on the
    object, so a mesh read without it is on the file's axes (measured: the cap
    pole landed 13.6 cm from where it started)."""
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co)
    V = co.reshape(-1, 3)
    if matrix is not None:
        M = np.array(matrix, dtype=np.float64)
        V = V @ M[:3, :3].T + M[:3, 3]
    lv = np.empty(len(me.loops), dtype=np.int32); me.loops.foreach_get("vertex_index", lv)
    starts = np.empty(len(me.polygons), dtype=np.int32); me.polygons.foreach_get("loop_start", starts)
    totals = np.empty(len(me.polygons), dtype=np.int32); me.polygons.foreach_get("loop_total", totals)
    attrs = {}
    for key in ("u", "v", "ci"):
        if key not in me.attributes:
            continue
        at = me.attributes[key]
        n = len(at.data)
        arr = np.empty(n, dtype=np.int32 if at.data_type == "INT" else np.float64)
        at.data.foreach_get("value", arr)
        attrs[key] = (at.domain, arr)
    return V, lv, starts, totals, attrs


def triangulate(lv, starts, totals):
    """Fan triangles per polygon, as loop indices, so per-corner data follows."""
    tris = []
    for s, n in zip(starts, totals):
        for i in range(1, n - 1):
            tris.append((s, s + i, s + i + 1))
    return np.array(tris, dtype=np.int32).reshape(-1, 3)


def per_corner(attrs, key, lv, loops):
    domain, arr = attrs[key]
    if domain == "POINT":
        return arr[lv[loops]].ravel()
    if domain == "CORNER":
        return arr[loops].ravel()
    raise RuntimeError(f"attribute {key} landed on the {domain} domain after Curve to Mesh")


# ---------------------------------------------------------------- load
def load():
    g = np.load(cfg["guides"])
    with open(cfg["atlas"]) as fh:
        atlas = json.load(fh)
    P = g["points"].astype(np.float64)
    # make_hair is +Y up, +Z the face; Blender is +Z up, -Y the face: (x, y, z) -> (x, -z, y),
    # which is what the OBJ importer does with forward_axis NEGATIVE_Z, up_axis Y
    B = np.stack([P[:, 0], -P[:, 2], P[:, 1]], axis=1)
    G = {"B": B, "off": g["offsets"].astype(np.int64), "layer": g["layer"].astype(np.int64),
         "lock": g["lock"], "wr": g["width_root"].astype(np.float64), "wt": g["width_tip"].astype(np.float64),
         "slot": g["slot"].astype(np.int64), "uflip": g["uflip"].astype(np.int64), "tent": g["tent"].astype(np.int64),
         "R": float(g["head_radius_cm"]), "cling": float(g["cling_cm"]),
         "root": g["colour_root"].astype(np.float64).tolist(), "tip": g["colour_tip"].astype(np.float64).tolist()}
    C = len(G["off"]) - 1
    report["counts"]["curves"] = int(C)
    report["counts"]["points"] = int(len(P))
    report["counts"]["per_layer_curves"] = {str(L): int((G["layer"] == L).sum()) for L in range(4)}
    report["counts"]["tents"] = int((G["tent"] >= 0).sum())
    report["counts"]["locks"] = int(len(np.unique(G["lock"])))
    clear_scene()
    report["device"] = gpu()
    return G, atlas


# ---------------------------------------------------------------- atlas
def emission_material(name, wiring):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    outn = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 1.0; nt.links.new(em.outputs[0], outn.inputs[0])
    hi = nt.nodes.new("ShaderNodeHairInfo"); wiring(nt, hi, em); return m


def shell_colour_srgb(atlas):
    """The ramp's midpoint lifted by the highlight band: the shell's flat
    colour, and the atlas ramp's middle element, from one place (a guess)."""
    col = atlas["colour"]
    r, t = np.array(col["root"]), np.array(col["tip"])
    return np.clip((r + t) / 2.0 * (1.0 + 0.5 * float(col.get("band", 0.0))), 0.0, 1.0)


def render_atlas(G, atlas):
    W, H = atlas["size"]
    sc = bpy.context.scene
    rng = np.random.RandomState(11)
    K = 24
    paths, radii, per_slot = [], [], []
    for s in atlas["slots"]:
        x0, x1, y0, y1 = s["x0"], s["x1"], s["y0"], s["y1"]
        w = x1 - x0
        # strands 2 px or wider (HAIR-062): radius is a half width, so 1 px at the tip floor
        r_root = max(float(s.get("strand_width_px_root", 4)) / 2.0, 1.0)
        r_tip = max(float(s.get("strand_width_px_tip", 2)) / 2.0, 1.0)
        n = int(s["strands"])
        per_slot.append(n)
        for _ in range(n):
            x = x0 + rng.uniform(0.12, 0.88) * w
            end = rng.uniform(float(s.get("end_low", 0.85)), float(s.get("end_high", 1.0)))
            t = np.linspace(0.0, 1.0, K)
            amp = float(s.get("waviness", 0.3)) * 0.3 * w * rng.uniform(0.3, 1.0)
            ph = rng.uniform(0, 2 * math.pi); fq = rng.uniform(1.0, 2.5)
            xs = np.clip(x + amp * np.sin(fq * math.pi * t + ph) * t, x0 + r_root, x1 - r_root)
            zs = y0 + t * end * (y1 - y0 - 2 * r_root) + r_root
            paths.append(np.stack([xs, np.zeros(K), zs], axis=1))
            radii.append(r_root * (1 - t) + r_tip * t)
    P = np.array(paths); Rr = np.array(radii)
    cv = bpy.data.hair_curves.new("atlas"); cv.add_curves([K] * len(P))
    cv.attributes["position"].data.foreach_set("vector", P.reshape(-1, 3).ravel())
    cv.attributes.new("radius", "FLOAT", "POINT").data.foreach_set("value", Rr.ravel())
    cv.set_types(type="POLY")
    ob = bpy.data.objects.new("atlas", cv); sc.collection.objects.link(ob)
    cam = bpy.data.objects.new("atlas_cam", bpy.data.cameras.new("atlas_cam")); sc.collection.objects.link(cam)
    cam.location = (W / 2.0, -1000.0, H / 2.0); cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.type = "ORTHO"; cam.data.ortho_scale = float(W); cam.data.clip_end = 5000.0; sc.camera = cam
    w = bpy.data.worlds.new("atlas_world"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    sc.cycles_curves.shape = "RIBBONS"; sc.cycles_curves.subdivisions = 2
    sc.render.resolution_x, sc.render.resolution_y = W, H; sc.render.resolution_percentage = 100
    sc.cycles.samples = int(cfg["samples"]); sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"; sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "8"
    col = atlas["colour"]
    root_lin = srgb_to_linear(col["root"]); tip_lin = srgb_to_linear(col["tip"])
    mid_lin = srgb_to_linear(shell_colour_srgb(atlas))
    ramp_pos = min(max(float(col.get("ramp", 0.5)), 0.05), 0.95)

    def colour_ramp(nt, hi, em):
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        els = ramp.color_ramp.elements
        els[0].position = 0.0; els[0].color = (*root_lin, 1.0)
        els[1].position = 1.0; els[1].color = (*tip_lin, 1.0)
        mid = els.new(ramp_pos); mid.color = (*mid_lin, 1.0)
        nt.links.new(hi.outputs["Intercept"], ramp.inputs[0])
        # a little brightness per strand so neighbours separate (a guess)
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 0.85
        mr.inputs["To Max"].default_value = 1.15
        nt.links.new(hi.outputs["Random"], mr.inputs["Value"])
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        nt.links.new(ramp.outputs[0], mix.inputs[6]); nt.links.new(mr.outputs[0], mix.inputs[7])
        nt.links.new(mix.outputs[2], em.inputs[0])

    def root_mask(nt, hi, em):
        nt.links.new(hi.outputs["Intercept"], em.inputs[0])

    def random_id(nt, hi, em):
        nt.links.new(hi.outputs["Random"], em.inputs[0])

    passes = {}
    for name, wiring, view in (("diffuse", colour_ramp, "Standard"), ("root", root_mask, "Raw"),
                               ("id", random_id, "Raw")):
        cv.materials.clear(); cv.materials.append(emission_material("atlas_" + name, wiring))
        try:
            sc.view_settings.view_transform = view
        except TypeError:
            sc.view_settings.view_transform = "Standard"
            report["warnings"].append(f"no {view} view transform; {name} pass written through Standard")
        out = os.path.join(D, f"_{NAME}_pass_{name}.png")
        sc.render.filepath = out
        t = time.time(); bpy.ops.render.render(write_still=True)
        passes[name] = {"seconds": round(time.time() - t, 2), "path": out}
    sc.view_settings.view_transform = "Standard"
    for o in (ob, cam):
        bpy.data.objects.remove(o, do_unlink=True)
    report["atlas"] = {"size": [W, H], "strands": int(len(P)), "strands_per_slot": per_slot,
                       "points": int(P.size // 3), "samples": int(cfg["samples"]), "passes": passes}
    return passes


def post_atlas(passes, atlas):
    """Dilate colour under alpha 0 and write the three sheets (HAIR-054)."""
    from PIL import Image
    W, H = atlas["size"]
    dif = np.asarray(Image.open(passes["diffuse"]["path"]).convert("RGBA")).copy()
    root = np.asarray(Image.open(passes["root"]["path"]).convert("RGBA"))
    ident = np.asarray(Image.open(passes["id"]["path"]).convert("RGBA"))
    a = dif[..., 3]
    known = a > 0
    rgb = dif[..., :3].astype(np.float32)
    dil = int(atlas.get("dilate_px", 32))
    fill = (shell_colour_srgb(atlas) * 255).astype(np.uint8)
    method = "scipy edt"
    try:
        from scipy import ndimage
        dist, (iy, ix) = ndimage.distance_transform_edt(~known, return_indices=True)
        near = rgb[iy, ix]
        rgb = np.where((~known & (dist <= dil))[..., None], near, rgb)
        rgb = np.where((~known & (dist > dil))[..., None], fill.astype(np.float32), rgb)
    except ImportError:
        method = "iterative"
        filled = known.copy()
        for _ in range(dil):
            acc = np.zeros_like(rgb); cnt = np.zeros(a.shape, dtype=np.float32)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                sh = np.roll(filled, (dy, dx), axis=(0, 1)); sr = np.roll(rgb, (dy, dx), axis=(0, 1))
                acc += sr * sh[..., None]; cnt += sh
            grow = ~filled & (cnt > 0)
            rgb[grow] = acc[grow] / cnt[grow][:, None]
            filled |= grow
        rgb[~filled] = fill
    dif[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    Image.fromarray(dif, "RGBA").save(path("_diffuse.png"))
    Image.fromarray(np.stack([a] * 4, axis=-1), "RGBA").save(path("_opacity.png"))
    pack = np.stack([root[..., 0], ident[..., 0], np.zeros_like(a)], axis=-1)
    Image.fromarray(pack, "RGB").save(path("_pack.png"))
    for p in passes.values():
        os.remove(p["path"])
    alphas = []
    for s in atlas["slots"]:
        # image row 0 is the top of the sheet, V = 0 the bottom
        block = a[H - s["y1"]:H - s["y0"], s["x0"]:s["x1"]]
        alphas.append(round(float(block.mean() / 255.0), 3))
    report["atlas"].update({"slot_mean_alpha": alphas, "dilate_px": dil, "dilate_method": method,
                            "partial_alpha_fraction": round(float(((a > 0) & (a < 255)).mean()), 4),
                            "covered_fraction": round(float(known.mean()), 4)})


# ---------------------------------------------------------------- geometry
# Width holds over the first 70 percent of the length, then tapers to the tip
# width (the brief's guess; constant within a layer is HAIR-013).
TAPER_FROM = 0.7


def curves_object(G, idx, name):
    """A hair Curves object holding the guides `idx`, with radius (half width),
    v (arc-length fraction) and ci (guide index) on its points."""
    sizes = (G["off"][idx + 1] - G["off"][idx]).tolist()
    cv = bpy.data.hair_curves.new(name); cv.add_curves(sizes)
    pos, rad, vs, cis = [], [], [], []
    for i in idx:
        pts = G["B"][G["off"][i]:G["off"][i + 1]]
        seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
        t = np.concatenate([[0.0], np.cumsum(seg)]) / max(seg.sum(), 1e-9)
        hold = np.clip((t - TAPER_FROM) / (1.0 - TAPER_FROM), 0.0, 1.0)
        width = G["wr"][i] * (1 - hold) + G["wt"][i] * hold
        pos.append(pts); rad.append(width / 2.0); vs.append(t); cis.append(np.full(len(pts), i))
    cv.attributes["position"].data.foreach_set("vector", np.concatenate(pos).ravel())
    cv.attributes.new("radius", "FLOAT", "POINT").data.foreach_set("value", np.concatenate(rad))
    cv.attributes.new("v", "FLOAT", "POINT").data.foreach_set("value", np.concatenate(vs))
    cv.attributes.new("ci", "INT", "POINT").data.foreach_set("value", np.concatenate(cis).astype(np.int32))
    cv.set_types(type="POLY")             # or an 8-point curve becomes 84 quads (design pass)
    ob = bpy.data.objects.new(name, cv); bpy.context.scene.collection.objects.link(ob)
    return ob


def sweep_nodes(curves_ob, lens, thin):
    """Curve to Mesh over the guides: a thin 8-point lens with end caps, or a
    line profile for a flat card.  Set Curve Normal to the radial direction so
    the profile's Y axis lies flat on the scalp (design pass); the radius
    attribute feeds Scale, so width = 2 x radius."""
    ng = bpy.data.node_groups.new("sweep_" + curves_ob.name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes; L = ng.links
    N.new("NodeGroupInput"); go = N.new("NodeGroupOutput")
    info = N.new("GeometryNodeObjectInfo"); info.inputs["Object"].default_value = curves_ob
    info.transform_space = "RELATIVE"
    pos = N.new("GeometryNodeInputPosition")
    norm = N.new("ShaderNodeVectorMath"); norm.operation = "NORMALIZE"
    setn = N.new("GeometryNodeSetCurveNormal"); setn.mode = "FREE"
    L.new(pos.outputs[0], norm.inputs[0]); L.new(info.outputs["Geometry"], setn.inputs["Curve"])
    L.new(norm.outputs[0], setn.inputs["Normal"])
    if lens:
        prof = N.new("GeometryNodeCurvePrimitiveCircle"); prof.mode = "RADIUS"
        # 8 points: with the crease split in dome_normals() a rounder profile
        # buys nothing, and 12 doubled the shell triangles (bob 20,196, curls
        # 37,776, both past HAIR-016's 20k; measured 2026-09-22)
        prof.inputs["Resolution"].default_value = 8; prof.inputs["Radius"].default_value = 1.0
        tr = N.new("GeometryNodeTransform"); tr.inputs["Scale"].default_value = (thin, 1.0, 1.0)
        L.new(prof.outputs[0], tr.inputs["Geometry"]); prof_out = tr.outputs[0]
    else:
        prof = N.new("GeometryNodeCurvePrimitiveLine"); prof.inputs["Start"].default_value = (0, -1, 0)
        prof.inputs["End"].default_value = (0, 1, 0); prof_out = prof.outputs[0]
    sp = N.new("GeometryNodeSplineParameter")
    stu = N.new("GeometryNodeStoreNamedAttribute"); stu.data_type = "FLOAT"; stu.domain = "POINT"
    stu.inputs["Name"].default_value = "u"; L.new(prof_out, stu.inputs["Geometry"])
    L.new(sp.outputs["Factor"], stu.inputs["Value"])
    c2m = N.new("GeometryNodeCurveToMesh"); c2m.inputs["Fill Caps"].default_value = bool(lens)
    rad = N.new("GeometryNodeInputNamedAttribute"); rad.data_type = "FLOAT"
    rad.inputs["Name"].default_value = "radius"
    L.new(setn.outputs[0], c2m.inputs["Curve"]); L.new(stu.outputs[0], c2m.inputs["Profile Curve"])
    L.new(rad.outputs[0], c2m.inputs["Scale"])
    L.new(c2m.outputs[0], go.inputs[0])
    return ng


def sweep(G, idx, name, lens, thin):
    """Sweep the guides `idx` and return triangles with per-corner u, v, ci."""
    cv = curves_object(G, idx, "guides_" + name)
    host = bpy.data.objects.new("host_" + name, bpy.data.meshes.new("host_" + name))
    bpy.context.scene.collection.objects.link(host)
    mod = host.modifiers.new("gn", "NODES"); mod.node_group = sweep_nodes(cv, lens, thin)
    host.update_tag(); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(host.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    if lens:
        # a closed volume: bmesh makes every shell's faces point out of it
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free()
    V, lv, starts, totals, attrs = read_mesh(me)
    missing = [k for k in ("u", "v", "ci") if k not in attrs]
    if missing:
        raise RuntimeError(f"Curve to Mesh dropped attributes {missing}; got {list(me.attributes.keys())}")
    tri_loops = triangulate(lv, starts, totals)
    F = lv[tri_loops]
    u = per_corner(attrs, "u", lv, tri_loops); v = per_corner(attrs, "v", lv, tri_loops)
    ci = per_corner(attrs, "ci", lv, tri_loops)
    quads = int(len(me.polygons))
    for o in (host, cv):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.meshes.remove(me)
    return V, F, u, v, ci, quads


def manifold(V, F):
    me = bpy.data.meshes.new("check"); me.from_pydata(V.tolist(), [], F.tolist()); me.update()
    bm = bmesh.new(); bm.from_mesh(me)
    out = {"boundary_edges": sum(1 for e in bm.edges if len(e.link_faces) == 1),
           "nonmanifold_edges": sum(1 for e in bm.edges if len(e.link_faces) > 2),
           "edges": len(bm.edges)}
    bm.free(); bpy.data.meshes.remove(me)
    out["manifold"] = out["boundary_edges"] == 0 and out["nonmanifold_edges"] == 0
    return out


# A shell edge sharper than this splits the smooth shading (a guess; the lens
# crease is close to 180 degrees between its two sheets, the front sheet's own
# facets a few degrees apart).
SHARP_DEG = 60.0


def dome_normals(V, F, R, mix):
    """Custom normals for the shells by Data Transfer off a smooth sphere
    (HAIR-020, HAIR-066), mixed with the shell's own by `mix`."""
    me = bpy.data.meshes.new("shells_tmp"); me.from_pydata(V.tolist(), [], F.tolist()); me.update()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    # Smooth across a sheet, sharp across the lens's two long edges.  Smoothed
    # straight across that crease, the edge vertices average to a normal that
    # points sideways and every shell wears a dark band down each flank, at
    # any dome mix (rendered shells alone at 0, 0.5 and 1.0, 2026-09-22).
    bm = bmesh.new(); bm.from_mesh(me)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(SHARP_DEG):
            e.smooth = False
    bm.to_mesh(me); bm.free(); me.update()
    ob = bpy.data.objects.new("shells_tmp", me); bpy.context.scene.collection.objects.link(ob)
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=64, v_segments=32, radius=R + 1.5)
    dm = bpy.data.meshes.new("dome"); bm.to_mesh(dm); bm.free()
    dm.polygons.foreach_set("use_smooth", [True] * len(dm.polygons))
    dome = bpy.data.objects.new("dome", dm); bpy.context.scene.collection.objects.link(dome)
    mod = ob.modifiers.new("dome_normals", "DATA_TRANSFER")
    mod.object = dome; mod.use_loop_data = True; mod.data_types_loops = {"CUSTOM_NORMAL"}
    mod.loop_mapping = "NEAREST_POLYNOR"
    mod.mix_mode = "REPLACE" if mix >= 1.0 else "MIX"; mod.mix_factor = float(mix)
    ob.update_tag(); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    n = len(ev.loops)
    nrm = np.empty(n * 3); ev.corner_normals.foreach_get("vector", nrm)
    for o in (ob, dome):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in (ev, me, dm):
        bpy.data.meshes.remove(m)
    return nrm.reshape(-1, 3)


def card_uv(u, v, ci, G, atlas):
    """Each corner's atlas position: its card's slot rectangle, U mirrored
    when the card's uflip is set."""
    W, H = atlas["size"]
    slots = {s["index"]: s for s in atlas["slots"]}
    uv = np.zeros((len(u), 2))
    for k in range(len(u)):
        s = slots.get(int(G["slot"][ci[k]]))
        if s is None:
            uv[k] = (u[k], v[k]); continue
        uu = 1.0 - u[k] if G["uflip"][ci[k]] else u[k]
        uv[k] = ((s["x0"] + uu * (s["x1"] - s["x0"])) / W, (s["y0"] + v[k] * (s["y1"] - s["y0"])) / H)
    return uv


def shell_uv(u, v, ci, idx, atlas):
    """A shell's corners laid over one of the atlas's base slots, alternating
    by shell, u around the profile and v along the length.  The shell is
    opaque, so only the slot's colour is read: the strand lines, the root to
    tip ramp and the highlight band.  A flat colour, the first bake's choice,
    read as beige plastic (2026-09-22)."""
    W, H = atlas["size"]
    slots = {s["index"]: s for s in atlas["slots"]}
    base = [slots[i] for i in atlas.get("bands", {}).get("base", [0]) if i in slots] or [atlas["slots"][0]]
    shell_of = np.searchsorted(idx, ci)
    # `u` runs once round the closed profile, so laid straight over the slot
    # the outward face saw only the slot's two edge quarters, where the
    # strands' dark roots sit, and every shell wore a dark band down each
    # flank (shells rendered alone, 2026-09-22).  The circle profile starts at
    # +X, the middle of a face, so each face is a half of u centred on 0 or
    # 0.5, and each is stretched over the whole slot; the back mirrors the
    # front across the crease.
    w = np.mod(np.asarray(u, dtype=np.float64) + 0.5, 1.0)     # face centres at 0.5 and 0
    front = (w >= 0.25) & (w <= 0.75)
    uu = np.where(front, (w - 0.25) * 2.0, np.mod(w - 0.75, 1.0) * 2.0)
    uv = np.zeros((len(u), 2))
    for k in range(len(u)):
        s = base[int(shell_of[k]) % len(base)]
        uv[k] = ((s["x0"] + np.clip(uu[k], 0, 1) * (s["x1"] - s["x0"])) / W,
                 (s["y0"] + np.clip(v[k], 0, 1) * (s["y1"] - s["y0"])) / H)
    return uv


def build(G, atlas):
    parts = []              # (material index, V, F, uv per corner, normal per corner, label)
    # shells: layer 0
    idx = np.where(G["layer"] == 0)[0]
    if len(idx):
        V, F, u, v, ci, quads = sweep(G, idx, "shells", True, float(cfg["thickness"]))
        # a closed shell has faces on its scalp side that rightly face the head,
        # so the radial dot is reported but the winding test is the signed
        # volume of each shell: positive means every face points out of it
        report["normals"]["shell_faces_dot_radial"] = dot_report(face_dot_radial(V, F))
        a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        vol = (a * np.cross(b, c)).sum(axis=1) / 6.0
        shell_of = np.searchsorted(idx, ci.reshape(-1, 3)[:, 0])
        per_shell = np.zeros(len(idx)); np.add.at(per_shell, shell_of, vol)
        report["normals"]["shell_signed_volume_cm3"] = {
            "min": round(float(per_shell.min()), 3), "mean": round(float(per_shell.mean()), 3),
            "all_positive": bool((per_shell > 0).all()), "shells": int(len(idx))}
        report["manifold"] = manifold(V, F)
        report["manifold"]["quads_before_triangulation"] = quads
        nrm = dome_normals(V, F, G["R"], float(cfg["dome_mix"]))
        # which half of the profile faces out: corners near u = 0 against u = 0.5,
        # by their distance from the head centre (the sweep's Set Curve Normal
        # puts the profile's +X, u = 0, on the radial, and this checks it)
        rad = np.linalg.norm(V[F.reshape(-1)], axis=1)
        uu = np.asarray(u); near0 = np.abs(np.mod(uu + 0.5, 1.0) - 0.5) < 0.08
        near5 = np.abs(uu - 0.5) < 0.08
        report["normals"]["shell_outward_face"] = {
            "u0_minus_u05_radius_cm": round(float(rad[near0].mean() - rad[near5].mean()), 3),
            "expected": "positive: u = 0 is the outward face"}
        uv = shell_uv(u, v, ci, idx, atlas)
        parts.append((1, V, F, uv, nrm, "shell"))
        report["counts"]["shell_triangles"] = int(len(F))
    # cards: layers 1 to 3, each with its own radial mix
    mixes = {1: float(cfg["card_mix"]), 2: float(cfg["card_mix"]), 3: float(cfg["card_mix"]) / 2.0}
    for L, label in ((1, "breakup"), (2, "hairline"), (3, "flyaway")):
        idx = np.where(G["layer"] == L)[0]
        if not len(idx):
            continue
        V, F, u, v, ci, quads = sweep(G, idx, label, False, 0.0)
        d = face_dot_radial(V, F)
        flipped = bool(d.mean() < 0)
        if flipped:
            # Curve to Mesh winds every card the same way, so one sign says it all
            F = F[:, [0, 2, 1]]; u = u.reshape(-1, 3)[:, [0, 2, 1]].ravel()
            v = v.reshape(-1, 3)[:, [0, 2, 1]].ravel(); ci = ci.reshape(-1, 3)[:, [0, 2, 1]].ravel()
            d = face_dot_radial(V, F)
        report["normals"][label + "_faces"] = dict(dot_report(d), flipped=flipped)
        own = smooth_vertex_normals(V, F)[F.ravel()]
        radial = unit_rows(V)[F.ravel()]
        nrm = unit_rows(mixes[L] * radial + (1.0 - mixes[L]) * own)
        report["normals"][label + "_corner_dot_radial"] = round(float((nrm * radial).sum(axis=1).mean()), 4)
        parts.append((2, V, F, card_uv(u, v, ci, G, atlas), nrm, label))
        report["counts"][label + "_triangles"] = int(len(F))
    return parts


def load_cap():
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=cfg["cap"], forward_axis="NEGATIVE_Z", up_axis="Y",
                          use_split_objects=False)
    added = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not added:
        raise RuntimeError(f"{cfg['cap']} imported no mesh")
    ob = added[0]; me = ob.data
    V, lv, starts, totals, _ = read_mesh(me, ob.matrix_world)
    tri_loops = triangulate(lv, starts, totals)
    F = lv[tri_loops]
    n = len(me.loops)
    nrm = np.empty(n * 3); me.corner_normals.foreach_get("vector", nrm)
    rot = np.array(ob.matrix_world, dtype=np.float64)[:3, :3]
    nrm = unit_rows(nrm.reshape(-1, 3) @ rot.T)[tri_loops.ravel()]
    uv = np.zeros((n, 2))
    if me.uv_layers:
        me.uv_layers[0].data.foreach_get("uv", uv.reshape(-1))
    uv = uv[tri_loops.ravel()]
    d = face_dot_radial(V, F)
    flipped = bool(d.mean() < 0)
    if flipped:
        F = F[:, [0, 2, 1]]; uv = uv.reshape(-1, 3, 2)[:, [0, 2, 1]].reshape(-1, 2)
        nrm = nrm.reshape(-1, 3, 3)[:, [0, 2, 1]].reshape(-1, 3); d = face_dot_radial(V, F)
        report["warnings"].append("the cap OBJ was wound into the head and has been flipped")
    report["normals"]["cap_faces"] = dict(dot_report(d), flipped=flipped)
    report["counts"]["cap_triangles"] = int(len(F)); report["counts"]["cap_polygons_in_file"] = int(len(me.polygons))
    mat = ob.material_slots[0].material if ob.material_slots and ob.material_slots[0].material else None
    bpy.data.objects.remove(ob, do_unlink=True); bpy.data.meshes.remove(me)
    return (0, V, F, uv, nrm, "cap"), mat


def image_material(name, diffuse, opacity):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    outn = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], outn.inputs[0])
    b.inputs["Roughness"].default_value = 0.55
    if diffuse:
        ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = bpy.data.images.load(diffuse, check_existing=True)
        nt.links.new(ti.outputs["Color"], b.inputs["Base Color"])
    if opacity:
        ta = nt.nodes.new("ShaderNodeTexImage"); ta.image = bpy.data.images.load(opacity, check_existing=True)
        ta.image.colorspace_settings.name = "Non-Color"
        nt.links.new(ta.outputs["Color"], b.inputs["Alpha"])
        try:
            m.surface_render_method = "DITHERED"    # EEVEE sorts blended surfaces per object (HAIR-070)
        except (AttributeError, TypeError):
            pass
    m.use_backface_culling = False
    return m


def flat_material(name, rgb_srgb):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    outn = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], outn.inputs[0])
    b.inputs["Base Color"].default_value = (*srgb_to_linear(rgb_srgb), 1.0)
    b.inputs["Roughness"].default_value = 0.45
    return m


def merge(parts, atlas, cap_mat):
    """One mesh, faces inside to outside, three material slots, UVs and custom normals."""
    order = {"cap": 0, "shell": 1, "breakup": 2, "hairline": 3, "flyaway": 4}
    parts = sorted(parts, key=lambda p: order[p[5]])
    V, F, UV, N, M = [], [], [], [], []
    base = 0
    for mi, v, f, uv, nrm, label in parts:
        V.append(v); F.append(f + base); UV.append(uv); N.append(nrm); M.append(np.full(len(f), mi))
        base += len(v)
    V = np.concatenate(V); F = np.concatenate(F); UV = np.concatenate(UV); N = np.concatenate(N)
    M = np.concatenate(M)
    me = bpy.data.meshes.new("hair"); me.from_pydata(V.tolist(), [], F.tolist()); me.update()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.polygons.foreach_set("material_index", M.astype(np.int32))
    layer = me.uv_layers.new(name="UVMap"); layer.data.foreach_set("uv", UV.ravel())
    shell_rgb = shell_colour_srgb(atlas)
    mats = [cap_mat if cap_mat is not None else image_material(NAME + "_cap", path("_cap_diffuse.png"), path("_cap_opacity.png")),
            image_material(NAME + "_shell", path("_diffuse.png"), None),
            image_material(NAME + "_card", path("_diffuse.png"), path("_opacity.png"))]
    for m in mats:
        me.materials.append(m)
    me.normals_split_custom_set([tuple(x) for x in N.tolist()])
    me.update()
    ob = bpy.data.objects.new("hair", me); bpy.context.scene.collection.objects.link(ob)
    report["counts"]["triangles"] = int(len(F)); report["counts"]["vertices"] = int(len(V))
    report["normals"]["all_faces_before_export"] = dot_report(face_dot_radial(V, F))
    report["normals"]["corners_before_export"] = corner_dot_radial(me)
    report["shell_colour_srgb"] = [round(float(c), 4) for c in shell_rgb]
    report["material_names"] = [m.name for m in mats]
    return ob, V


def write_mtl(atlas):
    col = [round(float(c), 3) for c in shell_colour_srgb(atlas)]
    with open(path(".mtl"), "w") as fh:
        fh.write(f"# written by scripts/bake_hair.py for {NAME}.obj\n\n")
        fh.write(f"newmtl {NAME}_cap\nKa 1.000 1.000 1.000\nKd 1.000 1.000 1.000\nKs 0.050 0.050 0.050\n"
                 f"Ns 8.0\nillum 2\nd 1.0\nmap_Kd {NAME}_cap_diffuse.png\nmap_d {NAME}_cap_opacity.png\n\n")
        fh.write(f"newmtl {NAME}_shell\nKa 1.000 1.000 1.000\nKd 1.000 1.000 1.000\n"
                 f"Ks 0.250 0.250 0.250\nNs 120.0\nillum 2\nd 1.0\nmap_Kd {NAME}_diffuse.png\n\n")
        fh.write(f"newmtl {NAME}_card\nKa 1.000 1.000 1.000\nKd 1.000 1.000 1.000\nKs 0.350 0.350 0.350\n"
                 f"Ns 430.0\nillum 2\nd 1.0\nmap_Kd {NAME}_diffuse.png\nmap_d {NAME}_opacity.png\n")


def export(ob):
    for o in bpy.data.objects:
        o.select_set(o is ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.wm.obj_export(filepath=path(".obj"), export_selected_objects=True, export_normals=True,
                          export_uv=True, export_materials=True, forward_axis="NEGATIVE_Z", up_axis="Y",
                          global_scale=1.0, export_triangulated_mesh=False, path_mode="RELATIVE")
    with open(path(".obj")) as fh:
        lines = fh.read().splitlines()
    report["obj"] = {"bytes": os.path.getsize(path(".obj")),
                     "v": sum(l.startswith("v ") for l in lines), "vt": sum(l.startswith("vt ") for l in lines),
                     "vn": sum(l.startswith("vn ") for l in lines), "f": sum(l.startswith("f ") for l in lines),
                     "o": [l[2:] for l in lines if l.startswith("o ")],
                     "usemtl": [l[7:] for l in lines if l.startswith("usemtl ")]}


def roundtrip(ob, V_in):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path(".obj"), forward_axis="NEGATIVE_Z", up_axis="Y",
                          use_split_objects=False)
    back = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if not back:
        raise RuntimeError("the written OBJ imported no mesh")
    me = back[0].data
    out = {"vertices": len(me.vertices), "faces": len(me.polygons),
           "materials": [s.material.name for s in back[0].material_slots if s.material],
           "uv_layers": [l.name for l in me.uv_layers],
           "custom_normal_attr": "custom_normal" in me.attributes,
           "corners": corner_dot_radial(me)}
    co = read_mesh(me, back[0].matrix_world)[0]
    if len(co) == len(V_in):
        out["max_position_error_cm"] = round(float(np.abs(co - V_in).max()), 5)
    else:
        out["max_position_error_cm"] = None
        report["warnings"].append(f"round trip changed the vertex count: {len(V_in)} out, {len(co)} back")
    lv = np.empty(len(me.loops), dtype=np.int32); me.loops.foreach_get("vertex_index", lv)
    starts = np.empty(len(me.polygons), dtype=np.int32); me.polygons.foreach_get("loop_start", starts)
    totals = np.empty(len(me.polygons), dtype=np.int32); me.polygons.foreach_get("loop_total", totals)
    F = lv[triangulate(lv, starts, totals)]
    d = face_dot_radial(co, F)
    out["faces_dot_radial"] = dot_report(d)
    mi = np.empty(len(me.polygons), dtype=np.int32); me.polygons.foreach_get("material_index", mi)
    if totals.max() == 3:
        for k, label in enumerate(("cap", "shell", "card")):
            sel = mi == k
            if sel.any():
                out["faces_dot_radial_" + label] = dot_report(d[sel])
    report["roundtrip"] = out


try:
    G, atlas = stage("load", load)
    passes = stage("atlas_render", lambda: render_atlas(G, atlas))
    stage("atlas_post", lambda: post_atlas(passes, atlas))
    parts = stage("sweep", lambda: build(G, atlas))
    cap_part, cap_mat = stage("cap", load_cap)
    parts.append(cap_part)
    ob, V = stage("merge", lambda: merge(parts, atlas, cap_mat))
    stage("export", lambda: (export(ob), write_mtl(atlas)))
    stage("roundtrip", lambda: roundtrip(ob, V))
    report["seconds"] = round(time.time() - T0, 2)
    print("HAIR_BAKE " + json.dumps(report), flush=True)
except Exception:
    report["error"] = traceback.format_exc()[-3000:]
    report["seconds"] = round(time.time() - T0, 2)
    print("HAIR_BAKE " + json.dumps(report), flush=True)
'''

# Stopping the docker exec client leaves its process running in the container.
# This ends the `python3 -c` jobs whose arguments hold the marker, the OBJ path
# unique to this run: SIGTERM, then SIGKILL for any still there after 10 s.
STOP = r'''
import json, os, signal, sys, time
marker = sys.argv[-1].encode()
me = os.getpid()


def jobs():
    found = []
    for d in os.listdir("/proc"):
        if not d.isdigit() or int(d) == me:
            continue
        try:
            with open(f"/proc/{d}/cmdline", "rb") as f:
                argv = f.read().split(b"\0")
        except OSError:
            continue
        if len(argv) > 2 and argv[1] == b"-c" and any(marker in a for a in argv[2:]):
            found.append(int(d))
    return found


ended = jobs()
for pid in ended:
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
deadline = time.time() + 10
while ended and time.time() < deadline and jobs():
    time.sleep(0.5)
killed = jobs()
for pid in killed:
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass
print("HAIR_STOP " + json.dumps({"ended": ended, "killed": killed}), flush=True)
'''


# ------------------------------------------------------------------ host side

class Stopped(Exception):
    """SIGTERM, raised so the same clean-up runs as for Ctrl-C."""


@contextlib.contextmanager
def signals_held():
    old = {s: signal.signal(s, signal.SIG_IGN) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        yield
    finally:
        for s, h in old.items():
            signal.signal(s, h)


def end_container_job(marker: str) -> None:
    try:
        r = exec_python(STOP, marker, timeout=40)
        line = next((l for l in r.stdout.splitlines() if l.startswith(STOP_SENTINEL)), None)
        res = json.loads(line[len(STOP_SENTINEL):]) if line else None
    except (OSError, subprocess.TimeoutExpired, ValueError):
        res = None
    if res is None:
        print(f"  ! could not check {container()} for the job writing {marker}; "
              f"look for it with `docker top {container()} -o pid,etimes,args`")
    elif res["ended"]:
        print(f"  stopped   Blender job(s) {res['ended']} in {container()}"
              + (f", {res['killed']} with SIGKILL" if res["killed"] else ""))


def other_blender_jobs() -> list[str]:
    """`python3 -c` processes in the container: any of them may be Blender."""
    try:
        out = subprocess.run(["docker", "top", container(), "-o", "pid,etimes,args"],
                             capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"(docker top failed: {exc})"]
    return [line.strip() for line in out.splitlines()[1:] if "python3 -c" in line]


def wait_for_idle(skip: bool) -> None:
    """Wait while ComfyUI runs or queues a job, or another Blender job runs in the container."""
    if skip:
        return
    while True:
        busy = []
        try:
            with urllib.request.urlopen(COMFY + "/queue", timeout=10) as r:
                q = json.load(r)
            n = len(q.get("queue_running", [])) + len(q.get("queue_pending", []))
            if n:
                busy.append(f"ComfyUI queue holds {n} job(s)")
        except (urllib.error.URLError, OSError, ValueError) as exc:
            busy.append(f"could not read {COMFY}/queue: {exc}")
        jobs = other_blender_jobs()
        if jobs:
            busy.append(f"{len(jobs)} other python3 -c job(s) in {container()}")
        if not busy:
            return
        print(f"  waiting: {'; '.join(busy)}; checking again in 30 s ({time.strftime('%H:%M:%S')})",
              flush=True)
        time.sleep(30)


@functools.lru_cache(maxsize=None)
def container_mounts() -> tuple:
    try:
        out = subprocess.run(["docker", "inspect", "-f", "{{json .Mounts}}", container()],
                             capture_output=True, text=True, timeout=30).stdout
        return tuple(json.loads(out) or ())
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return ()


def container_path(host: Path) -> str:
    """Where the container sees a host path, from its bind mounts."""
    best = None
    for m in container_mounts():
        src = Path(m.get("Source", ""))
        try:
            rel = host.resolve().relative_to(src)
        except ValueError:
            continue
        if best is None or len(str(src)) > len(str(best[0])):
            best = (src, str(PurePosixPath(m["Destination"]) / rel.as_posix()))
    if best is None:
        raise SystemExit(f"  ! {container()} mounts no folder holding {host}; "
                         "the files must sit under the repo's output/ folder")
    return best[1]


def find_inputs(folder: Path, name: str) -> Path:
    """The folder holding <name>_guides.npz: --dir itself, or <name>/ inside it."""
    for cand in (folder, folder / name):
        if (cand / f"{name}_guides.npz").is_file():
            return cand
    raise SystemExit(f"  ! no {name}_guides.npz in {folder} or {folder / name}; "
                     "scripts/make_hair.py writes it")


def obj_vertices(p: Path) -> list[list[float]]:
    with open(p) as fh:
        return [[float(x) for x in l.split()[1:4]] for l in fh if l.startswith("v ")]


def cap_block_error(folder: Path, name: str) -> float | None:
    """The cap is the first block of the written OBJ, so its vertices must
    match the numpy cap file to the exporter's six decimals: the one check
    that proves the export axes, since a rotated cap still passes every
    normal test."""
    cap = obj_vertices(folder / f"{name}_cap.obj")
    out = obj_vertices(folder / f"{name}.obj")
    if not cap or len(out) < len(cap):
        return None
    return max(abs(a - b) for va, vb in zip(cap, out) for a, b in zip(va, vb))


def shown(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


def fmt_dot(d: dict | None) -> str:
    return "n/a" if not d else f"{d['mean']:+.3f} ({d['fraction_positive']:.0%} positive)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__.split("\n", 1)[1])
    ap.add_argument("name", help="the hair's name: files are <name>_guides.npz and friends")
    ap.add_argument("--dir", type=Path, default=OUT,
                    help=f"folder holding the guides, atlas and cap files (default {shown(OUT)})")
    ap.add_argument("--dome-mix", type=float, default=0.5, metavar="F",
                    help="how far shell normals go towards the dome's: 1.0 replaces them "
                         "(HAIR-020). Default 0.5: at 1.0 a shell on the side of the head "
                         "carries a normal that faces away from a front camera and renders "
                         "as a dark stripe under a Principled BSDF (seen 2026-09-22)")
    ap.add_argument("--card-mix", type=float, default=0.6, metavar="F",
                    help="how far breakup and hairline card normals go from their ribbon "
                         "frame towards the radial direction; flyaways take half of it "
                         "(default 0.6, a guess)")
    ap.add_argument("--thickness", type=float, default=0.12, metavar="F",
                    help="lens shell thickness as a fraction of its width (default 0.3, "
                         "the design pass's value; VRoid shells reach about 1.8 cm, HAIR-150)")
    ap.add_argument("--samples", type=int, default=64,
                    help="Cycles samples per atlas pass (default 64; the design pass "
                         "rendered a clean sheet at 32 in 0.29 s)")
    ap.add_argument("--timeout", type=int, default=600, metavar="S",
                    help="seconds before the Blender job is ended inside the container "
                         "(default 600; the synthetic set baked in under 20 s)")
    ap.add_argument("--no-wait", action="store_true",
                    help="do not wait for an empty ComfyUI queue or an idle container")
    args = ap.parse_args()
    if not 0.0 <= args.dome_mix <= 1.0 or not 0.0 <= args.card_mix <= 1.0:
        print("  ! --dome-mix and --card-mix are fractions from 0 to 1")
        return 2
    folder = find_inputs(args.dir, args.name)
    n = args.name
    for suffix in ("_atlas.json", "_cap.obj"):
        if not (folder / f"{n}{suffix}").is_file():
            print(f"  ! missing {shown(folder / (n + suffix))}")
            return 2
    cfg = {"name": n, "dir": container_path(folder),
           "guides": container_path(folder / f"{n}_guides.npz"),
           "atlas": container_path(folder / f"{n}_atlas.json"),
           "cap": container_path(folder / f"{n}_cap.obj"),
           "dome_mix": args.dome_mix, "card_mix": args.card_mix, "thickness": args.thickness,
           "samples": args.samples}
    marker = f"{cfg['dir']}/{n}.obj"
    print(f"  container {container()}, {shown(folder)}, layout "
          f"{'folder' if folder != args.dir else 'flat'}")
    wait_for_idle(args.no_wait)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(Stopped()))
    t = time.time()
    try:
        res = exec_json(BLENDER, cfg, SENTINEL, timeout=args.timeout)
    except (KeyboardInterrupt, Stopped):
        with signals_held():
            end_container_job(marker)
        print("  ! stopped")
        return 130
    wall = round(time.time() - t, 1)
    if res is None:
        print(f"  ! Blender printed no result after {wall} s (see above)")
        return 1
    res["container"] = container()
    res["wall_s"] = wall
    res["settings"] = {k: v for k, v in cfg.items() if k in ("dome_mix", "card_mix", "thickness", "samples")}
    res["run_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    cap_err = cap_block_error(folder, n) if "error" not in res else None
    res["cap_block_max_error_cm"] = cap_err
    report_path = folder / f"{n}_bake.json"
    report_path.write_text(json.dumps(res, indent=2))
    c, nm, st = res.get("counts", {}), res.get("normals", {}), res.get("stages_s", {})
    print(f"  blender   {res.get('blender')}, numpy {res.get('numpy')}, Cycles {res.get('device')}")
    if c:
        pl = c.get("per_layer_curves", {})
        print(f"  guides    {c.get('curves')} curves, {c.get('points')} points: {pl.get('0')} shells, "
              f"{pl.get('1')} breakup ({c.get('tents')} tent members), {pl.get('2')} hairline, "
              f"{pl.get('3')} flyaway, {c.get('locks')} locks")
    if "error" in res:
        print("  ! the Blender job failed after stages " + ", ".join(st) + ":")
        print("\n".join("    " + l for l in res["error"].splitlines()[-25:]))
        print(f"  report    {shown(report_path)}")
        return 1
    a = res.get("atlas", {})
    if a:
        alphas = a.get("slot_mean_alpha", [])
        print(f"  atlas     {a['size'][0]} x {a['size'][1]}, {a['strands']} strands in "
              f"{len(a.get('strands_per_slot', []))} slots, {a['samples']} samples; slot mean alpha "
              + ", ".join(f"{v:.3f}" for v in alphas)
              + f"; dilated {a.get('dilate_px')} px ({a.get('dilate_method')}), "
              f"{st.get('atlas_render', 0) + st.get('atlas_post', 0):.2f} s")
    m = res.get("manifold", {})
    sv = nm.get("shell_signed_volume_cm3", {})
    print(f"  shells    {pl.get('0')} lens shells, {c.get('shell_triangles', 0)} triangles from "
          f"{m.get('quads_before_triangulation', 0)} polygons, "
          + ("manifold" if m.get("manifold") else f"NOT manifold: {m.get('boundary_edges')} boundary, "
             f"{m.get('nonmanifold_edges')} non-manifold edges")
          + (f", signed volume {sv.get('min')} to mean {sv.get('mean')} cm3"
             + (" (all wound outward)" if sv.get("all_positive") else " (SOME WOUND INWARD)") if sv else "")
          + f", dome mix {args.dome_mix}")
    print(f"  cards     breakup {c.get('breakup_triangles', 0)}, hairline {c.get('hairline_triangles', 0)}, "
          f"flyaway {c.get('flyaway_triangles', 0)} triangles, card mix {args.card_mix}"
          + ("; cards were rewound outward" if any(nm.get(k, {}).get("flipped")
                                                   for k in ("breakup_faces", "hairline_faces", "flyaway_faces"))
             else ""))
    print(f"  cap       {c.get('cap_triangles', 0)} triangles"
          + (" (flipped: it arrived wound inward)" if nm.get("cap_faces", {}).get("flipped") else ""))
    total = c.get("triangles", 0)
    print(f"  mesh      {c.get('vertices')} vertices, {total} triangles"
          + ("" if BUDGET[0] <= total <= BUDGET[1] else f" (outside the {BUDGET[0]} to {BUDGET[1]} game budget, HAIR-016)"))
    print(f"  winding   face normal dot radial: cap {fmt_dot(nm.get('cap_faces'))}, breakup "
          f"{fmt_dot(nm.get('breakup_faces'))}, hairline {fmt_dot(nm.get('hairline_faces'))}, "
          f"flyaway {fmt_dot(nm.get('flyaway_faces'))}; shells {fmt_dot(nm.get('shell_faces_dot_radial'))}, "
          "closed, so their scalp side faces the head by design")
    rt = res.get("roundtrip", {})
    cb = nm.get("corners_before_export", {})
    ca = rt.get("corners", {})
    print(f"  normals   corner dot radial {cb.get('mean_dot')} before export, {ca.get('mean_dot')} "
          f"after re-import (|dot| {ca.get('mean_abs_dot')}); faces after re-import "
          f"{fmt_dot(rt.get('faces_dot_radial'))}; max position error {rt.get('max_position_error_cm')} cm; "
          f"materials back {rt.get('materials')}")
    print(f"  axes      cap block in the written OBJ against {n}_cap.obj: max error "
          f"{'unreadable' if cap_err is None else f'{cap_err:.6f} cm'}")
    o = res.get("obj", {})
    print(f"  obj       o {o.get('o')}, usemtl {o.get('usemtl')}, {o.get('v')} v, {o.get('vt')} vt, "
          f"{o.get('vn')} vn, {o.get('f')} f, {o.get('bytes', 0) / 1e6:.2f} MB")
    for w in res.get("warnings", []):
        print(f"  ! {w}")
    print("  stages    " + ", ".join(f"{k} {v:.2f} s" for k, v in st.items()))
    for suffix in (".obj", ".mtl", "_diffuse.png", "_opacity.png", "_pack.png"):
        print(f"  wrote     {shown(folder / (n + suffix))}")
    print(f"  report    {shown(report_path)}  ({res.get('seconds')} s in Blender, {wall} s wall)")
    ok = (m.get("manifold", True) and o.get("usemtl") == [f"{n}_{k}" for k in MATERIALS]
          and rt.get("faces_dot_radial", {}).get("mean", 0) > 0
          and sv.get("all_positive", True) and cap_err is not None and cap_err < 1e-3
          and all(nm.get(k, {}).get("fraction_positive", 1.0) > 0.5
                  for k in ("cap_faces", "breakup_faces", "hairline_faces", "flyaway_faces")))
    if not ok:
        print("  ! a check failed: see the shells, winding, axes and obj lines above")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Project a generated mesh onto a game's own character mesh, keeping that
mesh's topology, UVs and skin weights, and bake the generated colour onto it.

    scripts/bg3_project.py BASE.glb SOURCE.glb --out output/bg3/halfling_m \
        [--colour output/textures/<name>/hunyuan_output.jpg] [--size 2048]
        [--lock eyes,mouth,neck] [--keep front,back]

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
    <out>.json        what was done, with every setting and count

The three TGA names follow BG3's material convention (BM, NM, PM packed
R metal, G rough, B AO, per docs.baldursgate3.game "Creating Armour"); their
DDS conversion and the GR2 export happen on the Windows side with LSLib and
the Toolkit, which this repo never carries.

The base mesh is the game's, so it lives OUTSIDE the repo, like the Daz
library (CLAUDE.md), and nothing it produces is committed.  Pass it by an
absolute path or a path under input/ or output/; the output goes under
output/bg3/, which `cleanup.py keep` should refuse.

Alignment: the source is scaled uniformly so its height matches the base
mesh's, and centred on the base's bounding box in X and Y, with both feet on
the base's floor.  That is a first alignment, not a pose match: the source
must already stand in roughly the base's rest pose (arms out as the base has
them), or the wrap folds limbs onto the wrong surface.  --lock names vertex
groups of the base mesh (comma-separated, substring match on group names) that
the wrap leaves where they are; eyes, mouth and neck seams are the usual ones.

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
from mathutils import Vector

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
        bpy.ops.import_scene.gltf(filepath=path)
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
base_objs = load(cfg["base"])
base_meshes = [o for o in base_objs if o.type == "MESH"]
armatures = [o for o in base_objs if o.type == "ARMATURE"]
if not base_meshes:
    raise SystemExit("the base file holds no mesh")
if len(base_meshes) > 1:
    select_only(base_meshes, base_meshes[0])
    bpy.ops.object.join()
    say(f"joined {len(base_meshes)} base meshes into one")
base = bpy.context.view_layer.objects.active if len(base_meshes) > 1 else base_meshes[0]
base.name = "base"
arm = armatures[0] if armatures else None
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

# ---- align the source to the base ------------------------------------------
blo, bhi = bounds([base])
slo, shi = bounds([source])
scale = (bhi.z - blo.z) / max(1e-9, (shi.z - slo.z))
select_only([source])
source.scale = source.scale * scale
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
slo, shi = bounds([source])
shift = Vector(((blo.x + bhi.x) / 2 - (slo.x + shi.x) / 2,
                (blo.y + bhi.y) / 2 - (slo.y + shi.y) / 2,
                blo.z - slo.z))
source.location += shift
bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
slo, shi = bounds([source])
say(f"aligned source by x{scale:.4f}: height {shi.z - slo.z:.3f} on base {bhi.z - blo.z:.3f}, "
    f"width {shi.x - slo.x:.3f} on {bhi.x - blo.x:.3f}, depth {shi.y - slo.y:.3f} on {bhi.y - blo.y:.3f}")

# ---- an untouched copy, for the normals bake and as a record ---------------
select_only([base])
bpy.ops.object.duplicate()
pristine = bpy.context.view_layer.objects.active
pristine.name = "base_pristine"
pristine.hide_render = True

# ---- lock groups: vertices the wrap must not move ---------------------------
lock = base.vertex_groups.new(name="bg3_project_lock")
locked = 0
patterns = [p.strip().lower() for p in cfg.get("lock", []) if p.strip()]
if patterns:
    names = {g.index: g.name for g in base.vertex_groups}
    hits = [g for g in base.vertex_groups if any(p in g.name.lower() for p in patterns)]
    idx = {g.index for g in hits}
    for v in base.data.vertices:
        if any(ge.group in idx and ge.weight > 0.0 for ge in v.groups):
            lock.add([v.index], 1.0, "REPLACE")
            locked += 1
    say(f"locked {locked:,} verts in {len(hits)} groups: {', '.join(g.name for g in hits)[:200]}")
# The wrap's own mask is the inverse of the lock.
wrapmask = base.vertex_groups.new(name="bg3_project_wrap")
for v in base.data.vertices:
    wrapmask.add([v.index], 1.0, "REPLACE")
if locked:
    for v in base.data.vertices:
        if any(ge.group == lock.index for ge in v.groups):
            wrapmask.add([v.index], 0.0, "REPLACE")

# ---- shrinkwrap the base onto the source ------------------------------------
select_only([base])
mod = base.modifiers.new("bg3_project", "SHRINKWRAP")
mod.target = source
mod.wrap_method = cfg.get("wrap_method", "NEAREST_SURFACEPOINT")
mod.wrap_mode = "ON_SURFACE"
mod.offset = float(cfg.get("offset", 0.0))
mod.vertex_group = wrapmask.name
smooth_passes = int(cfg.get("smooth", 2))
if smooth_passes:
    # A shrinkwrap alone pins every vertex to the nearest point of a dense
    # surface, which keeps the base's wrinkles but adds the source's facets;
    # a light Corrective Smooth after it takes the facets out and keeps the
    # loops even.  Masked the same way, so locked vertices stay put.
    cs = base.modifiers.new("bg3_project_smooth", "CORRECTIVE_SMOOTH")
    cs.iterations = smooth_passes * 5
    cs.smooth_type = "LENGTH_WEIGHTED"
    cs.vertex_group = wrapmask.name
    cs.use_pin_boundary = True
# Apply both so the mesh data itself changes and the weights stay attached.
# The Armature modifier, if the import added one, is left in place and last.
before = [v.co.copy() for v in base.data.vertices]
for m in [m for m in base.modifiers if m.name.startswith("bg3_project")]:
    bpy.ops.object.modifier_apply(modifier=m.name)
moved = [(v.co - before[i]).length for i, v in enumerate(base.data.vertices)]
say(f"wrapped: mean move {sum(moved) / len(moved):.4f}, max {max(moved):.4f}, "
    f"{sum(1 for d in moved if d < 1e-6):,} verts did not move")
# Removing a group invalidates every other VertexGroup handle, so look each
# up by name again rather than reuse the one made above.
for name in ("bg3_project_wrap", "bg3_project_lock"):
    base.vertex_groups.remove(base.vertex_groups[name])

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
base.data.materials.clear()
bpy.data.objects.remove(pristine, do_unlink=True)
bpy.data.objects.remove(source, do_unlink=True)
export = [base] + ([arm] if arm else [])
select_only(export, base)
bpy.ops.export_scene.gltf(filepath=f"{out}.glb", export_format="GLB", use_selection=True,
                          export_skins=bool(arm), export_animations=False, export_yup=True,
                          export_materials="NONE")
bpy.ops.export_scene.fbx(filepath=f"{out}.fbx", use_selection=True,
                         object_types={"ARMATURE", "MESH"}, add_leaf_bones=False,
                         bake_anim=False, use_armature_deform_only=True,
                         path_mode="STRIP")
written["glb"] = f"{out}.glb"
written["fbx"] = f"{out}.fbx"

info = {
    "base": cfg["base"], "source": cfg["source"], "colour": colour,
    "base_verts": len(base.data.vertices), "base_faces": len(base.data.polygons),
    "vertex_groups": len(base.vertex_groups), "bones": len(arm.data.bones) if arm else 0,
    "scale": scale, "locked": locked, "mean_move": sum(moved) / len(moved),
    "max_move": max(moved), "size": size, "written": written,
    "unreached": misses, "log": log,
}
with open(f"{out}.json", "w") as f:
    json.dump(info, f, indent=1)
print("BG3PROJECT " + json.dumps(info))
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
    ap.add_argument("--wrap-method", default="NEAREST_SURFACEPOINT",
                    choices=["NEAREST_SURFACEPOINT", "PROJECT", "NEAREST_VERTEX",
                             "TARGET_PROJECT"])
    ap.add_argument("--smooth", type=int, default=2,
                    help="corrective-smooth passes after the wrap, 0 for none (default 2)")
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
        "lock": [s for s in args.lock.split(",") if s],
        "wrap_method": args.wrap_method, "smooth": args.smooth,
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
    print(f"  record     {args.out}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

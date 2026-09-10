#!/usr/bin/env python3
"""Render a model to a sprite sheet: N angles across, one row per pose.

Runs Blender (the `bpy` module) inside the ComfyUI container, because that is the
only thing in this stack that can pose a rigged FBX.  ComfyUI-3D-Pack's renderer
only takes its own MESH type and its loader reads .obj/.ply/.glb — not the FBX
that rigging produces — and no node in the install outputs the RIGGED_MESH that
UniRigExportPosedFBX wants, so in-graph posing is unreachable headlessly.

    # static mesh, four facings
    scripts/render_sheet.py output/mesh/golem.glb

    # rigged FBX with an animation baked in: 4 poses sampled across the action
    scripts/render_sheet.py output/golem_rigged.fbx --poses even:4

    # explicit frames
    scripts/render_sheet.py output/golem_anim.fbx --poses frames:1,7,13,19

    # hand-authored poses from bone transforms
    scripts/render_sheet.py output/golem_rigged.fbx --poses transforms:poses/attack.json

Sheet layout is poses down, angles across — the order most engines want when
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
than silently ignored — a typo would otherwise cost you a whole sheet.
"""
from __future__ import annotations

import argparse
import json
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
if ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=path)
elif ext in (".glb", ".gltf"):
    bpy.ops.import_scene.gltf(filepath=path)
elif ext == ".obj":
    bpy.ops.wm.obj_import(filepath=path)
else:
    raise SystemExit(f"unsupported model format: {ext}")

meshes = [o for o in bpy.data.objects if o.type == "MESH"]

# A shape-only mesh (Hunyuan3D ShapeGen, TripoSG) arrives with no material, and
# Blender's default is white — which against a white world light renders as a
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
armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
if not meshes:
    raise SystemExit("no mesh in that file")

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
# own, or for baking an inventory icon -- a flask framed against a figure's
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
bpy.context.collection.objects.link(root)
for ob in list(bpy.data.objects):
    if ob is not root and ob.parent is None:
        ob.parent = root
root.location = (-centre.x, -centre.y, -floor)

pivot = bpy.data.objects.new("pivot", None)
bpy.context.collection.objects.link(pivot)
root.parent = pivot

# --- camera: orthographic, so sprites of the same asset stay the same size ---
cam_data = bpy.data.cameras.new("cam")
cam_data.type = "ORTHO" if cfg["ortho"] else "PERSP"
cam_data.ortho_scale = size * cfg["zoom"]
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera = cam

elev = math.radians(cfg["elevation"])
dist = size * 3.0
cam.location = (0.0, -dist * math.cos(elev), size * 0.5 + dist * math.sin(elev))
cam.rotation_euler = Euler((math.radians(90.0) - elev, 0.0, 0.0), "XYZ")

# --- light: flat and even, so the sheet has no directional bias -------------
world = bpy.data.worlds.new("w")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
world.node_tree.nodes["Background"].inputs[1].default_value = cfg["ambient"]
bpy.context.scene.world = world

key = bpy.data.lights.new("key", "SUN")
key.energy = cfg["key"]
key_ob = bpy.data.objects.new("key", key)
bpy.context.collection.objects.link(key_ob)
key_ob.rotation_euler = Euler((math.radians(55), 0, math.radians(30)), "XYZ")
key_ob.parent = cam            # light rides the camera: every facing lit alike

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = scene.render.resolution_y = cfg["size"]
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"   # no filmic wash on flat art

# --- poses ------------------------------------------------------------------
arm = armatures[0] if armatures else None
missing = set()

def apply_transforms(spec):
    if arm is None:
        return
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = Euler((0, 0, 0), "XYZ")
        pb.location = (0, 0, 0)
    for bone, t in spec.items():
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
    "frame_range": [scene.frame_start, scene.frame_end],
}))
'''


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
    ap.add_argument("model", type=Path, help=".fbx (rigged/animated), .glb or .obj")
    ap.add_argument("--poses", default="static",
                    help="static | frames:1,5,9 | even:N | transforms:FILE")
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
                         "a scale and a golem looms over a homunculus")
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
                         "can also name the down-and-right facing")
    ap.add_argument("--keep-frames", action="store_true",
                    help="keep the per-cell PNGs under output/_sheet_frames/ "
                         "instead of deleting them once the sheet is composed")
    ap.add_argument("--timeout", type=int, default=1800,
                    help="seconds before giving up on Blender (default 1800). A "
                         "hung render otherwise hangs forever")
    args = ap.parse_args()

    model = args.model if args.model.is_absolute() else ROOT / args.model
    if not model.exists():
        return int(bool(sys.stderr.write(f"no such model: {model}\n")))

    poses = parse_poses(args.poses, model)
    # A 2:1 dimetric grid (tile 64 wide by 32 high, so screen =
    # ((u-v)*32, (u+v)*16)).  A ground vector's vertical
    # screen component is sin(elevation), and isoTileH/isoTileW = 0.5, so the
    # camera sits at exactly 30 degrees.  It looks down the diagonal BETWEEN the
    # world axes, so a unit whose Facing is on a world axis (north/east/south/
    # west) must be rendered at 45/135/225/315, not 0/90/180/270 — otherwise the
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
        return 1
    info["run_id"] = run_id
    if info["missing_bones"]:
        print(f"  ! bones not in the rig: {', '.join(info['missing_bones'])}")
    if info["armature"]:
        print(f"  rig     {info['armature']} ({info['bones']} bones), "
              f"frames {info['frame_range'][0]}-{info['frame_range'][1]}")
    else:
        print("  rig     none (static mesh)")

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

#!/usr/bin/env python3
"""Scale a mesh to a declared world size, and record which rule was applied.

    scripts/normalise_mesh.py output/mesh/golem.glb --height 1.15
    scripts/normalise_mesh.py output/mesh/barracks.glb --footprint 1.0
    scripts/normalise_mesh.py output/mesh/*.glb --height 1.15 --check

WHY THIS EXISTS, and it is worth reading before deciding you do not need it:
`render_sheet.py` frames every model to its own bounding box.  A dagger and a
golem therefore fill their cells identically, and a model at ten times the
intended scale renders *perfectly*.  The error is invisible in exactly the
artefact the docs tell you to inspect, and it surfaces later in the engine as
every creature being the same size, which is then hunted for in the renderer.

Nothing else in this repo scales a mesh to a world size.

TWO RULES, because two kinds of asset are sized by different things:

  --height     the model is scaled so its Z extent is exactly this.  For
               anything that stands: figures, creatures, props.  A character is
               sized by how tall it stands.

  --footprint  the model is scaled so the LARGER of its X and Y extent is
               exactly this, and its base is centred on the origin.  For
               anything tile bound: buildings, scenery that sits on a tile.  A
               building is sized by the tile it occupies, not by its spire.

Both put the lowest vertex on z=0, because a model that floats or sinks reads
as a placement bug in the engine and gets debugged there.

A sidecar `<name>.scale.json` records the rule, the factor and the before/after
extents.  That is the part that matters six months later, when the question is
"was this one normalised, and to what?" and the mesh itself cannot say.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import exec_json  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

BLENDER = r'''
import bpy, sys, json, os
import numpy as np

cfg = json.loads(sys.argv[-1])


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
    return meshes


def world_bounds(objs):
    lo = [1e18] * 3
    hi = [-1e18] * 3
    for ob in objs:
        for c in ob.bound_box:
            w = ob.matrix_world @ __import__("mathutils").Vector(c)
            for i in range(3):
                lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
    return lo, hi


out = []
for src in cfg["files"]:
    meshes = load(src)
    lo, hi = world_bounds(meshes)
    span = [hi[i] - lo[i] for i in range(3)]

    if cfg["rule"] == "height":
        current = span[2]
    else:
        current = max(span[0], span[1])
    if current <= 0:
        raise SystemExit(f"{src}: degenerate bounding box {span}")
    k = cfg["target"] / current

    row = {
        "src": src,
        "rule": cfg["rule"],
        "target": cfg["target"],
        "factor": k,
        "before": {"x": span[0], "y": span[1], "z": span[2]},
    }

    if cfg["check"]:
        # Report only. `within` is the question a check is really asking: is
        # this already right, to a tolerance a human would not notice?
        row["after"] = row["before"]
        row["within"] = abs(k - 1.0) <= cfg["tolerance"]
        out.append(row)
        continue

    # One empty parent, so a multi-object scene scales as one thing rather
    # than each part scaling about its own origin.
    root = bpy.data.objects.new("normalise_root", None)
    bpy.context.collection.objects.link(root)
    for ob in list(bpy.data.objects):
        if ob is not root and ob.parent is None:
            ob.parent = root
    root.scale = (k, k, k)
    bpy.context.view_layer.update()

    lo2, hi2 = world_bounds(meshes)
    # Feet on the floor, and centred in the plane. A model that floats or sinks
    # reads as a placement bug in the engine rather than a scale one here.
    root.location = (
        root.location[0] - (lo2[0] + hi2[0]) / 2.0,
        root.location[1] - (lo2[1] + hi2[1]) / 2.0,
        root.location[2] - lo2[2],
    )
    bpy.context.view_layer.update()

    bpy.ops.object.select_all(action="DESELECT")
    for ob in meshes:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    lo3, hi3 = world_bounds(meshes)
    row["after"] = {"x": hi3[0] - lo3[0], "y": hi3[1] - lo3[1], "z": hi3[2] - lo3[2]}
    row["base_z"] = lo3[2]

    dst = cfg["dst"].get(src, src)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in meshes:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if dst.lower().endswith(".glb") or dst.lower().endswith(".gltf"):
        bpy.ops.export_scene.gltf(filepath=dst, use_selection=True,
                                  export_format="GLB")
    elif dst.lower().endswith(".fbx"):
        bpy.ops.export_scene.fbx(filepath=dst, use_selection=True,
                                 add_leaf_bones=False, bake_anim=False)
    else:
        bpy.ops.wm.obj_export(filepath=dst, export_selected_objects=True,
                              export_uv=True, export_normals=True)
    row["dst"] = dst
    out.append(row)

print("NORMALISE " + json.dumps({"rows": out}))
'''


def to_container(p: Path) -> str:
    p = p.resolve()
    for host, cont in ((ROOT / "output", "/app/output"), (ROOT / "input", "/app/input")):
        try:
            return f"{cont}/{p.relative_to(host)}"
        except ValueError:
            continue
    return str(p)


def to_host(p: str) -> Path:
    for cont, host in (("/app/output", ROOT / "output"), ("/app/input", ROOT / "input")):
        if p.startswith(cont + "/"):
            return host / p[len(cont) + 1:]
    return Path(p)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("models", nargs="+", type=Path)
    rule = ap.add_mutually_exclusive_group(required=True)
    rule.add_argument("--height", type=float, metavar="UNITS",
                      help="scale so the model's Z extent is exactly this. For "
                           "anything that stands")
    rule.add_argument("--footprint", type=float, metavar="UNITS",
                      help="scale so the larger of X and Y is exactly this. For "
                           "anything tile bound")
    ap.add_argument("--out-dir", type=Path,
                    help="write beside the source by default; here if given")
    ap.add_argument("--suffix", default="",
                    help="append to the stem, e.g. _norm. Empty overwrites in place")
    ap.add_argument("--check", action="store_true",
                    help="report only, change nothing. Exits 1 if any model is "
                         "outside the tolerance, so it works as a gate")
    ap.add_argument("--tolerance", type=float, default=0.02,
                    help="fractional slack for --check (default 0.02, so 2%%)")
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    files, dst = [], {}
    for m in args.models:
        p = m if m.is_absolute() else ROOT / m
        if not p.exists():
            sys.stderr.write(f"no such model: {p}\n")
            return 2
        c = to_container(p)
        files.append(c)
        target_dir = args.out_dir or p.parent
        if not Path(target_dir).is_absolute():
            target_dir = ROOT / target_dir
        dst[c] = to_container(Path(target_dir) / f"{p.stem}{args.suffix}{p.suffix}")

    cfg = {
        "files": files,
        "dst": dst,
        "rule": "height" if args.height is not None else "footprint",
        "target": args.height if args.height is not None else args.footprint,
        "check": args.check,
        "tolerance": args.tolerance,
    }

    info = exec_json(BLENDER, cfg, "NORMALISE ", timeout=args.timeout)
    if info is None:
        return 1

    bad = 0
    for row in info["rows"]:
        name = Path(row["src"]).name
        b, a = row["before"], row["after"]
        if args.check:
            ok = row["within"]
            bad += 0 if ok else 1
            print(f"  {'ok  ' if ok else 'OFF '} {name:<34} "
                  f"{row['rule']} {b['z' if row['rule'] == 'height' else 'x']:.3f} "
                  f"-> would scale by {row['factor']:.3f}x")
        else:
            print(f"  {name:<34} x{row['factor']:.4f}  "
                  f"[{b['x']:.2f} {b['y']:.2f} {b['z']:.2f}] -> "
                  f"[{a['x']:.2f} {a['y']:.2f} {a['z']:.2f}]")
            side = to_host(row["dst"])
            side.with_suffix(".scale.json").write_text(json.dumps(row, indent=2))

    if args.check:
        print()
        print(f"  {len(info['rows']) - bad}/{len(info['rows'])} within "
              f"{args.tolerance:.0%} of the declared size")
        return 1 if bad else 0

    print()
    print("  A .scale.json sits beside each model recording the rule and factor.")
    print("  Renders will not show you a scale error: render_sheet.py frames every")
    print("  model to its own bounding box, so a wrong scale renders perfectly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

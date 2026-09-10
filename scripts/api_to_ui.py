#!/usr/bin/env python3
"""Turn the API-format workflows into ones ComfyUI's editor can open.

The graphs in `workflows/api/` are what `run_workflow.py` posts to
`/prompt`.  That format is a flat dict of nodes keyed by id, with inputs
named -- which is exactly what a machine wants and exactly what the web
editor cannot open.  The editor wants the *UI* format: a node list with
positions, a link list, and widget values as a **positional array**.

That positional array is the whole reason this is a script and not a
hand-edit.  The order is the order the node declares its inputs in, and
it is only knowable from the running server's `/object_info` -- so this
reads it from there rather than guessing.  Two traps live in it:

- An input wired to another node is a *slot*, not a widget, and takes no
  place in the array.  Getting that wrong shifts every value after it,
  and the graph loads with the steps in the cfg box.
- An INT flagged `control_after_generate` (every `seed`) is followed in
  the array by an extra value the backend never sees -- the editor's
  randomise dropdown.  Miss it and everything after the seed shifts by
  one.

Written into `workflows/default/workflows/`, which is ComfyUI's own user
workflow folder (the compose file mounts `workflows/` at `/app/user`), so
they appear in the editor's sidebar with no import step.

    scripts/api_to_ui.py                 # convert them all
    scripts/api_to_ui.py txt2img_qwen    # or just one
"""

import argparse
import json
import pathlib
import sys
import textwrap
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent.parent
API_DIR = HERE / "workflows" / "api"
UI_DIR = HERE / "workflows" / "default" / "workflows"
SERVER = "http://127.0.0.1:8188"

# Laid out left to right in dependency order.  Generous, because the
# Comfy3D nodes carry a dozen widgets and overlapping nodes are the
# first thing that makes a graph look broken.
COL_W = 460
ROW_H = 320
MARGIN_X = 420          # room for the note at the left

# A short word on each graph, dropped in as a Note node at the top left
# so the editor is self-documenting.  Everything here was learned the
# hard way and is written up at length in ../README.md.
NOTES = {
    "txt2img_qwen": """CHARACTER CONCEPT -- Qwen-Image, 20 steps (~130s)

Edit the two CLIPTextEncode boxes: the top one is the prompt, the
bottom one is the negative.  This is the graph to use when the brief
is long -- it runs at cfg 4.0, so the negative actually steers.

What a prompt that reconstructs into 3D looks like:
  Full body head-to-toe view of a single <subject> standing upright,
  the entire figure visible with space above and below, three-quarter
  view.  <materials, colours, details, in plain sentences>.  Even flat
  studio lighting, plain neutral grey background, no cast shadow.
  Painted game asset concept art, crisp readable silhouette.

Write SENTENCES, not comma-separated tags.  Qwen is a text model and
tag soup wastes it.

Naming a thing in the positive SUMMONS it -- "no tattered hems" puts
tattered hems in the picture.  Unwanted things go in the negative box.

1104x1472 is Qwen's 3:4 and the default for a standing figure.  A
square crops at mid-thigh, and a cropped concept makes a cropped mesh.
1328x1328 is fine for a prop.""",
    "txt2img_qwen_fast": """CHARACTER CONCEPT -- 4-step Lightning, ~30s

For rolling through ideas.  Change the seed in KSampler to reroll.

THE NEGATIVE BOX DOES NOTHING HERE.  The distilled 4-step model runs at
cfg 1.0, where there is no classifier-free guidance to steer with --
so the second CLIPTextEncode is inert whatever you type in it.  Put
everything in the positive, or switch to txt2img_qwen for a real one.""",
    "img_edit_qwen": """CHARACTER EDIT -- Qwen-Image-Edit 2509

Load the image to change in LoadImage, then say what to change in the
TextEncodeQwenImageEditPlus 'prompt' box -- an instruction, not a
description: "replace the left pauldron with a glass chamber of green
fluid", not "a figure with a glass pauldron".

Denoise is a cliff, not a slider.  Below about 0.75 nothing moves;
above it the whole figure is redrawn.  If the edit will not take, it is
usually the prompt, not the number.""",
    "img2mesh_hunyuan3d21": """CONCEPT -> MESH -- Hunyuan3D 2.1 ShapeGen (~50s)

Shape only, no colour: it comes out grey clay.  It removes the
background itself, so a plain concept render is the right input.

LICENCE: Hunyuan3D's terms exclude the EU, the UK and South Korea.
Use img2mesh_triposg (MIT, no territory clause) for anything shipping
worldwide -- but TripoSG does NOT remove the background and needs an
alpha cut-out.

Decimate Mesh's target is a CEILING, not a target: a simpler mesh
stays simpler.""",
    "img2mesh_triposg": """CONCEPT -> MESH -- TripoSG (MIT, ~20s)

No territory clause, so this is the one for anything that ships.

It does NOT remove the background.  Feed it an RGBA cut-out; a
grey-background render comes back as a fragmented blob.""",
    "img2mesh_triposr": """CONCEPT -> MESH -- TripoSR

Fastest and roughest.  Needs an RGBA cut-out, like TripoSG.""",
    "mesh_texture_hunyuan3d21": """MESH -> TEXTURED MESH -- Hunyuan3D 2.1 TexGen

mesh_path is a path INSIDE THE CONTAINER: /app/output/mesh/<name>.glb.
The image is the same concept the shape was generated from.

Run this as its own pass, after the shape.  3D-Pack pins its pipelines
outside ComfyUI's model management, so shape and texture in one queue
run each other out of VRAM on 16GB -- all the shapes, then restart,
then all the textures.""",
    "mesh_render_sprites": """MESH -> TURNTABLE, for looking at

Renders 8 flat unlit frames.  Good enough to check a silhouette; for
form, use scripts/render_sheet.py, which lights it and puts a grey
clay on anything untextured.

mesh_file_path is a CONTAINER path: /app/output/mesh/<name>.glb""",
    "mesh_rig_unirig": """MESH -> RIGGED FBX -- UniRig

UniRigLoadMesh reads a combo of files that already exist on disk, so
the mesh must be saved first: this cannot be wired onto the end of a
generate graph.  source_folder is 'output' and file_path is relative
to it.

GLB in, FBX out.  FBX is what carries a skeleton; OBJ cannot carry one
at all.

MIA is better than mixamo for humanoids, and much faster.""",
    "rig_apply_animation": """RIGGED FBX + CLIP -> ANIMATED FBX

UniRig ships five Mixamo clips and none of them are game cycles.  For
idle/walk/attack, drop clips into input/animation_templates/mixamo/ or
use mesh2motion's 176 CC0 clips.  scripts/list_animations.py prints
both libraries.""",
    "txt2mesh_qwen_hunyuan3d21": """CHARACTER, END TO END -- prompt in, mesh out

One queue: Qwen paints the concept, Hunyuan3D turns it into a mesh.
Both the picture and the mesh are saved, so a good concept is not lost
if the mesh comes out badly.

Convenient, but it commits: the mesh is generated whether or not the
concept was worth it, and a bad concept is the usual reason a mesh
comes out as twenty disconnected pieces.  Use txt2img_qwen_fast to
find the picture first, then img2mesh_hunyuan3d21 on the one you like.

Same licence caveat as img2mesh_hunyuan3d21.""",
    "txt2mesh_sdxl_hunyuan3d21": """CHARACTER, END TO END -- the SDXL version

Kept for comparison.  SDXL base is a photo model: it renders a person
wearing a costume and drops most of a long brief.  Prefer
txt2mesh_qwen_hunyuan3d21.""",
    "img_refine_sdxl": """IMG2IMG REFINE -- SDXL

A second pass over a concept at low denoise.  Superseded by
img_edit_qwen for anything instruction-shaped.""",
    "txt2img_sdxl": """CONCEPT -- SDXL base

Kept, not recommended.  It renders "a person wearing a costume,
photographed in a studio" and drops most of a seven-clause brief.
Use txt2img_qwen.""",
}


def object_info():
    try:
        with urllib.request.urlopen(f"{SERVER}/object_info", timeout=30) as r:
            return json.load(r)
    except (urllib.error.URLError, OSError) as e:
        sys.exit(
            f"cannot reach ComfyUI at {SERVER} ({e}).\n"
            "The widget order can only be read from the running server -- "
            "start it with `docker compose --profile comfy up -d` and wait "
            "for /object_info to answer 200."
        )


def declared_inputs(spec):
    """Every input the node declares, in order, as (name, type, options)."""
    got = []
    for group in ("required", "optional"):
        for name, decl in (spec.get("input", {}).get(group) or {}).items():
            typ = decl[0] if isinstance(decl, list) and decl else decl
            opts = decl[1] if isinstance(decl, list) and len(decl) > 1 else {}
            got.append((name, typ, opts if isinstance(opts, dict) else {}))
    return got


#: Types you type into or pick from, rather than wire up.  "COMBO" is
#: the newer schema's way of declaring a dropdown -- the older one
#: inlines the choices as a list, and the UniRig pack uses the new one.
#: Reading it as a wire is what silently dropped five of its widgets.
WIDGET_TYPES = ("INT", "FLOAT", "STRING", "BOOLEAN", "COMBO")


def is_slot(typ):
    """A connection, rather than something you type or pick."""
    if isinstance(typ, list):
        return False        # an inline list of choices: a combo widget
    return typ not in WIDGET_TYPES


def convert(api, info, name):
    nodes_in = {k: v for k, v in api.items() if not k.startswith("_")}

    # Depth of each node = longest path from a node with no wired inputs,
    # which is what puts loaders on the left and the save on the right.
    depth = {}

    def depth_of(nid, seen=()):
        if nid in depth:
            return depth[nid]
        if nid in seen:
            return 0
        d = 0
        for v in nodes_in[nid]["inputs"].values():
            if isinstance(v, list) and len(v) == 2 and str(v[0]) in nodes_in:
                d = max(d, depth_of(str(v[0]), seen + (nid,)) + 1)
        depth[nid] = d
        return d

    for nid in nodes_in:
        depth_of(nid)

    order = sorted(nodes_in, key=lambda n: (depth[n], int(n)))
    row = {}
    nodes, links = [], []
    next_link = [1]
    # Where each (node, output slot) is, so a consumer can find it.
    produced = {}

    for nid in order:
        node = nodes_in[nid]
        ctype = node["class_type"]
        spec = info.get(ctype)
        if spec is None:
            sys.exit(
                f"{name}: the server does not know the node '{ctype}'.\n"
                "Either a node pack failed to load or the graph is stale -- "
                "check `docker compose logs comfyui` before converting."
            )
        col = depth[nid]
        row[col] = row.get(col, 0) + 1
        pos = [MARGIN_X + col * COL_W, 60 + (row[col] - 1) * ROW_H]

        inputs, widgets = [], []
        for iname, typ, opts in declared_inputs(spec):
            wired = node["inputs"].get(iname)
            if is_slot(typ):
                inputs.append({"name": iname, "type": typ, "link": None,
                               "_wire": wired})
                continue
            if isinstance(wired, list) and len(wired) == 2:
                # A widget that has been wired up instead of typed in:
                # it becomes a slot and drops out of the value array.
                inputs.append({"name": iname, "type": typ if isinstance(typ, str)
                               else "COMBO", "link": None, "_wire": wired})
                continue
            if iname in node["inputs"]:
                widgets.append(node["inputs"][iname])
            elif "default" in opts:
                widgets.append(opts["default"])
            elif isinstance(typ, list) and typ:
                widgets.append(typ[0])
            elif opts.get("options"):
                widgets.append(opts["options"][0])
            else:
                widgets.append("")
            # The editor's randomise dropdown rides along behind a seed.
            if opts.get("control_after_generate"):
                widgets.append("fixed")

        outs = []
        for i, (otype, oname) in enumerate(
                zip(spec.get("output", []), spec.get("output_name", []))):
            outs.append({"name": oname, "type": otype, "links": [],
                         "slot_index": i})
            produced[(nid, i)] = None

        nodes.append({
            "id": int(nid),
            "type": ctype,
            "pos": pos,
            "size": [400, 120],
            "flags": {},
            "order": order.index(nid),
            "mode": 0,
            "inputs": inputs,
            "outputs": outs,
            "properties": {"Node name for S&R": ctype},
            "widgets_values": widgets,
        })

    by_id = {str(n["id"]): n for n in nodes}
    for n in nodes:
        for slot in n["inputs"]:
            wire = slot.pop("_wire", None)
            if not (isinstance(wire, list) and len(wire) == 2):
                continue
            src_id, src_slot = str(wire[0]), int(wire[1])
            src = by_id.get(src_id)
            if src is None:
                continue
            lid = next_link[0]
            next_link[0] += 1
            slot["link"] = lid
            src["outputs"][src_slot]["links"].append(lid)
            links.append([lid, int(src_id), src_slot, n["id"],
                          n["inputs"].index(slot), slot["type"]])

    last_id = max(int(n) for n in nodes_in) if nodes_in else 0

    note = NOTES.get(name)
    if note:
        text = api.get("_comment", "")
        body = note if not text else f"{note}\n\n---\n\n" + "\n".join(
            textwrap.wrap(text, 64))
        last_id += 1
        nodes.insert(0, {
            "id": last_id,
            "type": "Note",
            "pos": [-20, 60],
            "size": [400, 600],
            "flags": {},
            "order": -1,
            "mode": 0,
            "title": "Read me",
            "properties": {"text": ""},
            "widgets_values": [body],
            "color": "#432",
            "bgcolor": "#653",
        })

    return {
        "id": name,
        "revision": 0,
        "last_node_id": last_id,
        "last_link_id": next_link[0] - 1,
        "nodes": nodes,
        "links": links,
        "groups": [],
        "config": {},
        "extra": {},
        "version": 0.4,
    }


def back_to_api(ui, info):
    """The UI graph read back the way ComfyUI reads it, for checking.

    The point of this is the widget array.  A misordered one produces a
    graph that opens, looks right, and runs with the steps in the cfg
    box -- so the only honest check is to put the values back on their
    names and compare with the graph we started from.
    """
    api = {}
    link_src = {l[0]: (str(l[1]), l[2]) for l in ui["links"]}
    for n in ui["nodes"]:
        if n["type"] == "Note":
            continue
        spec = info[n["type"]]
        wired = {i["name"]: i.get("link") for i in n["inputs"]}
        vals = list(n.get("widgets_values", []))
        inputs, at = {}, 0
        for iname, typ, opts in declared_inputs(spec):
            if iname in wired:
                link = wired[iname]
                if link is not None:
                    src, slot = link_src[link]
                    inputs[iname] = [src, slot]
                continue
            if at < len(vals):
                inputs[iname] = vals[at]
                at += 1
                if opts.get("control_after_generate"):
                    at += 1
        api[str(n["id"])] = {"class_type": n["type"], "inputs": inputs}
    return api


def check(name, info, out):
    src = json.loads((API_DIR / f"{name}.json").read_text())
    want = {k: v for k, v in src.items() if not k.startswith("_")}
    got = back_to_api(json.loads((out / f"{name}.json").read_text()), info)
    bad = []
    for nid, node in want.items():
        mine = got.get(nid)
        if mine is None:
            bad.append(f"node {nid} ({node['class_type']}) is missing")
            continue
        if mine["class_type"] != node["class_type"]:
            bad.append(f"node {nid} became {mine['class_type']}")
            continue
        for iname, val in node["inputs"].items():
            back = mine["inputs"].get(iname, "<absent>")
            if isinstance(val, list) and len(val) == 2:
                val = [str(val[0]), val[1]]
            if isinstance(back, list) and len(back) == 2:
                back = [str(back[0]), back[1]]
            if back != val:
                bad.append(
                    f"node {nid} ({node['class_type']}) .{iname}: "
                    f"{val!r} came back as {back!r}")
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("names", nargs="*",
                    help="workflow names to convert (default: all)")
    ap.add_argument("--out", default=str(UI_DIR))
    ap.add_argument("--check", action="store_true",
                    help="read the converted graphs back and compare them "
                         "with the API originals, value by value")
    args = ap.parse_args()

    info = object_info()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    wanted = args.names or sorted(p.stem for p in API_DIR.glob("*.json"))
    failed = 0
    for name in wanted:
        src = API_DIR / f"{name}.json"
        if not src.exists():
            sys.exit(f"no such workflow: {src}")
        ui = convert(json.loads(src.read_text()), info, name)
        (out / f"{name}.json").write_text(json.dumps(ui, indent=1))
        widgets = sum(len(n.get("widgets_values", [])) for n in ui["nodes"])
        note = ""
        if args.check:
            bad = check(name, info, out)
            failed += bool(bad)
            note = "  OK" if not bad else "  MISMATCH\n    " + \
                "\n    ".join(bad)
        print(f"{name:32s} {len(ui['nodes']):2d} nodes  "
              f"{len(ui['links']):2d} links  {widgets:3d} widget values{note}")
    if failed:
        sys.exit(f"\n{failed} workflow(s) did not survive the round trip -- "
                 "do not open these, the widget order is wrong")
    print(f"\nwritten to {out}")
    print("Open ComfyUI at http://127.0.0.1:8188 -- they are in the "
          "sidebar under Workflows.")


if __name__ == "__main__":
    main()

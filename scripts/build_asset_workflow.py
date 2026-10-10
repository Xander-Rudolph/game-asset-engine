#!/usr/bin/env python3
"""Join the pipeline's graphs into editor graphs: asset_workflow.json and krea_workflow.json.

The graphs in `workflows/api/` each do one job: paint a concept, edit it, turn
it into a mesh, texture the mesh, look at it.  Run one at a time, the output of
one has to be carried to the next by hand.  This builds a single graph for the
editor with every stage in it, a prompt at the top, and panels that switch the
stages on and off, one at a time where two stages are alternatives.

It builds two such graphs from the same machinery.  asset_workflow.json is the
whole pipeline, from a prompt to a rig and a video.  krea_workflow.json is its
image and video half, as complete_workflow.json is, with Krea 2 Turbo painting
the concept: Krea has no open edit or image-to-video model, so its Edit and
Animate are the same Qwen and Wan stages.  Krea 2's licence is free for
commercial use only under $1M of company revenue a year; see
docs/guide/licensing.md.

How the stages hand over, which is the point of the design:

- Each stage takes its input from the NEAREST STAGE ABOVE IT THAT IS ON.  Switch
  on Concept, Edit and Mesh together and one queue goes from prompt to mesh.
- A stage with no stage above it switched on takes its input from its own
  picker instead: "Load Image (from Outputs)" for an image, a path box for a
  mesh.  So a step can be run on its own as often as it takes, and the result
  you want is the one you pick.  The picker's refresh arrow selects the newest
  file, which is the run you just made.
- rgthree's Any Switch does the choosing: it passes on its first input that is
  present, and a muted stage sends nothing.  A picker must not be validated
  when a live stage above feeds the switch, or an empty picker would stop the
  whole queue, so an rgthree relay mutes it whenever any stage above is on
  (the same device complete_workflow.json uses for its input image).
- Each image stage makes a batch of takes, and an Image Filter (cg-image-filter)
  after it pauses the queue to show them and passes on the one clicked.  It is
  an ordinary node, so the server runs it only when a stage below reads it; a
  stage queued on its own just saves its takes.
- The pickers sit together in a Stage inputs row under the prompt, in stage
  order, so a run can be picked up at any stage from the top of the graph.  A
  picker is also muted while its own stage is off, so the pickers lit up are
  exactly the ones the next queue reads.  A relay can only say "mute when any
  input is active", so the second rule needs an inverter: a relay watching the
  stage drives a flag node that is active while the stage is off, and the
  picker's relay watches the sources and that flag together.

Stage images save to the top of output/, as asset_<stage>_NNNNN_.png, because
the picker lists only the top of that folder: ComfyUI's /internal/files/output
route reads it with os.scandir, not recursively.  Meshes stay in output/mesh/,
rigs in output/rigged/ and video in output/video/, so none of them lands in an
image picker, which lists every file at the top of output/, not only images.

Built, never hand-edited, from the base graphs, so a fix to one of them reaches
this graph on the next run.  Presets come first: the Simplify stage is read
from preset_simplify_concept.json, which scripts/build_presets.py writes.

    scripts/build_asset_workflow.py              # write both
    scripts/build_asset_workflow.py --check      # write both, then verify them
    scripts/build_asset_workflow.py --dry-run    # verify in memory, write nothing
    scripts/build_asset_workflow.py --graph krea_workflow   # just one

The check puts every widget value back on its name and compares the graph with
the base graphs it came from, as scripts/api_to_ui.py --check does.  It cannot
see the relays work, because they run in the browser; see
docs/guide/asset-workflow.md for how that was checked.  Needs the server
($COMFY_URL, or http://127.0.0.1:8188), for the same reason api_to_ui.py does:
the widget order is only knowable from /object_info.
"""

import argparse
import json
import pathlib
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import api_to_ui  # noqa: E402  (a sibling script, not a package)

API_DIR = api_to_ui.API_DIR

# Loaders every Qwen stage would otherwise load again for itself.  Merged into
# one copy each in the Models group: two CLIPLoaders are two 8.8GB text
# encoders in RAM on a 31GB host.  Merged only when class and settings match.
SHARED = {"UNETLoader", "CLIPLoader", "VAELoader", "ModelSamplingAuraFlow",
          "CFGNorm"}

# Frontend-only nodes: never sent to the server, so not in /object_info.
# Anything Everywhere is in /object_info but does nothing there: its work is
# done in the browser, when it wires its input into the prompt.
VIRTUAL = {"Note", "MarkdownNote", "Fast Groups Muter (rgthree)",
           "Mute / Bypass Relay (rgthree)", "Mute / Bypass Repeater (rgthree)",
           "Anything Everywhere"}
BROADCAST = {"CLIPLoader", "VAELoader"}
SWITCH = "Any Switch (rgthree)"
MUTE, ACTIVE = 2, 0
DROPPED = "<dropped>"

# Group titles the stage panels list.  Each filters groups by a regex on the
# stage number, so the Inputs and Models groups, which must never be muted,
# stay off every panel.  Stages that share a number are alternatives, such as
# the two Mesh stages, so each such number gets a panel of its own that lets at
# most one of them be on: TRELLIS and Hunyuan3D in one queue load both models.
STAGE_TITLE = r"^({})\. "

# ---------------------------------------------------------------- the stages
# src:      the base graph in workflows/api/
# drop:     nodes replaced by something outside the stage (its LoadImage)
# feed:     "node.input" -> what drives it instead: an input switch, a text
# set:      "node.input" -> a value this graph uses instead of the base one
# result:   (node, slot) the next stage reads, and the relays watch
# save:     node whose filename_prefix moves to the top of output/
# takes:    "node.input", the batch size the Takes box drives; or
#           "repeat:node.input", a latent input that gets a RepeatLatentBatch
#           in front of it, for a stage whose latent comes from an image
# pick:     an Image Filter after the result pauses the queue, shows the
#           takes, and passes on the one clicked; it runs only when a stage
#           below reads it, so a stage run on its own never pauses
# on:       switched on when the graph opens
STAGES = [
    # No base graph: one LoadImage, for concept art made elsewhere.  On, it
    # is the stage above every image stage, so Edit, Simplify, Mesh and
    # Animate read it when nothing nearer is on; its upload button puts the
    # file in input/.
    {"key": "own_image",
     "title": "0. Your image: start from concept art you already have",
     "result": ("1", 0)},
    {"key": "concept_fast", "src": "txt2img_qwen_fast", "on": True,
     "title": "1. Concept, fast: Qwen-Image 4-step",
     "feed": {"4.text": "prompt"}, "takes": "6.batch_size", "pick": True,
     "result": ("9", 0), "save": ("10", "asset_concept_fast")},
    {"key": "concept", "src": "txt2img_qwen",
     "title": "1. Concept, full: Qwen-Image 20 steps",
     "feed": {"4.text": "prompt"}, "takes": "6.batch_size", "pick": True,
     "result": ("9", 0), "save": ("10", "asset_concept")},
    {"key": "edit", "src": "img_edit_qwen",
     "title": "2. Edit: Qwen-Image-Edit 2509",
     "drop": ["1"], "feed": {"2.image": "image_switch:edit",
                             "8.prompt": "instruction"},
     "takes": "repeat:11.latent_image", "pick": True,
     "result": ("12", 0), "save": ("13", "asset_edit")},
    {"key": "simplify", "src": "preset_simplify_concept",
     "title": "3. Simplify: game-ready shapes, Qwen-Image-Edit 2509",
     "drop": ["1"], "feed": {"2.image": "image_switch:simplify"},
     "takes": "repeat:11.latent_image", "pick": True,
     "result": ("12", 0), "save": ("13", "asset_simplify")},
    {"key": "mesh_trellis", "src": "img2mesh_trellis",
     "title": "4. Mesh: TRELLIS (MIT)",
     "drop": ["1"], "feed": {"3.images": "image_switch:mesh"},
     "result": ("5", 0)},
    {"key": "mesh_hunyuan", "src": "img2mesh_hunyuan3d21",
     "title": "4. Mesh: Hunyuan3D 2.1 (excludes EU, UK, South Korea)",
     "drop": ["1"], "feed": {"3.image": "image_switch:mesh"},
     "result": ("5", 0)},
    {"key": "texture", "src": "mesh_texture_hunyuan3d21",
     "title": "5. Texture: Hunyuan3D 2.1 (excludes EU, UK, South Korea)",
     "drop": ["1"], "feed": {"3.image": "image_switch:mesh",
                             "3.mesh_path": "path_switch:texture"},
     "result": ("4", 0)},
    {"key": "turntable", "src": "mesh_render_sprites",
     "title": "6. Turntable: 8 flat frames to check the silhouette",
     "feed": {"1.mesh_file_path": "path_switch:turntable"}},
    # UniRig's loader offers a list of files, but a wired path skips the list:
    # the server checks a value against a list only when it is typed in, and
    # the node joins the path onto output/, where an absolute path wins.
    {"key": "rig", "src": "mesh_rig_unirig",
     "title": "7. Rig: UniRig, articulationxl skeleton",
     "feed": {"1.file_path": "path_switch:rig"},
     "set": {"3.fbx_name": "rigged/asset"},
     "result": ("3", 0)},
    {"key": "animate", "src": "img2video_wan22",
     "title": "8. Animate: Wan 2.2 image to video, five seconds",
     "drop": ["1"], "feed": {"12.start_image": "image_switch:animate",
                             "10.text": "motion"},
     "set": {"16.filename_prefix": "video/asset_animate",
             "17.filename_prefix": "video/asset_animate"},
     "save": ("19", "asset_animate_last")},
]

# Stage 0's graph, the one stage with no file in workflows/api/.
OWN_IMAGE_GRAPH = {
    "_comment": "Concept art you already have. Upload it here, or pick a file "
                "already in input/. With this stage on and the Concept stages "
                "off, Edit, Simplify, Mesh and Animate start from it.",
    "1": {"class_type": "LoadImage", "inputs": {"image": "example.png"},
          "_meta": {"title": "Your image"}},
}

# The texts typed at the top: key -> (stage, node, input, title).  Each takes
# its default from the base graph it feeds.
TEXTS = {
    "prompt": ("concept", "4", "text", "Prompt (both Concept stages)"),
    "instruction": ("edit", "8", "prompt", "Edit instruction (Stage 2)"),
    "motion": ("animate", "10", "text", "Motion prompt (Stage 8)"),
}

# How many takes each image stage makes per queue, and how long a pick waits.
# Two takes of Concept, fast, is about 45 s; the reference card's limit for a
# batch of 1104x1472 Qwen images is not measured.  A pick left alone for an
# hour sends the first take on, so an unattended queue still finishes.
TAKES = 2
PICK_TIMEOUT = 3600
PICK = "Image Filter"

# The input switches, in stage order, which is the order of the pickers in the
# Stage inputs row.  Sources are nearest first: the switch passes on the first
# one present.  The picker comes last, muted while any source is on.
SWITCHES = {
    "image_switch:edit": {
        "type": "IMAGE", "sources": ["concept", "concept_fast", "own_image"],
        "title": "2. Edit takes",
        "picker": "2. Edit: image to edit"},
    "image_switch:simplify": {
        "type": "IMAGE", "sources": ["edit", "concept", "concept_fast", "own_image"],
        "title": "3. Simplify takes",
        "picker": "3. Simplify: image to simplify"},
    "image_switch:mesh": {
        "type": "IMAGE",
        "sources": ["simplify", "edit", "concept", "concept_fast", "own_image"],
        "title": "4. Mesh and 5. Texture take",
        "picker": "4. Mesh and 5. Texture: concept image"},
    "path_switch:texture": {
        "type": "STRING", "sources": ["mesh_trellis", "mesh_hunyuan"],
        "title": "5. Texture mesh",
        "picker": "5. Texture: mesh to texture (container path)"},
    "path_switch:turntable": {
        "type": "STRING", "sources": ["texture", "mesh_trellis", "mesh_hunyuan"],
        "title": "6. Turntable mesh",
        "picker": "6. Turntable: mesh to render (container path)"},
    "path_switch:rig": {
        "type": "STRING", "sources": ["texture", "mesh_trellis", "mesh_hunyuan"],
        "title": "7. Rig mesh",
        "picker": "7. Rig: mesh to rig (container path)"},
    "image_switch:animate": {
        "type": "IMAGE",
        "sources": ["simplify", "edit", "concept", "concept_fast", "own_image"],
        "title": "8. Animate takes",
        "picker": "8. Animate: start frame"},
}

README = """## Asset pipeline

Write the subject in **Prompt**, switch stages on in the **Stage** panels, and queue.
Only Stage 1, fast, is on when the graph opens. Stages that share a number are
alternatives, and their panel lets one at a time be on: switching on Hunyuan3D
switches TRELLIS off, so one queue never loads both.

**Handing over.** Each stage takes its input from the nearest stage above it that
is on. With Concept, Edit and Mesh all on, one queue goes from prompt to mesh.

**Starting from your own concept art.** Switch on **0. Your image**, upload the
file there or pick one already in `input/`, leave the Concept stages off, and
switch on the stages to run: Edit, Simplify, Mesh, Texture, Animate. The Stage
inputs row does the same for a file already in `output/`.

**Takes and picks.** Each image stage (1 to 3) makes **Takes** images per queue,
and saves them all. When a stage below it is on, the queue pauses after the
stage, shows the takes, and carries on with the one you click and Send. Escape
cancels the queue; left alone for an hour it carries on with the first take.
Click one take: Mesh and Animate expect one image. A stage with nothing below it
on never pauses, so a stage on its own just makes its takes.

**Picking up at any stage.** The **Stage inputs** row below holds one picker per
stage, in stage order. A picker is read only when its stage is on and no stage
above it is on, and it is muted otherwise, so the pickers lit up are exactly the
ones the next queue reads. Switch on one stage, pick its input, and queue as often
as it takes. Then switch it off, switch on the next stage, and press that picker's
refresh arrow: it selects the newest file, which is the take you just made, or pick
any earlier one. To edit an edit, pick the last edit in Edit's own picker.

**Pickers** list the top of `output/`, where every image stage here saves as
`asset_<stage>_NNNNN_.png`. Meshes save to `output/mesh/`, rigs to
`output/rigged/` and video to `output/video/`; the mesh pickers are path boxes
holding a container path such as `/app/output/mesh/asset.glb`.

**Seeds** are set to randomise, so each queue of a stage is a new take.

**Models.** A loader only one stage uses sits in that stage. The shared ones sit
in Models, which is never muted: a loader there runs only when a stage that is on
needs it. The Qwen text encoder and VAE reach every stage through the two Use
Everywhere nodes in Models, so their wires are not drawn.

**Memory, on a 16 GB card and a 31 GB host.** Each Qwen stage loads a 20 GB
diffusion model, and a queue that runs two of them loads both: not yet run
together on the reference machine. Mesh and Texture in one queue run out of
VRAM, because 3D-Pack keeps its pipelines outside ComfyUI's model management:
run Mesh, restart ComfyUI, then run Texture with Mesh off.

**Licences.** The Hunyuan3D stages are under a licence that excludes the EU, the
UK and South Korea; TRELLIS is MIT; Wan 2.2 is Apache-2.0. See docs/guide/licensing.

**7. Rig** hands UniRig the mesh path from the Mesh or Texture stage, or from its
path box, so the mesh need not be in the loader's file list. Its skeleton is
`articulationxl`, whose bones are `bone_N`; `scripts/bone_roles.py map` names them.

**8. Animate** makes five seconds of video of the image with Wan 2.2, under
`output/video/`, and its last frame at the top of `output/`. Its settings are
the ones that ran on the 16 GB reference card: 480x640 and 20 steps, with the
4-step LoRAs in the graph at strength 0, because at strength 1 that card ran out
of memory merging them into the fp8 weights. It makes a video, not a clip:
nothing in this image turns the video into motion for the rig.
docs/reference/video-mocap.md is the state of that.

Built by scripts/build_asset_workflow.py from the graphs in workflows/api/.
Change those, not this."""

# ------------------------------------------------------- krea_workflow.json
# The image and video half of the pipeline, as complete_workflow.json is, with
# Krea 2 Turbo painting the concept.  Krea has no open edit or image-to-video
# model, so Edit and Animate are the Qwen and Wan stages of asset_workflow.json.
KREA_STAGES = [
    {"key": "own_image",
     "title": "0. Your image: start from concept art you already have",
     "result": ("1", 0)},
    {"key": "krea", "src": "txt2img_krea2", "on": True,
     "title": "1. Concept: Krea 2 Turbo, 8 steps",
     "feed": {"3.text": "prompt"}, "takes": "5.batch_size", "pick": True,
     "result": ("8", 0), "save": ("9", "krea_concept")},
    {"key": "krea_style", "src": "txt2img_krea2_style",
     "title": "1. Concept, styled: Krea 2 Turbo with a style reference",
     "feed": {"7.prompt": "prompt"}, "takes": "14.batch_size", "pick": True,
     "result": ("16", 0), "save": ("17", "krea_concept_styled")},
    {"key": "edit", "src": "img_edit_qwen",
     "title": "2. Edit: Qwen-Image-Edit 2509",
     "drop": ["1"], "feed": {"2.image": "image_switch:edit",
                             "8.prompt": "instruction"},
     "takes": "repeat:11.latent_image", "pick": True,
     "result": ("12", 0), "save": ("13", "krea_edit")},
    {"key": "animate", "src": "img2video_wan22",
     "title": "3. Animate: Wan 2.2 image to video, five seconds",
     "drop": ["1"], "feed": {"12.start_image": "image_switch:animate",
                             "10.text": "motion"},
     "set": {"16.filename_prefix": "video/krea_animate",
             "17.filename_prefix": "video/krea_animate"},
     "save": ("19", "krea_animate_last")},
]

KREA_OWN_IMAGE_GRAPH = {
    "_comment": "Concept art you already have. Upload it here, or pick a file "
                "already in input/. With this stage on and the Concept stages "
                "off, Edit and Animate start from it.",
    "1": OWN_IMAGE_GRAPH["1"],
}

KREA_TEXTS = {
    "prompt": ("krea", "3", "text", "Prompt (both Concept stages)"),
    "instruction": ("edit", "8", "prompt", "Edit instruction (Stage 2)"),
    "motion": ("animate", "10", "text", "Motion prompt (Stage 3)"),
}

KREA_SWITCHES = {
    "image_switch:edit": {
        "type": "IMAGE", "sources": ["krea_style", "krea", "own_image"],
        "title": "2. Edit takes",
        "picker": "2. Edit: image to edit"},
    "image_switch:animate": {
        "type": "IMAGE", "sources": ["edit", "krea_style", "krea", "own_image"],
        "title": "3. Animate takes",
        "picker": "3. Animate: start frame"},
}

KREA_README = """## Krea pipeline

The image and video half of the pipeline on Krea 2 Turbo: a concept from the
prompt, an edit of it, and five seconds of video. Krea has no open model for
editing or for image to video, so Stage 2 is Qwen-Image-Edit 2509 and Stage 3
is Wan 2.2, the same stages as in asset_workflow.json.

**Licence first.** The Krea 2 Community License allows commercial use of the
model and of what it makes only while your company, affiliates included, earns
under $1,000,000 a year. Past that you must stop commercial use, of its outputs
too, until Krea grants an enterprise licence; it makes no exception for images
made earlier. Krea may end the licence for any reason on 30 days' notice, and it
requires content filtering: look at every image before it ships. The style
reference LoRA is under the same licence. Qwen-Image-Edit 2509 and Wan 2.2 are
Apache-2.0. See docs/guide/licensing.

Write the subject in **Prompt**, switch stages on in the **Stage** panels, and
queue. Only Stage 1, Concept, is on when the graph opens. The two Stage 1 rows
are alternatives, and their panel lets one at a time be on. **Concept, styled**
paints the prompt in the style of the image in its **Style Reference** node: it
takes the look, not the content.

**Handing over.** Each stage takes its input from the nearest stage above it
that is on. With Concept, Edit and Animate all on, one queue goes from the
prompt to a video. To start from your own art, switch on **0. Your image** and
leave the Concept stages off.

**Takes and picks.** Stages 1 and 2 make **Takes** images per queue and save
them all. When a stage below is on, the queue pauses after the stage, shows the
takes, and carries on with the one you click and Send. Escape cancels the
queue; left alone for an hour it carries on with the first take. A stage with
nothing below it on never pauses.

**Picking up at any stage.** The **Stage inputs** row holds one picker per
stage that reads an image. A picker is read only when its stage is on and no
stage above it is on, and is muted otherwise. Its refresh arrow selects the
newest file in `output/`, where the stages save as `krea_<stage>_NNNNN_.png`;
the video goes to `output/video/`.

**Seeds** are set to randomise, so each queue of a stage is a new take. Krea
runs at cfg 1, so it has no negative prompt: put everything in **Prompt**.

**Memory, on a 16 GB card and a 31 GB host.** The Krea 2 Turbo weights are
12.6 GiB with a 4.9 GiB encoder, the edit model 19.0 GiB with an 8.7 GiB
encoder, and Wan's two experts 13.3 GiB each (file sizes). A queue that runs
every stage loads them in turn: not yet run on the reference machine.

**3. Animate** keeps the settings that ran on the 16 GB reference card: 480x640
and 20 steps, with the 4-step LoRAs in the graph at strength 0.

Built by scripts/build_asset_workflow.py from the graphs in workflows/api/.
Change those, not this."""

# The graphs this script builds.  Node and link ids start where no other graph
# here numbers, and where the two graphs' ranges do not meet, so a relay left
# running from one graph finds nothing in another opened after it (see the
# note above stage_rows below).
GRAPHS = {
    "asset_workflow": {
        "stages": STAGES, "own_image": OWN_IMAGE_GRAPH, "texts": TEXTS,
        "switches": SWITCHES, "readme": README,
        "takes_title": "Takes per image stage (each queue of Stages 1 to 3)",
        "models_title": "Models (shared by the Qwen stages; a loader only "
                        "runs for a stage that is on)",
        "node_base": 10000, "link_base": 100000},
    "krea_workflow": {
        "stages": KREA_STAGES, "own_image": KREA_OWN_IMAGE_GRAPH,
        "texts": KREA_TEXTS, "switches": KREA_SWITCHES, "readme": KREA_README,
        "takes_title": "Takes per image stage (each queue of Stages 1 and 2)",
        "models_title": "Models (shared by the Krea and Qwen stages; a loader "
                        "only runs for a stage that is on)",
        "node_base": 20000, "link_base": 200000},
}

# ------------------------------------------------------------------ layout
COL_W = 460
GAP = 40                # between rows, and between a group and its contents
HANDOFF_X = 0           # the pickers and switches, left of the stage groups
STAGE_X = 520


def height_of(node):
    """A rough height for spacing rows.  The editor sizes nodes to fit their
    widgets on load, so this only has to be generous, not exact."""
    if node["type"] in ("LoadImageOutput",):
        return 420
    slots = max(len(node.get("inputs", [])), len(node.get("outputs", [])))
    return 60 + 22 * slots + 28 * len(node.get("widgets_values") or [])


def note_node(nid, text, pos, size, markdown=False):
    return {"id": nid, "type": "MarkdownNote" if markdown else "Note",
            "pos": pos, "size": size, "flags": {}, "order": 0, "mode": 0,
            "inputs": [], "outputs": [], "properties": {},
            "widgets_values": [text], "color": "#432", "bgcolor": "#653"}


# ------------------------------------------------------------------- build
# Node ids from 10000 and link ids from 100000 in asset_workflow.json, and
# from 20000 and 200000 in krea_workflow.json (GRAPHS).  rgthree's Mute /
# Bypass Relays keep polling after the editor loads another graph, and find
# their targets by link id in whatever graph is now open; with ids from 1, the
# relays of asset_workflow.json muted and bypassed nodes of
# complete_workflow.json opened in the same tab (its CLIP switch and its LoRA
# loader, 2026-10-04).  No hand-built or converted graph here numbers that
# high, so a leftover relay finds nothing.


def stage_rows(spec, numbers):
    """The stages whose titles start with one of these numbers."""
    return [s for s in spec["stages"] if s["title"].split(".")[0] in numbers]


def stage_panels(spec):
    """(title, stage numbers, at most one on) for each stage panel, in order."""
    order = []
    for s in spec["stages"]:
        n = s["title"].split(".")[0]
        if n not in order:
            order.append(n)
    panels = []
    for n in order:
        rows = stage_rows(spec, [n])
        if len(rows) > 1:
            name = rows[0]["title"].split(". ", 1)[1].split(",")[0].split(":")[0]
            panels.append((f"Stage {n}, {name}: one at a time", [n], True))
        elif panels and not panels[-1][2]:
            panels[-1][1].append(n)
        else:
            panels.append(("", [n], False))
    out = []
    for title, numbers, only_one in panels:
        if not title:
            title = (f"Stage {numbers[0]}" if len(numbers) == 1 else
                     f"Stages {numbers[0]} and {numbers[1]}" if len(numbers) == 2 else
                     f"Stages {numbers[0]} to {numbers[-1]}")
        out.append((title, numbers, only_one))
    return out


def build(info, spec):
    api = {}                       # every backend node, as the server sees it
    group_of = {}                  # node id -> group key
    title = {}                     # node id -> title shown in the editor
    next_id = [spec["node_base"]]

    def new(ctype, inputs, group, name=None):
        nid = str(next_id[0])
        next_id[0] += 1
        api[nid] = {"class_type": ctype, "inputs": inputs}
        group_of[nid] = group
        if name:
            title[nid] = name
        return nid

    base = {s["key"]: (json.loads((API_DIR / f"{s['src']}.json").read_text())
                       if "src" in s else spec["own_image"])
            for s in spec["stages"]}

    # The texts typed at the top.  Their defaults are the base graphs' own.
    text_id = {}
    for key, (stage, lid, iname, name) in spec["texts"].items():
        text_id[key] = new("PrimitiveStringMultiline",
                           {"value": base[stage][lid]["inputs"][iname]},
                           "inputs", name)
    takes = new("PrimitiveInt", {"value": TAKES}, "inputs",
                spec["takes_title"])

    # Shared loaders first, so a stage can point at them.
    shared = {}                    # canonical key -> node id
    local = {}                     # (stage, local id) -> node id

    def canonical(stage, lid):
        node = base[stage][lid]
        ins = {}
        for k, v in node["inputs"].items():
            if isinstance(v, list) and len(v) == 2:
                ins[k] = ("link", canonical(stage, str(v[0])), v[1])
            else:
                ins[k] = v
        return (node["class_type"], json.dumps(ins, sort_keys=True))

    def is_shared(stage, lid):
        node = base[stage][lid]
        if node["class_type"] not in SHARED:
            return False
        return all(is_shared(stage, str(v[0])) for v in node["inputs"].values()
                   if isinstance(v, list) and len(v) == 2)

    for s in spec["stages"]:
        g = base[s["key"]]
        order = sorted((k for k in g if not k.startswith("_")), key=int)
        # Upstream before downstream, so a model chain's links resolve.
        for lid in sorted(order, key=lambda k: depth_in(g, k)):
            if not is_shared(s["key"], lid):
                continue
            key = canonical(s["key"], lid)
            if key not in shared:
                ins = {}
                for k, v in g[lid]["inputs"].items():
                    ins[k] = ([local[(s["key"], str(v[0]))], v[1]]
                              if isinstance(v, list) and len(v) == 2 else v)
                shared[key] = new(g[lid]["class_type"], ins, "models")
            local[(s["key"], lid)] = shared[key]

    # Stage nodes, with fresh ids.  Links are resolved in a second pass, once
    # every node in every stage has its new id.
    for s in spec["stages"]:
        g = base[s["key"]]
        for lid in sorted((k for k in g if not k.startswith("_")), key=int):
            if (s["key"], lid) in local or lid in s.get("drop", []):
                continue
            local[(s["key"], lid)] = new(g[lid]["class_type"],
                                         dict(g[lid]["inputs"]), s["key"])

    # Input switches, in the hand-off column, and their pickers, in the Stage
    # inputs row.  The flag is the inverter's output: a node that is active
    # while every stage reading the switch is off, which the picker's relay
    # watches beside the sources.  It is a string nobody reads, so the server
    # never runs it; a picker needs a node with an output to be muted through.
    switch_id, picker_id, flag_id = {}, {}, {}
    for key, sw in spec["switches"].items():
        if sw["type"] == "IMAGE":
            picker_id[key] = new("LoadImageOutput", {"image": ""},
                                 "inputs", sw["picker"])
        else:
            picker_id[key] = new("PrimitiveString",
                                 {"value": "/app/output/mesh/asset.glb"},
                                 "inputs", sw["picker"])
        switch_id[key] = new(SWITCH, {}, "handoff:" + key, sw["title"])
        flag_id[key] = new("PrimitiveString", {"value": ""}, "handoff:" + key,
                           sw["title"] + ": flag, active while its stage is off")

    # The pick after an image stage: an Image Filter on its result, which
    # becomes what the stages below and the relays read.  It is an ordinary
    # node, so the server runs it only when something below it is on.
    result = {}
    for s in spec["stages"]:
        if "result" in s:
            lid, slot = s["result"]
            result[s["key"]] = [local[(s["key"], lid)], slot]
        if s.get("pick"):
            number = s["title"].split(":")[0]
            filt = new(PICK, {"images": result[s["key"]],
                              "timeout": PICK_TIMEOUT, "ontimeout": "send first",
                              "tip": f"{number}: click the take to carry on "
                                     "with, then Send. Escape cancels the queue."},
                       s["key"], f"{number}: pick the take")
            result[s["key"]] = [filt, 0]

    # The stages that read each switch, by the node that reads it: what the
    # inverter watches.
    owners = {key: [] for key in spec["switches"]}
    for s in spec["stages"]:
        for target, what in s.get("feed", {}).items():
            if what in spec["switches"]:
                lid = target.split(".")[0]
                node = local[(s["key"], lid)]
                if (s["key"], node) not in owners[what]:
                    owners[what].append((s["key"], node))

    for key, sw in spec["switches"].items():
        wires = [result[k] for k in sw["sources"]] + [[picker_id[key], 0]]
        api[switch_id[key]]["inputs"] = {
            f"any_{i:02d}": w for i, w in enumerate(wires, 1)}

    # Rewire each stage: its links, what it is fed, where it saves.
    for s in spec["stages"]:
        g = base[s["key"]]
        for lid in g:
            if lid.startswith("_") or lid in s.get("drop", []):
                continue
            nid = local[(s["key"], lid)]
            if group_of[nid] == "models":
                continue
            ins = api[nid]["inputs"]
            for k, v in list(ins.items()):
                if isinstance(v, list) and len(v) == 2:
                    # A link to a dropped node waits for its feed below.
                    ins[k] = (DROPPED if str(v[0]) in s.get("drop", [])
                              else [local[(s["key"], str(v[0]))], v[1]])
        for target, what in s.get("feed", {}).items():
            lid, iname = target.split(".")
            src = [text_id[what] if what in text_id else switch_id[what], 0]
            api[local[(s["key"], lid)]]["inputs"][iname] = src
        for target, val in s.get("set", {}).items():
            lid, iname = target.split(".")
            api[local[(s["key"], lid)]]["inputs"][iname] = val
        if "takes" in s:
            repeat = s["takes"].startswith("repeat:")
            lid, iname = s["takes"].split(":")[-1].split(".")
            ins = api[local[(s["key"], lid)]]["inputs"]
            if repeat:
                ins[iname] = [new("RepeatLatentBatch",
                                  {"samples": ins[iname], "amount": [takes, 0]},
                                  s["key"]), 0]
            else:
                ins[iname] = [takes, 0]
        if "save" in s:
            lid, prefix = s["save"]
            api[local[(s["key"], lid)]]["inputs"]["filename_prefix"] = prefix

    # Anything still pointing at a dropped node was not fed: a stage spec bug.
    for nid, node in api.items():
        for k, v in node["inputs"].items():
            if v == DROPPED:
                sys.exit(f"{group_of[nid]}: {node['class_type']}.{k} reads a "
                         "dropped node; give it a 'feed'")

    # A loader only one stage uses belongs inside that stage, so switching the
    # stage off takes its loader with it.  Only what two or more stages share
    # stays in Models, which is never muted.
    users = {nid: set() for nid, g in group_of.items() if g == "models"}
    for nid, node in api.items():
        for v in node["inputs"].values():
            if isinstance(v, list) and len(v) == 2 and v[0] in users \
                    and group_of[nid] != "models":
                users[v[0]].add(group_of[nid])
    changed = True
    while changed:
        changed = False
        for nid in users:
            for v in api[nid]["inputs"].values():
                if isinstance(v, list) and len(v) == 2 and v[0] in users \
                        and not users[nid] <= users[v[0]]:
                    users[v[0]] |= users[nid]
                    changed = True
    for nid, stages in users.items():
        if len(stages) == 1:
            group_of[nid] = next(iter(stages))
    return api, group_of, title, {"switch": switch_id, "picker": picker_id,
                                  "flag": flag_id, "owners": owners,
                                  "result": result}


def depth_in(graph, lid, seen=()):
    """Longest chain of links above a node, inside one graph."""
    node = graph[lid]
    d = 0
    for v in node["inputs"].values():
        if isinstance(v, list) and len(v) == 2 and str(v[0]) in graph \
                and str(v[0]) not in seen:
            d = max(d, depth_in(graph, str(v[0]), seen + (lid,)) + 1)
    return d


def to_ui(api, group_of, title, wiring, info, spec):
    """The joined graph as the editor's file: nodes placed in groups, links,
    the stage panel and the relays."""
    switch_id, picker_id, flag_id = wiring["switch"], wiring["picker"], wiring["flag"]
    owners, result = wiring["owners"], wiring["result"]
    nodes, links = [], []
    by_id = {}
    next_link = [spec["link_base"]]
    last_id = max(int(k) for k in api)

    def fresh_id():
        nonlocal last_id
        last_id += 1
        return last_id

    def link(src_node, src_slot, dst_node, dst_slot, typ):
        lid = next_link[0]
        next_link[0] += 1
        src_node["outputs"][src_slot].setdefault("links", [])
        if src_node["outputs"][src_slot]["links"] is None:
            src_node["outputs"][src_slot]["links"] = []
        src_node["outputs"][src_slot]["links"].append(lid)
        dst_node["inputs"][dst_slot]["link"] = lid
        links.append([lid, src_node["id"], src_slot, dst_node["id"], dst_slot, typ])

    # Backend nodes.  Positions are placeholders until the layout pass.
    for nid, node in api.items():
        if node["class_type"] == SWITCH:
            n = len(node["inputs"])
            typ = spec["switches"][next(k for k, v in switch_id.items() if v == nid)]["type"]
            built = {"id": int(nid), "type": SWITCH, "pos": [0, 0],
                     "size": [260, 60 + 22 * (n + 1)], "flags": {}, "order": 0,
                     "mode": 0,
                     "inputs": [{"name": f"any_{i:02d}", "type": typ, "link": None,
                                 "_wire": node["inputs"][f"any_{i:02d}"]}
                                for i in range(1, n + 1)]
                     + [{"name": f"any_{n + 1:02d}", "type": typ, "link": None}],
                     "outputs": [{"name": "*", "label": typ, "type": typ,
                                  "links": [], "slot_index": 0}],
                     "properties": {"Node name for S&R": SWITCH},
                     "widgets_values": []}
        else:
            built = api_to_ui.build_node(nid, node, info[node["class_type"]],
                                         [0, 0], 0)
            # Every seed randomises: a stage run again is a new take.  The
            # value itself is the base graph's; only the control after it,
            # which the server never sees, changes.
            # The Takes box is an integer with the same dropdown, and must
            # stay put between queues.
            wv = built["widgets_values"]
            for i in range(len(wv) - 1):
                if wv[i + 1] == "fixed" and isinstance(wv[i], int) \
                        and not isinstance(wv[i], bool) \
                        and node["class_type"] != "PrimitiveInt":
                    wv[i + 1] = "randomize"
        if nid in title:
            built["title"] = title[nid]
        nodes.append(built)
        by_id[nid] = built

    # The shared CLIP and VAE reach every stage through a Use Everywhere node
    # each, as in complete_workflow.json, instead of a wire to every encoder
    # and decoder: drawn, they were twenty wires crossing every stage.  The
    # node fills each unwired input of its type when the prompt is built.
    broadcast = {nid for nid in api if group_of[nid] == "models"
                 and api[nid]["class_type"] in BROADCAST}
    for n in nodes:
        for slot_i, slot in enumerate(n["inputs"]):
            wire = slot.pop("_wire", None)
            if isinstance(wire, list) and len(wire) == 2:
                if str(wire[0]) in broadcast:
                    continue
                src = by_id[str(wire[0])]
                link(src, int(wire[1]), n, slot_i,
                     src["outputs"][int(wire[1])]["type"])
    for nid in sorted(broadcast, key=int):
        typ = by_id[nid]["outputs"][0]["type"]
        # The shape of the node exactly as the editor serialises one it made
        # itself (frontend 1.47.12, Use Everywhere at 50ae9f8).  Written with
        # less, Use Everywhere throws on every frame drawn.
        ue = {"id": fresh_id(), "type": "Anything Everywhere", "pos": [0, 0],
              "size": [260, 60], "flags": {}, "order": 0, "mode": 0,
              "title": f"{typ} to every stage",
              "inputs": [{"label": typ, "localized_name": "anything",
                          "name": "anything", "shape": 7, "type": typ,
                          "link": None},
                         {"label": "anything", "name": "anything2", "type": "*",
                          "link": None}],
              "outputs": [],
              "properties": {"ue_properties": {
                  "version": "7.8", "group_restricted": 0, "color_restricted": 0,
                  "widget_ue_connectable": {}, "input_ue_unconnectable": {},
                  "title_regex": None, "input_regex": None, "group_regex": None,
                  "title_regex_invert": False, "input_regex_invert": False,
                  "group_regex_invert": False, "repeated_type_rule": 0,
                  "apply_to_unrepeated": 0, "string_to_combo": 0,
                  "send_to_any": 0, "next_input_index": 3},
                  "Node name for S&R": "Anything Everywhere"}}
        nodes.append(ue)
        group_of[str(ue["id"])] = "models"
        link(by_id[nid], 0, ue, 0, typ)

    # Relays.  Both are inverted: an active input mutes, all muted activates.
    # The first watches the stages that read the switch and drives the flag,
    # so the flag is active exactly while they are all off.  The second
    # watches the sources and the flag and drives the picker, so the picker
    # is active exactly while no source is on and its stage is on.
    def relay_pair(names, what, title_relay, title_repeater):
        relay = {"id": fresh_id(), "type": "Mute / Bypass Relay (rgthree)",
                 "pos": [0, 0], "size": [260, 60 + 22 * (len(names) + 1)],
                 "flags": {"collapsed": False}, "order": 0, "mode": 0,
                 "title": title_relay,
                 "inputs": [], "outputs": [{"name": "REPEATER", "dir": 4, "shape": 5,
                                            "type": "_NODE_REPEATER_", "links": [],
                                            "color_on": "#Fc0", "color_off": "#a80"}],
                 "properties": {"on_muted_inputs": "ACTIVE",
                                "on_bypassed_inputs": "ACTIVE",
                                "on_any_active_inputs": "MUTE"},
                 "widgets_values": None}
        for name in names:
            relay["inputs"].append({"dir": 3, "name": name, "type": "*", "link": None})
        relay["inputs"].append({"dir": 3, "name": "", "type": "*", "link": None})
        repeater = {"id": fresh_id(), "type": "Mute / Bypass Repeater (rgthree)",
                    "pos": [0, 0], "size": [260, 90], "flags": {}, "order": 0,
                    "mode": 0, "title": title_repeater,
                    "inputs": [{"dir": 3, "name": "Mute / Bypass Relay (rgthree)",
                                "type": "*", "link": None},
                               {"dir": 3, "name": what, "type": "*", "link": None},
                               {"dir": 3, "name": "", "type": "*", "link": None}],
                    "outputs": [], "properties": {}, "widgets_values": None}
        link(relay, 0, repeater, 0, "_NODE_REPEATER_")
        return relay, repeater

    handoff = {}                   # switch key -> its column, top to bottom
    for key, sw in spec["switches"].items():
        stage_relay, stage_repeater = relay_pair(
            [stage for stage, _ in owners[key]], "flag",
            sw["title"] + ": flag on while every stage reading it is off",
            sw["title"] + ": flag switch")
        for i, (_, nid) in enumerate(owners[key]):
            link(by_id[nid], 0, stage_relay, i, by_id[nid]["outputs"][0]["type"])
        flag = by_id[flag_id[key]]
        link(flag, 0, stage_repeater, 1, flag["outputs"][0]["type"])

        relay, repeater = relay_pair(
            sw["sources"] + ["stage off"], "picker",
            sw["title"] + ": picker off while a source is on or its stage is off",
            sw["title"] + ": picker switch")
        for i, src in enumerate(sw["sources"]):
            rid, slot = result[src]
            link(by_id[rid], slot, relay, i, by_id[rid]["outputs"][slot]["type"])
        link(flag, 0, relay, len(sw["sources"]), flag["outputs"][0]["type"])
        picker = by_id[picker_id[key]]
        link(picker, 0, repeater, 1, picker["outputs"][0]["type"])

        column = [by_id[switch_id[key]], relay, repeater,
                  stage_relay, stage_repeater, flag]
        nodes += [stage_relay, stage_repeater, relay, repeater]
        for n in column:
            group_of[str(n["id"])] = "handoff:" + key
        handoff[key] = column

    # The panels and the notes.  One panel per run of stage numbers, in stage
    # order, so the stack reads top to bottom like the stages: a number two
    # stages share gets a panel of its own set to "max one", where switching
    # one on switches the other off; the numbers between share plain panels.
    readme = note_node(fresh_id(), spec["readme"], [0, 0], [480, 820], markdown=True)
    nodes.append(readme)
    group_of[str(readme["id"])] = "inputs"
    for title, numbers, only_one in stage_panels(spec):
        muter = {"id": fresh_id(), "type": "Fast Groups Muter (rgthree)",
                 "pos": [0, 0], "size": [440, 40 + 30 * len(stage_rows(spec, numbers))],
                 "flags": {}, "order": 0, "mode": 0, "title": title,
                 "inputs": [], "outputs": [{"name": "OPT_CONNECTION", "type": "*",
                                            "links": None}],
                 "properties": {"matchColors": "",
                                "matchTitle": STAGE_TITLE.format("|".join(numbers)),
                                "showNav": True, "showAllGraphs": True,
                                "sort": "position", "customSortAlphabet": "",
                                "toggleRestriction": "max one" if only_one else "default"}}
        nodes.append(muter)
        group_of[str(muter["id"])] = "inputs"

    for s in spec["stages"]:
        src = (json.loads((API_DIR / f"{s['src']}.json").read_text())
               if "src" in s else spec["own_image"])
        text = api_to_ui.NOTES.get(s.get("src"))
        comment = src.get("_comment", "")
        if isinstance(comment, list):
            comment = " ".join(comment)
        if not text:
            text = "\n".join(textwrap.wrap(comment, 64))
        if "src" in s:
            text += f"\n\n(From workflows/api/{s['src']}.json.)"
        note = note_node(fresh_id(), text, [0, 0], [420, 120 + 17 * text.count("\n")])
        nodes.append(note)
        group_of[str(note["id"])] = s["key"]

    groups = layout(nodes, group_of, handoff,
                    [by_id[picker_id[key]] for key in spec["switches"]], spec)

    # Starting modes: only the stages marked "on".  A flag and a picker start
    # in the mode their relays would give them, so the file is consistent
    # before the relays first run.
    on = {s["key"] for s in spec["stages"] if s.get("on")}
    for n in nodes:
        g = group_of.get(str(n["id"]), "")
        if g in {s["key"] for s in spec["stages"]}:
            n["mode"] = ACTIVE if g in on else MUTE
    for key, sw in spec["switches"].items():
        live = any(k in on for k in sw["sources"])
        owned = any(stage in on for stage, _ in owners[key])
        by_id[flag_id[key]]["mode"] = MUTE if owned else ACTIVE
        by_id[picker_id[key]]["mode"] = ACTIVE if owned and not live else MUTE

    for i, n in enumerate(sorted(nodes, key=lambda n: (n["pos"][1], n["pos"][0]))):
        n["order"] = i

    return {
        "id": spec["name"],
        "revision": 0,
        "last_node_id": last_id,
        "last_link_id": next_link[0] - 1,
        "nodes": sorted(nodes, key=lambda n: n["id"]),
        "links": links,
        "groups": groups,
        "config": {},
        "extra": {"ds": {"scale": 0.55, "offset": [80, 80]}},
        "version": 0.4,
    }


def layout(nodes, group_of, handoff, pickers, spec):
    """Inputs and Models across the top, the Stage inputs row under them, then
    one row per stage: the hand-off column on the left, the stage group to its
    right, laid out by depth."""
    by_group = {}
    for n in nodes:
        by_group.setdefault(group_of.get(str(n["id"]), ""), []).append(n)
    ids = {n["id"]: n for n in nodes}
    link_src = {}
    for n in nodes:
        for i in n.get("inputs", []):
            if i.get("link") is not None:
                link_src.setdefault(n["id"], []).append(i["link"])
    # Which node each link comes from, for the depth pass.
    origin = {}
    for n in nodes:
        for o in n.get("outputs", []):
            for lid in o.get("links") or []:
                origin[lid] = n["id"]

    def place_by_depth(members, x0, y0):
        mids = {n["id"] for n in members}
        depth = {}

        def d(n, seen=()):
            if n["id"] in depth:
                return depth[n["id"]]
            best = 0
            for lid in link_src.get(n["id"], []):
                up = origin.get(lid)
                if up in mids and up not in seen:
                    best = max(best, d(ids[up], seen + (n["id"],)) + 1)
            depth[n["id"]] = best
            return best

        notes = [n for n in members if n["type"] in ("Note", "MarkdownNote")]
        rest = [n for n in members if n not in notes]
        x = x0
        bottom = y0
        for note in notes:
            note["pos"] = [x, y0]
            bottom = max(bottom, y0 + note["size"][1])
            x += note["size"][0] + GAP
        cols = {}
        for n in sorted(rest, key=lambda n: (d(n), n["id"])):
            cols.setdefault(d(n), []).append(n)
        right = x
        for c in sorted(cols):
            y = y0
            width = max(max(n["size"][0], 400) for n in cols[c])
            for n in cols[c]:
                n["pos"] = [x, y]
                n["size"][0] = max(n["size"][0], 400)
                y += height_of(n) + GAP
            bottom = max(bottom, y)
            x += width + (COL_W - 400)
            right = x
        return right, bottom

    groups = []

    def group(title, members, colour, x0, y0):
        right, bottom = place_by_depth(members, x0 + GAP, y0 + 60)
        groups.append({"id": len(groups) + 1, "title": title,
                       "bounding": [x0, y0, right - x0, bottom - y0 + GAP],
                       "color": colour, "font_size": 24, "flags": {}})
        return right, bottom + GAP

    # Top row: Inputs, then Models.
    inputs = by_group["inputs"]
    readme = [n for n in inputs if n["type"] == "MarkdownNote"]
    prompts = [n for n in inputs if n["type"] == "PrimitiveStringMultiline"]
    panel = sorted((n for n in inputs if n["type"].startswith("Fast Groups")),
                   key=lambda n: n["id"])
    x, y = 0, 0
    readme[0]["pos"] = [x + GAP, y + 60]
    px = x + GAP + readme[0]["size"][0] + GAP
    py = y + 60
    for p in prompts:
        p["size"] = [620, 300]
        p["pos"] = [px, py]
        py += 300 + GAP
    for n in [n for n in inputs if n["type"] == "PrimitiveInt"]:
        n["size"] = [620, 80]
        n["pos"] = [px, py]
        py += 80 + GAP
    panel_y = y + 60
    for n in panel:
        n["pos"] = [px + 620 + GAP, panel_y]
        panel_y += n["size"][1] + GAP // 2
    inputs_right = px + 620 + GAP + max(n["size"][0] for n in panel) + GAP
    inputs_bottom = max(y + 60 + readme[0]["size"][1], py, panel_y)
    groups.append({"id": 1, "title": "Inputs", "color": "#3f789e",
                   "bounding": [x, y, inputs_right - x, inputs_bottom - y + GAP],
                   "font_size": 24, "flags": {}})
    _, models_bottom = group(
        spec["models_title"],
        by_group["models"], "#444", inputs_right + GAP, y)

    # Second row: the pickers, one per switch, in stage order.  An image
    # picker is sized for its preview; a path box is one line.
    y = max(inputs_bottom + GAP, models_bottom) + GAP
    px = x + GAP
    for n in pickers:
        n["pos"] = [px, y + 60]
        n["size"] = [400, 420 if n["type"] == "LoadImageOutput" else 110]
        px += 400 + GAP
    groups.append({"id": len(groups) + 1,
                   "title": "Stage inputs: each is read when its stage is on and "
                            "no stage above it is on, and muted otherwise",
                   "color": "#3f789e",
                   "bounding": [x, y, px - x, 60 + 420 + GAP],
                   "font_size": 24, "flags": {}})
    y += 60 + 420 + GAP

    # One row per stage.  The hand-off column holds the switch and the relays
    # of every switch this stage is the first to read.
    y += 2 * GAP
    placed = set()
    for s in spec["stages"]:
        row_top = y
        handoff_bottom = row_top
        for key, sw in spec["switches"].items():
            owner = next(st["key"] for st in spec["stages"]
                         if key in st.get("feed", {}).values())
            if owner != s["key"] or key in placed:
                continue
            placed.add(key)
            hy = row_top + 60
            for n in handoff[key]:
                n["pos"] = [HANDOFF_X + GAP, hy]
                n["size"][0] = max(n["size"][0], 400)
                hy += height_of(n) + GAP
            handoff_bottom = max(handoff_bottom, hy)
        colour = "#8A8" if s.get("on") else "#3f789e"
        _, bottom = group(s["title"], by_group[s["key"]], colour, STAGE_X, row_top)
        y = max(bottom, handoff_bottom) + 2 * GAP
    return groups


# ------------------------------------------------------------------- check
def check(text, api, info, broadcast):
    """Put the file's values back on their names and compare with `api`, the
    joined graph as the server should receive it with every stage on.

    An input fed by a broadcast loader has no link in the file, by design, so
    for those the check asks only that the input is there and left unwired
    for Use Everywhere to fill.  That it does fill them is checked in the
    browser, not here."""
    ui = json.loads(text)
    real = {"nodes": [n for n in ui["nodes"]
                      if n["type"] not in VIRTUAL and n["type"] != SWITCH],
            "links": ui["links"]}
    got = api_to_ui.back_to_api(real, info)
    link_src = {l[0]: (str(l[1]), l[2]) for l in ui["links"]}
    for n in ui["nodes"]:
        if n["type"] == SWITCH:
            got[str(n["id"])] = {"class_type": SWITCH, "inputs": {
                i["name"]: list(link_src[i["link"]]) for i in n["inputs"]
                if i.get("link") is not None}}
    bad = []
    for nid, node in api.items():
        mine = got.get(nid)
        if mine is None:
            bad.append(f"node {nid} ({node['class_type']}) is missing")
            continue
        if mine["class_type"] != node["class_type"]:
            bad.append(f"node {nid} became {mine['class_type']}")
            continue
        slots = {i["name"]: i for n in ui["nodes"] if str(n["id"]) == nid
                 for i in n.get("inputs", [])}
        for iname, val in node["inputs"].items():
            back = mine["inputs"].get(iname, "<absent>")
            if isinstance(val, list) and len(val) == 2:
                val = [str(val[0]), val[1]]
                if val[0] in broadcast and back == "<absent>" \
                        and iname in slots and slots[iname].get("link") is None:
                    continue
            if isinstance(back, list) and len(back) == 2:
                back = [str(back[0]), back[1]]
            if back != val:
                bad.append(f"node {nid} ({node['class_type']}) .{iname}: "
                           f"{val!r} came back as {back!r}")
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="write the graphs, then compare each value by value "
                         "with the base graphs it was built from")
    ap.add_argument("--dry-run", action="store_true",
                    help="build and compare in memory, and write nothing")
    ap.add_argument("--graph", choices=list(GRAPHS), action="append",
                    help="build only this graph; repeatable (default: all)")
    args = ap.parse_args()

    info = api_to_ui.object_info()
    bad = []
    for name in args.graph or GRAPHS:
        spec = {**GRAPHS[name], "name": name}
        api, group_of, title, wiring = build(info, spec)
        ui = to_ui(api, group_of, title, wiring, info, spec)
        text = json.dumps(ui, indent=1)

        out = api_to_ui.UI_DIR / f"{name}.json"
        if not args.dry_run:
            if out.is_file() and out.read_text() == text:
                print(f"{out}: already up to date")
            else:
                out.write_text(text)
                print(f"{out}: written")
        print(f"{name}: {len(ui['nodes'])} nodes, {len(ui['links'])} links, "
              f"{len(ui['groups'])} groups, {len(spec['stages'])} stages")
        if args.check or args.dry_run:
            broadcast = {nid for nid in api if group_of[nid] == "models"
                         and api[nid]["class_type"] in BROADCAST}
            mine = check(text, api, info, broadcast)
            if mine:
                bad += [f"{name}: {b}" for b in mine]
            else:
                print(f"{name}: round trip OK: every value is back on its name")
    if bad:
        sys.exit("MISMATCH\n  " + "\n  ".join(bad))


if __name__ == "__main__":
    main()

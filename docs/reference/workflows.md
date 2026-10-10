# Workflows

Graphs live in `workflows/api/` in the format the server accepts. They are also
converted into the editor's own format so they appear in the ComfyUI sidebar.

Every graph here is checked against a live server:

```sh
scripts/validate_workflows.py
```

## Presets: drop in and queue

These carry the settled decisions already applied. Open one in the sidebar,
replace the subject line, queue it. No flags, no arguments, nothing to remember.

| Preset | Makes | Canvas |
|---|---|---|
| `preset_concept_character.json` | Character concept art | 1104x1472 portrait |
| `preset_concept_creature.json` | Creature concept art | 1104x1472 portrait |
| `preset_concept_building.json` | Isometric building diorama | 1472x1104 landscape |
| `preset_concept_prop.json` | Small scenery prop | 1104x1104 square |
| `preset_concept_icon.json` | UI icon on a flat background | 1024x1024 square |
| `preset_ground_texture.json` | Overhead ground texture | 1024x1024 square |
| `preset_simplify_concept.json` | Simplified version of existing art | matches input |
| `preset_sprites_iso_8.json` | 8 facings, isometric camera | 512 per frame |
| `preset_sprites_topdown_8.json` | 8 facings, overhead camera | 512 per frame |

Each one has a `_comment` at the top saying what is baked in and why.

::: warning Presets are generated files
They are built from the base graphs and the prompt library:

```sh
scripts/build_presets.py            # rewrite them
scripts/build_presets.py --check    # fail if any is out of date
```

Edit the base graph or the prompt files, then rebuild. Editing a preset by hand
means it is silently reverted next time anyone runs the builder.
:::

## Base graphs

| File | Does |
|---|---|
| `txt2img_qwen_fast.json` | Prompt to concept image, 4 steps, about 30s. Guidance 1.0, so no negative prompt |
| `txt2img_qwen.json` | Same at 20 steps, about 130s. Negative prompt honoured |
| `txt2img_sdxl.json` | The older SDXL path. Weaker prompt adherence, photographic look |
| `txt2img_krea2.json` | Prompt to concept image with Krea 2 Turbo, 8 steps, guidance 1.0, so no negative prompt. 864x1152 in 22.3 s on the 16 GB card, one image at a time: 1104x1472, or two at once, ran out of memory. Free for commercial use only under 1 million dollars of company revenue a year, outputs included: see [licensing](/guide/licensing#krea-2). Needs the `krea2` weight group |
| `txt2img_krea2_style.json` | The same, painted in the style of a reference image through ostris's style reference LoRA. A style match, not an edit. Ran out of memory on the 16 GB card at 864x1152 and 672x896. Same licence. Needs the `krea2` weight group |
| `img_edit_qwen.json` | Change part of an existing image |
| `img_refine_sdxl.json` | Refine pass over an image |
| `img2mesh_hunyuan3d21.json` | Image to mesh, shape only. Best geometry. Removes the background itself. Territory limited licence |
| `img2mesh_trellis.json` | Image to mesh, TRELLIS. MIT, no territory clause. Removes the background itself. Needs the `trellis` weight group. [Details](/guide/trellis) |
| `img2mesh_triposg.json` | Image to mesh, TripoSG. Does not currently produce usable meshes in this install: a cage of fragments, whatever the input. Licence caveat in the licensing guide |
| `img2mesh_triposr.json` | Image to mesh, TripoSR. Does not work as wired, going by the node source: the mask from `LoadImage` is inverted. Would need an `InvertMask` and a cut-out |
| `mesh_texture_hunyuan3d21.json` | Paint texture maps onto an existing mesh. Territory limited licence, which covers the painted mesh too |
| `txt2mesh_qwen_hunyuan3d21.json` | Prompt to concept to mesh in one queue. Territory limited licence |
| `txt2mesh_sdxl_hunyuan3d21.json` | The same, the older way |
| `mesh_render_sprites.json` | Mesh to 8 facings, unlit. Silhouette check |
| `mesh_rig_unirig.json` | Mesh to skeleton and skin, out as FBX |
| `rig_apply_animation.json` | Rigged FBX plus a clip, out as animated FBX |
| `img2video_wan22.json` | Image to five seconds of video with Wan 2.2, 14B, two fp8 experts, at 480x640 and 20 steps, the settings that ran on the 16 GB reference card on 2026-10-02 in 604.7 s. The 4-step LoRAs sit in the graph at strength 0, because at strength 1 that card ran out of memory. Apache-2.0. Needs the `wan_i2v` weight group. Makes a video, not a clip for a rig: see [Video to 3D motion](/reference/video-mocap) |
| `txt2music_acestep15.json` | Caption to an instrumental music track with ACE-Step 1.5 turbo, saved as FLAC. MIT, and the model card allows commercial use of the music. Needs the `music` weight group. [Details](/guide/music) |

## Running one

```sh
scripts/run_workflow.py workflows/api/txt2img_qwen.json \
    --prompt 'a mossy stone golem' --negative 'cartoon, blurry'

scripts/run_workflow.py workflows/api/img2mesh_trellis.json \
    --image output/concept/golem_00001_.png --set target=12000

scripts/run_workflow.py --list-nodes Comfy3D    # what the server actually loaded
```

`--set` takes `widget=value` for any node with that input, or
`NodeTitle.widget=value` for one specific node. Values parse as JSON when they
can, so `steps=20` is a number and `prompt=20 golems` is a string.

Use `--prompt` and `--negative` rather than `--set text=...`. The `text` input
exists on both the positive and negative nodes, and a bare `--set` is refused for
that reason.

When the job ends, `run_workflow.py` lists the files it wrote, as paths under
`output/`. Most come from the server's `/history`, which names a file only when
the node that wrote it hands the file back to the interface. Some nodes do not:
Comfy3D's Save 3D Mesh passes its path on as a string, so a mesh graph's history
has no outputs at all, and UniRig's Auto Rig and Apply Animation and the
Hunyuan3D 2.1 texture stage, with its scratch files in `output/Hun2-1/`, write
files that history never names. For those, `run_workflow.py` works each file's
name out from the node's own inputs, then lists the matching files written while
the job ran, each with its size, so a file another job or a host script wrote
meanwhile is not taken for this job's. An output node it does not know that names
nothing in history is listed by id and class instead. Automation that polls
`/history` itself sees no outputs for a mesh graph: read the `save_path` you set.

## The rigging graph reads from disk

`mesh_rig_unirig.json` does not take a wired mesh. Its loader picks from files
already on disk, so run an image to mesh graph first and pass the result:

```sh
scripts/run_workflow.py workflows/api/mesh_rig_unirig.json \
    --set 'file_path=mesh/golem.glb'
```

`source_folder` is `output`, and `file_path` is relative to it.

## Editing graphs in the ComfyUI editor

The API format is a flat dictionary of nodes, which the web editor cannot open.
The converter writes editor versions into `workflows/default/workflows/`:

```sh
scripts/api_to_ui.py --check      # all of them, verified
scripts/api_to_ui.py txt2img_qwen # or one
```

Where they appear depends on the compose profile:

- **`comfy` and `comfy-local` (built from source).** The shared service block
  mounts `./workflows:/app/user` (`docker-compose.yml:32`), so a regenerated
  graph shows up in the sidebar under **Workflows**.
- **`packaged` (the published image).** It deliberately mounts no workflows
  (`docker-compose.yml:79-81`) and gives `/app/user` the named volume
  `comfy-user` instead (`:105-109`). The image already carries the editor
  graphs: the Dockerfile copies `workflows/default/workflows` into
  `/app/user/default/workflows`, and `scripts/entrypoint.sh` copies in any
  graph whose file name is not already in the volume. It skips a name that is
  already there, so a graph you regenerate on the host reaches neither the
  running server nor a recreated container. Open a regenerated file in that
  editor by hand, or use the `comfy` profile.

::: danger Widget order is the core challenge
Node values are stored as a **positional array** in the editor format, and the
position depends on the order the node declares its inputs, which is only
knowable from a running server.

Two things shift that array and load a graph that looks perfectly fine while
running with the steps value in the guidance box:

- an input that is **wired** is a slot, not a widget, and takes no place in the
  array
- an integer the editor gives a randomise dropdown is followed by an extra value
  the backend never sees. That is one flagged to change after each generation,
  and also, in frontend 1.47.12, any integer named `seed` or `noise_seed` that
  is not flagged off, whether the node asks for the dropdown or not

`--check` reads each converted graph back the way the converter believes ComfyUI
reads it, and compares every value against the original. It caught the rigging
nodes declaring their dropdowns with a newer type, which had silently dropped
five widgets across two workflows. It cannot catch a belief that is wrong, since
it shares it: until 2026-09-30 the converter added the extra value only when a
node set the flag, which 3D-Pack's TRELLIS, Hunyuan3D and TripoSG nodes do not.
Opened in the editor, those five graphs sent every value after the seed one
place early, such as Hunyuan3D ShapeGen with 7.5 steps and guidance 256. Graphs
run by `run_workflow.py` use the API file and were never affected. The check
that found it loaded every converted graph in the editor and compared the
prompt it would send with the API original; all 25 now match.
:::

Converted graphs are generated. Edit the API JSON and re-run the converter,
unless you are crafting in the editor, in which case save from ComfyUI and it
lands in the same folder.

## Three graphs made for the editor

Three graphs in `workflows/default/workflows/` have no API version, because they
are built for the editor and lean on node packs that do their work in the
browser: rgthree's stage panels, relays and switches, and Use Everywhere.

- `asset_workflow.json` joins the base graphs above into one pipeline, from a
  prompt to a rig and a video, with panels that switch stages on and off, one
  at a time for alternatives, a row of pickers at the top, one per stage, for
  picking a run up at any stage, and a pause after each image stage to choose
  which of its takes carries on.
  `scripts/build_asset_workflow.py` builds it from the base graphs, so edit
  those, not it.
- `krea_workflow.json` is the image and video half of that pipeline, as
  `complete_workflow.json` is, with Krea 2 Turbo painting the concept, plain or
  from a style reference, then Qwen-Image-Edit 2509 and Wan 2.2: Krea has no
  open edit or image-to-video model. The same builder makes it, with the same
  panels, pickers and pauses. Krea 2's licence is free for commercial use only
  under 1 million dollars of company revenue a year.
- `complete_workflow.json` is the owner's image and video graph on the Rapid AIO
  merge and Wan 2.2, and the one editor graph that is built by hand. Its weights
  are the `qwen_rapid` and `wan_i2v` groups. Some of those weights, and its Pose
  Transfer flow, are not cleared for commercial use.

[The whole pipeline in one graph](/guide/asset-workflow) covers all three.

## Export format

`Save 3D Mesh` picks the format from the extension on `save_path`. The supported
set is `.glb`, `.obj` and `.ply`, and an unrecognised extension is refused rather
than guessed at. See [meshes](/guide/meshes#file-formats) for which to use.

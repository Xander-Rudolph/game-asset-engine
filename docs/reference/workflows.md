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
| `img_edit_qwen.json` | Change part of an existing image |
| `img_refine_sdxl.json` | Refine pass over an image |
| `img2mesh_hunyuan3d21.json` | Image to mesh, shape only. Best geometry. Removes the background itself. Territory limited licence |
| `img2mesh_triposg.json` | Image to mesh, TripoSG. Clean watertight shapes. Licence caveat in the licensing guide |
| `img2mesh_triposr.json` | Image to mesh, fastest. Needs a cut out with transparency |
| `mesh_texture_hunyuan3d21.json` | Paint texture maps onto an existing mesh |
| `txt2mesh_qwen_hunyuan3d21.json` | Prompt to concept to mesh in one queue |
| `txt2mesh_sdxl_hunyuan3d21.json` | The same, the older way |
| `mesh_render_sprites.json` | Mesh to 8 facings, unlit. Silhouette check |
| `mesh_rig_unirig.json` | Mesh to skeleton and skin, out as FBX |
| `rig_apply_animation.json` | Rigged FBX plus a clip, out as animated FBX |

## Running one

```sh
scripts/run_workflow.py workflows/api/txt2img_qwen.json \
    --prompt 'a mossy stone golem' --negative 'cartoon, blurry'

scripts/run_workflow.py workflows/api/img2mesh_triposg.json \
    --image output/concept/golem_00001_.png --set target=12000

scripts/run_workflow.py --list-nodes Comfy3D    # what the server actually loaded
```

`--set` takes `widget=value` for any node with that input, or
`NodeTitle.widget=value` for one specific node. Values parse as JSON when they
can, so `steps=20` is a number and `prompt=20 golems` is a string.

Use `--prompt` and `--negative` rather than `--set text=...`. The `text` input
exists on both the positive and negative nodes, and a bare `--set` is refused for
that reason.

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
The converter writes editor versions into the folder ComfyUI reads:

```sh
scripts/api_to_ui.py --check      # all of them, verified
scripts/api_to_ui.py txt2img_qwen # or one
```

They then appear in the sidebar under **Workflows**, because the compose file
mounts `workflows/` as ComfyUI's user directory.

::: danger The widget order is the whole difficulty
Node values are stored as a **positional array** in the editor format, and the
position depends on the order the node declares its inputs, which is only
knowable from a running server.

Two things shift that array and load a graph that looks perfectly fine while
running with the steps value in the guidance box:

- an input that is **wired** is a slot, not a widget, and takes no place in the
  array
- an integer flagged to change after each generation, which every seed is, is
  followed by an extra value the backend never sees

`--check` reads each converted graph back the way ComfyUI reads it and compares
every value against the original. It is not decoration. It caught the rigging
nodes declaring their dropdowns with a newer type, which had silently dropped
five widgets across two workflows.
:::

Converted graphs are generated. Edit the API JSON and re-run the converter,
unless you are crafting in the editor, in which case save from ComfyUI and it
lands in the same folder.

## Export format

`Save 3D Mesh` picks the format from the extension on `save_path`. The supported
set is `.glb`, `.obj` and `.ply`, and an unrecognised extension is refused rather
than guessed at. See [meshes](/guide/meshes#file-formats) for which to use.

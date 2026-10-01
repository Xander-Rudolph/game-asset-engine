# The whole pipeline in one graph

::: tip Status: built, checked in the editor, and run on 2026-09-30
`asset_workflow.json` was opened in ComfyUI's editor (frontend 1.47.12) in the
packaged container, built from this repo's Dockerfile with the node packs
below. Its stage panel, relays and switches were driven there, and the prompt the
editor would send was captured with the submit call stubbed out, for fourteen
combinations of stages, then checked against the server's node definitions. Four
runs were then queued from the editor on the reference machine: Concept, fast;
Edit, twice, from its picker; TRELLIS and Turntable from a picked edit; and
Concept, Edit and TRELLIS as one queue. All four finished; the figures are under
[Measured runs](#measured-runs). Concept, full, Simplify, the Hunyuan3D mesh and
Texture have not been queued from this graph. `complete_workflow.json` was built
by the owner, and the prompt for each of its seven flows was captured and checked
the same way; it has not been run here.
:::

Two graphs are made for the editor rather than for `run_workflow.py`, and both
open from the sidebar under **Workflows**:

- **`asset_workflow.json`** is the pipeline in one graph: a prompt at the top,
  a panel that switches stages on and off, and every stage from concept to
  turntable, wired so that each one hands over to the next.
- **`complete_workflow.json`** is the owner's image and video graph on Phr00t's
  Qwen-Image-Edit Rapid AIO merge and Wan 2.2, one flow at a time off a shared
  image and prompt.

## asset_workflow.json

### Using it

1. Write the subject in **Prompt**. It feeds both Concept stages.
2. Switch stages on in the **Stages** panel. Only Stage 1, fast, is on when the
   graph opens. The arrow on each row jumps to that stage.
3. Queue.

With Concept, Edit and Mesh all on, one queue goes from the prompt to a saved
mesh.

### The stages

Each stage is a copy of a base graph in `workflows/api/`, so what its page says
holds here too.

| Stage | Built from | Saves |
|---|---|---|
| 1. Concept, fast | `txt2img_qwen_fast.json` | `output/asset_concept_fast_NNNNN_.png` |
| 1. Concept, full | `txt2img_qwen.json` | `output/asset_concept_NNNNN_.png` |
| 2. Edit | `img_edit_qwen.json`, instruction from **Edit instruction** | `output/asset_edit_NNNNN_.png` |
| 3. Simplify | `preset_simplify_concept.json` | `output/asset_simplify_NNNNN_.png` |
| 4. Mesh, TRELLIS | `img2mesh_trellis.json` | `output/mesh/TRELLIS_<date>.glb` |
| 4. Mesh, Hunyuan3D 2.1 | `img2mesh_hunyuan3d21.json` | `output/mesh/Hunyuan21_<date>.glb` |
| 5. Texture | `mesh_texture_hunyuan3d21.json` | `output/mesh/textured_<date>.glb` |
| 6. Turntable | `mesh_render_sprites.json` | `output/sprites/asset_NNNNN_.png` |

Rigging is not a stage. UniRig reads a saved file from a list, so it cannot be
wired onto the end of a graph; use `mesh_rig_unirig.json` on the saved mesh, as
[Rigging](/guide/rigging) describes.

### How a stage finds its input

Each stage takes its input from the **nearest stage above it that is on**. Edit
reads a Concept stage, Simplify reads Edit, or a Concept stage if Edit is off,
and so on down. Texture reads the mesh the Mesh stage saved and the same image
the Mesh stage used, and Turntable reads Texture's mesh, or a Mesh stage's.

A stage with no stage above it switched on reads its own **picker** instead, in
the column to the left of its group:

- An image stage's picker is **Load Image (from Outputs)**. It lists the top of
  `output/`, newest first, and its refresh arrow selects the newest file. You can
  also pick any earlier one, or upload an image of your own into it.
- A mesh stage's picker is a path box holding a container path, such as
  `/app/output/mesh/asset.glb`.

That is why the image stages save to the top of `output/` rather than into a
subfolder. The server lists that folder with `os.scandir`, which does not look
into subfolders, and sorts it by modification time, newest first. That was read
in the server code of this image, not run.

The choosing is done by rgthree's **Any Switch**, which passes on the first of its
inputs that is present. A muted stage sends nothing, so the switch falls through
to the next stage up, and last to the picker. A picker must not be checked while a
live stage feeds its switch, or an empty picker would stop the whole queue, so an
rgthree relay mutes the picker whenever any stage above it is on. It is the same
device `complete_workflow.json` uses for its input image.

### Running one step as often as you like

Switch on only the stage you want. With nothing above it on, it reads its picker:
pick the image to work from, and queue as many times as it takes. Every seed here
is set to randomise, so each queue is a new take. When one is right, switch that
stage off and the next one on. The next stage's picker refresh arrow selects the
newest file, which is the take you just made, or you can pick an earlier one.

To edit an edit, pick the last edit in Edit's own picker and queue again.

### Models

A loader only one stage uses sits inside that stage, so switching the stage off
takes its loader with it. The loaders two or more stages share sit in **Models**,
which is never muted, and a loader there runs only when a stage that is on needs
it: the Qwen text encoder, the Qwen VAE, and the Qwen-Image-Edit 2509 model that
Edit and Simplify both use. The encoder and VAE reach each stage through a
**Use Everywhere** node each, so their wires are not drawn; that node fills every
unwired input of its type when the prompt is sent.

### Memory

On the reference machine's 16 GB card and 31 GB of RAM:

- Each Qwen stage loads a diffusion model of about 20 GB, and a queue that runs
  two Qwen stages loads two of them. Concept, fast, Edit and TRELLIS as one queue
  finished without an out-of-memory kill; the figures are under
  [Measured runs](#measured-runs). Concept, full, with Edit has not been run.
- Mesh and Texture in one queue run out of VRAM, because 3D-Pack keeps its
  pipelines outside ComfyUI's model management. That is what the texture graph's
  own note says; it was not re-measured for this graph. Run Mesh, restart
  ComfyUI, then run Texture with Mesh off.

### Licences

Each stage carries its base graph's licence. The two Hunyuan3D stages are under a
licence that excludes the EU, the UK and South Korea; TRELLIS is MIT. See
[Licensing](/guide/licensing). This graph uses no pose preprocessor.

### Rebuilding it

The graph is built, never hand-edited, by `scripts/build_asset_workflow.py`, from
the base graphs in `workflows/api/`. Rebuild the presets first, because Simplify
is read from one:

```sh
scripts/build_presets.py
scripts/build_asset_workflow.py --check
```

It needs a running server, because the order of every node's values in the
editor's format is only knowable from `/object_info`, as for
`scripts/api_to_ui.py`. `--check` puts every value back on its name and compares
the graph with the base graphs. It cannot see the relays, which run in the
browser. The packaged service keeps its own copies of the editor graphs and only
adds a file name it lacks, so open a rebuilt graph there by hand, as
[Workflows](/reference/workflows#editing-graphs-in-the-comfyui-editor) explains.

### What was checked, and how

All on 2026-09-30, in the packaged container on this branch's image, on the copy
of the graph the entrypoint seeded into the `comfy-user` volume, through
Playwright driving the editor. None of it generated anything.

- The graph loads with its 86 nodes and 102 links. The Stages panel lists the
  eight stage groups and not Inputs or Models, and each group holds exactly its
  own nodes.
- Fourteen combinations of stages were switched through the panel's own toggles:
  each stage alone, and six chains from Concept, Edit and TRELLIS to every stage
  on at once. With the editor's submit call replaced by a stub, the prompt it
  would send was captured each time. In every one, each of the five pickers was
  muted exactly when a stage above it was on, and each switch's first input was
  the nearest stage above that was on, or its picker. Use Everywhere filled every
  CLIP and VAE input of every node sent, reached no other input, and left no drawn
  wire behind. The server's queue stayed empty throughout.
- All fourteen prompts passed `scripts/validate_workflows.py`'s checks against
  the live server. The one complaint is an extra `refresh` value the editor adds
  to **Load Image (from Outputs)**, which the server ignores: its input gathering
  keeps only the inputs a node declares. That was read in `execution.py`, and the
  queued runs below confirm it.

### Measured runs

Queued from the editor on 2026-09-30, on the reference machine, in the packaged
container, one after another, each on the default golem prompt. Seconds are
ComfyUI's own, from `execution_start` to `execution_success` in `/history`.
Memory was sampled every 2 seconds: the container's figure is `docker stats`
MemUsage, the host's is `free`'s available column, and VRAM is `nvidia-smi`.

| Run | Stages on | Input | Seconds | Saved |
|---|---|---|---|---|
| A | 1. Concept, fast | the prompt | 22.1 | `asset_concept_fast_00001_.png`, 1104x1472 |
| B | 2. Edit, queued twice | its picker, after refresh | 147.8, 171.6 | `asset_edit_00001_.png` and `_00002_`, 880x1184 |
| C | 4. TRELLIS, 6. Turntable | Mesh's picker, set to the first edit | 22.2 | a 48,000-face mesh, then 8 frames and 8 masks from it |
| D | 1. Concept, fast, 2. Edit, 4. TRELLIS | the prompt | 204.6 | a concept, an edit and a 48,000-face mesh |

- **The hand-over worked both ways.** In B, Edit's refresh arrow selected the
  concept A had just made, the newest file, and the two queues ran on different
  seeds and made different takes. In C, Mesh's refresh arrow selected the second
  take, the newest, and picking the first from the list worked; Turntable then
  rendered the mesh TRELLIS had just saved, through its path switch. In D, each
  stage read the one above, with every picker muted.
- **Memory.** Across A and B, the container peaked at 26.4 GiB, the host never fell
  below 13.9 GiB available, and VRAM peaked at 15,731 MiB. Across D, with two Qwen
  diffusion models in one queue, the container peaked at 22.0 GiB, the host never
  fell below 12.2 GiB available, VRAM peaked at 15,718 MiB, and Docker reported no
  out-of-memory kill and no restart. `docker stats` counts some page cache, which
  is likely why its peak sits above what the host's available figure implies.
- **The edit is the model's, not the graph's.** Asked to put a pauldron on "the
  golem's left shoulder", the first take in B did and the second put a larger one
  on the right; D's also went right. Running a step again and picking the take is
  what the pickers are for.
- **The first queue of C found a bug the editor checks had not.** TRELLIS arrived
  with its settings one place out, and ComfyUI refused a structured-latent step
  count of 0. The editor adds a randomise dropdown after any integer named `seed`,
  and the converter had added the matching value only when a node asked for one.
  It is fixed in `scripts/api_to_ui.py`, which this graph's builder shares, and
  [Workflows](/reference/workflows#editing-graphs-in-the-comfyui-editor) records
  the five older editor graphs it had also broken.

## complete_workflow.json

The owner's graph, and the one editor graph here that is not generated. Edit it
in the editor.

It runs one flow at a time off a shared **Input Image**, a **Secondary Image** and
one **Prompt**: basic editing, clothes swap, pose transfer, image to real, Wan 2.2
image to video to a final frame, text to image, and editing with a LoRA. Its
**Switch Mode** panel keeps exactly one flow on. **Switch Quants** chooses between
the Rapid AIO checkpoint, which holds its own text encoder and VAE, and a GGUF
quant of it with the separate Qwen encoder and VAE.

### What it needs

Four node packs are in the image, pinned in the Dockerfile: rgthree-comfy, Use
Everywhere, ComfyUI-GGUF and Comfyui-QwenEditUtils. The fifth,
comfyui_controlnet_aux, which Pose Transfer needs, is not, because its pose code's
licence forbids distributing it. The container fetches it from GitHub, at the
commit the Dockerfile pins, when it starts; `ASSET_ENGINE_CONTROLNET_AUX=0` skips
that. The weights are not in the image either, and come from three groups:

```sh
scripts/fetch_models.py --download --group qwen --group qwen_rapid --group wan_i2v
```

That is about 40GB for `qwen_rapid` and 35GB for `wan_i2v`, in the fetcher's
units, on top of the `qwen` group's encoder and VAE, which the quant route needs.
The Anything2Real LoRA that Image to Real loads is refused unless you add
`--accept-noncommercial`; see below.

The graph also names two Wan 2.2 LoRAs, `wan2.2anime to realv2 high` and `low`,
off by default. They match Civitai model 2417550, "anime to real" by qiaoy123,
whose v2.0 for Wan 2.2 I2V-A14B ships as `wan2.2anime to realv2.zip`. On
2026-09-30 its Civitai permissions allowed commercial use including selling, and
derivatives, with no credit required; those are the uploader's settings, and no
licence file was found. Nothing here fetches it: Civitai refuses an anonymous
download (HTTP 401), and `fetch_models.py` cannot unpack a zip. Download it while
signed in and put the two files in `models/loras/`.

### Licences

Read [Licensing](/guide/licensing) before shipping anything this graph makes. In
short:

- The Rapid AIO merge and its GGUF quant are unsettled: the merge's card declares
  Apache-2.0 but folds in community LoRAs it does not license, and the quant
  declares nothing.
- Anything2Real is treated as non-commercial. The author's Civitai page for the
  same file allows no commercial use and no derivatives.
- **Pose Transfer is non-commercial.** It runs DWPose through
  comfyui_controlnet_aux, whose pose code carries CMU's OpenPose licence:
  noncommercial research use only.
- Wan 2.2, its encoder, VAE and the 4-step LoRAs are Apache-2.0.

### Checked, and not yet run here

Each of its seven flows was switched on through **Switch Mode** in the editor, on
2026-09-30, and the prompt it would send was captured with the submit call
stubbed. Every core node in all seven passed `scripts/validate_workflows.py`
against the live server. Its only complaints were inputs the editor adds that
the server's node definitions do not list: rgthree's LoRA loader declares its
optional inputs with a type that accepts any name, the image comparer's extra
value is ignored as `refresh` is above, and a Use Everywhere node has no outputs,
so the server never runs it. Those three readings are from the node source, not
a run. Nothing was queued.

- The Rapid AIO checkpoint is one 26.5GB file, in the fetcher's units, loaded
  whole by **Load Checkpoint**. Whether it fits beside everything else in 31 GB
  of RAM, with the compose file's `--disable-pinned-memory --cache-none`, is not
  measured. The GGUF route is the smaller one.
- The Wan 2.2 flow loads two 14B experts, 13.3GB each in fp8, plus a 6.3GB text
  encoder. Not measured here.

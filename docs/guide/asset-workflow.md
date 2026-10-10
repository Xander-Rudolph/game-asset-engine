# The whole pipeline in one graph

::: tip Status: built, checked in the editor, and run on 2026-09-30, 2026-10-02 and 2026-10-03
`asset_workflow.json` was opened in ComfyUI's editor (frontend 1.47.12) in the
packaged container, built from this repo's Dockerfile with the node packs
below. On 2026-10-02 its stage panel, relays and switches were driven there for
twenty combinations of stages, and the prompt the editor would send was captured
with the submit call stubbed out, then checked against the server's node
definitions; on 2026-10-03, after the picks were added, six combinations were
captured and checked again. Eight runs have been queued on the reference
machine: on 2026-09-30, Concept, fast; Edit, twice, from its picker; TRELLIS and
Turntable from a picked edit; and Concept, Edit and TRELLIS as one queue; on
2026-10-02, Rig on a saved TRELLIS mesh, and Animate, which ran once given the
owner's 20-step route without the 4-step LoRAs, at 480x640, after four
out-of-memory failures with the LoRAs on; on 2026-10-03, Concept, fast, and Edit
as one queue with two takes each, pausing for the pick, and Your image straight
to TRELLIS. The figures are under
[Measured runs](#measured-runs). Concept, full, Simplify, the Hunyuan3D mesh and
Texture have not been queued from this graph. `complete_workflow.json` was built
by the owner, and the prompt for each of its seven flows was captured and checked
the same way; it has not been run here.
:::

Three graphs are made for the editor rather than for `run_workflow.py`, and all
three open from the sidebar under **Workflows**:

- **`asset_workflow.json`** is the pipeline in one graph: the prompts at the
  top, panels that switch stages on and off, one at a time for alternatives, a
  row of pickers for picking a run up at any stage, and every stage from
  concept to a rig and a video, wired so that each one hands over to the next.
- **`krea_workflow.json`** is the image and video half of that pipeline with
  Krea 2 Turbo painting the concept, plain or from a style reference, then
  Qwen-Image-Edit 2509 and Wan 2.2. Same panels, pickers and pauses. Krea 2's
  licence is free for commercial use only under 1 million dollars of company
  revenue a year: see [below](#krea-workflow-json).
- **`complete_workflow.json`** is the owner's image and video graph on Phr00t's
  Qwen-Image-Edit Rapid AIO merge and Wan 2.2, one flow at a time off a shared
  image and prompt.

## asset_workflow.json

### Using it

1. Write the subject in **Prompt**. It feeds both Concept stages. **Edit
   instruction** feeds Stage 2 and **Motion prompt** Stage 8. **Takes** is how
   many images each of Stages 1 to 3 makes per queue; two when the graph opens.
   Already have concept art? Switch on **0. Your image** instead, upload the file
   there or pick one already in `input/`, and leave the Concept stages off.
2. Switch stages on in the **Stage** panels, which list the stages in order.
   Only Stage 1, fast, is on when the graph opens. Stages that share a number
   are alternatives, and their panel lets one at a time be on: switching on
   Hunyuan3D switches TRELLIS off, so one queue never loads both mesh models.
   The arrow on each row jumps to that stage.
3. To start anywhere but Concept, pick that stage's input in the **Stage
   inputs** row under the prompts. There is one picker per stage, in stage
   order, and the pickers lit up are exactly the ones the next queue reads.
4. Queue. When an image stage has a stage below it on, the queue pauses after
   it and shows the takes: click the one to carry on with, then **Send**.

With Concept, Edit and Mesh all on, one queue goes from the prompt to a saved
mesh, pausing twice for you to choose. With every stage on one path on, it goes
on to a rigged FBX and a video.

::: warning Open it in a fresh tab, not over another graph with relays in it
rgthree's relays poll their inputs every 500 ms and never stop, even after the
graph they belong to has been replaced in the tab, and they act through link
ids, which a newly loaded graph numbers afresh. On 2026-10-02, with an older
copy of this graph loaded first into the same tab, its relays went on running
and muted a switch of the new graph, which then vanished from the prompt; on
2026-10-03 the same thing muted the CLIP broadcaster, and every text encoder
was sent without a CLIP. Read in `node_mode_relay.js` at the commit the
Dockerfile pins: `stabilize()` reschedules itself and never checks that its node
is still in a graph.

On 2026-10-04 it reached `complete_workflow.json`: opened after this graph's
stages had been switched, its CLIP switch was muted and its LoRA loader
bypassed, so Basic Image Editing failed validation with `Required input is
missing: clip` and Image Edit + LoRA failed with `'NoneType' object has no
attribute 'tokenize'`. It began with image 0.1.5: the 10 relays and repeaters of
0.1.3 and 0.1.4 held no link number that a relay could follow into those nodes,
while the stage-input pickers of 0.1.5 added 18 more, one of which reads link
135 (in that graph, the muted GGUF CLIP loader into the CLIP switch) and writes
through link 134 (the checkpoint into the same switch). A relay copies the mode
of what its input links come from onto what its output links lead to
(`node_mode_relay.js`, `stabilize()`); a leftover repeater does nothing until its
own mode changes, which it cannot once its graph is gone. The node packs and
`complete_workflow.json` are the same in all four images. Since then
`scripts/build_asset_workflow.py` numbers this
graph's nodes from 10000 and its links from 100000, which no other graph here
uses, so its leftover relays find nothing; the same sequence in the editor then
left both edit groups whole. `complete_workflow.json` has relays of its own,
numbered from 1, which can still reach a graph opened after it. Open a graph in
a new tab, and if nodes mute themselves for no reason, close the other graph's
tab and reload the page.
:::

::: tip A new image does not replace the copy you already have
The container's start-up script copies a graph into the editor's folder only
when no file of that name is there (`scripts/entrypoint.sh`), so pulling a new
image leaves your `asset_workflow.json` as it was. Image 0.1.10 is the first
whose graph has a panel per stage number, with the two Concept stages and the
two Mesh stages one at a time; an older copy has the single Stages panel, which
lets both Mesh stages be on. To take the new one, delete `asset_workflow.json`
in the **Workflows** sidebar, restart the container and reload the page. Save
anything of yours in it under another name first.
:::

### Picking a take

Each image stage, 1 to 3, makes **Takes** images per queue and saves them all.
Behind each sits an **Image Filter**, from cg-image-filter, that passes on only
the take you choose. The server runs it only when something below it is on, so:

- A stage with nothing below it on never pauses. Queue Concept alone and you get
  its takes, saved and listed in the pickers.
- With a stage below on, the queue pauses after each image stage. A window
  shows the takes; click one (its border turns green), press **Send** or Enter,
  and the chosen take goes on to the next stage. **Cancel** or Escape stops the
  queue. Left alone for an hour it carries on with the first take, so an
  unattended queue still finishes. Clicking two sends both; Mesh and Animate
  expect one.
- The takes are the stage's saved files, so a take you did not choose is still
  there for the Stage inputs row later.
- Click exactly one. In the run under [Measured runs](#measured-runs), driven
  from a script, the window already held the first take as picked before
  anything was clicked, for a reason not found, and reported both as picked
  after the second was clicked; Edit then made its two takes from the second
  concept only. What two green takes send on was not established.

The Concept stages get their takes from the latent batch size; Edit and
Simplify repeat the encoded source that many times before sampling, so each
take is a new seed on the same input.

The Image Filter node comes from cg-image-filter, which the Dockerfile added on
2026-10-02 and image 0.1.5 (built and pushed 2026-10-03) is the first to carry. Image 0.1.6 (built and pushed later on 2026-10-03, digest `e83e51df`) is the first to carry the graph with its own-image start, Stage 0, and 0.1.7 (2026-10-04, digest `914a3ab9`) the first whose graph numbers its nodes from 10000, so its relays cannot reach `complete_workflow.json` (the relay warning below).
An earlier image lacks it, and the editor then opens
this graph with four missing nodes; the stages still run, but nothing pauses
and nothing flows between them. Rebuild the image, or clone the pack into
`custom_nodes/` at the commit the Dockerfile pins and restart.

### The stages

Each stage is a copy of a base graph in `workflows/api/`, so what its page says
holds here too.

| Stage | Built from | Saves |
|---|---|---|
| 0. Your image | one Load Image node, no base graph | nothing; it reads `input/` |
| 1. Concept, fast | `txt2img_qwen_fast.json`, **Takes** per queue, then a pick | `output/asset_concept_fast_NNNNN_.png`, one per take |
| 1. Concept, full | `txt2img_qwen.json`, the same | `output/asset_concept_NNNNN_.png` |
| 2. Edit | `img_edit_qwen.json`, instruction from **Edit instruction**, **Takes** per queue, then a pick | `output/asset_edit_NNNNN_.png` |
| 3. Simplify | `preset_simplify_concept.json`, the same | `output/asset_simplify_NNNNN_.png` |
| 4. Mesh, TRELLIS | `img2mesh_trellis.json` | `output/mesh/TRELLIS_<date>.glb` |
| 4. Mesh, Hunyuan3D 2.1 | `img2mesh_hunyuan3d21.json` | `output/mesh/Hunyuan21_<date>.glb` |
| 5. Texture | `mesh_texture_hunyuan3d21.json` | `output/mesh/textured_<date>.glb` |
| 6. Turntable | `mesh_render_sprites.json` | `output/sprites/asset_NNNNN_.png` |
| 7. Rig | `mesh_rig_unirig.json`, with `fbx_name` set to `rigged/asset` | `output/rigged/asset_articulationxl.fbx` |
| 8. Animate | `img2video_wan22.json`, motion from **Motion prompt** | `output/video/asset_animate_NNNNN_.webm` and `.webp`, and the last frame as `output/asset_animate_last_NNNNN_.png` |

**Rig** is a stage although UniRig's loader offers a list of files. The list
only binds a path that is typed in: the server checks a value against a list
only then, and a path wired into `file_path` from another node is passed
through, after which the node joins it onto the source folder, where an
absolute container path wins. Here the Mesh or Texture stage's saved path, or
the Rig picker's path box, is wired in, so the mesh need not be on any list.
Its skeleton is `articulationxl`, whose bones are `bone_0` to `bone_N`;
`scripts/bone_roles.py map` names them, as [Rigging](/guide/rigging) explains.
A rig made this way overwrites the last one, because the name is fixed.

**Animate** makes five seconds of video of the image with Wan 2.2's two 14B
experts, as [its graph](/reference/workflows) does. Its defaults are the
settings that ran here: 480x640, 20 steps, cfg 3.5, with the lightx2v 4-step
LoRAs in the graph at strength 0, which the server skips. With them at strength
1, and the samplers at 4 steps, cfg 1 and a split at step 2, the reference card
ran out of GPU memory four times on 2026-10-02; see [Memory](#memory). Write the
motion in **Motion prompt**, not the subject again.

### How a stage finds its input

Each stage takes its input from the **nearest stage above it that is on**. Edit
reads a Concept stage, or Your image, Simplify reads Edit, or a Concept stage if
Edit is off, and so on down; Your image is the stage above every image stage,
so with the Concept stages off it feeds whichever of Edit, Simplify, Mesh and
Animate is nearest. Texture reads the mesh the Mesh stage saved and the same image
the Mesh stage used; Turntable and Rig read Texture's mesh, or a Mesh stage's;
Animate reads the same image stages as Mesh does.

A stage with no stage above it switched on reads its own **picker** instead, in
the **Stage inputs** row under the prompts:

- An image stage's picker is **Load Image (from Outputs)**. It lists the top of
  `output/`, newest first, and its refresh arrow selects the newest file. You can
  also pick any earlier one, or upload an image of your own into it.
- A mesh stage's picker is a path box holding a container path, such as
  `/app/output/mesh/asset.glb`.

A picker is muted whenever it would not be read: while any stage above it is
on, so that an empty picker never stops a chained run, and while its own stage
is off. The pickers lit up are therefore exactly the ones the next queue reads.

That is why the image stages save to the top of `output/` rather than into a
subfolder, and the mesh, rig and video stages into subfolders. The server lists
that folder with `os.scandir`, which does not look into subfolders, sorts it by
modification time, newest first, and lists every file there, not only images;
on 2026-10-02 an FBX at the top of `output/` appeared in the image pickers.

The choosing is done by rgthree's **Any Switch**, which passes on the first of its
inputs that is present. A muted stage sends nothing, so the switch falls through
to the next stage up, and last to the picker. The muting is done by rgthree's
relays, which can only say "mute when any input is active, activate when all are
muted". The first rule is one relay watching the stages above. The second needs
an inverter: a relay watching the stages that read the switch drives a **flag**
node that is active exactly while they are all off, and the picker's relay
watches the stages above and that flag together. The flag is a string nobody
reads, so the server never runs it. It is the same device
`complete_workflow.json` uses for its input image, used twice.

### Running one step as often as you like

Switch on only the stage you want. With nothing above it on, it reads its picker:
pick the image or path to work from, and queue as many times as it takes. Every
seed here is set to randomise, so each queue is a new take. When one is right,
switch that stage off and the next one on. The next stage's picker refresh arrow
selects the newest file, which is the take you just made, or you can pick an
earlier one.

To edit an edit, pick the last edit in Edit's own picker and queue again.

### Models

A loader only one stage uses sits inside that stage, so switching the stage off
takes its loader with it. The loaders two or more stages share sit in **Models**,
which is never muted, and a loader there runs only when a stage that is on needs
it: the Qwen text encoder, the Qwen VAE, and the Qwen-Image-Edit 2509 model that
Edit and Simplify both use. The encoder and VAE reach each stage through a
**Use Everywhere** node each, so their wires are not drawn; that node fills every
unwired input of its type when the prompt is sent. The Animate stage's umT5
encoder and Wan VAE are wired in the ordinary way inside that stage, so Use
Everywhere leaves them alone; the captured prompts confirm it.

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
- Rig runs in UniRig's own worker process, which held 5,544 MiB of VRAM after
  the run (nvidia-smi, 2026-10-02). That needs no purging before Animate:
  comfy-env registers the worker's models with ComfyUI's memory manager, so when
  Animate asks for the Wan expert, ComfyUI evicts them over the worker's socket
  along with its own text encoder and VAE. The worker's log shows that within
  70 ms of "Requested to load WAN21", and Animate got the same weight budget
  whether the worker was loaded or the card free beforehand: 6,157 and 6,151 MB
  usable. Only the worker's CUDA context stays, 474 MiB. Read in comfy-env 0.4.1
  and ComfyUI's `model_management.py`, and in that day's logs. By hand,
  `scripts/run_workflow.py --free` and the editor's **Unload Models** entry (the
  ComfyUI menu at the top of the left sidebar, then Edit) do the same, with one
  read-not-run caveat: after a second Rig run in the same worker the models are
  not re-registered, so neither reaches them until the worker is replaced.
- Animate with the 4-step LoRAs on ran out of GPU memory on the empty card as
  well, four times on 2026-10-02: at 624x832 in the forward pass, after the
  expert had loaded with 5,976 MB on the card and 7,655 MB offloaded; and at
  480x640 twice while merging the LoRA into the fp8 weights, once with the umT5
  encoder moved to the CPU, which did not help. The card was as empty as it
  gets each time: ComfyUI's "usable" figure is the free VRAM minus a reserve it
  keeps for the latent, 8,251 MiB at 624x832 and 81 frames and 5,045 MiB at
  480x640, and both figures back-solve to about 14.4 GB free. Merging a LoRA
  into fp8-scaled weights dequantises each weight on the card and re-rounds it
  through an eager fallback that allocates about a dozen weight-sized
  temporaries, which the loader's fit test does not count, so anything freed
  beforehand only loads more weights to merge. Without the LoRAs, at 480x640 and
  20 steps, the stage finished: the expert loaded with 9,259 MB on the card and
  4,372 MB offloaded, VRAM peaked at 14,876 MiB, the container at 21.7 GiB, the
  host never fell below 17 GiB available, and Docker reported no out-of-memory
  kill. On a 16 GB card leave the LoRAs at strength 0. What would bring 4 steps
  back is a pre-merged 4-step checkpoint, which has nothing to patch, a larger
  `--reserve-vram` in the compose command, or the Wan 2.2 5B model; none was
  tried here, and `research/untested.md` lists them.

### Licences

Each stage carries its base graph's licence. The two Hunyuan3D stages are under a
licence that excludes the EU, the UK and South Korea; TRELLIS is MIT; Wan 2.2,
its encoder, VAE and the 4-step LoRAs are Apache-2.0. The picks run on
cg-image-filter, Apache-2.0, pinned in the Dockerfile at `1602dbe`; its licence
file was read at that commit on 2026-10-02. See [Licensing](/guide/licensing).
This graph uses no pose preprocessor.

### From the video to the rig

Animate makes a video of the character moving. Rig makes a skeleton with no
motion on it. Nothing in this image joins the two: no node here extracts motion
from a video, and UniRig's Apply Animation node takes Mixamo clips only, onto a
rig made with the `mixamo` template, which the Rig stage does not use. What a
video-to-motion step would take, and what each candidate's licence allows, is in
[Video to 3D motion](/reference/video-mocap); which route to trial is an open
decision in `research/untested.md`. Until one is built, the video is for looking
at, for a final frame to feed back as a concept, and for a capture service or
model that is chosen later.

### Rebuilding it

The graph is built, never hand-edited, by `scripts/build_asset_workflow.py`, from
the base graphs in `workflows/api/`. Rebuild the presets first, because Simplify
is read from one:

```sh
scripts/build_presets.py
scripts/build_asset_workflow.py --check
```

The same command rebuilds [`krea_workflow.json`](#krea-workflow-json);
`--graph asset_workflow` builds this one alone.

It needs a running server, because the order of every node's values in the
editor's format is only knowable from `/object_info`, as for
`scripts/api_to_ui.py`. `--check` puts every value back on its name and compares
the graph with the base graphs. It cannot see the relays, which run in the
browser. The packaged service keeps its own copies of the editor graphs and only
adds a file name it lacks, so open a rebuilt graph there by hand, as
[Workflows](/reference/workflows#editing-graphs-in-the-comfyui-editor) explains.

### What was checked, and how

All on 2026-10-02, in the packaged container on this branch's image, on the
rebuilt graph served to the editor from `input/`, through Playwright driving
the editor. None of it generated anything.

- The graph loads with its 140 nodes and 181 links. The Stages panel lists the
  ten stage groups and not Inputs, Models or Stage inputs, and each group holds
  exactly its own nodes.
- Twenty combinations of stages were switched through the panel's own toggles:
  each stage alone, eight chains from Concept, Edit and TRELLIS to every stage
  on one path at once, every stage on, and none. With the editor's submit call
  replaced by a stub, the prompt it would send was captured each time, through
  the queue call so that Use Everywhere did its work. In every one, each of the
  seven pickers was muted exactly when a stage above it was on or its own stage
  was off, each flag was active exactly while every stage reading its switch
  was off, the nodes sent were exactly the live ones, each switch's inputs were
  the stages above that were on, nearest first, then its picker when active,
  every wired input was a drawn link apart from the CLIP and VAE inputs Use
  Everywhere filled with the Qwen loaders, and no CLIP or VAE input of a sent
  node was left unfilled. The server's queue stayed empty throughout.
- All twenty prompts went through `scripts/validate_workflows.py` against the
  live server. Its two complaints are inputs the server's node definitions do
  not list: the extra `refresh` value the editor adds to **Load Image (from
  Outputs)**, which the server ignores because its input gathering keeps only
  the inputs a node declares, and the Any Switch's `any_NN` inputs, which the
  node declares none of because it takes any keyword. The queued runs below,
  which pass through both, confirm the server accepts them.
- The pickers' values were set on the captured prompts with `--set`, and the
  prompts were queued with `scripts/run_workflow.py`, so runs E and F went
  through the server exactly as the editor would have sent them.
- On 2026-10-03, with the picks and the Takes box added (147 nodes, 191 links),
  six combinations were captured the same way and passed the same checks, with
  one Image Filter sent for each image stage on, the Takes box wired to both
  Concept latents and to a RepeatLatentBatch in Edit and in Simplify. Run G was
  queued from the editor itself, and the pause window was driven through its
  own click handlers.
- The same day, with Stage 0 added (149 nodes, 199 links), nine combinations
  were captured and checked, six of them with Your image on: alone, with Mesh,
  with Edit and Mesh, with Simplify and Texture, with Animate, and with Concept,
  fast, and Edit on at once, where Edit read the concept and not the image, as
  the nearest-above rule says.
- On 2026-10-06 the one Stages panel became five, in stage order, with Stage 1
  and Stage 4 each in a panel that lets one stage at a time be on (153 nodes,
  199 links). Each panel listed exactly its own groups. Switching on Hunyuan3D
  muted the TRELLIS group, and the captured prompt held Hunyuan3D's shape nodes
  and no TRELLIS node, and the same the other way round. Concept, full switched
  Concept, fast off. Texture with Turntable, and Edit with Simplify, stayed on
  together. Nothing was queued. That day a queue from the old single panel had
  both mesh stages on and ran out of GPU memory in Hunyuan3D's shape decoder.

### Measured runs

Queued on the reference machine, in the packaged container, one after another.
Seconds are ComfyUI's own, from `execution_start` to `execution_success` in
`/history`. Memory was sampled every 2 seconds: the container's figure is
`docker stats` MemUsage, the host's is `free`'s available column, and VRAM is
`nvidia-smi`. Runs A to D were queued from the editor on 2026-09-30 on the
previous layout of this graph, whose stage nodes are unchanged; E and F were
queued on 2026-10-02 from the captured prompts.

| Run | Stages on | Input | Seconds | Saved |
|---|---|---|---|---|
| A | 1. Concept, fast | the prompt | 22.1 | `asset_concept_fast_00001_.png`, 1104x1472 |
| B | 2. Edit, queued twice | its picker, after refresh | 147.8, 171.6 | `asset_edit_00001_.png` and `_00002_`, 880x1184 |
| C | 4. TRELLIS, 6. Turntable | Mesh's picker, set to the first edit | 22.2 | a 48,000-face mesh, then 8 frames and 8 masks from it |
| D | 1. Concept, fast, 2. Edit, 4. TRELLIS | the prompt | 204.6 | a concept, an edit and a 48,000-face mesh |
| E | 7. Rig | its path box, set to `TRELLIS_2026-10-01-00-08-06.glb` from C's day | 21.6 | `rigged/asset_articulationxl.fbx`, 2,474,364 bytes, with a skeleton and skinning |
| F | 8. Animate | its picker, set to A's concept | 604.7 | `video/asset_animate_00001_.webm`, vp9 at 480x640 and 16 fps, its `.webp` twin, and `asset_animate_last_00001_.png` |
| G | 1. Concept, fast, 2. Edit, Takes 2 | the prompt; the second take clicked at the pause | 289.0, of which 33 to the pause | `asset_concept_fast_00008_.png` and `_00009_`, 1104x1472; `asset_edit_00006_.png` and `_00007_`, 880x1184, both from the second concept |
| H | 0. Your image, 4. TRELLIS | `input/my_concept.png`, a copy of G's second concept, named in Stage 0 | 33.0, on a cold TRELLIS pipeline after a container start | `mesh/TRELLIS_2026-10-04-02-31-27.glb`, 48,000 triangles |

- **The hand-over worked both ways.** In B, Edit's refresh arrow selected the
  concept A had just made, the newest file, and the two queues ran on different
  seeds and made different takes. In C, Mesh's refresh arrow selected the second
  take, the newest, and picking the first from the list worked; Turntable then
  rendered the mesh TRELLIS had just saved, through its path switch. In D, each
  stage read the one above, with every picker muted. In E, UniRig loaded a file
  that was on none of its lists, through the path switch.
- **Memory.** Across A and B, the container peaked at 26.4 GiB, the host never fell
  below 13.9 GiB available, and VRAM peaked at 15,731 MiB. Across D, with two Qwen
  diffusion models in one queue, the container peaked at 22.0 GiB, the host never
  fell below 12.2 GiB available, VRAM peaked at 15,718 MiB, and Docker reported no
  out-of-memory kill and no restart. `docker stats` counts some page cache, which
  is likely why its peak sits above what the host's available figure implies.
  After E, UniRig's worker held 5,544 MiB of VRAM. Across F, VRAM peaked at
  14,876 MiB, the container at 21.7 GiB, and the host never fell below 17 GiB
  available. Across G, with two takes in each stage, VRAM peaked at 15,587 MiB
  of 16,066, the container at 27.2 GiB, and the host never fell below 13 GiB
  available; the edit model loaded partially, 12,497 MB on the card and
  6,987 MB offloaded. Two takes is close to the card's limit at these sizes,
  and more was not tried.
- **The pause worked.** In G the queue stopped 33 s in, with the two concepts
  on screen, the tip from the graph and a 3,600 s countdown; clicking a take
  and Send resumed it, and Edit ran on the take clicked. Nothing in the server
  log marks the pause: it shows one prompt, executed in 288.98 s.
- **The video is a take, not a cycle.** Three frames of F tiled with ffmpeg
  show the golem keeping its design and the background while it shifts its
  weight and lifts a leg: a slow step on the spot, which is what the motion
  prompt asked for. Nothing here turns it into motion on the rig; see
  [From the video to the rig](#from-the-video-to-the-rig).
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

## krea_workflow.json

::: tip Status: Concept run on its own on 2026-10-10; the graph checked in the editor, not queued
`txt2img_krea2.json`, the base graph of Stage 1, ran on the reference machine
on 2026-10-10. `txt2img_krea2_style.json` ran out of memory there, and the graph
itself has not been queued. The figures are under
[Measured on the 16 GB card](#measured-on-the-16-gb-card).
:::

The image and video half of the pipeline, as `complete_workflow.json` is, with
[Krea 2](/guide/licensing#krea-2) Turbo painting the concept. Krea publishes no
open model for editing or for image to video, so the Edit and Animate stages are
the ones in `asset_workflow.json`.

| Stage | Base graph | Does |
|---|---|---|
| 0. Your image | none | Starts from concept art you already have |
| 1. Concept | `txt2img_krea2.json` | Krea 2 Turbo, 8 steps, from the prompt |
| 1. Concept, styled | `txt2img_krea2_style.json` | The same, painted in the style of the image in its **Style Reference** node. A style match, not an edit. Ran out of memory on the 16 GB card |
| 2. Edit | `img_edit_qwen.json` | Qwen-Image-Edit 2509 |
| 3. Animate | `img2video_wan22.json` | Wan 2.2, five seconds at 480x640 |

It works as `asset_workflow.json` does: **Prompt** feeds both Concept stages,
**Edit instruction** Stage 2 and **Motion prompt** Stage 3. The two Concept
stages share a panel that lets one at a time be on. Each stage takes its input
from the nearest stage above it that is on, a stage with a stage below it on
pauses for you to [pick a take](#picking-a-take), and the **Stage inputs** row
holds a picker for Edit and one for Animate. Only Concept is on when it opens,
and **Takes** opens at 1, because two Krea images at once ran out of memory on
the 16 GB card.
Stage images save to the top of `output/` as `krea_<stage>_NNNNN_.png`, and the
video under `output/video/`. Its node ids start at 20000 and its link ids at
200000, a range no other graph here uses, so the
[relay warning](#asset-workflow-json) above cannot reach between it and
`asset_workflow.json`; `complete_workflow.json`, numbered from 1, can still be
reached by its relays, so open each graph in its own tab.

### What it needs

Image 0.1.11 is the first to carry it and its two Krea base graphs; an editor
volume from an older image gains them on the first start, since their names are
new. No node pack beyond those `asset_workflow.json` needs. The weights:

```sh
scripts/fetch_models.py --download --group krea2 --group qwen_edit --group qwen --group wan_i2v
```

`krea2` is about 18GB in the fetcher's units: Krea 2 Turbo's int8 ConvRot weights
(12.6GB), its Qwen3-VL 4B encoder (4.9GB), ostris's style reference LoRA and the
Qwen VAE. The Edit stage needs `qwen_edit` and the `qwen` group's text encoder,
and Animate needs `wan_i2v`. Downloading the Krea weights binds you to the Krea 2
Community License, whether or not the download page asks. The packaged container
fetches them itself on boot with `ASSET_ENGINE_FETCH_MODELS=1` and
`ASSET_ENGINE_FETCH_GROUPS` naming the groups
([running the image](/guide/running-the-image)).

### Licences

Read [Krea 2](/guide/licensing#krea-2) before shipping anything the Concept
stages make. In short:

- **Krea 2 Turbo, its encoder and the style LoRA**: commercial use of the model
  and of what it makes only while your company, affiliates included, earns under
  1 million dollars a year. Past that you must stop commercial use, of the
  outputs too, until Krea grants an enterprise licence. Krea may end the licence
  for any reason on 30 days' notice, and it requires content filtering, which
  here means looking at every image before it ships.
- **Qwen-Image-Edit 2509 and Wan 2.2**: Apache-2.0. Your image, through Edit, to
  Animate never touches Krea.

### Measured on the 16 GB card

On 2026-10-10, on image 0.1.11, with the server's own timings and VRAM read by
`nvidia-smi` every half second:

| Graph | Size | Result |
|---|---|---|
| `txt2img_krea2.json` | 864x1152, the graph's size | 22.3 s, 8 steps at 2.43 s each, peak 15,786 MiB of 16,066 |
| `txt2img_krea2.json` | 1024x1024 | 27.9 s, 2.62 s a step, peak 15,678 MiB |
| `txt2img_krea2.json` | 1104x1472 | Out of GPU memory in the sampler |
| `txt2img_krea2.json` | 864x1152, a batch of two | Out of GPU memory |
| `txt2img_krea2_style.json` | 864x1152, and 672x896 | Out of GPU memory in the sampler, both |
| `txt2img_krea2_style.json` | 864x1152, server started with `--reserve-vram 2`, then 4 | Out of GPU memory sooner, merging the LoRA into the int8 weights |
| `txt2img_krea2_style.json` | 864x1152, on Comfy-Org's fp8 weights in place of int8 | Out of GPU memory merging the LoRA into the fp8 weights |

Both times include loading the 4,999 MB encoder and the 12,867 MB int8 weights,
which the server log shows loaded whole. The weights fill most of the card,
which is why 1104x1472, a second image in the batch, or a style reference, whose
latent the encoder scales to about a megapixel and adds to every step, do not
fit. A larger `--reserve-vram` makes the server load only part of the model,
but for the style reference that moved the failure rather than curing it: the
LoRA is merged into the weights as they load, each patched int8 weight becomes a
float32 copy on the card, and the log shows `ERROR lora
diffusion_model.blocks.25.mlp.down.weight Allocation on device`. At that point
PyTorch had 7,308 MiB allocated at its peak and 9,600 MiB reserved, far short of
the card, so the cause is not simply room; it was not found. The fp8 weights,
`krea2_turbo_fp8_scaled.safetensors`, in place of int8 and at the usual flags,
failed in the same merge, as it converted each patched weight back to fp8, with
the 4,999 MB text encoder still on the card: 10,556 MiB allocated at the peak,
14,880 MiB reserved. Every attempt fails on merging a full-precision LoRA into
quantised weights on a full card. The same flag was
not tried for 1104x1472 or for two takes, and the compose file keeps its usual
flags. The 864x1152 golem came out head to toe on a
plain grey background, as the prompt asked.

**Krea's encoder also reads images.** Its text encoder is Qwen3-VL 4B, a
vision-language model, and ComfyUI's `TextGenerate` node takes an image. Given
the golem and an instruction to describe it for a text-to-image prompt, with
greedy decoding, it wrote an accurate paragraph about its stone, moss, pose,
lighting and plain grey background in 15.0 s, peaking at 6,542 MiB. That was a
test graph, not one in `workflows/api/`.

### Checked, and not yet run

On 2026-10-10, in the packaged container on image 0.1.10 (ComfyUI 0.30.2):

- Both Krea base graphs passed `scripts/validate_workflows.py`, and their editor
  copies `scripts/api_to_ui.py --check`. This graph passed
  `scripts/build_asset_workflow.py --check`, and the rebuild left
  `asset_workflow.json` byte for byte as it was.
- It was opened in the editor, with the relay guard from the warning above, and
  its panels driven through their own widgets for nine combinations of stages:
  each Concept alone, Concept and Edit, Concept, styled with Edit and Animate,
  Your image with Edit and with Edit and Animate, Edit alone, Animate alone, and
  Concept and Animate. The prompt each would send was captured with the submit
  call stubbed. In all nine every node the server knows passed
  `scripts/validate_workflows.py`, which complained only of the Any Switch's
  numbered inputs and the picker's `refresh`, as for `asset_workflow.json`; every
  link resolved inside the prompt; and Edit and Animate read the stage above
  that was on, or their picker when none was. Use Everywhere gave the Krea stages
  the Qwen3-VL encoder and the Qwen VAE; Edit kept its own Qwen 2.5 VL encoder,
  and Animate its umT5 and Wan VAE.
- Switching **Concept, styled** on with a click, with Concept on, switched
  Concept off.

Not yet run: this graph itself, so whether a queue that runs Krea, then the
19.0GB edit model, then Wan, fits the 31 GB host.

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

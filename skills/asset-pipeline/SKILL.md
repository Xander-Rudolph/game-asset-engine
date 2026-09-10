---
name: asset-pipeline
description: Generate a game asset from a text prompt through a local ComfyUI, stopping for approval at each stage - concept image, then 3D mesh, then rigging, then sprite frames. Use when the user wants to make a 3D game asset, character, creature or prop from a description, or asks to run the asset pipeline. Also use when they want to redo one stage of an asset they already made.
---

# Asset pipeline: prompt to rigged model, with a gate at every stage

Each stage is **shown to the user and approved before the next one starts**. Never
run two stages in one go. A concept image costs 30 seconds; a rejected mesh three
stages later costs an afternoon.

Work in the asset-engine repo root. Every path below is relative to it.

## Before you start: check the engine, do not assume it

```sh
scripts/doctor.py --skip-models
```

Read the output. It ends with either `Ready.` or a `Next step:` naming the one
thing to do. Do not start generating until it says ready.

If it is not ready, walk the user through it rather than doing it silently:

| What it says | What to tell the user |
|---|---|
| `docker` missing | Docker is not installed or they are not in the `docker` group. The fix is printed. Adding a group needs a re-login. |
| `gpu runtime` warning | The NVIDIA container toolkit is missing. Mesh generation will not work without it. Give them the `nvidia-ctk` command it prints. |
| `.env` missing | Offer to run `scripts/doctor.py --fix`, which writes it from the example. They still need to set `MODELS_DIR`. |
| `image` missing | 27GB pull. Say the size before starting it. `docker pull ghcr.io/xander-rudolph/game-asset-engine-comfy:latest` |
| `container` not running | `docker compose --profile packaged up -d`, or offer `--fix`. |
| `server` not answering | The container can be up while ComfyUI is still importing nodes. That takes a minute or two on a cold start. Wait, do not restart. `docker logs -f comfyui` shows progress. |
| `node packs` not loaded | A pack failed to import. The reason is only in the startup log: `docker logs comfyui 2>&1 \| grep -i -A5 error \| head -40` |
| `weights` missing | `scripts/fetch_models.py --download`. Core is about 21GB. Say the size first. |

If the user has never run this before, offer to run `scripts/doctor.py --fix`
and then walk the remaining steps with them one at a time.

If the user gave no subject, ask what they want to make before generating.

---

## Stage 1: concept image

Prompts that reconstruct well into 3D are specific in the same way every time:
**one subject, full body, three-quarter view, even lighting, flat background, no
cast shadow.** Add the user's subject to that skeleton rather than passing their
words through raw. Say what you added.

**Use Qwen-Image, not SDXL.** SDXL base is a photo model. It renders a person
wearing a costume photographed in a studio, and it drops most of a long brief.
Qwen holds a seven clause description at once and paints concept art.

```sh
# finding a look, about 30 seconds
scripts/run_workflow.py workflows/api/txt2img_qwen_fast.json \
    --prompt 'Full body head-to-toe view of a single <subject> standing upright, the entire figure visible with space above and below, three-quarter view. <materials, colours, details, in plain sentences>. Even flat studio lighting, plain neutral grey background, no cast shadow. Painted game asset concept art, crisp readable silhouette.'

# the real one, about 130 seconds, negative prompt works
scripts/run_workflow.py workflows/api/txt2img_qwen.json --prompt '...' --negative '...'
```

Or use a preset, which already carries the house style and its matching negative:

```sh
scripts/run_workflow.py workflows/api/preset_concept_character.json \
    --prompt '<subject>'
```

Three things that are load bearing:

- **Write full sentences, not comma separated tags.** Qwen is a text model. Tag
  soup wastes its strength, and SDXL habits produce worse results here.
- **The fast workflow ignores `--negative`.** A distilled 4-step LoRA runs at
  guidance 1.0, so there is no guidance to steer with. Put everything in the
  positive, or use the 20-step workflow.
- **Both default to 1104x1472.** Do not switch to square for a standing figure.
  It crops at mid thigh, and a cropped concept makes a cropped mesh. Square is
  fine for a prop.

Use `--prompt` and `--negative`, never `--set text=...`. The `text` input exists
on both the positive and negative nodes, and a bare `--set` is refused for
exactly that reason.

> ### STOP. Read the image file before doing anything else.
>
> Call the **Read** tool on the path it printed so the picture renders in the
> conversation. Printing a path is not showing an image. Then look at it and say
> what you see: one subject, uncropped, plain background, matching the brief.
>
> **Do not generate a mesh in the same turn.** Stage 2 inherits every flaw in the
> image. A cropped concept makes a cropped mesh; two figures make one fused blob.

Then ask with AskUserQuestion: **Approve**, **Reroll** (`--set seed=<new>`),
**Change the prompt**, or **Stop**. Do not proceed on silence or a vague reply.

---

## Stage 2: 3D mesh

Pick the generator and **say which one you picked and why**:

| Use | When |
|---|---|
| `img2mesh_triposg.json` | Fast and clean. MIT upstream, but the copy in this pack ships a licence file with the EU/UK/Korea exclusion, which is unresolved. Needs a cut out image. |
| TRELLIS | **The choice with no territory clause** (MIT), for anything shipping into the EU, UK or South Korea. No graph ships for it yet: the weights are in the `trellis` group and the nodes are loaded (`[Comfy3D] Trellis Structured 3D Latents Models`), so it needs a graph building. Say that rather than pretending there is a one-liner. |
| `img2mesh_hunyuan3d21.json` | Best geometry, removes the background itself. **Licence excludes the EU, UK and South Korea.** Say so before using it for anything that ships. |
| `mesh_texture_hunyuan3d21.json` | Paints an existing shape. Run after a shape graph. |
| `img2mesh_triposr.json` | Fastest, lowest quality. Needs a cut out too. |

```sh
scripts/run_workflow.py workflows/api/img2mesh_hunyuan3d21.json \
    --image output/concept/character_00002_.png \
    --set 'save_path=mesh/<name>.glb'
```

### Check it yourself before showing it

A mesh cannot be displayed, so render it and read the render:

```sh
scripts/render_sheet.py output/mesh/<name>.glb --angles 4 --size 320 \
    --out output/sheets/<name>.png
```

Read that file. Then get the numbers, because the picture hides things:

```sh
docker exec comfyui python3 -c "
import trimesh; m = trimesh.load('/app/output/mesh/<name>.glb', force='mesh')
print('faces', len(m.faces), '| bodies', m.body_count, '| watertight', m.is_watertight)"
```

What to flag rather than let the user discover later:

- **`bodies` well above 1** means disconnected pieces. A few is normal for a
  detailed creature. Twenty or more from a small mesh means the generator failed,
  usually from a bad input image. Offer to go back to stage 1.
- **A near empty render** means the same thing.
- **Grey clay** in the render means no texture yet, which is expected from a
  shape only workflow. Say so rather than letting it read as a failure.
- **Face count** is a ceiling, not a target. The decimation step will not add
  faces to a simpler mesh.

Then ask: **Approve**, **Reroll**, **Back to stage 1**, **Different generator**,
or **Stop**.

---

## Stage 3: rigging

Only after the mesh is approved.

```sh
cp output/mesh/<name>.glb input/3d/<name>.glb
scripts/rig_units.sh <name>
```

Two settings in that script are load bearing and neither should be changed
casually. `articulationxl` rather than `mixamo`, because Mixamo demands a fixed
52 bone humanoid and aborts on most generated figures. `fp16` rather than `auto`,
because auto picks bfloat16 on recent cards and the sparse convolution library
has no bfloat16 kernels.

**Tell the user what the rigger did to their mesh.** It decimates anything above
its budget of 48,000 faces and hands back the decimated version, not the
original. Under the budget, nothing happens. Check:

```sh
docker exec comfyui python3 -c "
import bpy; bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath='/app/output/rigged/<name>.fbx')
ms=[o for o in bpy.data.objects if o.type=='MESH']
ar=[o for o in bpy.data.objects if o.type=='ARMATURE']
print('faces', sum(len(m.data.polygons) for m in ms), 'bones', len(ar[0].data.bones))"
```

If the face count came back lower than the input and the detail mattered, offer
`scripts/transfer_weights.py` to put the skeleton onto the original mesh.

Output is an FBX. Note the format handoff plainly: GLB in, FBX out, because FBX
carries the skeleton and OBJ cannot carry one at all.

---

## Stage 4: animation frames

```sh
scripts/list_animations.py                    # what is actually installed
scripts/render_sheet.py output/rigged/<name>.fbx \
    --poses transforms:poses/walk.json --angles 4 --size 220 \
    --out output/sheets/<name>_walk.png
```

**Ask which camera the game uses before rendering.** The default is isometric,
elevation 30 with facings starting at 45 degrees. A top down game needs
`--elevation 90 --azimuth-start 0`. Getting this wrong produces sprites that face
square on while the ground runs diagonally underneath, and it is not obvious in a
single frame.

Read the sheet. A mis signed rotation produces a confident, well rendered, wrong
cycle, and no log line will tell you.

---

## Rules

- **One stage per turn.** Show, ask, wait. Never run stage N+1 in the turn that
  produced stage N's output, even when the result looks obviously good.
- **Read every image you generate** so the user sees it. Do not just print a path.
- **Verify with the running server rather than guessing.** The commands above are
  there so you can check geometry, bone counts and node availability directly.
  Never describe what a file probably contains.
- **Report what you chose and why:** generator, prompt edits, camera angle.
- After editing any workflow, run `scripts/validate_workflows.py`. It checks node
  names and wiring against the live server.
- If a stage errors, read the real cause before retrying:
  `docker logs --since 3m comfyui 2>&1 | grep -iE 'error|exception'`

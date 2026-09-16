---
name: asset-pipeline
description: Generate a game asset from a text prompt through a local ComfyUI, stopping for approval at each stage (concept image, 3D mesh, texture, rigging, sprite frames). Use when the user wants to make a 3D game asset, character, creature or 3D prop from a description (a flat billboard prop needs only the concept image and a cut-out), or asks to run the asset pipeline. Also use when they want to redo one stage of an asset they already made.
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
| `image` missing | About 17GB to download, 27.6GB on disk. Say the size before starting it. `docker pull ghcr.io/xander-rudolph/game-asset-engine-comfy:latest`. While the package is private, log in first with a GitHub token that has `read:packages`: `echo "$GITHUB_TOKEN" \| docker login ghcr.io -u <github-username> --password-stdin`. Without that the pull fails with `denied` or `manifest unknown`, which looks like a wrong tag. |
| `container` not running | `docker compose --profile packaged up -d`, or offer `--fix`. |
| `server` not answering | The container can be up while ComfyUI is still importing nodes. That takes a minute or two on a cold start. Wait, do not restart. `docker logs -f "$(python3 scripts/_engine.py)"` shows progress. |
| `node packs` not loaded | A pack failed to import. The reason is only in the startup log: `docker logs "$(python3 scripts/_engine.py)" 2>&1 \| grep -i -A5 error \| head -40` |
| `weights` missing | The check covers the `core` group (SDXL, TripoSR and TripoSG), about 20GB, which `scripts/fetch_models.py --download` fetches. The default path below needs other groups: `--download --group qwen` for stage 1 (about 48GB), `--group trellis` for the TRELLIS shape graph (about 9GB), and `--group hunyuan` for either Hunyuan graph (about 24GB). Say the size first. |

If the user has never run this before, offer to run `scripts/doctor.py --fix`
and then walk the remaining steps with them one at a time.

If the user gave no subject, ask what they want to make before generating.

**Redoing one stage?** Go straight to that stage below, or hand off to the skill
that owns it: `concept-edit` to change one detail of an approved concept,
`mesh-budget` for a face budget, decimation or rigging a heavy mesh, `pose-sheet`
for poses, cycles and facings on a rigged model.

**A flat prop?** One that never shows its other side (a tree, a rock on a map)
stops after stage 1, generated with `preset_concept_prop.json`, and is cut out,
not meshed. Start from `scripts/cut_icon.py <src> <dst>`, then add what the
Cutting section of docs/guide/props.md adds and the script does not do: clear
enclosed pockets, bleed the rim colour, stand every prop on one baseline.

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
    --subject '<subject>'
```

`--subject` fills the preset's subject slot; `--prompt` would replace the whole
text, house style and all. The character, creature, building and prop presets
also carry an `<<< ART DIRECTION: ... >>>` slot that `--subject` leaves alone.
**Never queue past `still has an unfilled slot (<<< ART DIRECTION >>>)`:** the
script warns and queues anyway, and the placeholder reaches the model as
literal text. Add `--dry-run` first. If it warns, ask the user for their look,
put it in that slot in `prompts/<folder>/_style.txt` (`scenery` for the prop
preset; it reaches every asset from that folder), run
`scripts/build_presets.py`, and dry-run again until the warning is gone.

Four things that are load bearing:

- **Write full sentences, not comma separated tags.** Qwen is a text model. Tag
  soup wastes its strength, and SDXL habits produce worse results here.
- **The fast workflow ignores `--negative`.** A distilled 4-step LoRA runs at
  guidance 1.0, so there is no guidance to steer with. Put everything in the
  positive, or use the 20-step workflow.
- **Both default to 1104x1472.** Do not switch to square for a standing figure.
  It crops at mid thigh, and a cropped concept makes a cropped mesh. Square is
  fine for a prop.
- **Naming a thing in the positive summons it, even to forbid it.** "No ragged
  tatters, no tears, no frayed edges" in the positive made a more tattered coat
  every time. When something keeps appearing, say what it should be in the
  positive ("a smooth even curved hem") and put what it must not be in the
  negative, which only the 20-step workflow and the presets use. The "no cast
  shadow" above breaks this rule. docs/guide/props.md records the same kind of
  short "no ..." list working across a whole batch; if a shadow creeps back,
  delete those words from the positive first and let the negative carry them.

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

Free the concept models first. The Qwen models stay loaded after stage 1, and
the shape run that follows can run out of memory:

```sh
scripts/run_workflow.py --free
```

It unloads the models ComfyUI manages. It does not release 3D-Pack's Hunyuan
pipelines, which the pack caches itself; only a container restart does.

Pick the generator and **say which one you picked and why**:

| Use | When |
|---|---|
| `img2mesh_trellis.json` | **The choice with no territory clause** (MIT), for anything shipping into the EU, UK or South Korea. Removes the background itself, so a plain-background concept works as is. Needs the `trellis` weight group: `scripts/fetch_models.py --download --group trellis`. |
| `img2mesh_hunyuan3d21.json` | Best geometry, removes the background itself. **Licence excludes the EU, UK and South Korea.** Say so before using it for anything that ships. |
| `img2mesh_triposr.json` | **Does not work as wired.** Read from the source, not run: the graph feeds `LoadImage`'s mask straight into `reference_mask`, and that mask is 1 minus alpha. A transparent cut-out comes out with the subject greyed and the background kept, and an image with no transparency fails on a mask size mismatch. It would need an `InvertMask` before `reference_mask`, plus a cut-out. |
| `img2mesh_triposg.json` | **Do not use for now.** In this install it returns a cage of fragments instead of the subject, whatever the input: plain grey background, white background, a transparent cut-out, square framing and the non-flash decoder all failed the same way. Its licence status inside this pack is also unresolved. |

```sh
scripts/run_workflow.py workflows/api/img2mesh_trellis.json \
    --image output/concept/character_00002_.png \
    --set 'save_path=mesh/<name>.glb'
```

### Check it yourself before showing it

A mesh cannot be displayed, so render it and read the render:

```sh
scripts/render_sheet.py output/mesh/<name>.glb --angles 4 --size 320 \
    --out output/sheets/<name>.png --check
```

`--check` exits non-zero if a cell is empty, the subject touches its cell border
or its size swings a lot between angles. Passing it does not make the mesh good.

Read that file. Then get the numbers, because the picture hides things:

```sh
docker exec "$(python3 scripts/_engine.py)" python3 -c "
import trimesh; m = trimesh.load('/app/output/mesh/<name>.glb', force='mesh')
big = max(len(p.faces) for p in m.split(only_watertight=False)) / len(m.faces)
print('faces', len(m.faces), '| bodies', m.body_count, '| largest piece', f'{big:.0%}',
      '| watertight', m.is_watertight)"
```

What to flag rather than let the user discover later:

- **A small `largest piece`** means the generator failed. A good mesh keeps
  nearly all its faces in one piece: the meshes measured here held 99% or more,
  with anywhere from 3 to 30 `bodies`. The failed TripoSG runs held 30% or less.
  So do not judge by `bodies` alone, because a few dozen tiny loose pieces are
  normal. Offer to go back to stage 1 or to try a different generator.
- **A near empty render** means the same thing.
- **Grey clay** in the render means no texture yet, which is expected from a
  shape only workflow. Say so rather than letting it read as a failure.
- **Face count** is a ceiling, not a target. The decimation step will not add
  faces to a simpler mesh.

Then ask: **Approve**, **Reroll**, **Back to stage 1**, **Different generator**,
or **Stop**.

---

## Stage 3: texture

Optional. **Say the licence first:** this runs Hunyuan3D 2.1, whose licence
excludes the EU, UK and South Korea for the textured model and every sprite
rendered from it, even when TRELLIS made the shape. For an asset that ships
there, skip to stage 4.

```sh
scripts/run_workflow.py workflows/api/mesh_texture_hunyuan3d21.json \
    --image output/concept/<concept>.png \
    --set "mesh_path=/app/output/mesh/<name>.glb" \
    --set "TexGen Pipeline.max_num_view=6" \
    --set "TexGen Pipeline.resolution=512" \
    --set "save_path=mesh/<name>_textured.glb"
```

Pass the approved concept image again: it is what gets painted.

- **Copy the maps out before the next asset.** They go to the same fixed paths
  every run (`output/Hun2-1/hunyuan_output*.jpg`), and the next asset
  overwrites them without a warning.
- **Texturing rebuilds the mesh**, typically to about 40,000 faces
  (docs/guide/meshes.md). Decimate after texturing, not before, and rig the
  textured mesh.
- **The texture model stays in GPU memory** and `--free` cannot release it, so
  the next shape run fails with `torch.OutOfMemoryError: Allocation on device`.
  **Before the next asset's shape stage, the container needs a restart**
  (`docker restart "$(python3 scripts/_engine.py)"`). A restart ends every job
  on the shared server, not only yours, so run
  `curl -s http://127.0.0.1:8188/queue` first and ask the user.
- **For several assets, restart, run all shapes, restart again, run all
  textures.** Offer `scripts/asset_to_mesh.sh <concept.png> <name> ...`, which
  checks the queue before each of those restarts and copies the maps out. **It
  uses Hunyuan3D for the shape as well as the texture**, so all its output
  carries the territory clause.

Render and read `output/mesh/<name>_textured.glb` as in stage 2, then ask:
**Approve**, **Reroll**, **Skip texturing**, or **Stop**.

---

## Stage 4: rigging

Only after the mesh is approved.

```sh
cp output/mesh/<name>_textured.glb input/3d/<name>.glb   # <name>.glb if untextured
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
docker exec "$(python3 scripts/_engine.py)" python3 -c "
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

## Stage 5: animation frames

```sh
scripts/list_animations.py                    # what is actually installed
scripts/render_sheet.py output/rigged/<name>.fbx \
    --poses transforms:poses/walk.json --angles 4 --size 220 \
    --out output/sheets/<name>_walk.png --check
```

**Ask which camera the game uses before rendering.** The default is isometric,
elevation 30 with facings starting at 45 degrees. A top down game needs
`--elevation 90 --azimuth-start 0`. Getting this wrong produces sprites that face
square on while the ground runs diagonally underneath, and it is not obvious in a
single frame.

`--check` exits non-zero on a fault it can measure, including a pose row
identical to the first row at every angle, which means the pose did nothing even
if every bone name was right. It also names the cell that faces down and to the
right, which is where the game's facing mapping starts.

Then read the sheet. A mis signed rotation produces a confident, well rendered,
wrong cycle, and neither the check nor a log line will tell you. A pose file
fits only the rig it was written for; on a new rig, the `pose-sheet` skill reads
the bone names and probes the axes first.

**For a set, one scale.** Each model is framed to its own bounding box. Size
unrigged meshes with `scripts/normalise_mesh.py <meshes> --height <units>`
(`--footprint <units>` if tile bound), confirm with the same command plus
`--check`, and render all of them with one `--span <units>`. Never normalise a
rigged FBX, which loses its skeleton. Normalising before rigging is undone: the
rigger rescales each model so its largest dimension is 2.0 units (four upright
figures rigged here measured 2.000 tall), so upright figures under one `--span`
render the same height and a model longer than it is tall comes back shorter.
Say so.

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
  `docker logs --since 3m "$(python3 scripts/_engine.py)" 2>&1 | grep -iE 'error|exception'`

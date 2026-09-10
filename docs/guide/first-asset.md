# Make your first asset

This walks one character from a sentence to a sprite sheet. About ten minutes,
most of it waiting.

Check the engine is up first:

```sh
scripts/doctor.py --skip-models
```

## 1. Draw the concept

```sh
scripts/run_workflow.py workflows/api/txt2img_qwen.json \
    --prompt "a mossy stone golem, thick moss on the shoulders, game asset, plain grey background" \
    --set "Save.filename_prefix=concept/golem"
```

The image lands in `output/concept/`. Open it and look at it before going on.

This is the cheapest stage and the one that decides everything after it. A weak
concept image produces a weak mesh, and no amount of work later recovers it.
Reroll here rather than pressing on.

If you want to reroll quickly, use `txt2img_qwen_fast.json` instead. It takes
about 30 seconds instead of two minutes. Use it to find a look, then generate
the real one with the slower graph, because the fast one ignores negative
prompts. [Why that is](/guide/concept-art#the-fast-workflow-ignores-negative-prompts).

## 2. Build the shape

```sh
scripts/run_workflow.py workflows/api/img2mesh_triposg.json \
    --image output/concept/golem_00001_.png \
    --set "save_path=mesh/golem.glb"
```

You get untextured geometry in `output/mesh/golem.glb`. It has no colour yet, so
it renders grey. That is expected, not a fault.

TripoSG is the default here because it is MIT licensed and can ship anywhere.
Hunyuan3D makes better meshes but cannot ship to the EU, UK or South Korea. See
[licensing](/guide/licensing) before choosing.

## 3. Look at it

```sh
scripts/render_sheet.py output/mesh/golem.glb --angles 4 --size 340 \
    --out output/sheets/golem_turnaround.png
```

Four views on one image. This is a silhouette check. Most bad meshes are obvious
here and nowhere else: a limb fused to a body, a face that only exists from the
front, a back that was never in the concept image so the generator invented
something.

If it is wrong, go back to step 1. Fixing geometry later costs far more than
rerolling a concept image.

## 4. Texture it

```sh
scripts/run_workflow.py workflows/api/mesh_texture_hunyuan3d21.json \
    --image output/concept/golem_00001_.png \
    --set "mesh_path=/app/output/mesh/golem.glb" \
    --set "TexGen Pipeline.max_num_view=6" \
    --set "TexGen Pipeline.resolution=512"
```

The concept image goes in again here. The texture stage paints the model to match
the drawing, so it needs the drawing.

::: warning Copy the maps out before the next asset
The texture stage always writes its maps to the same fixed paths. Generate a
second asset and the first one's maps are gone. `scripts/asset_to_mesh.sh` does
the copying for you, which is the main reason to use it for more than one asset.
:::

## 5. Rig it

Copy the mesh where the rigger looks, then run it:

```sh
cp output/mesh/golem_textured.glb input/3d/golem.glb
scripts/rig_units.sh golem
```

Out comes `output/rigged/golem.fbx` with a skeleton inside it.

Two settings in that script are load bearing and both were found by failing on
real assets: the skeleton template is `articulationxl` rather than `mixamo`, and
precision is `fp16` rather than `auto`. [Rigging](/guide/rigging) explains why.

## 6. Render the animation frames

```sh
scripts/render_sheet.py output/rigged/golem.fbx \
    --poses transforms:poses/walk.json --angles 4 --size 220 \
    --out output/sheets/golem_walk.png
```

Angles run across, animation frames run down. That is the order most engines
expect when slicing a sheet.

The camera defaults to the isometric one: 30 degrees elevation, first facing at
45 degrees. If your game is top down rather than isometric, that is the wrong
camera and [facings and camera angles](/guide/facings) has the right one.

## 7. Keep the good parts

```sh
scripts/cleanup.py keep golem \
    --concept output/concept/golem_00001_.png \
    --model   output/mesh/golem_textured.glb \
    --rig     output/rigged/golem.fbx \
    --sheets  output/sheets/golem_walk.png
```

This copies the keepers into `output/assets/golem/` with predictable names and
records where each came from. It copies rather than moves, so a later sweep
cannot destroy a curated asset.

Then clear the intermediates:

```sh
scripts/cleanup.py sweep --delete
```

## Doing it for many assets at once

Do not loop the steps above. Run the batch script instead:

```sh
scripts/asset_to_mesh.sh output/concept/golem.png golem output/concept/wyrm.png wyrm
```

It restarts the container between the shape stage and the texture stage, and runs
every shape before any texture. That ordering is not tidiness. The texture model
stays resident in GPU memory after it runs, and the next asset's shape stage then
dies with an out of memory error in its loader. Two restarts for a whole batch,
and each heavy model loads exactly once.

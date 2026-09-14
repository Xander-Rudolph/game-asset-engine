# Make your first asset

This walks one character from a sentence to a sprite sheet. About ten minutes,
most of it waiting, once the weights are on disk.

Check the engine is up first:

```sh
scripts/doctor.py --skip-models
```

## Fetch the weights, once

The walkthrough needs three weight groups. Fetch them before step 1. Only
missing files are downloaded, so running it again costs nothing.

```sh
scripts/fetch_models.py --download --group qwen --group trellis --group hunyuan
```

| Group | Size | Used in |
|---|---|---|
| `qwen` | about 48GB | Step 1, the concept image |
| `trellis` | about 9GB | Step 2, the shape |
| `hunyuan` | about 24GB | Step 4, the texture |

That is about 81GB. A plain `--download` fetches the `core` group instead (SDXL,
TripoSR and TripoSG), and no step here uses it. Without `qwen`, step 1 is
rejected with `value_not_in_list` on `unet_name`.

If the asset will ship in the EU, UK or South Korea, leave out `hunyuan` and skip
step 4. The warning there says why.

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
scripts/run_workflow.py workflows/api/img2mesh_trellis.json \
    --image output/concept/golem_00001_.png \
    --set "save_path=mesh/golem.glb"
```

You get untextured geometry in `output/mesh/golem.glb`. It has no colour yet, so
it renders grey. That is expected, not a fault.

TRELLIS is the default here for three reasons. It removes the plain background
itself, so the concept image goes in as it is. It is MIT licensed, so the shape
it makes carries no territory clause. And on a plain grey character concept it
produced a clean mesh in under 30 seconds. Texturing it in step 4 adds a
territory clause, so read the warning there before you ship.

Hunyuan3D (`img2mesh_hunyuan3d21.json`) makes the best geometry here, but its
licence excludes the EU, UK and South Korea. See [licensing](/guide/licensing).

## 3. Look at it

```sh
scripts/render_sheet.py output/mesh/golem.glb --angles 4 --size 340 \
    --out output/sheets/golem_turnaround.png --check
```

Four views on one image. This is a silhouette check. Most bad meshes are obvious
here and nowhere else: a limb fused to a body, a face that only exists from the
front, a back that was never in the concept image so the generator invented
something.

`--check` exits non-zero if a cell is empty, the subject touches its cell
border, or its size swings a lot between angles. It cannot see a bad shape, so
still look.

If it is wrong, go back to step 1. Fixing geometry later costs far more than
rerolling a concept image.

## 4. Texture it

::: warning This step uses Hunyuan3D
The texture stage runs Hunyuan3D 2.1, whose licence excludes the EU, UK and South
Korea. The textured model, and any sprite rendered from it, is a result of that
model, even though TRELLIS made the shape. If the asset will ship in any of those
regions, skip this step and use `output/mesh/golem.glb` wherever a later step
says `golem_textured.glb`. See [licensing](/guide/licensing).
:::

```sh
scripts/run_workflow.py workflows/api/mesh_texture_hunyuan3d21.json \
    --image output/concept/golem_00001_.png \
    --set "mesh_path=/app/output/mesh/golem.glb" \
    --set "TexGen Pipeline.max_num_view=6" \
    --set "TexGen Pipeline.resolution=512" \
    --set "save_path=mesh/golem_textured.glb"
```

The concept image goes in again here. The texture stage paints the model to match
the drawing, so it needs the drawing.

`save_path` names the result `output/mesh/golem_textured.glb`, which is what the
next steps use. Leave it out and the graph saves under a timestamp instead,
`output/mesh/textured_<date and time>.glb`.

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
    --out output/sheets/golem_walk.png --check
```

Angles run across, animation frames run down. That is the order most engines
expect when slicing a sheet.

`--check` exits non-zero on a fault it can measure, such as a pose row identical
to the first row at every angle, which means the pose did nothing. It also names
the cell where the figure faces down and to the right, which is where your
game's facing mapping starts.

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

The batch script builds each shape with Hunyuan3D (`img2mesh_hunyuan3d21.json`),
not TRELLIS, and textures it with Hunyuan3D too. So everything it makes carries
the EU, UK and South Korea exclusion. See [licensing](/guide/licensing).

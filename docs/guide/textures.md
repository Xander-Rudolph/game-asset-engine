# Textures

A generated shape has no colour. Texturing paints it, using the concept image as
the reference.

::: warning This stage runs Hunyuan3D
The texture graph runs Hunyuan3D 2.1, whose licence excludes the EU, UK and South
Korea. The textured model, and any sprite rendered from it, is a result of that
model, whichever generator made the shape. If the asset will ship in any of
those regions, leave it untextured. See [licensing](/guide/licensing).
:::

```sh
scripts/run_workflow.py workflows/api/mesh_texture_hunyuan3d21.json \
    --image output/concept/golem_00001_.png \
    --set "mesh_path=/app/output/mesh/golem.glb" \
    --set "TexGen Pipeline.max_num_view=6" \
    --set "TexGen Pipeline.resolution=512" \
    --set "save_path=mesh/golem_textured.glb"
```

You pass the concept image again. The texture stage renders the model from
several angles, paints each view to match the concept, and projects the painted
views back onto the surface. It needs the concept image to know what to paint.

## Settings that matter

| Setting | Default here | What it does |
|---|---|---|
| `max_num_view` | 6 | How many angles are painted and projected back |
| `resolution` | 512 | Size of each painted view |

More views cover more surface but take longer and can conflict where they
overlap. Six is a working compromise for a character. Tall thin subjects benefit
from more views. Compact ones do not.

Higher resolution has limits too. The final map is limited by what each view can
see. Doubling resolution when each view covers only a third of the surface won't
double the useful detail.

On a 16GB card, six views at 512 is what fits. Eight views at 768 ran out of
memory.

## What comes out

You get a textured `.glb` and a set of maps. The maps are colour, metal and
roughness. The `.glb` goes where `save_path` says. Leave that out and it gets a
timestamped name, `output/mesh/textured_<date and time>.glb`.

::: danger Copy the maps out before the next asset
The texture stage always writes its maps to the same fixed paths. Generate a
second asset and the first one's maps are overwritten. There is no warning and
no counter in the filename.

`scripts/asset_to_mesh.sh` copies them into `output/textures/<name>/` after every
run, which is the main reason to use it rather than calling the workflow directly
for more than one asset.
:::

## Texturing changes the mesh

A shape generated at 18,000 faces comes back from the texture stage at around
40,000. The texture stage rebuilds the geometry to lay out UVs.

Two consequences:

- **Decimate after texturing, not before.** The face count in your shape workflow
  is not the count you end up with.
- **The rig should be built from the textured mesh** if you want the rig and the
  texture on the same geometry.

## Memory, and why texture runs are batched separately

The texture model stays in GPU memory after it runs, about 5GB. Asking ComfyUI
to free memory does not release it, because the node pack keeps its models in
its own cache, outside ComfyUI's control.

The next asset's shape stage then crashes inside its loader with
`torch.OutOfMemoryError: Allocation on device`. It looks like a broken workflow.
It's not.

The fix is the order you run things in, not a setting: restart the container,
run all shapes, restart again, run all textures. `asset_to_mesh.sh` does this
automatically. Don't mix the stages in your own scripts.

**On a shared server, run `curl -s http://127.0.0.1:8188/queue` before any
restart.** A restart ends every running and queued job on the server, not only
yours. `asset_to_mesh.sh` checks that queue before each of its restarts and
stops if anything is running or pending, unless `ASSET_ENGINE_FORCE_RESTART=1`
is set.

## Grey means untextured, not broken

The render tools give an untextured mesh a mid-grey clay material. Blender's
default material is white, and white against a white world light renders as a
featureless blob. So grey is on purpose. It means "not textured yet", not
"texture failed".

Force clay on a textured mesh with `--clay` when you want to judge shape without
colour distracting you. It is the honest way to check a silhouette.

## Judging a texture

Render it from several angles and look at the seams:

```sh
scripts/render_sheet.py output/mesh/golem_textured.glb --angles 8 --size 340
```

What goes wrong, in order of frequency:

1. **The back is invented.** The concept image only showed the front. If the back
   matters, generate a back view concept and use a multi view workflow.
2. **Seams where views disagree.** Two painted views met and did not match. More
   views sometimes helps, and sometimes makes it worse by adding more meetings.
3. **Texture sliding on a decimated model.** The UVs survived decimation but the
   triangles under them moved. Covered with measurements in
   [decimation](/guide/decimation).
4. **Flat lighting baked into the colour.** If your engine lights the model
   itself, painted shadows fight the engine's lighting. Ask for even lighting in
   the concept prompt.

## Texture maps as separate files

Export as `.obj` instead of `.glb` and you get the maps as editable PNGs
alongside, wired up in a `.mtl` file:

```
golem.obj
golem.mtl
golem_albedo.png
golem_metallic.png
golem_roughness.png
```

Keep them together. The `.obj` references the `.mtl` by relative name, so moving
one file quietly breaks it. And remember `.obj` cannot carry a skeleton, so it is
an input to rigging and never an output of it.

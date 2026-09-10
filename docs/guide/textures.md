# Textures

A generated shape has no colour. Texturing paints it, using the concept image as
the reference.

```sh
scripts/run_workflow.py workflows/api/mesh_texture_hunyuan3d21.json \
    --image output/concept/golem_00001_.png \
    --set "mesh_path=/app/output/mesh/golem.glb" \
    --set "TexGen Pipeline.max_num_view=6" \
    --set "TexGen Pipeline.resolution=512"
```

The concept image goes in a second time here. The texture stage renders the model
from several angles, paints each view to match the drawing, and projects the
result back onto the surface. Without the drawing it has nothing to match.

## Settings that matter

| Setting | Default here | What it does |
|---|---|---|
| `max_num_view` | 6 | How many angles are painted and projected back |
| `resolution` | 512 | Size of each painted view |

More views cover more of the model but take longer and can disagree with each
other where they overlap. Six is a working compromise for a character. A tall
thin subject benefits from more; a compact one does not.

Higher resolution is not free either. The map you end up with is limited by how
much of the model each view covers, so doubling the view resolution on a model
where each view sees a third of the surface does not double the useful detail.

## What comes out

You get a textured `.glb` and a set of maps. The maps are colour, metal and
roughness.

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

The texture model stays resident in GPU memory after it runs. About 5GB, and a
request to free memory does not release it, because the node pack keeps its
pipelines in its own cache outside ComfyUI's model management.

So the next asset's shape stage dies with an out of memory error inside its
loader. It looks like a broken workflow. It is not.

The fix is ordering, not tuning: restart, run every shape, restart, run every
texture. That is what `asset_to_mesh.sh` does. Never interleave the two stages in
your own scripts.

## Untextured is grey, and that is on purpose

When a mesh has no texture, the render tools give it a mid grey clay material.
Blender's default is white, and white against a white world light renders as a
featureless blob with no readable form.

So grey means "not textured yet". It does not mean the texture failed.

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

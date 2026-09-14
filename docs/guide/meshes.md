# Turning art into a mesh

One image goes in, geometry comes out. The generator guesses the sides and back
from the front view, which is why the concept art matters so much.

## Which generator

| Workflow | Generator | Notes |
|---|---|---|
| `img2mesh_trellis.json` | TRELLIS | MIT, no territory clause, so the choice for shipping into the EU, UK or South Korea. Removes the background itself, so no cut-out needed. [Details](/guide/trellis). |
| `img2mesh_hunyuan3d21.json` | Hunyuan3D 2.1 | Best geometry here. Removes the background itself. Cannot ship to the EU, UK or South Korea. |
| `mesh_texture_hunyuan3d21.json` | Hunyuan3D 2.1 | Paints an existing shape. Same licence limit, and it covers any shape it paints, a TRELLIS one included. |
| `txt2mesh_qwen_hunyuan3d21.json` | Qwen-Image, then Hunyuan3D 2.1 | Prompt to concept to mesh in one queue. Same licence limit. |
| `img2mesh_triposg.json` | TripoSG | Does not currently produce usable meshes in this install. It returns a cage of fragments instead of the subject, whatever the input. MIT upstream, but the copy in this pack ships a territory-limited licence file. See [licensing](/guide/licensing). |
| `img2mesh_triposr.json` | TripoSR | Does not work as wired, going by the node source (not run). The mask it takes from `LoadImage` is inverted, so a cut-out's subject is greyed out, and an image with no transparency fails. It would need an `InvertMask` added, plus a cut-out. [The same trap on the TRELLIS page](/guide/trellis#plain-trellis-weights-present-wiring-awkward). |

::: danger Decide the generator before the asset ships, not after
Hunyuan3D produces the best meshes in this stack, and its licence does not apply
in the EU, UK or South Korea. A storefront that sells worldwide reaches all
three. Rendering the mesh to a 2D sprite does not get around it either, because
the licence covers results of the output.

This is why concept images are kept rather than thrown away. Regenerating a mesh
through TRELLIS from the same concept image is the fix, and it is only possible
if the image still exists. Record which generator made which shipped asset.
[Full detail](/guide/licensing).
:::

## Watertight versus multi-part

Two types of mesh behave very differently when you decimate them (cut their
face count) or rig them.

**Generated meshes have one main shell.** Hunyuan3D and TRELLIS put almost all
the faces into one piece, sometimes with a few tiny loose pieces beside it. The
creature measured in [decimation](/guide/decimation#a-generated-mesh-measured)
has 99% of its faces in its main shell and only a handful of open edges
(boundary edges). Meshes like this decimate smoothly, rig without surprises, and
can be cut down a long way.

**Scanned or assembled meshes are multi-part.** Body, clothes, eyes and hair are
whole separate parts, each with its own open edges. They refuse to decimate
below a floor set by those boundaries. See
[decimation](/guide/decimation#where-it-stops-working-the-floor) for details.

If you didn't generate the mesh here, assume it is multi-part until you have
counted the pieces.

## Face budgets

Every image to mesh graph ends with a decimation step at 18,000 faces, then
saves. Change it per run:

```sh
scripts/run_workflow.py workflows/api/img2mesh_trellis.json \
    --image concept.png --set target=12000
```

18,000 is chosen to sit under the rigger's own budget, which is 48,000. The
rigger decimates anything above its budget before solving, and hands back the
decimated mesh rather than yours. Staying under it means your geometry passes
through untouched. See
[rigging](/guide/rigging#the-decimate-then-rig-shortcut).

Bear in mind the texture stage rebuilds the mesh and typically returns about
40,000 faces, so the number in the shape workflow is not the number you finish
with.

For what a budget costs in visible quality, with measurements, see
[decimation](/guide/decimation).

## File formats

`Save 3D Mesh` picks the format from the extension you give it. Anything else is
refused with a message rather than guessed at.

| | `.glb` | `.obj` | `.ply` |
|---|---|---|---|
| Geometry and UVs | yes | yes | geometry only |
| Textures | embedded in one file | sidecar `.mtl` plus PNGs | dropped, with a warning |
| Vertex colours | yes | non standard extension | no |
| Skeleton and skinning | yes | no | no |
| Files per asset | 1 | 4 or 5 | 1 |

Use `.glb` unless you have a reason not to. It is one self contained file and the
only one of the three that can carry a rig.

Use `.obj` when a tool downstream wants it, or when you want the texture maps as
separate editable PNGs. It cannot carry a skeleton, so it is an input to rigging
and never an output of it.

Use `.ply` only for raw geometry. It discards textures, and it warns rather than
failing, so it is easy to lose work with.

::: tip OBJ writes a whole material set
Alongside `golem.obj` you get `golem.mtl`, and when the mesh has texture maps you
also get `golem_albedo.png`, `golem_metallic.png` and `golem_roughness.png`,
wired up in the `.mtl`. Keep those files together. The `.obj` references the
`.mtl` by relative name, so moving one file breaks it.
:::

## Memory, and why batches are staged

The 3D node pack keeps its pipelines in its own cache, outside ComfyUI's model
management. A request to free memory does not release them, and about 5GB stays
pinned.

So after a texture run, the texture model is still resident, and the next asset's
shape stage dies with an out of memory error inside its loader. It looks like a
broken workflow. It is not.

`scripts/asset_to_mesh.sh` handles this by restarting the container once, running
every shape, restarting again, then running every texture. Two restarts for a
whole batch instead of one per asset, and each heavy model loads exactly once.

If you write your own batch loop, copy that shape. Do not interleave the stages.

## Checking a mesh

Render four views and look at them:

```sh
scripts/render_sheet.py output/mesh/golem.glb --angles 4 --size 340
```

An untextured mesh is given a grey clay material automatically. Blender's default
white against a white world light renders as a featureless blob, so grey is what
makes form readable. If you see grey, the mesh has not been textured yet. That is
not a bug.

What to look for, in order of how often it goes wrong:

1. **The back.** The generator invented it. Check it is not a smear.
2. **Limbs fused to the body.** Common when the concept art had an arm against a
   torso. It cannot be fixed later. Reroll the concept with the arm clear of the
   body.
3. **Thin parts.** Straps, staffs and horns come out either thick and clumsy or
   broken. If the asset depends on one, say so in the concept prompt and make it
   larger than realistic.
4. **The silhouette at size.** Render at the size your game draws the asset,
   such as 128 pixels. Detail invisible there is detail you are paying for and
   not getting.

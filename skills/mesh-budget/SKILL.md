---
name: mesh-budget
description: Choose a face count for a model, decimate it without wrecking it, and rig a high resolution mesh. Use when the user asks how many faces or polygons an asset should have, why a model looks wrong after simplifying, why decimation is not reaching the target, or how to rig a heavy or scanned mesh.
---

# Face budgets, decimation and rigging heavy meshes

Work in the asset-engine repo root.

## Before you start

```sh
scripts/doctor.py --skip-models
```

Everything here runs Blender inside the container, so the `blender` line in that
output has to be ok. If it is not, the failures look like broken models rather
than a missing dependency.

## Measure, do not guess

There is a tool for this. Run it before recommending a budget, because the answer
differs per model:

```sh
scripts/decimation_report.py output/mesh/<name>.glb --sprite 128
```

It reports three kinds of damage at each budget, and they do not arrive together:

- **surface**: how far the surface moved, as a percentage of model height. Read
  the p95. The max is one spike on one spur.
- **silhouette**: overlap of the rendered outline against the full resolution
  render, at the size the asset is actually seen. For a 2D game this is the
  number that matters.
- **texture**: mean colour difference inside the shared outline, 0 to 255.

Pass `--sprite` at the size the game actually uses. A budget judged at 340 pixels
and shipped at 128 wastes geometry.

## What the numbers usually say

Measured on a watertight generated creature, 39,956 faces:

| Faces | Silhouette | Outline lost | Texture |
|---:|---:|---:|---:|
| 20,000 | 0.9945 | 0.1% | 1.0 |
| 12,000 | 0.9851 | 0.7% | 2.1 |
| 8,000 | 0.9644 | 2.0% | 3.2 |
| 4,000 | 0.9558 | 3.0% | 4.5 |
| 2,000 | 0.9443 | 3.9% | 6.0 |
| 1,000 | 0.8829 | 8.5% | 9.1 |
| 500 | 0.7584 | 22.4% | 13.1 |

Read three things out of that:

- **Halving a generated mesh is free.** Do not agonise over it.
- **Texture damage arrives before outline damage.** At 12,000 the outline has
  lost 0.7% while the texture already differs by 2.1 levels. A heavily decimated
  model can look right in silhouette and wrong when textured, because the UVs
  survive but the triangles under them move.
- **Below about 2,000 faces it falls off a cliff**, not a slope. 3.9% to 8.5% to
  22% in two halvings.

Starting points, still worth measuring:

| Budget | For |
|---:|---|
| 18,000 | The pipeline default, and safely under the rigger's ceiling |
| 10,000 to 12,000 | A figure baked into a game as a model |
| 4,000 to 6,000 | A model only ever seen as a 128 pixel sprite |

**Large flat panels collapse first.** A cloaked or coated figure is mostly large
flat panels, so it suffers at budgets a detailed creature survives.

## When decimation refuses to reach the target

Check the produced count, not the requested one. On a 642,547 face multi part
model, every budget below 7,771 came back as 7,771. No error, no warning.

The cause is boundary edges. Collapse decimation will not collapse an edge on the
border of a surface, and a model made of separate pieces is full of borders:
every shell, every place clothing meets skin, every eye socket.

Tell the user which of these applies:

- **Decimate the pieces separately** and keep them separate, if the engine takes
  multiple objects.
- **Weld the shells first** if they should be one surface, then decimate.
- **Rebuild it as one watertight surface**, by remeshing or by putting it back
  through image to 3D. Generated meshes have almost no boundary edges, which is
  why they reach 500 faces without complaining.

There is a second signal in that data worth repeating: the surface error stopped
improving at 8,000 faces while the silhouette kept getting worse. That is thin
parts being deleted rather than displaced. Averaged surface error cannot see a
fringe disappear.

## Rigging a high resolution mesh

The rigger decimates before it solves, and this is what makes rigging a heavy
mesh possible at all. The solver has a fixed appetite; 600,000 faces is not slow,
it is impossible.

**The catch, and always say this out loud:** the FBX it hands back contains the
decimated mesh, not the original. The skinning stage writes out the vertices the
skeleton stage recorded, which are the decimated ones.

The budget is a **ceiling, not a target**:

| Input | Output |
|---|---|
| Under 48,000 faces | The same mesh, now with a skeleton. Verified: 39,996 in, 39,996 out with 47 bones. |
| Over 48,000 faces | A decimated copy, with a skeleton. The detail is gone. |

### Keeping the detail as well as the rig

```sh
scripts/transfer_weights.py output/rigged/<name>.fbx input/3d/<name>_full.glb \
    --out output/rigged/<name>_full.fbx
```

Verified on a real pair: a 47 bone skeleton solved on a 39,996 face proxy,
transferred onto a 642,547 face mesh with 394,992 vertices, zero vertices left
unweighted.

Two things make it work:

- **The meshes are aligned first.** The rigger normalises its output, centring
  and scaling into a unit box, so the original never sits on top of it. Skip the
  alignment and every weight is read from the wrong part of the body.
- **Weights are interpolated across the nearest face**, not snapped to the
  nearest vertex, which would quantise them to the proxy's sparse vertices and
  band the joints.

The script reports unweighted vertices. Above 1% means alignment failed, not that
the transfer is imprecise. An unweighted vertex does not move, which shows up as
part of the model staying behind mid stride.

**Say when it is not worth it.** If the asset is only ever a sprite, the proxy is
better in every way that matters. Smaller, faster, and identical at 128 pixels.

## Rules

- **Run the report before recommending a number.** The answer depends on the
  model and this takes seconds.
- **Always check the produced face count**, never assume the requested one was
  reached.
- **Decimate after texturing, not before.** The texture stage rebuilds the mesh
  and typically returns about 40,000 faces regardless of what you asked for
  earlier.
- **Use collapse decimation, which preserves UVs.** The plain quadric variant
  drops them and leaves the model flat grey, and it fails silently.

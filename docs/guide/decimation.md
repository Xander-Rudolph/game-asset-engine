# Face counts and decimation

Decimation means simplifying a mesh by removing triangles. The key question is
how many you can remove before it looks wrong. The answer depends on what you're
looking at.

This page uses measurements, not opinions. You can reproduce everything here.

## Get an answer

```sh
scripts/decimation_report.py output/mesh/golem.glb --target-iou 0.985 --sprite 128
```

Finds the lowest face count whose silhouette still holds at or above the
threshold, at the sprite size you actually use, and prints the answer:

```
  ANSWER: ship this at 3,184 faces (6.6% of the original), silhouette 0.9855 at 128px
```

Each probe decimates and renders the model once, then halves the range left to
search. Eight probes by default. 0.985 is a sensible starting threshold for a 2D
asset; raise it if the outline is doing more work than usual.

## Or measure the whole curve

```sh
scripts/decimation_report.py output/mesh/golem.glb --sweep --faces 20000,8000,4000
scripts/decimation_report.py input/3d/hero.glb --sprite 128 --json out.json
```

The sweep is worth running when you're learning about an asset class, not just
shipping one model. The full table shows the trade-offs. The sections below are
from actual sweep data.

It reports three kinds of changes at each face count. They don't all happen at
the same time:

- **Surface**: how far points moved, as a percentage of the model's height. Read
  the 95th percentile, not the max (which is one spike on a corner).
- **Silhouette**: how well the outline matches the full resolution render, at
  the size you actually use. It is the area both outlines share divided by the
  area either one covers (IoU), so it runs from 0 to 1 and 1 means identical.
  For 2D games this is the one that matters, because a sprite is just its
  outline. The "Outline lost" column is the part of the original outline that
  is gone.
- **Texture**: average colour difference inside the shared outline, on a scale
  of 0 to 255. UVs stay in place, but the triangles beneath them move. Texture
  problems appear before outline problems.

The camera is isometric, so you're seeing the angle your game will use, not a
flattering three-quarter view.

## A generated mesh, measured

A textured creature straight out of the pipeline: 39,956 faces. It is one main
shell holding 99% of the faces, plus 29 tiny loose pieces of 46 faces or fewer
and a handful of open edges. Silhouette measured at 128 pixels.

| Faces | Of original | Surface p95 | Silhouette | Outline lost | Texture |
|---:|---:|---:|---:|---:|---:|
| 30,000 | 75% | 0.028% | 0.9992 | 0.0% | 0.4 |
| 20,000 | 50% | 0.070% | 0.9945 | 0.1% | 1.0 |
| 12,000 | 30% | 0.190% | 0.9851 | 0.7% | 2.1 |
| 8,000 | 20% | 0.399% | 0.9644 | 2.0% | 3.2 |
| 6,000 | 15% | 0.553% | 0.9549 | 2.3% | 3.9 |
| 4,000 | 10% | 0.755% | 0.9558 | 3.0% | 4.5 |
| 2,000 | 5% | 1.165% | 0.9443 | 3.9% | 6.0 |
| 1,000 | 2.5% | 1.666% | 0.8829 | 8.5% | 9.1 |
| 500 | 1.3% | 2.093% | 0.7584 | 22.4% | 13.1 |

### Where the trade offs start

**Down to 50% is free.** Surface movement is under a tenth of a percent of the
model's height and the outline is essentially identical. If you are cutting a
generated mesh in half, stop worrying about it.

**30% is the working point.** 12,000 faces from 40,000 costs 0.7% of the
outline. Nothing you will see at sprite size. This is where the pipeline's 18,000
default sits for a bigger mesh, and it is a good place to be.

**20% is the first real step.** At 8,000 faces the outline loses 2% and the
texture difference doubles. Visible if you flick between the two. Acceptable
alone.

**Below 5% it falls apart quickly.** From 2,000 to 1,000 faces the outline loss
jumps from 3.9% to 8.5%, and from there to 500 it more than doubles again to
22%. That is not a gentle slope, it is a cliff. If a budget forces you under
about 2,000 faces for a character sized subject, the answer is a different
approach rather than more decimation.

**Texture damage arrives before outline damage.** Look at the two columns
together. At 12,000 faces the outline has lost 0.7% but the texture already
differs by 2.1 levels. By 4,000 the outline is still 95% intact while the texture
is off by 4.5. This is why a heavily decimated model can look fine in silhouette
and wrong when textured: the UVs are still there, but the triangles they are
painted across have moved.

## Where it stops working: the floor

Now the same test on a 642,547 face multi-part model, the kind you get from a
scan or an asset store. Seven separate objects, joined.

| Faces asked for | Faces produced | Surface p95 | Silhouette | Outline lost |
|---:|---:|---:|---:|---:|
| 200,000 | 199,999 | 0.004% | 0.9992 | 0.0% |
| 100,000 | 100,000 | 0.015% | 0.9981 | 0.1% |
| 50,000 | 50,000 | 0.051% | 0.9950 | 0.2% |
| 25,000 | 25,000 | 0.101% | 0.9895 | 0.5% |
| 18,000 | 18,000 | 0.126% | 0.9845 | 0.9% |
| 12,000 | 11,999 | 0.165% | 0.9768 | 1.8% |
| 8,000 | 8,000 | 0.206% | 0.9303 | 6.5% |
| 4,000 | **7,771** | 0.206% | 0.9090 | 8.3% |
| 2,000 | **7,771** | 0.206% | 0.9090 | 8.3% |
| 1,000 | **7,771** | 0.206% | 0.9090 | 8.3% |

::: warning A budget below the floor is silently ignored
Ask for 1,000 faces and you get 7,771. No error, no warning. The ratio is
applied and the modifier simply cannot reach the target.

The cause is boundary edges. Collapse decimation will not collapse an edge that
sits on the border of a surface, and a model made of separate pieces is full of
borders: every shell edge, every place where clothing meets skin, every eye
socket. Once every remaining edge is a boundary, decimation stops.

If your face counts are not landing where you asked, this is why. Check the
produced column, not the requested one.
:::

There is a second thing hiding in that table. Notice the surface error stops
improving at 8,000 faces, but the silhouette keeps getting worse: 6.5% lost at
8,000 and 8.3% at the floor. The surface barely moved, yet the outline broke.
That is thin parts being deleted rather than displaced. Averaged surface error
cannot see a fringe disappear, which is exactly why the silhouette is measured
separately.

### What to do about a floor

- **Decimate the pieces separately** and keep them separate, if the engine can
  take multiple objects.
- **Weld the shells together first** if they should be one surface. Merge by
  distance, then decimate.
- **Rebuild it as a single watertight surface**, either by remeshing or by
  putting the model back through image to 3D. Generated meshes have almost no
  boundary edges, which is why they decimate to 500 faces without complaining.

## Budgets in this pipeline

| Budget | Where it is used | Why |
|---:|---|---|
| 50,000 | The rigger's own default | Its upstream default. This repo lowers it. |
| 18,000 | Every image to mesh graph, and the rigging step | So the skeleton is solved against the mesh that was saved |
| 10,000 to 12,000 | Figures baked into a game as models | The measured floor for large flat panels |
| 4,000 to 6,000 | A model only ever seen as a 128 pixel sprite | Everything above this is thrown away before a pixel is drawn |

The 10,000 to 12,000 figure has a specific cause worth repeating: **large flat
panels collapse first**. A coated or cloaked figure is mostly large flat panels,
so it is exactly the case that suffers. A creature with lots of small curved
detail survives lower budgets better than a person in a long coat.

## Always decimate with texture preserved

If you decimate outside this repo, use quadric edge collapse **with texture
coordinates**. The plain variant drops UVs, which leaves the texture unusable and
the model flat grey. In Blender that is the Collapse modifier, which keeps UVs.
In MeshLab it is the "with texture" variant of quadric edge collapse, and picking
the wrong one is a silent failure.

## Texturing undoes your decimation

Worth knowing before you plan a budget. A shape generated at 18,000 faces comes
back from the texture stage at around 40,000. The texture stage rebuilds the mesh
to lay out UVs.

So decimate **after** texturing, not before, or do both and check the count. The
number in the shape workflow is not the number you end up with.

# Ground relief and blending

*The long version. If you only need to generate a ground texture and make it
repeat, [ground and terrain](/guide/terrain) is the shorter path.*

## Making a tiling texture, and laying it on terrain that bends

Two jobs that look like one and are not. The first is generation — getting a
square of photographic ground out of a diffusion model that repeats without a
seam and reads at the right scale. The second is the **relief engine**: the
arithmetic that decides where a tile's ground sits, how one terrain hands over
to the next, and how the edge of the known world fades out.

Everything below was paid for. Each heading is a thing that was tried, measured
and found wrong before it was found right.

---

## Part 1 — Generating ground that tiles

### No node in a stock ComfyUI install makes a tiling texture

There is no circular-padding VAE decode and no tiled sampler in the four packs
this image ships. So the seam is dealt with *afterwards*, in
`scripts/make_seamless.py`, and every trick below is post-processing.

### Rolling the image by half does nothing

It is the first thing everyone reaches for and it is a **phase shift**. Whether
the right-hand column continues into the left-hand one is not something a shift
can change. Measured, it took an 81% seam to 78%.

Rolling by half *is* worth doing, for a different reason: the first and last
rows of a rolled image were *adjacent* rows in the original, so the outer edges
come out continuous by construction. What the roll does is move the one real
discontinuity into the **middle** of the tile, where it can be mended without
touching the edges that have to match.

An early version then blended the rolled image back toward the unrolled one,
which put that discontinuity straight back on the edge. It measured as doing
nothing, because it did nothing.

### Mirroring the seam scores 0.98 and looks terrible

Reflecting the strip about the seam makes the two sides identical, so the
metric is delighted. The tile grows a **butterfly through its middle** and a
field of it reads as kaleidoscope wallpaper.

What works instead: near the seam, take pixels from **half a tile away**. They
are unrelated content but the same texture, and crucially they are *continuous
with each other* — `a[x + w/2]` and `a[x+1 + w/2]` are neighbours — so the
discontinuity is replaced by ordinary ground. Weighted to 1 at the seam and 0 at
the band's edges, the join reads as variation.

This is the single strongest argument in this document for **looking at the
picture**. A number said 0.98 and the texture was unusable.

### The seam metric has to be told what "bad" means

The first metric divided edge difference by the image's own contrast and scored
an already-perfect texture at 81%: two adjacent columns of any organic texture
differ by a good fraction of its standard deviation, so good and bad both looked
bad.

The honest question is whether the first and last columns differ by about as
much as **any other adjacent pair** — they are neighbours when the tile repeats.
1.0 is seamless.

**And the ratio lies on smooth textures.** Water scores 2.06 by the ratio while
its edges differ by 2.1 levels out of 255, which no eye will ever see: when
neighbouring pixels barely differ, dividing by that turns a nothing into a
problem. Acting on the ratio alone, the tool "repaired" that texture into a
worse one. Report the **absolute** difference too, and only complain when both
tests fail.

### The generator paints a mat around your texture

Asked for a full-bleed surface, the model sometimes returns a *picture* of one:
a smaller square inset on a white ground. Every edge is then the same flat
colour, and tiling it lays a bright lattice across the map — which looks like a
seam bug and is not one.

Told not to draw a border in the negative prompt, it drew one anyway. **The
prompt is not where this gets fixed.** A mat is recognisable without knowing its
colour: a row of it has almost no variance where any row of real ground has
plenty. Walk in from each edge while the rows stay flat, then trim a few pixels
more, because the mat's inner edge is feathered by the JPEG.

Seen in practice: 227 pixels of white around a water texture.

### Texture scale is set by how big the things IN it should look

This is the constant that matters most and the one that is easiest to reason
about wrongly. The temptation is to maximise texel density — pick the repeat
that maps one texel to one screen pixel. That argument gives a large repeat, and
a large repeat is also *less* obviously repeating, because the pattern's period
is longer.

Both are true and both lose to the third consideration: **a repeat spanning
eight tiles put a leaf twenty-five screen pixels across, against a person of
about thirty-four.** Leaves the size of a soldier, gravel the size of a shield.
Four tiles to a repeat puts a leaf at nine pixels, which is the scale the map is
pretending to be at.

Pay for the texel density with resolution instead — the materials are 1024px,
not 512 — and let the *subject scale* pick the repeat.

### Measure the texture, do not trust the thumbnail

A desert material shipped looking fine and read as flat colour on the live
build. Measured across the set, the grey-channel spread told the whole story:

| | desert | tundra | the other seven |
|---|---|---|---|
| std | **3.0** | **3.7** | 12.4 – 33.1 |

Seventeen grey levels. Nothing was broken — it was a truthful photograph of very
even sand. `--check` now prints contrast alongside the seam score and warns
below a floor, because a texture that even reads as a painted rectangle at map
scale.

### The command

```sh
scripts/run_workflow.py workflows/api/txt2img_qwen.json \
    --prompt "$(cat prompts/ground/plains.txt)" \
    --negative "$(cat prompts/ground/_negative.txt)" \
    --set width=1328 --set height=1328 \
    --set Save.filename_prefix=ground/plains

scripts/make_seamless.py output/ground/plains_00001_.png \
    --out assets/materials/plains.jpg --check
```

Wants a seam score of 1.0–1.2 and a contrast std in the low teens or above.

---

## Part 2 — The relief engine

Generation gets you one square of ground. Laying it across terrain that rises,
falls and changes country is a separate problem, and it is arithmetic rather
than art.

### A seam is a shared NUMBER, not a shared shape

This is the whole design, and it is worth stating before the alternative,
because the alternative is what everyone proposes first.

**The obvious idea is a tileset**: generate edge and corner meshes for each
terrain and stamp the right one per tile. It cannot work, for four reasons in
increasing order of how fatal they are:

1. It multiplies — 9 terrains × 16 edge configurations × N heights.
2. A generated mesh's boundary vertices are **wherever the generator put them**,
   so a set whose seams meet exactly has to be hand-welded, not generated.
3. If meshes are baked to fixed-resolution sprites (which they are, in any
   engine that blits rather than rasterising per frame), they blur at high zoom
   and alias at low.
4. **A baked sprite carries no normal**, so it can never take the scene's light.
   It sits next to vertex-lit ground under a different sun forever.

What works instead: give every grid **corner** one height that all four tiles
touching it agree on. The surfaces then meet exactly — no tolerance, no fitting,
no tileset — because both tiles computed the *same number*.

### Deriving the corner value: two rules, both got wrong first

Sort the heights of the tiles meeting at a corner. Cut the list where
consecutive values are more than a `taper` apart. Take the mean of the run your
own height falls in. **Then clamp that to within one taper of your own height.**

- **Cutting on the gap alone is single-linkage clustering, and single linkage
  chains.** `[0,1,2,3]` has no gap above one, so the whole staircase fuses to a
  mean of 1.5 and a tile the rules put at zero draws its corner three half-steps
  in the air. The clamp is not a safety net over this — it is the mechanism that
  bounds it.
- **Cutting on the run's own span was the planned fix and is worse.** It splits
  `[0,1,2,2]` into `{0,1}` and `{2,2}`, so two tiles *one walkable step apart*
  get a ledge two and a half steps tall drawn between them — on exactly the
  graded ramp the taper exists to smooth. A test written before any of it was
  drawn caught this.

The residual property is honest and worth writing down: where two tiles land on
different values, a **flank** is drawn between them built from both numbers, so
the ground is closed whether it fused or not. You do not need every pair to
agree; you need every disagreement to be filled.

### Pick the taper below the smallest step you want to keep visible

The tempting value is the game's own climb allowance, so a wall is drawn exactly
where a step is illegal. That is a beautiful invariant and it was wrong here: a
full-height step is *legal and costs an extra move point*, and fusing it turned
the terraced battlefield into a featureless ramp and hid what the player was
paying.

One half-step. Hills and swells flow; terraces and craters keep their steps; a
mesa's face and a crag stay sheer.

### Height must not be excused where terrain is

The generator guarded relief with "keep clear of anything built here", which is
correct for the pass that changes the **country** — painting rock over a capital
moves where things may stand. Applying the same guard to the **height** leaves a
hold in the middle of a ridge sitting at sea level with its neighbours five
half-steps up, and the taper reads that, correctly, as a cliff.

Ranges came out with quarries cut through them. Height is decoration: nothing
paths by it, nothing is placed by it, and a building drawn on a slope sits on
its own ground patch anyway.

### A few broad ranges on a level plain still draws a flat map

A range that falls away a half-step a tile is a slope of about five degrees.
Between the ranges there was nothing at all for the eye to find, and the map
read as flat despite being full of relief.

**Density is where "flowing" comes from.** One low swell per fifteen tiles,
none tall enough to change the terrain type, is country that rolls. One per
ninety is a billiard table with hills on it.

### Shading a real slope honestly is invisible

Measured: six pixels of lift across a sixty-four pixel tile shades a tile by
**four per cent**. The first build looked completely flat — the ground was
rising correctly and nothing on screen said so.

Light slopes at ~3× their true steepness. That is a deliberate lie and the
picture needs it: sixteen per cent reads as a hillside and not as a cliff. It
touches slopes only — a vertical flank takes a fixed horizontal normal, so
exaggerating the height unit cannot darken a wall.

### `BlendMode.modulate` cannot brighten

It multiplies, and the vertex colour clamps at white. So **anchor the lighting
at flat ground**: if flat is anchored anywhere below 1.0, every flat tile in the
game comes out darker than it was. At a figure renderer's own gain that is 6%,
which reads as "the map went muddy".

Anchored at flat, only slopes and walls darken and the change is strictly
additive. The cost is that a slope tilted *into* the light cannot brighten past
flat — on ground, where every normal is within a few degrees of up, that half of
the range was never worth much.

### `drawVertices` and the paint colour

The API is documented as blending the paint's colour with the vertices'. With
**no shader on the paint**, at least one backend takes the vertex colour alone.
A white vertex modulated against a dark paint came out white, and the first
build of a fog gradient produced a bank of fog the colour of milk.

**Put the colour on the geometry** and leave the paint plain white. That is
right whichever way the backend reads it.

### Reuse the scene's existing lamp

Terrain that computes its own light direction will disagree with everything
standing on it. Worse, two maps that each hand-tune their own will disagree with
*each other* — this codebase had the same two walls lit from opposite sides on
the world map and the battlefield, so marching onto a field flipped the sun.

Feed the same shading function the figures use. Then delete the hand-tuned
constants rather than re-tuning them.

---

## Part 3 — Blending one country into the next

### Fade to HALF at the shared edge, not to full

The natural first implementation fades the neighbour's material in across the
shared edge, opaque at the edge and gone at the far corners. The neighbour does
the same thing back. So at the boundary **each tile wears the other's
material**, and the line between them is not softened — it is *flipped*: forest
fading to water, a hard edge, then forest again fading to water.

At a half, both sides land on the same fifty-fifty mix along the edge they
share. That is what makes the handover continuous rather than merely gradual.

### Blend only the quarter of the tile nearest that edge

Fading across the whole tile leaves a quarter of the neighbour's ground sitting
on this tile's middle, so a single lake tints every field around it. One
triangle from the two shared-edge corners to the tile's centre is the region
that should blend, and it is also cheaper.

### Carry the alpha on the geometry

A `Paint` carries one shader, so fading a textured fill needs either a
`saveLayer` per edge — four per tile, hundreds per frame — or the alpha on the
vertices. `drawVertices` with `BlendMode.modulate` multiplies the texture by the
corner colours, alpha included, and costs one draw call.

### A blend cannot make an impossible boundary plausible

This is the part people skip. Worldgen scatters climates by noise, so it will
cheerfully lay a dune against a snowfield, and **no amount of fading one
material into the other makes that read as somewhere**. A blend softens a
boundary; it does not justify one.

Give terrains an adjacency rule — which may lie beside which — and have worldgen
lay a neutral bridge terrain between the pairs that cannot meet. Three notes
from doing it:

- **Which of the pair gives way should be the intruder**: the tile with fewer of
  its own kind in its eight neighbours. That erodes a speck of desert stranded
  in the tundra rather than chewing a notch out of the desert proper.
- **Run it again after any later pass that paints terrain.** Rock laid on the
  crown of a range does not care what it lands beside, so a ridge crossing a
  marsh put broken hills against swamp — the exact adjacency the first sweep
  exists to prevent.
- **The second sweep must leave alone anything that has been built on.** A hold
  sits on the country it was placed on, and a faction's seat carries home ground
  that is worth a bonus in every fight fought on it. Where two protected tiles
  disagree, let them.

### Fog is a gradient, not a cutoff

Fog of war drawn per tile ends at a tile boundary, so the frontier of the known
world is a staircase of hard diamonds and the map falls off it.

Use the same corner trick: a corner's fog is the mean of the four tiles touching
it, so one gradient is continuous across every shared edge by construction. Draw
the **real ground** under the fade, so a range dissolves rather than ending in a
cliff of nothing.

Keep the cheap path: where a tile is unseen *and* nothing touching it has been
seen either, there is nothing for the dark to fade into, so draw one flat
diamond. That is most of an unexplored map, so it still costs what it always
did.

---

## Part 4 — Testing ground you cannot look at

A seam a third of a pixel wide is invisible on a screenshot and a bright crack
at 3× zoom on somebody else's phone. The arrangements that open one are rare
enough that a hand-picked field will not contain any. So:

- **Sweep every corner of every tile over every generated shape.** Assert that
  two tiles sharing a corner either agree exactly, or that a flank is required
  and the drawn step is not inverted.
- **Assert the deviation bound** — a corner is never more than one taper from
  its own tile's height. This is the assertion that catches chaining, and it is
  what keeps figures off stilts.
- **Assert flat ground still costs two triangles.** Most ground is flat and it
  must not have got more expensive.
- **Write the test against the naive implementation first and watch it fail.** A
  green test that has never been red is a guess.

And for hit-testing raised ground, ask the right question. "Is the answer the
tile I aimed at" **cannot be asked** — ground in front is *allowed* to cover
ground behind, which is the whole reason the picker exists. Ask **"does the
answer explain the tap"**: dropping the point by the returned tile's own lift
must land on that tile. That question found two real bugs; the other found none.

Finally: **write a throwaway entrypoint that boots straight into the state you
need**, and delete it afterwards. Terrain worth looking at is usually somewhere
a fresh game will not show you — worldgen deliberately keeps relief away from a
starting position, and fog hides everything else. Fifteen lines that turn the
fog off and park the camera on the tallest ground in the seed is the difference
between measuring and squinting.

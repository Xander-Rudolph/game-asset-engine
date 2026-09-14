# Ground relief and blending

*This is the long version. If you only need a ground texture that tiles,
[Ground and terrain](/guide/terrain) is the shorter path.*

## Two separate jobs that look like one

The first job is generation: getting a diffusion model to give you a square of
ground that repeats with no visible seam and reads at the right scale. The
second is the **relief engine**: the maths that decides how high each tile's
ground sits, how one terrain hands over to the next, and how the shading over
unexplored ground fades out at its edge.

This repo covers the first job. The second belongs to your own map code (the
generator and the renderer), so Parts 2 to 4 describe what that code has to get
right. They come from a 2D tile map drawn as textured triangles, but most of the
lessons apply to any engine.

Everything below was tested and measured. Each section describes what failed and
what worked instead.

---

## Part 1: Generating ground that tiles

### Stock ComfyUI can't make tiling textures

ComfyUI and the four node packs this image ships have no circular-padding VAE
decode and no tiled sampler. So the seam is fixed after generation, in
`scripts/make_seamless.py`, and every trick below is post-processing.

### Rolling the image by half does nothing

Rolling shifts the image by half its width and height, wrapping round at the
edges. It is the first thing everyone tries, and it is only a **phase shift**:
it moves the break between the right-hand column and the left-hand one, but it
cannot remove it. Measured, it took an 81% seam to 78%. That was on the first
seam metric (see below), which scored even a seamless texture at 81%, so the
change tells you nothing.

Rolling is still worth doing, for a different reason. The first and last rows
of the rolled image sat next to each other in the original (and so did the first
and last columns), so its outer edges come out continuous. The one real break,
where the original's last row met its first, moves into the **middle** of the
tile. You can mend it there without touching the edges that have to match.

An early version then blended the rolled image back toward the original, which
put the seam straight back on the edge. It measured as doing nothing, because it
did nothing.

### Mirroring the seam scores 0.98 and looks terrible

Mirroring makes both sides match perfectly, so the seam metric says it's great.
But the tile gets a butterfly down the middle, and a field of them looks like
kaleidoscope wallpaper.

What works instead: near the seam, sample pixels from **half a tile away**. They
show different content but the same texture, and critically they're *continuous
with each other* (`a[x + w/2]` and `a[x+1 + w/2]` are neighbours), so the
discontinuity is replaced by ordinary ground. Weighted to 1 at the seam and 0 at
the band's edges, the join reads as variation.

**Look at the picture.** The seam metric said 0.98 and the texture was
unusable.

### The seam metric has to be told what "bad" means

The first metric divided edge difference by the image's own contrast and scored
an already-perfect texture at 81%: two adjacent columns of any organic texture
differ by a good fraction of its standard deviation, so good and bad both looked
bad.

The honest question is whether the first and last columns differ by about as
much as **any other adjacent pair**, since they are neighbours when the tile
repeats. 1.0 is seamless.

**And the ratio lies on smooth textures.** Water scores 2.06 by the ratio while
its edges differ by 2.1 levels out of 255, which no eye will ever see: when
neighbouring pixels barely differ, dividing by that turns a nothing into a
problem. Acting on the ratio alone, the tool "repaired" that texture into a
worse one. Report the **absolute** difference too, and only complain when both
tests fail.

### The generator paints a mat around your texture

Asked for a full-bleed surface, the model sometimes returns a *picture* of one:
a smaller square inset on a white ground. Every edge is then the same flat
colour, and tiling it lays a bright lattice across the map. That looks like a
seam bug and is not one.

Told not to draw a border in the negative prompt, it drew one anyway. **The
prompt is not where this gets fixed.** A mat is recognisable without knowing its
colour: a row of it has almost no variance where any row of real ground has
plenty. Walk in from each edge while the rows stay flat, then trim a few pixels
more, because the mat's inner edge is feathered by the JPEG.

Seen in practice: 227 pixels of white around a water texture.

### Texture scale is set by how big the things IN it should look

This is the constant that matters most and the one that is easiest to reason
about wrongly. The temptation is to maximise texel density: pick the repeat
that maps one texel to one screen pixel. That argument gives a large repeat, and
a large repeat is also *less* obviously repeating, because the pattern's period
is longer.

Both are true and both lose to the third consideration: **a repeat spanning
eight tiles put a leaf twenty-five screen pixels across, against a person of
about thirty-four.** Leaves the size of a soldier, gravel the size of a shield.
Four tiles to a repeat puts a leaf at nine pixels, which is the scale the map is
pretending to be at.

Pay for the texel density with resolution instead (the materials are 1024px,
not 512), and let the *subject scale* pick the repeat.

### Measure the texture, do not trust the thumbnail

A desert material shipped looking fine and read as flat colour on the live
build. Measured across the set, the grey-channel spread told the whole story:

| | desert | tundra | the other seven |
|---|---|---|---|
| std | **3.0** | **3.7** | 12.4 to 33.1 |

Seventeen grey levels. Nothing was broken. It was a truthful photograph of very
even sand. `make_seamless.py` now prints the contrast (the std) next to the
seam score on every run, and warns when it falls under 8, because a texture with
so little contrast reads as a painted rectangle at map scale.

### The command

```sh
scripts/run_workflow.py workflows/api/txt2img_qwen.json \
    --prompt "$(cat prompts/ground/plains.txt)" \
    --negative "$(cat prompts/ground/_negative.txt)" \
    --set width=1024 --set height=1024 \
    --set Save.filename_prefix=ground/plains

scripts/make_seamless.py output/ground/plains_00001_.png \
    --out output/materials/plains.jpg --size 1024 --check
```

Generate square. The Qwen graph's default size is a 3:4 portrait, and
`make_seamless.py` scales whatever it gets to a square of `--size` pixels (1024
by default), so a portrait would come out squashed. Every run prints the
contrast, the seam ratio and the absolute seam difference. `--check` adds the
ratio from before the fix, so you can see what the fix did.

Aim for a seam score of 1.0 to 1.2 and a contrast std in the low teens or above.

---

## Part 2: The relief engine

Generation gets you one square of ground. Laying it across terrain that rises,
falls and changes country is a separate problem, and it is arithmetic rather
than art.

### A seam is a shared NUMBER, not a shared shape

This is the core design principle.

**The obvious idea is a tileset**: generate edge and corner meshes for each
terrain and stamp the right one per tile. It cannot work, for four reasons in
increasing order of how fatal they are:

1. It multiplies: 9 terrains × 16 edge configurations × N heights.
2. A generated mesh's boundary vertices are **wherever the generator put them**,
   so a set whose seams meet exactly has to be hand-welded, not generated.
3. If meshes are baked to fixed-resolution sprites (which they are, in any
   engine that blits rather than rasterising per frame), they blur at high zoom
   and alias at low.
4. **A baked sprite carries no normal**, so it can never take the scene's light.
   It sits next to vertex-lit ground under a different sun forever.

What works instead: give every grid **corner** one height that all four tiles
touching it agree on. The surfaces then meet exactly (no tolerance, no fitting,
no tileset) because both tiles computed the *same number*.

### Deriving the corner value: two rules, both got wrong first

Sort the heights of the tiles meeting at a corner. Cut the list where
consecutive values are more than a `taper` apart. Take the mean of the run your
own height falls in. **Then clamp that to within one taper of your own height.**

- **Cutting on the gap alone is single-linkage clustering, and single linkage
  chains.** `[0,1,2,3]` has no gap above one, so the whole staircase fuses to a
  mean of 1.5 and a tile the rules put at zero draws its corner three half-steps
  in the air. The clamp is not a safety net over this. It is the mechanism that
  bounds it.
- **Cutting on the run's own span was the planned fix and is worse.** It splits
  `[0,1,2,2]` into `{0,1}` and `{2,2}`, so two tiles *one walkable step apart*
  get a ledge two and a half steps tall drawn between them, on exactly the
  graded ramp the taper exists to smooth. A test written before any of it was
  drawn caught this.

The residual property is honest and worth writing down: where two tiles land on
different values, a **flank** is drawn between them built from both numbers, so
the ground is closed whether it fused or not. You do not need every pair to
agree; you need every disagreement to be filled.

### Pick the taper by what the view is for

The taper was first set to one half-step, below the full-height step the
movement rules still allow at an extra cost. Fusing that step had turned
terraced ground into a featureless ramp and hidden the cost. On a map where
height is decoration, that is still right: hills and swells flow, terraces and
craters keep their steps, and a mesa's face and a crag stay sheer.

On a battlefield it read the other way. With a half-step taper every
full-height step was a sheer wall, the field looked like stacked boxes, and the
picture said "wall" about ground a soldier could walk up. Setting the
battlefield's taper to the largest step anyone on foot can climb (two
half-steps) drew every climbable rise as a slope and kept walls only where the
rules refuse the climb. A steeper slope still shades darker than a gentle one,
so the extra cost is not invisible.

So pick it per view. On a map that is read for its shape, set it below the
smallest step you want seen. On a board that is read for its rules, set it at
the climb limit.

### Height must not be excused where terrain is

The map generator guarded relief with "keep clear of anything built here". That
is correct for the pass that changes the **terrain type**: painting rock over a
town changes where things may stand. Applying the same guard to the **height**
leaves a building in the middle of a ridge sitting at sea level with its
neighbours five half-steps up, and the taper reads that, correctly, as a cliff.

Ranges came out with quarries cut through them. If nothing in your rules reads
height (no pathfinding and no placement use it), height is decoration: guard
only the terrain pass and let relief run under buildings. A building drawn on a
slope sits on its own ground patch anyway.

### A few broad ranges on a level plain still draws a flat map

A range that falls away a half-step a tile is a slope of about five degrees.
Between the ranges there was nothing at all for the eye to find, and the map
read as flat despite being full of relief.

**Density is where "flowing" comes from.** One low swell per fifteen tiles,
none tall enough to change the terrain type, is country that rolls. One per
ninety is a billiard table with hills on it.

### Shading a real slope honestly is invisible

Measured: six pixels of lift across a sixty-four pixel tile shades a tile by
**four per cent**. The first build looked completely flat. The ground was
rising correctly and nothing on screen said so.

Light slopes at about 3× their true steepness. That is a deliberate lie, and the
picture needs it: shading a tile by sixteen per cent reads as a hillside and not
as a cliff. It touches slopes only. A vertical flank takes a fixed horizontal
normal, so exaggerating the height unit cannot darken a wall.

### A multiply blend cannot brighten

Lighting ground by multiplying its texture with a vertex colour can only darken,
because the vertex colour clamps at white. So **anchor the lighting at flat
ground**: if flat is anchored anywhere below 1.0 (full white), every flat tile
comes out darker than it was. With the gain the figure renderer used, that is
6%, which reads as "the map went muddy".

Anchored at flat, only slopes and walls darken and the change is strictly
additive. The cost is that a slope tilted *into* the light cannot brighten past
flat. On ground, where every normal is within a few degrees of up, that half of
the range was never worth much.

### Vertex colour versus the paint colour

A 2D canvas call that draws coloured triangles may be documented as blending the
draw's own paint colour with the vertex colours. With **no shader or texture on
the paint**, at least one rendering backend takes the vertex colour alone. A
white vertex multiplied against a dark paint came out white, and the first build
of the fade over unexplored ground produced a bank of fog the colour of milk.

**Put the colour on the geometry** and leave the paint plain white. That is
right whichever way the backend reads it.

### Reuse the scene's existing lamp

Terrain that computes its own light direction will disagree with everything
standing on it. Worse, two views that each hand-tune their own light will
disagree with *each other*. The same two walls came out lit from opposite sides
in two views of one map, so switching between the views flipped the sun.

Feed the terrain the same shading function the figures use, in every view. Then
delete the hand-tuned constants rather than re-tuning them.

### Some per-pixel tricks exist on one backend only

Two ways of shaping ground per pixel look available in a 2D canvas API and are
not, at least in Flutter's Impeller renderer (its Android default):

- **A colour filter on a textured triangle draw is dropped in silence.** The
  same filter works in the web renderer. A blend that sharpened its edges with a
  per-pixel threshold would have shipped on one platform and quietly not on the
  other, so it was cut rather than kept as a web-only look.
- **A custom fragment shader on triangles with texture coordinates is not run
  per pixel.** Impeller renders it into an offscreen texture at one texel per
  texture-coordinate unit, then samples that onto the mesh with nearest
  filtering, every frame. A shader does run per pixel on a rectangle draw, so
  the route that stays open is baking blended ground into an image and drawing
  that like any other texture.

Anything that must look the same everywhere has to be built from what every
backend does: textures, vertex colours and ordinary blending.

### Find where cliffs come from before styling them

Every cliff on one generated map turned out to be a coastline. Relief was built
as swells falling a half-step per tile and merged by taking the highest, so two
land tiles side by side could never differ by more than a half-step. A sheer
step only appeared where land met water pinned at zero. Styling "cliffs" meant
styling coasts, and most coasts should not be cliffs at all.

What worked: a pass that lowers land toward the water so most coasts become
shoreline, while a genuine range that reaches the sea keeps its cliff. It only
ever lowers, and it never lowers a crown (anything at the height that paints
rock), so terrain, buildings and every random stream that depends on them stay
where they were. Checked over twenty seeds, not one tile's terrain or building
moved.

### A wall needs its own material, its own texture scale and a foot

Three things made walls read as streaky sand:

- **The wall wore the ground's material.** A cliff above water now takes the
  rock material, and land lips keep their own ground.
- **Its texture was squashed.** Down the wall, the texture was mapped by the
  exaggerated height unit the lighting uses (3×), which squeezed the strata 2.7
  times. Map down the wall by the true height, and along it by a coordinate
  anchored to the screen, so the texture carries round a corner rather than
  restarting at every tile.
- **It had no foot.** Darken each wall toward its base (up to 30% for a tall
  drop), and lay a soft dark wash on the ground below it that fades in with the
  drop's height, so a low step gets none.

Light textured walls more gently than flat-coloured ones. At the flat-colour
gain the walls went to mud; at 0.45 of it they kept their texture and still read
as walls. A board where light is the only thing separating an unclimbable face
from a walkable slope keeps the stronger gain on purpose.

**Draw the fog over the walls too.** A veil drawn only over tile tops left the
walls at full light, glowing through unexplored ground.

### Water lies level

A pool grown downhill from a spring ran down a hillside in steps, and the relief
drew it as a ramp of blue. Grow pools only across ground level with their
spring, never up against a pool at a different height, and draw every water
tile's corners at its own height. Ground within a taper of the water bends down
to meet it; anything higher keeps a wall. Level-only pouring cost about a tenth
of the water, and every map that had water still did.

### A tactical board drawn as boxes

A tile board can look like a stack of boxes even with continuous ground under
it. Three things did it, none of them the ground itself:

- **A grid line over every tile.** Tactics games mostly show no grid until the
  player is choosing a move. Drop it, and show cells faintly, only inside a
  highlighted reach.
- **A reach drawn as a net.** Stroke each highlighted tile and the area reads as
  a lattice. Fill per tile, and run one bright line round the region's outside.
- **Height light in bands.** A flat "higher is brighter" wash per tile steps at
  every tile edge. Light it at the corners instead, so a slope brightens along
  its length.

The fourth thing was the taper ([above](#pick-the-taper-by-what-the-view-is-for)):
walls drawn where the rules allowed a climb.

---

## Part 3: Blending one country into the next

### Don't fade neighbours in over each tile

The first two attempts both faded a neighbour's ground in over each tile along
their shared edge. At full strength from both sides the boundary *flipped*: each
tile wore the other's material at the join. At half strength from both sides it
stopped flipping and went wrong in three new ways, all visible at once:

- **Double exposure.** Two photographs cross-faded across the band read as
  patchy, and a crossfade between a dark texture and a light one passes through
  mud.
- **Straight seams at corners.** Where only one edge of a corner changed
  material, the fade dropped from half to nothing across the line from the
  corner to the tile's centre, drawing hard radial lines and diamond staircases.
- **Blending across cliffs.** The fade ignored height, so water was painted onto
  a plateau's rim and rock onto the water at its foot.

Shipped grid games do it differently. One side covers at full strength through a
mask chosen from all the terrains at a corner (Age of Empires II's blend masks,
Warcraft III's per-corner terrain), so nothing is double-exposed and the shape
follows every tile at the corner rather than one edge.

### One weight per corner, shared by every tile that touches it

Give each grid corner a blend weight per material: the fraction of the tiles
meeting there that wear it. Every tile touching the corner computes the *same
number*, so the blend is continuous across every shared edge by construction,
exactly as the relief is ([a seam is a shared number](#a-seam-is-a-shared-number-not-a-shared-shape)).
Edge midpoints take half and half where the edge fuses, and a tile's centre is
its own material. Interpolate between those points across a finer mesh inside
the tile.

**Count only the tiles in your own run.** The corner's height run (from the
relief) already says which tiles fuse there, so a tile across a cliff gets no
say in your corner's blend. That is the "no blending across cliffs" rule, and it
needs no separate definition: two tiles share a run exactly when no wall is
drawn between them. Gating on exactly equal corner heights instead is stricter,
and wrong: a taper can draw two fused tiles at slightly different corner values,
and exact equality then notches the blend right where a cliff tapers into a
beach.

### Draw it as stacked layers, not a crossfade

To show those weights with ordinary blending, fix a global order of materials.
Draw the lowest material present opaque, then each later material over it at

`alpha_j = w_j / (w_1 + ... + w_j)`, taking 0/0 as 0.

At every vertex the result is exactly the weighted sum of the textures, and
because both tiles at an edge compute the same weights, they compute the same
alphas. It needs no special blend mode: each layer is a textured triangle draw
with vertex colours, as the ground already was. A tile of a single material
draws exactly as before, at the same cost.

Giving one side priority everywhere (one "higher" material floods its
neighbours) was ruled out on structure, not taste: to stay continuous, a lone
tile's material has to flood every tile touching its corners, which erases a
one-tile lake.

### Sharpen the weights, with noise pinned to the world

Linear weights still draw a soft band. Shape them (a gamma curve in log space,
plus a little value noise) so the boundary is organic and fairly crisp rather
than a gradient. Key the noise to the world, not to the screen or the tile: a
position that stays the same whichever way the camera turns, wrapped by the
map's size if the map wraps. A hash does not "just" repeat at the map's edge.
The wrap has to be explicit, and a test caught the unwrapped version failing at
the seam.

### Judge the terrain set in pairs, on the grid

Brightness across one set of nine ground materials spanned 3.3 times, from a
dark forest floor to pale desert. A blend between a far-apart pair passes
through mud, and no technique fixes a pair that should never touch. Render the
common pairs blended on the grid before accepting a set, not each texture alone.

### A blend cannot make an impossible boundary plausible

A map generator that scatters climates by noise will lay a dune against a
snowfield. Blending them softens the boundary but doesn't make it read as a real
place.

Give terrains an adjacency rule (which may lie beside which) and have the
generator lay a neutral bridge terrain between the pairs that cannot meet. Three
notes from doing it:

- **Which of the pair gives way should be the intruder**: the tile with fewer of
  its own kind in its eight neighbours. That erodes a speck of desert stranded
  in the tundra rather than chewing a notch out of the desert proper.
- **Run it again after any later pass that paints terrain.** Rock laid on the
  crown of a range does not care what it lands beside, so a ridge crossing a
  marsh put broken hills against swamp: the exact adjacency the first sweep
  exists to prevent.
- **The second sweep must leave alone anything that has been built on.** A
  building sits on the terrain it was placed on, and your rules may give that
  terrain a meaning (a bonus, a cost), so repainting it changes the game. Where
  two protected tiles disagree, let them.

### Fog is a gradient, not a cutoff

If you shade ground the player has not explored (fog of war), fog drawn per
tile ends at a tile boundary, so the edge of the explored area is a staircase of
hard diamonds and the map falls off it.

Use the same corner trick: a corner's fog is the mean of the four tiles touching
it, so one gradient is continuous across every shared edge by construction. Draw
the **real ground** under the fade, so a range dissolves rather than ending in a
cliff of nothing.

Keep the cheap path: where a tile is unseen *and* nothing touching it has been
seen either, there is nothing for the dark to fade into, so draw one flat
diamond. That is most of an unexplored map, so it still costs what it always
did.

---

## Part 4: Testing ground you cannot look at

A seam a third of a pixel wide is invisible on a screenshot and a bright crack
at 3× zoom on somebody else's phone. The arrangements that open one are rare
enough that a hand-picked field will not contain any. So:

- **Sweep every corner of every tile over every generated shape.** Assert that
  two tiles sharing a corner either agree exactly, or that a flank is required
  and the drawn step is not inverted.
- **Assert the deviation bound**: a corner is never more than one taper from
  its own tile's height. This is the assertion that catches chaining, and it is
  what keeps figures off stilts.
- **Assert flat ground still costs two triangles.** Most ground is flat and it
  must not have got more expensive.
- **Write the test against the naive implementation first and watch it fail.** A
  green test that has never been red is a guess.
- **Make sure a test reaches the textured path at all.** No test ever loaded a
  ground material, so the whole textured branch, where the old blend's corner
  seams lived, was never drawn by any test. Build small images inside the test
  and paint whole frames through that branch, at every camera quarter.
- **Sweep blend agreement over whole generated worlds, not a hand-built field.**
  At every grid corner, every pair of tiles either draws the identical weight
  vector or is provably in a different height run. Three seeds at four camera
  quarters is over a hundred thousand pairs. A field small enough to check by
  hand contains none of the arrangements that break a seam.
- **Image creation that needs real async hangs inside a test that fakes the
  clock.** Create the test images outside the fake-clock body (in setup, or in
  a plain test), then use them inside.

And for hit-testing raised ground, ask the right question. "Is the answer the
tile I aimed at" **cannot be asked**. Ground in front is *allowed* to cover
ground behind, which is the whole reason a picker that allows for height exists.
Ask **"does the answer explain the pointer position"**: dropping the point by
the returned tile's own lift must land on that tile. That question found two
real bugs; the other found none.

Finally: **write a throwaway entrypoint that boots straight into the state you
need**, and delete it afterwards. Terrain worth looking at is usually somewhere
a fresh game will not show you: a map generator may keep relief away from where
the player starts, and fog hides everything else. Fifteen lines that turn the
fog off and park the camera on the tallest ground in the seed is the difference
between measuring and squinting.

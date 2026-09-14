# Ground and terrain

Ground textures are the one asset type here that never becomes a mesh. You
generate a flat image and make it tile.

::: tip There's more detail on the next page
[Ground relief and blending](/guide/ground-and-relief) repeats the generation
lessons at more length, then covers what your own map code has to get right:
corner heights so tiles on slopes meet without seams, lighting slopes so they
read, blending one terrain into the next, a soft edge for shading over
unexplored ground, and how to test ground you can't easily look at. Read it
after you get the texture working.
:::

```sh
WIDTH=1024 HEIGHT=1024 scripts/generate_concepts.sh prompts/ground
scripts/make_seamless.py output/ground/plains_00001_.png \
    --out output/materials/plains.jpg --size 1024 --check
```

## How to write a ground prompt

Ground is not a landscape photo. It's a close-up of a surface. The generator
wants to compose scenes, so the prompt has to say so in several ways.

Here's the prompt for forest ground:

> A seamless tileable ground texture of **dense woodland floor of fallen leaves,
> moss, twigs and needles**, photographed from directly overhead looking straight
> down. Fine even detail spread uniformly across the whole frame, the same
> density everywhere, no large shapes and no focal point, like a close macro crop
> of a much larger surface. Flat shadowless overcast light, painted game texture,
> crisp small-scale detail.

Only the bold part changes per terrain type. Water is the one exception: its
prompt swaps the middle sentence for one asking for even ripples and no
gradient. Everywhere else the rest is fixed, and each clause is preventing a
specific failure:

| Clause | Stops |
|---|---|
| photographed from directly overhead looking straight down | A horizon appearing |
| the same density everywhere | Detail bunching in the middle |
| no large shapes and no focal point | A composition with a subject |
| like a close macro crop of a much larger surface | The texture reading at the wrong scale |
| flat shadowless overcast light | Baked shadows that fight your lighting |

The negative prompt matters as much:

> horizon, sky, perspective, vanishing point, buildings, figures, people,
> animals, path, road, river, fence, text, watermark, signature, border, frame,
> vignette, drop shadow, strong directional shadow, single large object, centred
> subject, large shapes, sweeping curves, arcs, swirls, composition, focal
> point, tilt shift, blur, depth of field, mosaic, tiles, bricks

Note that mosaic, tiles and bricks are in there. Ask for a tileable texture and
the generator will helpfully draw a picture of tiles.

## Size and contrast

Generate at **1024 pixels**, not 512. The difference between detail that reads as
rock and detail that reads as coloured noise is mostly resolution.

Generate square, too. `generate_concepts.sh` uses the Qwen graph's default size,
a 3:4 portrait, unless `WIDTH` and `HEIGHT` are set. `make_seamless.py` scales
whatever it gets to a square of `--size` pixels (1024 by default), so a portrait
comes out squashed.

Aim for real contrast, and measure it rather than trusting a thumbnail. A desert
material shipped looking fine and read as flat colour on the live build.
Measured across a set of nine, the grey channel spread told the whole story:

| | desert | tundra | the other seven |
|---|---|---|---|
| Standard deviation | **3.0** | **3.7** | 12.4 to 33.1 |

Seventeen grey levels. Nothing was broken. It was a truthful photograph of very
even sand. `make_seamless.py` prints the contrast (the standard deviation) next
to the seam score on every run, and warns when it falls under 8, because a
texture with so little contrast reads as a painted rectangle at map scale.

## Scale is set by how big things in the texture should look

The temptation is to maximise texel density: pick the repeat that maps one
texel (one pixel of the texture) to one screen pixel. That gives a large repeat,
and a large repeat is harder to spot. Both arguments are true, and both lose to
a third: how big the things in the texture look.

A repeat spanning eight tiles put a leaf **25 screen pixels across, against a
person of about 34**. Leaves the size of a soldier. Four tiles to a repeat puts
that leaf at 9 pixels, which is the scale the map is pretending to be at.

Pay for texel density with resolution instead, which is why the materials are
1024 pixels rather than 512, and let the size of things in the picture choose
the repeat.

## Making it tile

No node in this ComfyUI install generates tiling textures. There is no circular
padding decode and no tiled sampler. The seam has to be dealt with afterwards.

```sh
scripts/make_seamless.py in.png --out out.jpg --size 1024 --check
```

### Four approaches that failed

Each of these seemed sensible and failed when tested. That's why they're here.

**Rolling by half doesn't fix the seam.** Rolling shifts the image by half its
width and height, wrapping round at the edges. Everyone tries it first, but it's
only a phase shift. A tile repeats exactly as badly after rolling, because a
shift moves the break but cannot remove it. Measured, it took an 81% seam to
78%, on the metric at the end of this list that scored even a perfect texture at
81%.

**Blending the rolled image back toward the unrolled one** puts the discontinuity
straight back on the edge. It measured as doing nothing because it did nothing.

**Mirroring the strip about the seam** scored 0.98 and drew a butterfly through
the middle of every tile. The map read as kaleidoscope wallpaper. Perfect number,
unusable picture.

**A seam metric divided by the image's own contrast** scored an already perfect
texture at 81%. Two adjacent columns of any organic ground differ by a good
fraction of its standard deviation, so with nothing to compare against, good and
bad both looked bad.

### What actually works

Two steps, in this order.

**Roll by half first.** Not to fix anything, but to move the problem. The first
and last rows of a rolled image were adjacent rows in the original, so the outer
edges come out continuous by construction. The one real discontinuity moves into
the middle of the tile, where a neighbour never sees it.

**Then mend the middle by fading in content from half a tile away.** Near the
seam, take pixels from half a tile across. They are unrelated content but the
same texture, and crucially they are continuous with each other. The
discontinuity is replaced by ordinary ground. Weighted with a smoothstep to 1 at
the seam and 0 at the band edges, so the join reads as variation rather than as a
repair.

### Reading the score

Every run prints two seam numbers, and you need both. `--check` adds the ratio
from before the fix, so you can see what the fix did.

The **ratio** compares how much the edge columns differ against how much any two
adjacent columns differ. A tiling texture's edges are neighbours, so 1.0 is
seamless. Shipped materials score 1.0 to 1.2.

The **absolute** difference is in levels out of 255.

::: warning The ratio lies about smooth textures
A water texture scored 2.06 by the ratio while its edges differed by 2.1 levels
out of 255, which no eye will ever see. When neighbouring pixels barely differ,
dividing by that makes a nothing look like a problem.

Acting on the ratio alone, the tool repaired a working texture into a worse one.
It now complains only when both numbers say so, and the water texture was
reverted untouched.
:::

## The white mat problem

Asked for a full bleed surface, the generator sometimes returns a picture of one:
a smaller square inset on a white ground. Roughly one time in nine, whatever the
negative prompt says.

Tiling that lays a bright lattice across your map, which looks exactly like a seam
bug and is not one.

The tool trims it automatically. A mat is recognisable without knowing its colour,
because a row of it has almost no variance where any row of real ground has
plenty. It walks in from each edge while the rows stay flat. It caught a 227 pixel
border on one attempt.

Telling the model not to draw a border does not work, so this is not fixed in the
prompt.

## Beyond one image per terrain

A single texture per terrain type is wallpaper. A field of desert shows the same
blob in the same place on every tile. Two things fix it, and both live in your
game rather than here.

**Bake several variants** and pick one by hashing the tile position. Four per
terrain is enough to break the pattern.

**Blend at the boundaries between different terrains.** One warning from doing
this wrong: painting a neighbour's ground at full opacity along a shared edge, and
having the neighbour do the same back, does not soften the boundary. It flips it.
Each tile wears the other's material at the join. Blend at half strength from
both sides, so both land on the same fifty fifty mix along the edge they share,
and only across the part of the tile nearest that edge. Fading across a whole
tile leaves a quarter of the neighbour's ground sitting in this tile's middle, and
one lake tints every field around it.

**Some pairs should never touch at all.** A blend can soften a boundary, it
cannot make an impossible one plausible. Noise based world generation will
cheerfully lay a dune against a snowfield. Decide which terrain types may border
each other and insert a neutral one between the pairs that may not.

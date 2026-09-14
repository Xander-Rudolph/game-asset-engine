# Props and scenery

*Trees, rocks, scrub and bones standing on a map or a battlefield. Generated as
concept art and cut out as flat images: no mesh, no rig, no texture stage.*

A flat image is enough for a prop that never has to show its other side. A
turning camera doesn't change that: each prop is redrawn upright from the same
picture at every quarter-turn, the way a billboard is. It is also the cheaper
way to match photographic ground. Props built from a handful of primitive
shapes under a studio light read as plastic beside it, and a painted stone reads
as a stone.

Everything below was measured on a batch of 13 scenery props and 15 stones for a
tile-based strategy game, drawn over generated ground materials. Each section
says what failed and what worked instead.

## Prompts

### The scenery style used to stand every prop on a slab

The shipped `prompts/scenery/_style.txt` asked for "one isolated object standing
on a small patch of bare ground". Every prop came back on a little square
diorama tile of dirt. A flood fill keeps that tile, because it is not
background, and in the game it becomes a second patch of ground drawn on top of
the real one.

The style now asks for a clean cut-out instead:

> one isolated object shown as a clean cut-out on a plain flat neutral 50% grey
> background with nothing around or beneath it: no ground, no soil, no base, no
> tile and no shadow under it, the object simply ending where it ends

and the negative adds `ground patch, soil, dirt base, plinth, pedestal,
platform, square tile, slab, diorama base, cast shadow, drop shadow, shadow on
the ground, contact shadow, shadow beneath the object, pebbles, gravel`.

The shadow and pebble words came after the first test. A boulder came back
without its slab but still sat on a pale disc of shadow with a few tufts of grass
in it, and the cut kept those too. With both changes in, every subject in the
batch came back with nothing under it except one, covered in the next section.

::: warning This breaks a rule from the concept art page
[Naming a thing in the positive summons it](/guide/concept-art#what-a-good-prompt-for-this-pipeline-says),
and the style above names ground, soil and a base. It worked anyway, across the
whole batch. The likely reason is that "a clean cut-out" does the work. If a
base starts creeping back, first try deleting the "no ..." list from the
positive, and leave the negative to carry it.
:::

For grassy subjects (dune grass, reeds, a frozen tuft), don't add "grass tufts"
or "weeds" to the negative. For everything else it helps.

### Word ground cover as an object

"A small mound of windblown snow over a tuft of frozen grass" came back twice as
a square of snowy ground, whatever the negative said. A mound of snow **is**
ground, so the model drew ground. "Dusted with snow" brought a smaller square
with it on the third try. What finally worked names a thing with nothing under
it: "a single loose clump of stiff grass blades rimed with white frost, the
blades gathered together at the root, with no snow, soil or ground under the
clump".

If a subject is a heap, a mound, a drift or a patch, reword it as the object
that sits in one: a clump, a pile, a cone.

### Pick the background against the subject's finest parts

The background is what the cut removes, so it has to differ from every part of
the subject, including the smallest.

- **"Mid-grey" is not a colour the model honours.** It returned a light grey
  around 200, close enough to snow and pale grass for the fill to eat into
  them. "Neutral 50% grey" landed a true mid grey.
- **A white background ate a cactus's white spines.** The body was green, so
  white looked safe, but the spines merged into it and came out of the cut as
  specks down both sides. The same cactus on grey came out clean.
- **A dark background hollowed out a dry shrub.** Charcoal was tried for pale,
  twiggy subjects. The cut then matched the shrub's own shadowed centre and dark
  stems, and it came back a ring of twigs with nothing in the middle. The same
  shrub on light grey cut whole.

Neutral 50% grey is the best default. The cases it gets wrong, such as grey
stone, are fixed at the cut (below) without a reroll.

### Colour words set the rendering style, not just the colour

"Wind-worn sandstone in warm ochre and rust layers" came back a saturated,
painted-looking orange, from the same style that gave photographic grey and
mossy stones. On a green or dark swatch it looked fine. On the photographic sand
it was meant for, it read like a sticker. The fix is to ask for colours near the
ground's own palette ("pale weathered desert sandstone, dusty buff and tan with
faint darker banding") and to name the realism outright.

**Judge a prop on its own ground, in a real screenshot.** A swatch is not the
ground it will stand on.

## Cutting

Start from the icon cut ([Icons](/guide/icons)): flood fill in from the corners,
drop scraps that touch the canvas edge, pull the edge in a pixel and feather it.
Props need four more things.

### Clear the pockets the fill cannot reach

A flood fill only removes background it has a path to. Sky fenced in between a
tree's trunk and canopy, or between a shrub's twigs, survives as pale slivers:
invisible against the generator's grey, glaring on dark ground.

After the fill, clear any connected patch that is still opaque, within about 30
of the background colour, and at least about 40 pixels in area at the
generator's 1104-pixel size. Take the background colour as the median of the
four corners, as the icon cut does. Smaller patches are left alone, because a
highlight on a leaf can be grey too. On clean subjects (a bush, a fir) the step
made no visible difference.

### Bleed the rim colour before you shrink the image

The colour under a feathered edge is still the generator's background. Shrink
the image to game size and that colour averages into the rim, which then halos
on whatever ground the prop stands on. Before resizing, grow the opaque
interior's colours outward under the transparent rim: repeatedly give each
uncoloured pixel the average of its coloured neighbours (16 passes is plenty),
then keep the original alpha.

### The tolerances belong to the subject, so write them down

The defaults (flood fill 60, pocket 30) suit fine parts: needles, twigs and
spines need a generous fill to shed the background between them. Other subjects
need less:

| Subject | Problem at the defaults | What fixed it |
|---|---|---|
| A grey boulder capped with snow, on grey | The fill took whole chunks and holed the snow cap | Flood 20, pocket 8 |
| A pile of bleached bones, on grey | The pocket step punched streaks out of the long bones | Pocket 15 |
| A frozen grass clump in a ring of snow | The snow ring came out in broken pieces | Flood 35, pocket 15 |

A solid subject has no fine parts reaching into the background, so it can take
tight tolerances. Try a gentler cut before spending GPU time on a reroll.

Because the right values differ per subject, **record each prop's source image
and cut flags beside the shipped asset.** Otherwise nobody can cut it the same
way again.

### Stand every prop on the same line

An icon is centred. A prop has to stand. Put every prop on the same square
canvas with its lowest pixel on the same line (0.92 of the height worked),
centred across. The game can then land any prop on a tile with one anchor rather
than a number per file. A 320-pixel canvas came to between 45 and 165 KB per
prop as a PNG.

### Two fixes that did not work

- **A darker background for pale subjects.** See the hollowed shrub above.
- **Trimming a leftover base under a trunk by its shape.** The idea was to find
  the narrow trunk just above a patch of ground and clear everything below it.
  On the one tree that had a patch, the lowest branches hung out over it, so
  there was no narrow row to find: the patch was 274 pixels wide, the narrowest
  row above it 242, and the branches 382. Fix a base in the prompt, not the
  cut.

## Putting them in the game

### Size props against a figure, not against each other

Primitive props that share one frame all come out the same size, so a tree
stands no taller than a standing stone. Size each prop against the box a figure
is drawn in instead: a fir about 1.7 times as tall, a stump about three
quarters. Give every prop a soft contact shadow sized to its footprint.

### A file named off by one capital is ignored in silence

The props were generated as `scn_duneGrass`, and the game looked them up as
`scn_dunegrass`. Nothing failed. The loader found no match and drew the old
primitive, and a size table keyed the same wrong way quietly fell back to a
default size. A test caught both: it lists the shipped folder and checks every
file name against the keys the game looks up, and it checks the size table's
keys against the same set in both directions.

### Fade tall props with the fog

A fog veil drawn over a tile's diamond does not cover a tree, which stands well
above its tile, so crowns poked out over unexplored ground as bright shapes.
Fade each prop by its own tile's fog, and skip props on fully fogged tiles.

### Scatter by position, or a forest is an orchard

Two trees per tile at the same two spots read as rows planted on a grid. Nudge
each tree a few pixels and resize it by up to about 15%, with numbers taken from
the tile's position. Take them from the tile's position in the *world*, not on
screen, so turning the camera does not reshuffle the forest.

## How long a batch takes

The concept graph is documented at about 130 seconds an image. With another
project's jobs sharing the card, images took 166 to 237 seconds, and a batch of
26 props ran close to two hours. Queue the batch, then cut and review it in sets
as images land, rather than waiting for the end.

All of it runs on Qwen-Image (Apache-2.0), and the cut is a flood fill with no
matting model, so nothing in the chain adds a licence question beyond the
model's own.

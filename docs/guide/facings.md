# Facings and camera angles

This is the page for the question "why does my unit face the wrong way".

A 2D game shows a 3D model as a set of flat pictures, one per direction the unit
can face. Getting them right means agreeing on three things: how high the camera
sits, which way round the model is turned for each picture, and which picture the
game reaches for when a unit walks north.

## Render a sheet

```sh
scripts/render_sheet.py output/rigged/golem.fbx \
    --poses transforms:poses/walk.json --angles 4 --size 220 \
    --out output/sheets/golem_walk.png
```

Angles run across the sheet. Animation frames run down. That is the order most
engines expect when slicing a sheet into a flipbook.

## Camera height

The camera elevation has to match the shape of your ground tiles, or figures sit
at a different angle from the ground they stand on. It looks subtly wrong in a
way that is hard to name and impossible to unsee.

The rule is short:

> **elevation = arcsin(tile height / tile width)**

Because with an orthographic camera at elevation θ, a flat vector on the ground
takes up sin(θ) of its length vertically on screen. That ratio is exactly what
your tile proportions describe.

| Your ground | Tile ratio | Elevation | Also called |
|---|---|---|---|
| 2 to 1 diamonds | 0.5 | **30 degrees** | isometric, dimetric |
| 4 to 3 diamonds | 0.75 | 48.6 degrees | steep isometric |
| Square grid seen from above | 1.0 | **90 degrees** | top down, overhead |
| Very shallow | 0.25 | 14.5 degrees | near side on |

Most tile based games calling themselves isometric are 2 to 1, which means 30
degrees. That is the default here.

```sh
--elevation 30    # isometric, the default
--elevation 90    # true top down
```

## Which way the model is turned

Now the part that actually causes wrong facing sprites.

An isometric camera does not look along the world axes. It looks down the
diagonal between them. So a unit facing north in the game is not facing the
camera, it is facing away and to one side.

That means the four facings have to be rendered at **45, 135, 225 and 315
degrees**, not at 0, 90, 180 and 270.

Render them at 0, 90, 180, 270 and every unit stands square on to the viewer
while the ground runs diagonally underneath. This is the single most common
mistake, and here is what both look like.

### Square on, azimuth starting at 0

![Four facings rendered at 0, 90, 180 and 270 degrees](/facing-square-on.png)

Front, side, back, side. Correct for a side scroller or a paper doll portrait.
Wrong for an isometric map.

### Isometric, azimuth starting at 45

![Four facings rendered at 45, 135, 225 and 315 degrees](/facing-isometric.png)

Three quarter views throughout. These sit on a diamond grid properly.

```sh
--azimuth-start 45     # isometric, the default
--azimuth-start 0      # square on, for top down or side views
```

The `--flat` flag does both at once: elevation stays put and the azimuth starts
at 0. It is for looking at a model, not for producing sprites.

## What azimuth means here

Measured, not assumed. Rendering one model at 0, 90, 180 and 270 gives:

| Azimuth | What you see |
|---|---|
| 0 | The model facing the camera |
| 90 | The model facing screen right |
| 180 | The model's back |
| 270 | The model facing screen left |

So azimuth turns the model anticlockwise seen from above, starting from facing
the viewer.

## Mapping game directions to sheet cells

For four facings on a 2 to 1 isometric map, with the sheet rendered starting at
45 degrees:

| Cell | Azimuth | Model faces | Typical game direction |
|---|---|---|---|
| 0 | 45 | Toward viewer and right | South east, or "south" |
| 1 | 135 | Away and right | North east, or "east" |
| 2 | 225 | Away and left | North west, or "north" |
| 3 | 315 | Toward viewer and left | South west, or "west" |

Whether you call cell 0 south or south east depends on whether your game names
directions by the screen or by the world grid. Pick one and write it down, because
this is where the confusion comes from later.

::: tip Verify it once per project, then never again
Render the sheet, look at it, and pick the cell where the figure faces down and to
the right on screen. That is your first facing. Everything else follows by 90
degree steps.

Two minutes of looking beats an afternoon of reasoning about handedness.
:::

## Eight facings

Pass `--angles 8` and you get 45 degree steps. Starting at 45 that gives 45, 90,
135, 180, 225, 270, 315, 0, which covers both the diagonals and the axes. Useful
when units move on eight directions rather than four.

Eight facings is four times the storage of four facings once you multiply by
animation frames and team colours. Consider baking four and turning the model at
runtime if your engine renders 3D at all.

## The game side of the same agreement

The renderer produces pictures. The game has to pick the right one. Three things
need stating in your own code, and they need to match what you rendered.

**Which way the model was built.** Every model in a project should be authored
facing the same direction. If figures are built facing +z and your camera reads
+z as south, then south is no rotation at all and the other three are quarter
turns from it.

```
south = 0 degrees
east  = 90 degrees
north = 180 degrees
west  = 270 degrees
```

**What happens when the camera rotates.** If players can spin the map, the world
does not turn but the picture does. A fighter looking north is still looking north
after the camera walks a quarter turn, but you must draw a different sprite. One
quarter of camera spin moves the view one step backwards through the facing list.

**One definition, not two.** Write the direction to grid step mapping once. In a
project this pattern came from, it was written twice, once to place compass arrows
and once to pick the sprite, and they drifted. Tapping north selected east. It
regressed twice before being pinned by a test that presses every arrow at every
camera rotation.

## Why the renders look consistent

Details in `render_sheet.py` that exist for specific reasons.

**Orthographic by default.** This is what makes two assets rendered on different
days share a scale. A perspective camera makes size depend on distance, so a
figure rendered alone and a figure rendered in a group come out different sizes.
Use `--persp` only when you want the look.

::: warning The in graph sprite renderer is perspective
`mesh_render_sprites.json` uses the 3D pack's orbit renderer, which has a field
of view rather than an orthographic scale. It is fine for a quick turnaround and
wrong for sprites that need to match each other. Use `render_sheet.py` for
anything the game will load.
:::

**The key light is attached to the camera.** It rides round with it, so every
facing is lit identically. A fixed light makes one facing bright and the opposite
one a silhouette, and no amount of colour correction later fixes it.

**Feet on the floor, not centre on the floor.** The model is anchored by the
bottom of its bounding box, so a tall figure and a short one both stand on the
same line in their cell. Centring instead makes tall figures float.

**Ambient light is deliberately high and flat.** Sprites want form, not drama. The
world light is on and the sun is soft, so nothing goes fully black.

**Untextured meshes get grey clay.** Blender's default white against a white
world light renders as a featureless blob. Grey clay makes shape readable. If
your render is grey, the mesh has not been textured yet.

**Each run gets its own frame folder.** Two renders running at once used to
interleave their frames into one shared folder, and each composed a sheet
containing the other model. That happened for real when a batch overlapped a
manual render.

## Sizes

Render at the size the sprite will be used, then judge it there.

| Use | Size |
|---|---|
| Map token | 128 px |
| Battlefield figure | 220 px |
| Portrait or inspection view | 340 px and up |

Judging a walk cycle at 340 pixels and shipping it at 128 is how you get a cycle
that reads as a shimmer. See
[animation cycles](/guide/animation#exaggerate-more-than-feels-right) for how
much to exaggerate.

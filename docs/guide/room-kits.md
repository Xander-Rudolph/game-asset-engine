# Room kits

*Floors, raised platforms, stairs, pits, walls and props for rooms on a tile
grid, modelled by a Blender script and rendered under the same camera and light
as the character sheets.*

[Props and scenery](/guide/props) cuts generated pictures out as flat props, and
[ground relief](/guide/ground-and-relief) builds terrain from heights. This page
is a third route, for rooms with height changes inside them: a kit of pieces
built from primitives by a script and rendered once. No script for it is in this
repo. A 2.5D isometric game made with the engine built one for a clean test
facility of panels and grating, and what follows is its approach and what broke.
Its notes count 48 renders: 9 floor tops, 14 height pieces, 10 walls, 2 posts
and 13 for 8 props, the wall props in two facings.

## Light it like the sheets

Render the kit under the camera and light the figures had, or the two will not
sit together. The game rebuilt `render_sheet.py`'s set-up in its own Blender
scene: an orthographic camera at 30 degrees elevation, a sun parented to the
camera at (55, 0, 30) degrees, and a white world, at the strengths its figures
were drawn with, `--key 2.9 --ambient 0.6`.

That sun shines from below the horizon. With the camera at 30 degrees, the light
`render_sheet.py` parents to it travels about 19 degrees upward, computed on
2026-10-09 from the two rotations the script sets, not rendered. A level top
therefore takes only the world light, and only faces turned toward the camera
take the key. Two things followed in the game:

- **Floors need a dark albedo.** By its notes, an albedo of about 0.11 brought
  the floor tops near 70 of 255, and the white wall panels, which face the key,
  took 0.29.
- **No shadow catcher.** A Cycles shadow catcher under each prop darkened a whole
  rectangle, because to a light below the horizon the whole floor is in shadow.
  The props stand on soft blob shadows instead, as the figures do.

## Build in tile space, and record every anchor

- Build each piece in tile-local coordinates, along the grid's two axes, under a
  root turned 45 degrees. The script then thinks in tiles, and the camera sees
  diamonds.
- Give each kind of piece a reference point in the room: the tile's centre for a
  floor top or a prop, the middle of the edge it stands on, at the floor, for a
  wall, the middle of an edge at its top for the face of a ledge, and a tile's
  corner for a post.
- Record where the reference point lands in each render. That pixel is the
  piece's anchor, and the game draws the texture with that pixel on the point.
  The game writes every anchor into one manifest beside the textures.

The game's sizes, from its notes: 128 by 64 px tiles, 24 px for one height step
and 96 px wall faces, at 40 px per character unit, rendered at 80 and halved.

## Draw order

Sort the pieces into height bands, the pit first, then the ground, then each
level's faces and tops. Within a band, draw back to front by the sum of the
tile's two grid coordinates, so a nearer, higher tile covers what is behind it.
Walls, posts and props sort with the figures instead, by how far down the screen
each one stands.

## Lift the sprite, not the body

A figure on a raised tile is drawn higher by offsetting its sprite, while its
position, its collision and its depth sort stay on the ground plane. The game
records each tile's height and each stair's slope per room, and a small
component on each figure lifts the sprite to the floor under it.

For pathfinding, pit tiles, the dropping edges of raised tiles and the
footprints of blocking props become obstacles. The game grows them by 14 px and
cuts them out of the room's navigation mesh, so enemies path round pits and
props and up the stairs.

## What broke

- **Collision half a tile low.** The blocking shapes took the tile-to-screen
  position as a tile's top corner, while the floor sprites took it as the
  centre, so a figure could walk onto the back half of a pit. Define it once, as
  [facings](/guide/facings#the-game-side-of-the-same-agreement) says of
  directions.
- **Walls half a tile up**, leaving a gap behind the back walls. Each wall
  carries its own anchor now.
- **Figures sinking into platforms**, drawn on the ground plane until the lift
  above went in.
- **The shadow catcher**, above.

## How long a build takes

Run by the game on 2026-10-09 and not re-run here, because its build has no
output option and writes into the game's own folders: 48 renders in 12.3 s with
Cycles on the CPU at 96 samples and 28 threads, and a rebuild wrote
byte-identical textures, with Cycles' seed at 0 and the OIDN denoiser. On the
CPU it stays off the graphics card, which
[other jobs share](/guide/troubleshooting#out-of-memory-when-several-jobs-share-the-card).

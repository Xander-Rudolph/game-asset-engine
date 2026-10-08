# Rooms for generated maps

*This repo makes the art a room is drawn with. Stitching rooms into a map is
your own generator's job. This page is what one game's generator got wrong, so
that the rooms you author, and the code that places them, do not repeat it.*

## Where this comes from

The case study is
[The Gaoler Protocol](https://github.com/Xander-Rudolph/The-Gaoler-Protocol)
(a private repository at the time of writing), a 2D isometric dungeon crawler
whose maps are stitched together from hand-authored rooms. A level design
review of its generator on 2026-10-08 found twelve problems. Three kinds of
evidence sit behind this page, and every section says which it rests on:

- **Read in the code, not run.** The game's generator at commit `1f19b66`
  (2026-10-08) was read for this page, not run.
- **Run in a browser port of the generator, not in a game engine.** The review
  ported the generator to JavaScript (`gaoler_gen.js`). The port carries the
  game's room data and sector settings, and those were checked against the
  repository. It was run with Node 22.22.1 on 2026-10-08 over seeds 1 to 1000.
  A port can drift from the game it copies, so its numbers say what to measure,
  not what the game does.
- **Measured in Godot 4.6 by the implementation's test runs.** The review's
  proposal was then built into the game, in its pull requests #10, #12, #13 and
  #14 (branch `level/pr4-minimap-sectors` at `5238ffc`). Those runs cover seeds 1
  to 1000 unless a section says otherwise. They were not re-run for this page.

The port loads rooms in sorted order and the original game did not, so the two
built different dungeons from the same seed
([determinism](#determinism-takes-more-than-a-seed)). The port's per-seed numbers
are what the original code builds once its room list is sorted. Measured in
Godot 4.6 by the implementation's test runs, the sorted game reproduced the port
exactly for seeds 12345, 42 and 77141.
[The last section](#measured-after-the-refactor) has the numbers after the
refactor.

## A room is a footprint with faces

The case study authors each room as a set of cells on a grid, with 4 by 4
floor tiles of 128 by 64 pixels in every cell. Every outside face of a cell is a
wall unless the room says otherwise:

| Face | What it is in the case study |
|---|---|
| Wall | The default. No connector. |
| Door | A doorway of a set width, 80 pixels unless the room says otherwise |
| Hatch | A narrow doorway, described in the code as slow to pass through |
| Gate | A doorway that can lock and unlock, for puzzles |
| Open | The whole face, with no wall and no door. Rooms joined this way open into each other. |

Two lessons, both read in the code:

- **Key every connector by cell and face, not by side of the room.** "A door on
  the north side" means nothing on an L-shaped room. The case study started with
  one marker per side and had to migrate them to cell faces by position.
- **Check every connector against the footprint.** One combat room's only door
  named a cell that is not one of its eight cells. The loader finds connectors
  by walking the footprint, so the door was dropped without a warning and the
  room kept only its open faces. An editor should refuse the key outright.

## Lay room origins on the grid their cells use

Read in the code. Room origins sat on a grid with a one-tile gap built in, 320
by 160 pixels per half-cell step, while the cells inside a room were drawn on
the tile grid itself, 256 by 128. The two agree only at a room's anchor cell.
Where two anchor cells touch, the gap is the intended one tile. Anywhere else
the gap grows, or the seam skews, with how far each touching cell sits from its
own room's anchor (worked out from the two pitches). Doors and the navigation
links between rooms were placed at the midpoint on the origin grid, so they
hung where a cell would have been on that grid rather than where it was drawn.

Use one grid for everything, and make the doorway between two rooms part of
the rooms rather than part of the grid pitch. Building that in Godot 4.6, the
implementation found two more details. A face 4 tiles wide has no centred
doorway 1 tile wide, so doorways became 2 tiles wide. And once the two grids
were one, perimeter walls had to be added to the rooms.

## Every connector is a ticket in the draw

Read in the code. To fill a connector, the generator lists every room with a
connector facing back the other way: one entry per point of weight, for each
such connector. Rooms with three or more connectors get two extra points. A
seeded shuffle then takes the first entry that fits.

So a room's share of the draw is not its weight. It is its weight times the
number of its connectors that face the right way, and nothing at all if none
do. Worked out from the case study's rooms, before any fit check:

| A connector facing | Can be filled by (points) | Share of the draw |
|---|---|---|
| East | Straight corridor (8), spawn hub (5 + 2), large hall (1 + 2) | 44.4%, 38.9%, 16.7% |
| North | Ring-shaped combat room (3 + 2, on each of three faces), straight corridor (8), 2 by 2 room (6 + 2), spawn hub (5 + 2), large hall (1 + 2) | 36.6%, 19.5%, 19.5%, 17.1%, 7.3% |

The large hall's weight was never set, so it took the default of 1.

Run in the port over seeds 1 to 1000: corridors made up a median 46.7% of a
sector's rooms (26.4% to 73.9%), and the spawn hub, which nothing kept out of
the draw, turned up a median of 9 extra times per sector (up to 21).

Measured in Godot 4.6 by the implementation's test runs, changing weights alone
made corridors worse, not better: they rose to 49% to 55% of the rooms, because
the share the spawn hub lost when it left the draw went to corridors. Placing
rooms by role fixed it. After the refactor the median corridor share was 0% to
5.6%, depending on the sector.

Have the room editor show each room's effective share for each direction,
across the whole set, as you author. A weight on its own says little about
how often a room appears, and the faces you give rooms decide which ones the
map can grow from.

## Keep set pieces out of the draw

Read in the code. Weight 0 meant "dead end, used when nothing else fits". The
spawn room had weight 5 and a `spawn` tag that the generator never read, so it
was drawn like any other room.

The review gives every room a role (traversal, combat, spawn, vault, boss and
so on). Weight only matters within a role, and weight 0 marks a set piece that
is chosen by role and never by the draw. Its catalogue lists 23 rooms (its
heading says 21), and twelve of them are set pieces. A set piece has to fit
wherever the plan puts it, so author a connector on every face it might be
entered from and let the placer wall the ones it does not use. The
implementation built this, and how much the catalogue mattered is in the next
section.

## Build the map from the plan, not the plan from the map

Read in the code. The case study does make a plan first: a spine of rooms from
spawn to boss, side branches, and the special rooms each sector requires. But
rooms are placed by a flood fill out from the spawn room, and the plan is
painted on afterwards: a new room next to a planned one takes that node's first
unplaced neighbour. If the spine's next node lands on a dead end, the spine
stops there.

Run in the port over seeds 1 to 1000:

- A median 44% of the plan's rooms were ever placed. All of them were placed in
  20 seeds, and the boss in 365.
- A median 88.1% of the rooms present at spawn were outside the plan altogether
  (50.0% to 97.6%).

The review's alternative, also run in the port, places the spine room by room
from the previous one, hangs the branches off it and walls every connector left
over. It placed the whole plan in 977 of 1000 seeds. It is not free:

- 487 seeds needed a fallback.
- Almost every fallback was a branch moved to a neighbouring room, because the
  room it should hang from had no free face: 312 combat, 192 vendor and 39 vault
  branches over the 1000 seeds.
- 23 branch rooms were dropped.

Rooms on a spine need spare faces, and that is decided when they are authored.

Measured in Godot 4.6 by the implementation's test runs:

- Built into the game, it placed the whole plan in all 1000 seeds of every
  sector, with no node dropped. That took fallbacks the review had not
  specified: backing up along the spine, re-rooting a branch on any spine room
  rather than only one step back, and a corridor standing in for a branch
  before the branch is dropped.
- How often a branch has to move depends on the rooms you author. In the first
  sector the six old rooms needed a branch re-rooted in 893 seeds and dropped a
  node in 59. The 23-room catalogue, with small set pieces and a room for every
  role, needed a re-root in 505 and dropped none.
- With the six old rooms, a placement rule that preferred rooms with spare
  doors at branch roots made it worse: seeds that dropped a node went from 59 to
  88.

## Give each special room one rule

Read in the code, run in the port. The plan made its last spine node the boss,
and the sector settings also required a boss near the end of the spine. The
second rule found the end taken and moved one step back, so the plan held two
boss rooms in all 1000 seeds. Let one rule own each special room, and keep a
test that counts them. After the refactor every seed of every sector held
exactly one boss (measured in Godot 4.6 by the implementation's test runs).

## Stop growing

Read in the code. Every room the player entered ran the flood fill again, out
to four rooms away, and the sector's room limit only bounded the plan.

Measured in Godot 4.6 by the implementation's test runs on the original,
unsorted code, seeds 12345, 42 and 77141 grew from 55, 48 and 62 rooms at spawn
to 118, 105 and 86 after entering every room within six steps of spawn. Run in
the port, which sorts its rooms, seed 77141 grew from 23 to 109, and the game
did the same once its list was sorted. After the refactor the map did not grow
at all.

Generate the map once. One room per plan node, and the room limit is a budget
the placer checks.

## Make a missing room set fail loudly

Read in the code, run in the port. Three of the four sectors had settings but
no folder of rooms. The spawn room then fell back to the first room loaded, a
one-door dead end from the shared folder, and each of those sectors came out as
two rooms (seed 12345). Fail when a role has no room to fill it, and test that
every sector reaches its budget.

## Determinism takes more than a seed

- **Sort the room list.** Read in the code: it was built in directory-listing
  order and never sorted, and that list is what the seeded shuffle reorders.
  Measured in Godot 4.6 by the implementation's test runs, the engine's listing
  put a different room first than alphabetical order would, and sorting the
  list changed every seed's dungeon. Seeds 12345, 42 and 77141 had 55, 48 and 62
  rooms at spawn unsorted, and 48, 60 and 23 sorted. So the review's per-seed
  numbers describe the sorted order, not what the unsorted code built. Sort in
  code-point order, which does not depend on a machine's locale, so that every
  machine builds the same map from the same seed. That matters most when a
  multiplayer host sends only the seed.
- **Advance the seed for every decision.** Read in the code: each required room
  was placed at the midpoint of its depth range without touching the seed, so
  the range was a constant.
- **Key the seed to the position.** Read in the code, and this part the case
  study got right: the seed for a cell is hashed from the sector seed, the
  cell's position and the face it is reached through, so what appears at a cell
  does not depend on loop order.
  The review adds a salt per stage, so changing one stage cannot reshuffle the
  next.

## Pace with beats, not a filler roll

Read in the code. Rooms with no special role rolled a type from a hash: 55%
empty, 20% monster, 12% treasure, 8% trap and 5% shrine. Rooms outside the plan
only ever got this roll.

The review replaces it with a short cycle of beats for each sector's spine. For
the first sector that is traversal, combat, combat, hybrid, combat, traversal.
Branch interiors alternate combat and traversal, and every branch ends in a
reward. For whoever authors the rooms, the beat list is the shopping list: it
says how many rooms of each role a sector needs.

## Settings nobody reads

Read in the code. The sector settings carried an enemy density and a difficulty
curve that nothing read, and the planner wrote a room hint onto each node that
the placer never looked at. A setting that does nothing is worse than none,
because people tune it and see no change. A test that changes each setting and
expects the map to change would have caught all three.

## Measure every seed

Print these for every seed, over at least 1000 seeds, as minimum, median and
maximum:

- rooms at spawn, and rooms after walking a few steps
- plan nodes placed, out of the total
- boss rooms placed, and how many the plan holds
- the share of each role, corridors in particular
- extra copies of rooms that should appear once
- rooms outside the plan
- placement fallbacks, by kind

Every finding on this page showed up in those numbers before anyone had to play
the map. A browser port made the sweep cheap, but only while it stays in step
with the game. Measured in Godot 4.6 by the implementation's test runs, the
port's version of the proposal and the built game made identical plans in all
500 seeds compared and identical placements in 492. In all 8 that differed, the
game's extra fallbacks placed a node the port dropped.

## Measured after the refactor

Measured in Godot 4.6 by the implementation's test runs over seeds 1 to 1000,
in Gaoler's pull requests #10, #12, #13 and #14 (branch
`level/pr4-minimap-sectors` at `5238ffc`). Every sector placed its whole plan
in all 1000 seeds, with no node dropped and exactly one boss.

| Sector | Rooms, median | Seeds that needed a branch re-rooted | Corridor share, median |
|---|---|---|---|
| alpha | 12 | 505 | 0% |
| beta | 18 | 623 | 5.3% |
| gamma | 18 | 773 | 5.6% |
| delta | 19 | 723 | 0% |
| core | 11 | 189 | 0% |

In the first sector, alpha, the rooms were 27.8% combat, 11.1% vault, 8%
traversal and 5.3% hybrid, with each set piece at 8%.

The same sector beside the port. The port's columns were run over the same
seeds, in sorted room order:

| Alpha, seeds 1 to 1000 | Current generator, run in the port | Proposed generator, run in the port | After the refactor, measured in Godot 4.6 |
|---|---|---|---|
| Rooms at spawn, median (range) | 59 (19 to 105) | 12 (9 to 16) | 12 |
| Plan nodes placed, median | 44% | 100% | 100% |
| Seeds with the whole plan placed | 20 | 977 | 1000 |
| Boss rooms in the plan | 2 in every seed | 1 in every seed | 1 in every seed |
| Seeds that needed a branch re-rooted | none reported: dead-end fallbacks are silent | 471 | 505 |
| Seeds that dropped a node | not reported | 23 | 0 |

The built game re-roots in more seeds than the port and drops none. Its extra
fallbacks are listed under
[Build the map from the plan](#build-the-map-from-the-plan-not-the-plan-from-the-map).

See also [Ground relief and blending](/guide/ground-and-relief), whose later
parts cover what map code has to get right underneath the rooms, and
[Facings and camera angles](/guide/facings) for matching figures to 2 to 1
floor tiles.

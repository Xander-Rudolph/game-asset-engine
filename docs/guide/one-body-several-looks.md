# One body, several looks

*Several characters from one rigged body, each with its own build, skin, hair,
garments and kit, all playing the same clips and all fitting the same sprite
cell.*

A 2.5D isometric game made with the engine gave each of its seven character
classes a sprite set of its own this way on 2026-10-09. Every set kept the base
figure's clips, frame picks, camera, cell and strike frames, so the game swaps a
whole set per class and nothing else changes. It builds on
[Quaternius clips on an MPFB body](/guide/animation#quaternius-clips-on-an-mpfb-body).
The game's scripts are its own, and are described here rather than copied.
Numbers credited to the game come from its notes and were not re-run.

## Share one MPFB install

MPFB keeps its add-on, its asset packs and its user data in one user folder. The
game pointed every look at a single copy of it rather than one copy per look:
630,107,471 bytes, measured with `du -sb` on 2026-10-09. Each look's builds,
textures and sheets went in a folder of their own beside it.

## Check each asset's own licence entry

MPFB's pack loader writes a JSON file for each pack, with a `license` field for
every asset in it. Read that field for each asset you use, not the pack's name:
the shoe pack, downloaded as `shoes01_cc0.zip`, lists a pair of boots as CC-BY
(its installed JSON, read on 2026-10-09), and the game left them out. It also left out three meshes marked CC0 that are modelled on
named characters from other works, on the reasoning that a mesh's author cannot
license a character design they do not own. Its build looks every asset up again
when it builds and writes the licence into the build's JSON, so the record
cannot drift from what was built. [Licensing](/guide/licensing) has the wider
rules.

## Not every garment follows the rig

Put each garment through a clip before you use it. One CC0 pair of gloves kept
its right glove's fingers spread as the rest pose had them, whatever the hand
did, and the game dropped it. Three more garment faults from the game's notes:

- **Skin through the cloth.** The packs' garments carry no delete groups, so the
  calves showed through the trousers. Mask the body wherever a garment covers
  it, tested on the body as shaped: MPFB keeps its macro sliders as shape keys,
  so the plain vertex positions are the neutral base mesh, and testing those cut
  a hole along the jaw.
- **Boots inside the trousers.** Drop the trouser legs below the boot tops, and
  mask the body under both.
- **A normal map painted over.** A recolour that replaced every image on a
  garment except those named "normal" also replaced a pair of boots' maps named
  `-norm` and `-spec`. Swap only the colour map, MPFB's `diffuseTexture` node.

## Fit one kit to every body

The kit, the straps, plates, packs and visors the game's script builds, is
written once in the base figure's frame and mapped onto each look's body by its
joints: heights piecewise between the foot, knee, hip, spine, neck and head
joints, and widths by the hip and shoulder joints. The joints come from a probe
build of each body with no kit on it. Pieces held by a bone are not mapped, and
pieces on the face are placed from that look's own eye height.

## Keep every look inside one cell

Scale each figure to its height measured without hair or a hood, then measure
reach and height on every frame of every sheet against the cell, before
rendering anything. The game's cell, read from its framing, allows at most 1.28
units from the figure's axis, with a reach budget of about 1.15, and a screen
height from -0.40 to 2.16.

Every look fitted, measured by the game over every frame on 2026-10-09. Two
moments set the limits:

- **Reach: the charge glow.** The furthest reach on every look was a charged
  punch's glow at contact, which extends past the fist: 0.993 to 1.134 units.
  Measure a glow's mesh as well as the body.
- **Height: a cast's raised hand**, up to 2.138 on the broadest look. At 2.13
  tall, that look's cast reached 2.169, past the cell, so it stands at the base
  figure's 2.1.

On screen the front idles stood 73 to 79 px tall against the base figure's 76
(the game's in-game comparison, alpha above 200, shadow left out).

## Glows clip under the Standard view

`render_sheet.py` renders with Blender's Standard view transform (read from the
script), which clips each colour channel at 1. So a coloured glow keeps its hue
only while its strength times its brightest channel stays near 1, and past that
it runs to white. Taken alone, an amber of (1.0, 0.72, 0.15) at strength 4 comes
to (4.0, 2.88, 0.6), which clips to (1, 1, 0.6), a pale yellow, while at 1.1 it
stays amber (computed, not rendered). The game ran its looks' glows at 1.1 where
the base figure's near-white glows ran at 4.0, and scaled every animated glow key
by 0.4, so a coloured glow keeps its hue through the animation.

## Rendering on the CPU while the card is busy

[Sharing one card](/guide/troubleshooting#out-of-memory-when-several-jobs-share-the-card)
can mean a long wait. The game rendered one look's five sheets on the card and,
while other jobs held it, the other thirty on the CPU. `render_sheet.py` has no
switch for that. The game emptied `CUDA_VISIBLE_DEVICES` inside the Blender
script the tool runs, so Cycles found no CUDA device and the script took the CPU
path it takes on a machine without one, warning as it does, and passed
`--no-wait`, since that wait is for the card. On the CPU a sheet took 17 to 27 s,
where the card's idle sheets had taken 17 to 21 s (the game's notes).

The two agree. A CPU render of one look's idle sheet differed from its GPU render
in 9 of its 3,145,728 pixels by more than 8 levels, the largest by 44 (the game's
comparison). That is a different question from
[two render engines](/guide/render-engines), where mixing Cycles and EEVEE puts
about 11% of a figure's lit pixels 10 or more levels apart.

To judge a kit while the card was busy, the game also rendered four views on the
CPU at 12 samples, about 20 s for four 400 px views by its script's own note, and
never used them for a sheet.

## Which choices can be undone

- **One body per look.** Each body is one block of its look's config, so it can
  change later. A second body per look would need a choice in the game and twice
  the sets, so the game left that for later.
- **Generated configs.** The looks' configs are written by a script from the base
  figure's config, so edit the script rather than a generated file. Clips, frame
  picks, sheets, rest pose and shadow come from the base as they are, and a clip
  added there reaches every look on the next run.
- **New build options, switched off.** The game's five new build options default
  to off, and the base figure, rebuilt with them, matched its shipped build
  exactly: height, scale, extents, masked vertices, strap faces, box hits and
  every bone head.

All 35 sheets, five for each look, rendered with the base figure's flags and
`--check`, which found no fault (the game's run, 2026-10-09).

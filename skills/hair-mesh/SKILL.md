---
name: hair-mesh
description: Grow a stylised hair-card mesh with a parting and its own diffuse and opacity maps, look at it, and put it on a figure. Use when the user says "make a hairstyle", "generate hair for this character", "I need hair cards" or wants hair that can ship, unlike a Daz hair product. Writes OBJ, MTL and two PNGs the repo owns outright.
---

# Hair mesh: cards grown on a scalp, with maps, that may ship

Work in the asset-engine repo root. The script is `scripts/make_hair.py`; the
long version, with the measurements and what failed on the way, is
`docs/reference/scripts.md`, "make_hair.py".

Every number below was measured on 2026-09-22 on this host: the generator on the
host's `python3` (numpy 2.3.5, Pillow 12.1.1), the renders in the container's
Blender 4.5.9 on Cycles on the RTX 4070 Ti SUPER.

## Why this exists

The other two routes to hair stop short.

- **A Daz hair product** is Daz 3D data. It renders, but it may not ship as 3D
  without an Interactive License for that product (`daz-figure` skill, step 1).
- **A strand hair** is empty, not just licence-bound: the two in the library
  carry 236,136 and 167,264 vertices and **no polygons at all**, so Cycles draws
  the cap and nothing else. `scripts/daz_characters.py` leaves them out and says
  so.

What this writes is polygons, with maps, that the repo owns outright.

## What it makes, and what it does not

Five files in `output/hair/`: `<name>.obj`, `<name>.mtl`, `<name>_diffuse.png`,
`<name>_opacity.png`, `<name>.json` with every setting and measurement, and,
unless `--no-preview`, `<name>_preview.obj`, the hair on a plain scalp sphere.

It is **static geometry**: no rig, no fitting, no morphs, no physics. It is
placed on a head, not skinned to one.

## The one command

```sh
scripts/make_hair.py --list                       # styles and colours
scripts/make_hair.py --style wavy --colour brown  # the default: a stylised bob
scripts/make_hair.py --style long --colour blond --part left --name lyra
```

Styles set the shape: `wavy`, `straight`, `curly`, `short`, `long`. Colours:
`black`, `brown`, `auburn`, `red`, `blond`, `grey`, `white`, or `R,G,B` in sRGB
0 to 255. `--part` is `centre`, `left`, `right`, `none` or an x from -1 to 1.
Every number a style or a look sets is also a flag, so "longer but keep the
waves" is `--style wavy --length 24`.

`--look stylised`, the default, gathers the cards into locks, draws three hard
edged strands per card, keeps half the root to tip colour range and lays a
highlight band across the upper length. `--look realistic` leaves every card to
itself with seven fine wispy strands, the full range and no band.

### Six that were built and looked at

| Name | Command |
|---|---|
| bob | `--style wavy --colour brown --part centre` |
| curtains | `--style straight --colour blond --part left --length 30` |
| crop | `--style short --colour black --part none --length 5 --volume 0.6` |
| curls | `--style curly --colour auburn --part centre --length 20` |
| elder | `--style long --colour white --part centre --length 34` |
| bounce | `--style wavy --colour red --part right --length 20 --volume 2.6` |

## Look at it before putting it on anything

```sh
scripts/render_sheet.py output/hair/<name>_preview.obj \
    --azimuths 0,90,180 --elevation 0 --size 560 --key 6.5 --ambient 1.3 \
    --out output/hair/<name>_preview.png
```

The preview has no figure in it, so it can be shown and looked at freely. 3
cells at 560 px took 1.7 s wall on Cycles on the card.

## The two things that decide whether it reads as hair

**Cylindrical card normals, `--round`.** This is worth more than everything else
here put together. A card with one flat normal shades like paper: a fringe in
front of a face is square to the camera, the key sun is overhead, and the card
catches none of it, so the fringe renders black while the crown is lit. At
`--round 62` each card's two edges carry normals tilted out about the strand and
the card shades like a clump of round hairs. Same hair, same maps, same light:
**mean luma 16.5 flat against 51.7 round, 3.12 times as bright.**

**Card density, which the script prints.**

```
  layers    3.2 cards deep: 4256 cm2 of card over 1334 cm2 of head
```

**Aim for 3 to 5.** At 8.8, which 1,400 cards of 0.9 cm gave, a ray crosses nine
dark cards, almost none of the light gets out and the hair renders as a black
mass. Raise or lower it with `--strands` or `--width-root`.

## Putting it on a Genesis figure

```sh
scripts/daz_import_probe.py scene --out output/daz/NAME.blend \
    --figure "People/Genesis 9/Genesis 9.duf" --subdivision off --declip 1.5 \
    --mat-preset "People/Genesis 9/Materials/Daz Originals/Base Materials/G9 Masculine Skin 01 MAT.duf" \
    --wear-obj output/hair/<name>.obj --obj-no-shadow
scripts/render_sheet.py output/daz/NAME.blend --azimuths 0,45,90 --elevation 6 \
    --size 560 --span 0.46 --look-at 1.60 --key 5.5 --ambient 1.5 \
    --out output/daz/NAME_head.png
```

- `--wear-obj` fits a sphere to the upper half of the `head` bone's own skin,
  puts the OBJ's origin at its centre and scales it so the roots land on it. On
  Genesis 9 that sphere is **8.26 cm, centred 162.1 cm up**, and 636 skull
  vertices sit within 4.6 mm of it. `--obj-offset DX,DY,DZ` in millimetres and
  `--obj-yaw DEG` are there if the report says they are needed.
- **`--obj-no-shadow`.** Cards three layers deep shadow each other. Same hair,
  same light: **mean luma 38.7 casting, 51.7 not.**
- **`--declip 1.5`.** Without it 11.24% of the hair's vertices sat inside the
  body at the neck; with it, 0.00%.
- **`--mat-preset`, not `--mat-replace`, for the base figure.** The base
  Genesis 9 materials have no maps linked, so there is nothing to swap and the
  swap silently does nothing: it renders with a blown-out white face.
- **`--span 0.46 --look-at 1.60`** frames the head. Without `--look-at` the
  camera aims at half the frame and a small span gives the knees.

**The figure is still Daz.** Everything in `docs/reference/daz-genesis.md`
applies to the render and the `.blend`: renders may ship on conditions, the 3D
data may not, and none of it goes near an AI stage. The hair itself is not Daz
and carries none of that. You may open the render and say how it looks (the
owner allowed it on 2026-09-22).

## What to check before saying it worked

- `layers` is 3 to 5, and `--round` is not 0.
- On a figure, the fit report says `0.00%` inside after the declip.
- Open the head render. The face should be visible: long hair is brushed out to
  the sides by `--sweep` as it falls, and at `--sweep 0` it hangs flat over the
  nose and the declip then pushes it onto it.
- The parting reads as a line, not a wedge of bare scalp. Lower `--part-flow` or
  `--part-width` if it does not.
- The opacity PNG is **RGBA**. Blender's OBJ importer wires `map_d`'s image
  *Alpha* output into Principled Alpha, and a greyscale PNG has no alpha
  channel, so that output is 1.0 everywhere and the hair renders as solid cards
  with blunt ends. The script writes the mask into all four channels.

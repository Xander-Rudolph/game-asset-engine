---
name: hair-mesh
description: Grow a hair-card mesh with its own diffuse and opacity maps, look at it, and put it on a figure. Use when the user says "make a hairstyle", "generate hair for this character", "I need hair cards" or wants hair that can ship, unlike a Daz hair product. Writes OBJ, MTL and two PNGs the repo owns outright.
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

Four files plus a preview, in `output/hair/`: `<name>.obj`, `<name>.mtl`,
`<name>_diffuse.png`, `<name>_opacity.png`, `<name>.json` with every setting and
measurement, and `<name>_preview.obj`, the hair on a plain scalp sphere.

It is **static geometry**: no rig, no fitting, no morphs, no physics. It is
placed on a head, not skinned to one.

## The one command

```sh
scripts/make_hair.py --list                       # styles and colours
scripts/make_hair.py --style wavy --colour brown
scripts/make_hair.py --style long --colour blond --name lyra
```

Styles: `wavy`, `straight`, `curly`, `short`, `long`. Colours: `black`, `brown`,
`auburn`, `red`, `blond`, `grey`, `white`, or `R,G,B` in sRGB 0 to 255. Every
number a style sets is also a flag, so "longer but keep the waves" is
`--style wavy --length 24`.

## Look at it before putting it on anything

```sh
scripts/render_sheet.py output/hair/<name>_preview.obj \
    --azimuths 0,90,180 --elevation 0 --size 560 --key 6.5 --ambient 1.3 \
    --out output/hair/<name>_preview.png
```

The preview has no figure in it, so it can be shown and looked at freely. 3
cells at 560 px took 1.7 s wall on Cycles on the card.

## The number that decides whether it reads as hair

The script prints it:

```
  layers    3.2 cards deep: 4256 cm2 of card over 1334 cm2 of head
```

Card area over the area the hair covers. **Aim for 3 to 5.** At 8.8, which
1,400 cards of 0.9 cm gave, a ray crosses nine dark cards and the hair renders
as a black mass with a hard silhouette. Raise it with `--strands` or
`--width-root`, lower it the same way.

`--hairs` (default 7) is how many strands are drawn inside each card's slot in
the maps. One blob per card ends in blunt rectangles and reads as straw.

## Putting it on a Genesis figure

```sh
scripts/daz_import_probe.py scene --out output/daz/NAME.blend \
    --figure "People/Genesis 9/Genesis 9.duf" --subdivision off --declip 1.5 \
    --wear-obj output/hair/<name>.obj
```

`--wear-obj` fits a sphere to the upper half of the `head` bone's own skin, puts
the OBJ's origin at that sphere's centre, scales it so the roots land on it, and
bone-parents it so it follows a pose. On Genesis 9 that sphere is **8.26 cm,
centred 162.1 cm up**, and 636 skull vertices sit within 4.6 mm of it. Nothing is
guessed: `--obj-offset DX,DY,DZ` in millimetres and `--obj-yaw DEG` are there if
the report says they are needed.

`--declip` reaches the OBJ too. Without it **11.24%** of the hair's 9,600
vertices sat inside the body, at the neck and shoulders; `--declip 1.5` moved
1,830 of them out by at most 8.38 mm and left **0.00%** inside.

**The figure is still Daz.** Everything in `docs/reference/daz-genesis.md`
applies to the render and to the `.blend`: renders may ship on conditions, the
3D data may not, and none of it goes near an AI stage. The hair itself is not
Daz and carries none of that.

## What to check before saying it worked

- `layers` is 3 to 5.
- The preview render shows the crown covered and the strand tips feathered, not
  square.
- On a figure, the fit report says `0.00%` inside after the declip.
- The opacity PNG is **RGBA**. Blender's OBJ importer wires `map_d`'s image
  *Alpha* output into Principled Alpha, and a greyscale PNG has no alpha
  channel, so that output is 1.0 everywhere and the hair renders as solid cards
  with blunt ends. The script writes the mask into all four channels.

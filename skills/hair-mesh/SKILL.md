---
name: hair-mesh
description: Grow a stylised head of hair the repo owns, as lens-shell locks and cards over a scalp cap with a rendered atlas, look at it, and put it on a figure. Use when the user says "make a hairstyle", "generate hair for this character", "I need hair cards" or wants hair that can ship, unlike a Daz hair product. Writes OBJ, MTL and maps.
---

# Hair mesh: locks grown on a scalp, with maps, that may ship

Work in the asset-engine repo root. Two scripts: `scripts/make_hair.py` lays
the hair out with numpy and `scripts/bake_hair.py` turns it into geometry in
the container's Blender; the first runs the second. The long version, with
every measurement and what failed on the way, is `docs/reference/scripts.md`
("make_hair.py" and "bake_hair.py"); the research it was built from is
`docs/reference/hair-cards.md`.

Every number below was measured on 2026-09-22 on this host: numpy 2.3.5 and
Pillow 12.1.1 on the host's `python3`, Blender 4.5.9 in the container, Cycles on
the RTX 4070 Ti SUPER.

## Why this exists

The other two routes to hair stop short.

- **A Daz hair product** is Daz 3D data. It renders, but it may not ship as 3D
  without an Interactive License for that product (`daz-figure` skill, step 1).
- **A strand hair** is empty, not just licence-bound: the two in the library
  carry 236,136 and 167,264 vertices and **no polygons at all**, so Cycles draws
  the cap and nothing else. `scripts/daz_characters.py` leaves them out.

What this writes is polygons the repo owns outright: closed lens shells for the
big locks (the construction the stylised references use), flat alpha cards
over them, a scalp cap under them, and an atlas rendered from real strands.

## The one command

```sh
scripts/make_hair.py --list                                  # styles, looks, colours, layers
scripts/make_hair.py --style wavy --colour brown --part centre --name bob
```

That writes `output/hair/bob_guides.npz`, the atlas plan, the cap, a numpy-only
fallback OBJ and a preview, then runs `scripts/bake_hair.py bob` in the
container and writes **`output/hair/bob.obj`**, its `.mtl`, `bob_diffuse.png`
(RGBA), `bob_opacity.png` and `bob_pack.png`, plus `bob.json` and
`bob_bake.json` with every number. About four seconds: 1.0 to 1.3 s of numpy
and 2.6 to 2.9 s wall in Blender. `--no-bake` stops after the numpy files.

Styles set the shape: `wavy`, `straight`, `curly`, `short`, `long`. Colours:
`black`, `brown`, `auburn`, `red`, `blond`, `grey`, `white`, or `R,G,B` in sRGB
0 to 255. `--part` is `centre`, `left`, `right`, `none` or an x from -1 to 1.
`--look stylised` (default) clusters at 4.5 cm and lays a highlight band;
`--look realistic` clusters at 2.5 cm with no band and has not been rendered
since the rewrite. Every number a style sets is also a flag, and
`--layers shell=120,flyaway=0` overrides a layer's count.

### Six that were built and looked at on the figure

| Name | Command | Baked triangles |
|---|---|---|
| bob | `--style wavy --colour brown --part centre` | 14,436 |
| curtains | `--style straight --colour blond --part left --length 30` | 14,436 |
| crop | `--style short --colour black --part none --length 5 --volume 0.6` | 18,378 |
| curls | `--style curly --colour auburn --part centre --length 20` | 19,296 |
| elder | `--style long --colour white --part centre --length 34` | 15,750 |
| bounce | `--style wavy --colour red --part right --length 20 --volume 2.6` | 14,436 |

All six keep the face clear and sit inside the 4k to 20k triangle budget the
research gives. The long two hang down the neck and turn at the shoulders:
strands slide over five body capsules measured on Genesis 9 (`--no-drape`
switches that off), and the preview OBJ draws the capsules in grey.

## Look at it before putting it on anything

```sh
scripts/render_sheet.py output/hair/bob.obj --azimuths 0,90,180 --elevation 0 \
    --size 560 --key 6.5 --ambient 1.3 --out output/hair/bob_sheet.png
```

No figure in it, so it can be shown freely. Open the PNG and look.

## What the reports must say

`make_hair.py` prints, and `bob.json` keeps:

- `winding   face normal . radial +0.951 mean (cap +1.000, shell +0.917, card +0.940); must be positive`.
  The old generator wound every face into the head, which is what made the
  hair render black; a negative number here is that bug back.
- `roots     poisson: 90 shell, 150 breakup (50 tents), 40 hairline, 30 flyaway`
  and `locks     14 of 14 centres at 4.5 cm`.

`bake_hair.py` prints, and `bob_bake.json` keeps:

- `shells    90 lens shells, 11160 triangles ..., manifold, signed volume ... (all wound outward)`.
- `mesh      8853 vertices, 14436 triangles`, and a warning if it is outside 4k to 20k.
- `normals   corner dot radial ... before export, ... after re-import` (0.9979 on the bob).
- `axes      cap block in the written OBJ against bob_cap.obj: max error 0.000001 cm`.

## Putting it on a Genesis figure

```sh
scripts/daz_import_probe.py scene --out output/daz/h_bob.blend \
    --figure "People/Genesis 9/Genesis 9.duf" --subdivision off --declip 1.5 \
    --mat-preset "People/Genesis 9/Materials/Daz Originals/Base Materials/G9 Masculine Skin 01 MAT.duf" \
    --wear-obj output/hair/bob.obj --obj-no-shadow
scripts/render_sheet.py output/daz/h_bob.blend --azimuths 0,45,90 --elevation 6 \
    --size 560 --span 0.46 --look-at 1.60 --key 5.5 --ambient 1.5 \
    --out output/daz/h_bob_head.png
```

- `--wear-obj` fits a sphere to the upper half of the `head` bone's own skin,
  puts the OBJ's origin at its centre and scales it so the roots land on it. On
  Genesis 9 that sphere is **8.26 cm, centred 162.1 cm up**, and 636 skull
  vertices sit within 4.6 mm of it. `--obj-offset DX,DY,DZ` in millimetres and
  `--obj-yaw DEG` are there if the report says they are needed.
- **`--declip 1.5`.** The bob had 4.53% of its vertices inside the body before
  it and 0.00% after.
- **`--obj-no-shadow`.** Cards three deep shadow each other by about 11%.
- **`--mat-preset`, not `--mat-replace`, for the base figure.** Its materials
  have no maps linked, so a swap finds nothing and the face renders white.
- **`--span 0.46 --look-at 1.60`** frames the head; without `--look-at` a small
  span gives the knees.

**The figure is still Daz.** Everything in `docs/reference/daz-genesis.md`
applies to the render and the `.blend`: renders may ship on conditions, the 3D
data may not, and none of it goes near an AI stage. The hair itself is not Daz
and carries none of that. You may open the render and say how it looks (the
owner allowed it on 2026-09-22).

## What to check before saying it worked

- Every `winding` figure is positive and the bake reports every shell manifold.
- The baked triangle count is inside 4k to 20k, or the user asked for more.
- Open the head render: the face is clear, the parting reads as a line, no
  skin shows through the crown, and no shell wears a dark band down its flank
  (that band was a texture wrap the bake now maps round; if it is back, look at
  `shell_outward_face` in the bake report, which must be positive).
- The opacity PNGs are **RGBA**. Blender's OBJ importer wires `map_d`'s image
  *Alpha* output into Principled Alpha, and a greyscale PNG has none.
- Nothing from `output/daz/` is committed, and no Daz render reaches an AI stage.

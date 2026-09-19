# Two render engines

::: tip Status: measured on 2026-09-18
Every number and image on this page was produced on the reference machine, an
RTX 4070 Ti SUPER with 16,376 MiB beside an i7-14700K, in the packaged
container on `bpy` 4.5.9 LTS. The four pairs were rendered by
`scripts/render_sheet.py`, one job at a time with nothing else running, each
pair identical apart from `--engine`. Nothing here was read from a manual.
:::

`scripts/render_sheet.py` draws a sheet with Cycles on the graphics card by
default, and with EEVEE on `--engine eevee`. Cycles has been the default since
2026-09-18. This page is the comparison that decided it, kept so the choice can
be argued with rather than taken on trust.

## Why EEVEE is the slow one here

EEVEE needs a graphics context, and this container has none. The NVIDIA
runtime gave it the driver's compute libraries and not its graphics ones:
`libEGL_nvidia.so.0` is present, `libnvidia-eglcore` is not, and forcing the
NVIDIA vendor ends in `EGL Error (0x300C): EGL_BAD_PARAMETER`. Blender falls
back to Mesa's `llvmpipe` and rasterises on the processor.

Cycles needs no graphics context. It finds the card through CUDA and path
traces there. OptiX is not available, because that wants the same missing
libraries, but plain CUDA is enough.

Giving the container `capabilities: [gpu, graphics, display]` in
`docker-compose.yml` would put EEVEE on the card too, at the price of
recreating the container. It has not been tried.

## What it costs

The same 16 cell sheet, `output/assets/alchemist_warrior/rig.fbx` with a
compiled walk, four poses across four angles:

| | EEVEE, `llvmpipe` | Cycles, CUDA |
|---|---|---|
| Whole sheet | 108.7 s | 3.12 s |
| One 128 px cell | 5.97 s | 0.138 s |
| Peak host memory | 2,386 MB | 869 MB |
| Card memory | none | 1,531 MiB of 16,376 |
| Samples by default | 64 | 128 |

The software renderer is what costs the host memory, so moving to the card
takes less of it, not more.

## What it changes

The two are the same drawing with occlusion added. Across the walk sheet, 95%
of lit pixels move by less than 3.2 levels of 255, and whole-cell mean
absolute difference is 0.85 of 255. The engines part where light has to bend
around something.

### Clay, where form has to read

![The same mesh in clay, four angles, EEVEE against Cycles with a difference
map](/engines/basilisk_clay_compare.png)

EEVEE renders the belly, the underside of the jaw and the gap between the
front leg and the body at nearly the value of the lit chest. Cycles separates
all three. On this mesh 40.5% of the creature's pixels are darker in Cycles
and 8.4% are darker by 10 levels or more, against a mean brightness of 131.88
on EEVEE and 129.92 on Cycles.

![One clay cell at three times, with the difference
map](/engines/basilisk_clay_detail.png)

That matters most for `--clay`, which exists so shape reads without a texture
to hide behind.

### A textured asset

![The textured creature at 128 px, EEVEE against Cycles](/engines/basilisk_detail.png)

The silhouette and the colours are the same. Cycles darkens the same hollows
and runs the emissive stripes hotter, because it bounces that light and EEVEE
at factory settings does not: `scene.eevee.use_raytracing` is off out of the
box.

### A rigged figure

![One walk cell at three times, EEVEE against Cycles](/engines/walk_rig_detail.png)

The cloak lifts off the leg and the arm separates from the chest. On this
sheet 59.6% of lit pixels are darker in Cycles, 10.8% by 10 levels or more.

### A mouth on a portrait

![The same head at six times, neutral and an open viseme, on both
engines](/engines/visemes_mouth.png)

Over a 54 by 44 pixel head crop, going from neutral to an open viseme moves a
pixel by at most 37 levels on EEVEE and 89 on Cycles. The mouth is a dark
cavity on one and a smudge on the other, which is the difference between a
portrait that reads as talking and one that does not. See
[talking portraits](/guide/talking-portraits).

## Reading a difference map

The maps above amplify the difference eight times, so a 2 level change looks
like 16. Red is darker in Cycles, cyan brighter.

::: warning One engine for a whole set
The two are not interchangeable. Mixing them puts about 11% of a figure's lit
pixels 10 or more levels apart between frames, measured on the walk sheet, and
12.4% on a second sheet at a different size. Re-render a set whole rather than
topping it up, and check the `engine` line a run prints, or the `engine` field
in the RENDERED json, before matching new frames to old ones. Sheets in this
repository from before 2026-09-18 were drawn with EEVEE.
:::

## Which to use

- **Cycles, the default.** Anything new, and anything where form or a mouth has
  to read.
- **EEVEE, on `--engine eevee`.** Matching a set drawn before the switch, and
  any run where the card is wanted for something else. It is the only engine
  the Daz probe and the MakeHuman probe use, so their recorded numbers stay
  comparable ([Daz figures](/guide/daz-figures)).

Cycles takes the card that image generation also uses, where an edit peaks near
15 GB of the same 16,376 MiB, and a collision is a CUDA out-of-memory error
rather than a fallback. So a Cycles render waits for ComfyUI's queue to empty
and for any other Blender job to finish, polling every 30 seconds. `--no-wait`
skips the check and `--max-wait` bounds it. EEVEE never waits, because it never
touches the card.

## What was not measured

- No existing set has been re-rendered on Cycles.
- `--persp`, `--span`, `--flat` and non-default `--key` or `--ambient` have
  never been drawn by Cycles.
- Cycles stops on an adaptive sampling threshold, 0.01 at factory settings,
  which nothing here varies, so 128 samples is a ceiling rather than the real
  knob.
- `--denoise` was measured only at 16 and 128 samples. It costs about 62% more
  time per cell and changes almost nothing at 128.
- EEVEE with `scene.eevee.use_raytracing` on was measured once, on the clay
  mesh: it moves the lit surface past Cycles' value for 40.10 s against
  34.42 s on four cells, and its mean difference from Cycles rises rather than
  falls.

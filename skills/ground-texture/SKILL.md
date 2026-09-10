---
name: ground-texture
description: Generate a tileable ground or terrain texture and make it repeat without a visible seam. Use when the user wants terrain, ground, floor, wall or surface textures, tileable or seamless textures, or asks why their texture shows a grid or seam when it repeats.
---

# Ground textures: generate flat, then make it tile

Ground is the one asset type here that never becomes a mesh. Work in the
asset-engine repo root.

## Before you start

```sh
scripts/doctor.py --skip-models
```

The seam tool runs on the host and needs `numpy` and `Pillow`. The generation
step needs the server. If the doctor is not ready, follow the one command it
prints rather than working around it.

## 1. Generate at 1024, not 512

```sh
scripts/run_workflow.py workflows/api/preset_ground_texture.json \
    --prompt 'dense woodland floor of fallen leaves, moss, twigs and needles'
```

Or generate a whole set from the prompt library:

```sh
scripts/generate_concepts.sh prompts/ground
```

The preset carries a fixed sentence and **only the subject phrase should
change**. Every other clause is preventing one specific failure:

| Clause | Stops |
|---|---|
| photographed from directly overhead looking straight down | A horizon appearing |
| the same density everywhere | Detail bunching in the middle |
| no large shapes and no focal point | A composition with a subject |
| like a close macro crop of a much larger surface | Reading at the wrong scale |
| flat shadowless overcast light | Baked shadows fighting the engine's lighting |

The negative includes mosaic, tiles and bricks on purpose. Ask for a tileable
texture and the generator will draw a picture of tiles.

## 2. Make it tile

The output is **not tileable**. Nothing in this install generates tiling
textures, because there is no circular padding decode and no tiled sampler. Say
this to the user rather than letting them discover a grid across their map.

```sh
scripts/make_seamless.py output/ground/texture_00001_.png \
    --out output/materials/forest.jpg --size 1024 --check
```

## 3. Read the numbers, both of them

`--check` prints a ratio and an absolute figure, and you need both.

The **ratio** compares how much the edge columns differ against how much any two
adjacent columns differ. Edges of a tiling texture are neighbours, so 1.0 is
seamless. Good materials score 1.0 to 1.2.

The **absolute** figure is in levels out of 255.

**The ratio lies about smooth textures.** A water texture scored 2.06 by ratio
while its edges differed by 2.1 levels out of 255, which no eye will ever see.
Acting on the ratio alone, the tool once repaired a working texture into a worse
one. It only complains when both numbers agree, and you should apply the same
rule when reading them.

Also watch the contrast figure. Below about 8 the texture reads as a painted
rectangle at map scale, and the tool warns. This project has shipped a flat
rectangle for a desert before.

## 4. Look at it tiled, not flat

A texture can score well and still look wrong when repeated. Check it:

```sh
python3 -c "
from PIL import Image
im = Image.open('output/materials/forest.jpg')
w,h = im.size
sheet = Image.new('RGB', (w*3, h*3))
for y in range(3):
    for x in range(3): sheet.paste(im, (x*w, y*h))
sheet.resize((w, h)).save('output/materials/_forest_tiled.png')"
```

Then Read that file. What you are looking for is anything that repeats
recognisably: a bright patch, a distinctive stone, a butterfly pattern through
the middle. All three read as wallpaper on a map even when the seam itself is
perfect.

## What does not work, so you do not suggest it

- **Rolling the image by half fixes nothing.** It is a phase shift. Measured, it
  took an 81% seam to 78%.
- **Blending a rolled image toward the unrolled one** puts the discontinuity back
  on the edge.
- **Mirroring about the seam** scores almost perfectly and draws a butterfly
  through every tile. The map reads as kaleidoscope wallpaper.
- **Telling the generator not to draw a border** does not stop it. Roughly one
  time in nine it paints a white mat around the texture whatever the negative
  prompt says. The tool trims it automatically by walking in from each edge while
  the rows stay flat, and it caught a 227 pixel border on one attempt.

## Rules

- **One texture per terrain is wallpaper.** Suggest four variants picked by
  hashing the tile position, and boundary blending between different terrains.
- **Blend at half strength from both sides.** Painting a neighbour's ground at
  full opacity along a shared edge, with the neighbour doing the same back, flips
  the boundary rather than softening it.
- **Never hand over a texture you have not seen tiled.**
- Materials go in `output/materials/`. Save as `.jpg` at quality 92 with no
  chroma subsampling for ground, which is what the tool does by default.

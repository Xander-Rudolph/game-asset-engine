# Concept art

The concept image decides the asset. Everything downstream copies it, including
its mistakes. This is the cheapest stage to redo and the most expensive to skip.

## Which workflow to use

| File | Use it for | Time |
|---|---|---|
| `txt2img_qwen_fast.json` | Finding a look. Rerolls in about 30 seconds. | ~30s |
| `txt2img_qwen.json` | The real thing. Negative prompts work here. | ~130s |
| `txt2img_sdxl.json` | Comparison only. Weaker at following prompts. | ~60s |
| `img_edit_qwen.json` | Changing an image you already have | ~90s |

## The fast workflow ignores negative prompts

The fast graph runs at guidance scale 1.0, because that is what the four step
Lightning LoRA needs. At guidance 1.0 there is no negative prompt. Not a weak
one. None at all. The negative text is not used.

This matters because the negative prompt is what keeps ragged hems, clutter and
cartoon styling out of the picture. So the fast graph is for finding a
composition, and the 20 step graph is for producing the image you will actually
build on.

If you are wondering why your carefully written negative prompt did nothing, this
is almost always why.

## How prompts are organised

Prompts live in `prompts/`, one folder per subject type, one text file per
subject. Two files in each folder start with an underscore and are shared:

- `_style.txt` carries the **technique**: one subject, whole thing in frame,
  plain background, even lighting, large readable shapes. Those clauses are the
  same whatever you are making. In the middle of it is an
  `<<< ART DIRECTION: ... >>>` slot. **Replace that one phrase with your
  project's look and change nothing else.**
- `_negative.txt` is passed as the negative prompt for every subject in that
  folder.

That split is deliberate. A shared style file is the single highest-leverage
place to contaminate a whole asset set: bake a house style into the default and
every generation silently carries someone else's project. `prompts/examples/`
holds one project's filled-in version, to show what a completed art direction
looks like. Nothing in the default path reads from it.

Generate a whole folder:

```sh
scripts/generate_concepts.sh prompts/creatures
scripts/generate_concepts.sh prompts/creatures golem chimera   # just these two
```

A single subject can override the shared negative with `<name>.neg.txt`.

::: tip When a shared style fights one subject
The creature lair needed its own negative file. The shared building style talks
about roofs, chimneys and lit windows, and that preamble kept putting a cottage
on top of what should have been a bare cave mouth, however firmly the subject's
own line said otherwise.

If one subject in a folder keeps coming out wrong in the same way, the shared
style is probably describing something the subject does not have.
:::

## Shape of the canvas

Characters and creatures want a portrait canvas, which is the workflow default at
3:4. Buildings want landscape, because an isometric diorama is wider than it is
tall:

```sh
WIDTH=1472 HEIGHT=1104 scripts/generate_concepts.sh prompts/buildings
```

## What a good prompt for this pipeline says

The prompts here are not art prompts. They are instructions for something that
will be converted to 3D, so they are written to make that conversion possible.

Four things every subject prompt states:

1. **The whole subject is in frame** with space around it. A cropped figure
   becomes a cropped mesh.
2. **Plain flat background.** The mesh generators cut the subject out
   themselves, and a plain background makes that reliable. It also lets icons be
   cut out with a flood fill instead of a matting model.
3. **Large simple shapes with a clear silhouette.** Small detail does not survive
   the trip to 3D and then down to a sprite. It becomes noise.
4. **Real materials and lighting.** Say metal, leather and cloth with proper
   shading. Say it plainly, because the alternative is flat vector art, and flat
   art gives the mesh generator nothing to read depth from.

Here is a filled-in character style, as an example of all four:

> Full body head to toe view of a single figure standing upright and facing the
> viewer, the entire figure visible from the top of the head to the boots with
> clear space above and below. Simple bold game ready character design built
> from a few large clean shapes with a strong readable silhouette. Detailed
> painted fantasy illustration with realistic materials and lighting: worn brass
> with real specular highlights, leather with visible grain, woven fabric with
> natural folds, soft cinematic studio lighting and gentle shadows. Plain light
> grey background.

And the matching negative:

> ragged, tattered, torn, ripped, frayed, jagged hem, damaged clothing, dangling
> chains, hanging trinkets, cluttered detail, tiny buckles, busy filigree,
> cartoon, cel shaded, anime, flat vector art, plastic, toy, low detail, blurry,
> cropped, cut off, multiple figures, text, watermark, harsh cast shadow

The ragged and cluttered words are there for a reason. Generators love to add
torn hems and hanging trinkets, and both turn into unreadable geometry.

::: danger Naming a thing in the positive summons it, even to forbid it
This one costs an afternoon to learn. Writing *"no ragged tatters, no tears, no
frayed edges"* into the **positive** prompt produced a **more** tattered coat
every single time.

The split that works: the positive says only what the thing **should be** ("a
smooth even curved hem, pristine, freshly tailored"), and the negative carries
what it must not be. Never negate in the positive.
:::

## Simplifying art you already have

If you have concept art that is too busy to convert, `img_edit_qwen.json` can
redraw it more simply while keeping the same character.

```sh
scripts/simplify_concepts.sh concept_art/unit_*.png
DENOISE=0.93 scripts/simplify_concepts.sh concept_art/lord_*.png
```

### Denoise behaves like a cliff, not a dial

This is the single most useful number on the page.

| Denoise | What you get |
|---|---|
| 0.70 and below | The source dominates. Almost nothing is simplified. |
| 0.85 | Painterly rendering kept, clutter genuinely reduced. Good default. |
| 0.93 | Pushed further to clean game ready forms, still shaded. |
| 1.00 | The model's own style takes over and returns flat vector art, no matter how many times the prompt says not cartoon. |

The cliff moves depending on how busy the source is. Four unit portraits
simplified well at 0.85 and went flat at 1.0. Eight heavily detailed figures,
dense with chains and filigree, were barely touched at 0.85, right at 0.93, and
already flat vector art at 0.97 with their goggles and lanterns gone.

Test one image before running a batch.

## Naming outputs

Outputs are named after the source file, not after ComfyUI's own counter. The
counter records nothing about which input or which settings produced a file, and
becomes unreadable within a dozen runs. When you write your own batch script,
set `Save.filename_prefix` per item.

## Checking a batch without opening a file manager

Every batch script writes a log under `logs/`. But the useful check is to look at
the images. A sheet of them at once:

```sh
scripts/render_sheet.py --help    # for models
```

For flat images, open the folder. There is no substitute for looking. A prompt
that is subtly wrong produces a confident, well rendered, wrong picture, and no
log line will tell you.

# Game Asset Engine

Turn a written description into a textured, rigged, animated game asset, on your
own machine.

ComfyUI in Docker with the 3D, rigging and animation node packs on top, plus the
scripts, prompt libraries, drop in workflows and Claude Code skills to drive the
whole thing from a terminal.

**[Read the guides](https://xander-rudolph.github.io/game-asset-engine/)**

```
"a mossy stone golem"
        |
   concept image       Qwen-Image, about 30 seconds
        |
    3D shape           TRELLIS or Hunyuan3D, under a minute
        |
    textures           colour, metal and roughness maps
        |
    skeleton           UniRig, automatic, no weight painting
        |
  sprite sheet         four or eight facings, one row per animation frame
```

## Quick start

```sh
cp .env.example .env          # set MODELS_DIR to where the weights should live
scripts/fetch_models.py --download --group core --group qwen    # about 68GB
scripts/doctor.py --fix       # checks everything, starts what it can
docker compose --profile packaged up -d
```

The health check looks for the `core` group. The example below runs on
Qwen-Image, which is in the `qwen` group.

Then <http://localhost:8188>, or make something from the terminal:

```sh
scripts/run_workflow.py workflows/api/preset_ground_texture.json \
    --subject "dense woodland floor of fallen leaves, moss, twigs and needles"
```

`--subject` fills the preset's subject slot and keeps its technique text;
`--prompt` would replace the whole text, technique and all. The character,
creature, building and prop presets also carry an `<<< ART DIRECTION: ... >>>`
slot that `--subject` leaves alone; `run_workflow.py` warns about it and
queues anyway. Fill it first, as
[Bring your own art direction](#bring-your-own-art-direction) describes, and run
`scripts/build_presets.py`, or the placeholder reaches the model as literal
text.

There is a [click through notebook](notebooks/asset_pipeline.ipynb) that walks
the whole pipeline one cell at a time.

## What is here

```
scripts/          one script per stage, plus the health check
workflows/api/    graphs, including drop in presets with the settings baked in
prompts/          prompt libraries by subject type, with shared style files
poses/            hand authored animation poses
skills/           Claude Code skills that drive the pipeline
notebooks/        a click through walkthrough
docs/             the documentation site
Dockerfile        CUDA 12.4, Python 3.11, torch 2.6.0, the node packs
models.json       the weight manifest
```

## Is it working?

```sh
scripts/doctor.py
```

Checks Docker, the GPU runtime, your `.env`, the image, the container, the
server, the node packs, Blender and the weights. Prints the single next step
rather than a wall of output. Every skill runs it before doing anything.

## The measured parts

Numbers in these docs come with the tool that produced them.

```sh
scripts/decimation_report.py output/mesh/asset.glb --sprite 128
```

Reports how far the surface moved, how much of the outline was lost, and how far
the texture drifted, at each face budget, rendered from the camera your game
uses. [What the numbers say](https://xander-rudolph.github.io/game-asset-engine/guide/decimation).

## Using this with Claude

This repo is a Claude Code plugin. Point Claude at it and ask for an asset in
plain language; the skills carry the settings, the gates and the checks.

```
/plugin marketplace add Xander-Rudolph/game-asset-engine
/plugin install game-asset-engine@game-asset-engine
```

Or from a shell:

```sh
claude plugin marketplace add Xander-Rudolph/game-asset-engine
claude plugin install game-asset-engine@game-asset-engine --scope user
```

Or skip installing and load your working copy for one session. From the repo
root:

```sh
claude --plugin-dir .
```

Plain `claude` in the repo root does not find the skills. A `skills/` folder at
the root is the plugin layout, and Claude Code only picks up project skills on
its own from `.claude/skills/`.

### What to say

You do not invoke skills by name. Describe what you want and the right one is
picked from its description:

| Say something like | Runs |
|---|---|
| "make me a mossy stone golem for the map" | `asset-pipeline`, prompt to rigged model with a gate at each stage |
| "use that one but swap the shoulder pauldron" | `concept-edit`, changes one element without redrawing |
| "render walk and attack sheets for the golem" | `pose-sheet`, sprite sheets and facings |
| "I need a tileable swamp ground texture" | `ground-texture`, generation plus seam fixing |
| "I need a looping battle theme for the boss fight" | `game-music`, licence-clear music looped without a seam |
| "how many faces should this be" / "rig this 600k mesh" | `mesh-budget`, measured budgets and heavy-mesh rigging |
| "tidy up, I'm done with this asset" | `asset-cleanup`, curate the keepers and sweep the rest |

### What Claude will do first, every time

Run `scripts/doctor.py`. Nothing starts until it says ready, because almost
every confusing failure here is something ordinary the health check looks at
(Docker, the GPU runtime, `.env`, the image, the container, the server, the node
packs, Blender, sparse convolution, the weights, the output folders) that would
otherwise surface much later disguised as a broken workflow. If it is not ready, Claude walks you
through the fix rather than guessing.

### How the skills are meant to behave

Worth knowing so you can tell when something is off:

- **One stage per turn.** Concept art is shown and approved before a mesh is
  built. A rejected mesh three stages later costs far more than a rerolled
  image, so the gates are deliberate. If Claude runs two stages without asking,
  that is a bug.
- **It shows you the picture.** Every generated image is read back into the
  conversation. A printed file path is not a result.
- **It checks rather than assumes.** Face counts, bone names, body counts and
  node availability are read off the running server and the real files, never
  described from memory.
- **It says what it chose and why.** Which generator, which camera angle, what
  it added to your prompt.

### Bring your own art direction

The prompt library ships **technique**, not a look. Each `prompts/*/_style.txt`
carries the clauses that make an image convert cleanly to 3D, with an
`<<< ART DIRECTION: ... >>>` slot in the middle. Put your project's style in
that one phrase and change nothing else.

`prompts/examples/` holds one project's filled-in version so you can see what a
finished art direction looks like. Nothing in the default path reads from it.

### MCP

`.mcp.json` declares the servers this repo expects. Keys come from the
environment, never the repo:

```sh
export MESHY_API_KEY=...
```

### The skills

| Skill | For |
|---|---|
| `asset-pipeline` | Prompt to rigged model, with a gate at every stage |
| `concept-edit` | Change one element of an approved image |
| `pose-sheet` | Sprite sheets, facing sheets, bone poses |
| `ground-texture` | Tileable terrain, and fixing seams |
| `game-music` | Licence-clear instrumental music, looped without a seam |
| `mesh-budget` | Face counts, decimation, rigging heavy meshes |
| `asset-cleanup` | Curate the keepers, sweep the rest |

## Documentation

The site is VitePress with local search.

```sh
npm install
npm run docs:dev        # http://localhost:5173
npm run docs:build
```

It deploys to GitHub Pages on every push to `main`.

| Page | For |
|---|---|
| [Install and first run](https://xander-rudolph.github.io/game-asset-engine/guide/install) | Getting it running |
| [Make your first asset](https://xander-rudolph.github.io/game-asset-engine/guide/first-asset) | Ten minutes, end to end |
| [Facings and camera angles](https://xander-rudolph.github.io/game-asset-engine/guide/facings) | Why a sprite faces the wrong way |
| [Face counts and decimation](https://xander-rudolph.github.io/game-asset-engine/guide/decimation) | How much geometry you actually need |
| [Rigging](https://xander-rudolph.github.io/game-asset-engine/guide/rigging) | Including heavy and scanned meshes |
| [Ground and terrain](https://xander-rudolph.github.io/game-asset-engine/guide/terrain) | Tileable textures, and four ways to get seams wrong |
| [Music](https://xander-rudolph.github.io/game-asset-engine/guide/music) | Licence-clear music that loops without a seam |
| [Licensing](https://xander-rudolph.github.io/game-asset-engine/guide/licensing) | Read before shipping anything |

## Licensing, briefly

The animation sources here are all clear for commercial use. The model weights
are not uniformly so. One in particular, the best mesh generator in the stack, is
royalty free but **does not licence use in the EU, UK or South Korea**, and
rendering its output to a 2D sprite does not sidestep that.

There is a route through this pipeline with no conditions at all, and it is the
default in the walkthrough. See
[licensing](https://xander-rudolph.github.io/game-asset-engine/guide/licensing).

## Credits

This repo is scripts, prompts, documentation and glue. The capability comes from
[ComfyUI-3D-Pack](https://github.com/MrForExample/ComfyUI-3D-Pack),
[ComfyUI-UniRig](https://github.com/PozzettiAndrea/ComfyUI-UniRig) and
[ComfyUI-mesh2motion](https://github.com/jtydhr88/ComfyUI-mesh2motion), on top of
[ComfyUI](https://github.com/comfyanonymous/ComfyUI) and Blender, plus the model
authors and the CC0 animation library. Full list in [CREDITS.md](CREDITS.md).

## Requirements

A CUDA GPU. Tested on an RTX 4070 Ti SUPER (16GB) with 31GB of RAM; a 12GB card
is untested. About 200GB of disk for weights, about 28GB for the image, Docker
with the NVIDIA container toolkit. Linux.

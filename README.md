# Asset Engine

Turn a written description into a textured, rigged, animated game asset, on your
own machine.

ComfyUI in Docker with the 3D, rigging and animation node packs on top, plus the
scripts, prompt libraries, drop in workflows and Claude Code skills to drive the
whole thing from a terminal.

**[Read the guides](https://xander-rudolph.github.io/asset-engine/)**

```
"a mossy stone golem"
        |
   concept image       Qwen-Image, about 30 seconds
        |
    3D shape           Hunyuan3D or TripoSG, about a minute
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
scripts/doctor.py --fix       # checks everything, starts what it can
docker compose --profile packaged up -d
```

Then <http://localhost:8188>, or make something from the terminal:

```sh
scripts/run_workflow.py workflows/api/preset_concept_creature.json \
    --prompt "a mossy stone golem, thick moss on the shoulders"
```

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
uses. [What the numbers say](https://xander-rudolph.github.io/asset-engine/guide/decimation).

## Claude Code plugin

This repo doubles as a plugin. It ships six skills and the MCP server
definitions that go with them.

```sh
claude plugin install /path/to/asset-engine
```

| Skill | For |
|---|---|
| `asset-pipeline` | Prompt to rigged model, with a gate at every stage |
| `concept-edit` | Change one element of an approved image |
| `pose-sheet` | Sprite sheets, facing sheets, bone poses |
| `ground-texture` | Tileable terrain, and fixing seams |
| `mesh-budget` | Face counts, decimation, rigging heavy meshes |
| `asset-cleanup` | Curate the keepers, sweep the rest |

MCP keys come from the environment, never from the repo:

```sh
export MESHY_API_KEY=...
```

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
| [Install and first run](https://xander-rudolph.github.io/asset-engine/guide/install) | Getting it running |
| [Make your first asset](https://xander-rudolph.github.io/asset-engine/guide/first-asset) | Ten minutes, end to end |
| [Facings and camera angles](https://xander-rudolph.github.io/asset-engine/guide/facings) | Why a sprite faces the wrong way |
| [Face counts and decimation](https://xander-rudolph.github.io/asset-engine/guide/decimation) | How much geometry you actually need |
| [Rigging](https://xander-rudolph.github.io/asset-engine/guide/rigging) | Including heavy and scanned meshes |
| [Ground and terrain](https://xander-rudolph.github.io/asset-engine/guide/terrain) | Tileable textures, and four ways to get seams wrong |
| [Licensing](https://xander-rudolph.github.io/asset-engine/guide/licensing) | Read before shipping anything |

## Licensing, briefly

The animation sources here are all clear for commercial use. The model weights
are not uniformly so. One in particular, the best mesh generator in the stack, is
royalty free but **does not licence use in the EU, UK or South Korea**, and
rendering its output to a 2D sprite does not sidestep that.

There is a route through this pipeline with no conditions at all, and it is the
default in the walkthrough. See
[licensing](https://xander-rudolph.github.io/asset-engine/guide/licensing).

## Credits

This repo is scripts, prompts, documentation and glue. The capability comes from
[ComfyUI-3D-Pack](https://github.com/MrForExample/ComfyUI-3D-Pack),
[ComfyUI-UniRig](https://github.com/PozzettiAndrea/ComfyUI-UniRig) and
[ComfyUI-mesh2motion](https://github.com/jtydhr88/ComfyUI-mesh2motion), on top of
[ComfyUI](https://github.com/comfyanonymous/ComfyUI) and Blender, plus the model
authors and the CC0 animation library. Full list in [CREDITS.md](CREDITS.md).

## Requirements

A CUDA GPU with 12GB or more, about 200GB of disk for weights, 27GB for the
image, Docker with the NVIDIA container toolkit. Linux.
